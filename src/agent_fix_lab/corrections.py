"""Conservative correction candidates; role chronology is not identity authentication."""

import json
import re
import time
import uuid
from typing import Literal

from pydantic import Field

from .history import snapshot, validate_schema
from .models import Contract, digest


class CorrectionCandidate(Contract):
    id: str
    source_id: str
    session_id: str
    case_id: str | None
    operation: dict | None
    assistant_claim: dict | None
    user_message: dict
    selection_reason: str
    evidence_kind: Literal["inferred-candidate"] = "inferred-candidate"
    role_evidence: Literal["observed-user-role-not-authenticated"] = (
        "observed-user-role-not-authenticated"
    )
    confidence: float = Field(default=0.6, ge=0, le=1)
    review_status: Literal["pending"] = "pending"
    parser: Literal["corrections.v1", "corrections.v2"] = "corrections.v2"
    preceding_tool_ids: list[int] = Field(default_factory=list)


class CorrectionReview(Contract):
    id: str
    candidate_id: str
    decision: Literal["accepted", "rejected", "retracted"]
    reviewer_kind: Literal["operator", "human-declared", "agent"]
    note: str = Field(min_length=1, max_length=4000)
    timestamp_seconds: float
    retracts: str | None = None


MARKER = re.compile(
    r"\b(that(?:'s| is) (?:wrong|incorrect)|you (?:misunderstood|assumed)|i (?:asked|meant)|not what i|instead of|do not assume|don't assume|actually[, ]|no[, ]+you)\b",
    re.IGNORECASE,
)
CLAIM = re.compile(r"\b(done|completed|fixed|passed|implemented|verified)\b", re.IGNORECASE)


def scan(store, path, source_id, before, after=0, limit=500, after_id=0, session=None):
    if not 1 <= limit <= 10000:
        raise ValueError("limit must be between 1 and 10000")

    stats = {
        "scanned_users": 0,
        "selected": 0,
        "added": 0,
        "insufficient_evidence": 0,
        "unsupported": ["authenticated human identity", "cross-session causal pairing"],
        "parser": "corrections.v2",
        "next_cursor": {"timestamp": after, "id": after_id},
    }
    with snapshot(path) as c:
        validate_schema(c)
        for row in c.execute(
            "select id,session_id,role,substr(content,1,4000) content,timestamp "
            'from messages where role="user" and (timestamp>? or (timestamp=? and id>?)) and timestamp<? '
            "and (? is null or session_id=?) "
            "order by timestamp,id limit ?",
            (after, after, after_id, before, session, session, limit),
        ):
            stats["scanned_users"] += 1
            user = dict(row)
            stats["next_cursor"] = {"timestamp": user["timestamp"], "id": user["id"]}
            if not MARKER.search(user["content"] or ""):
                continue
            # Preserve legacy candidate IDs/reviews instead of manufacturing a second queue item.
            with store.connect() as existing:
                old = existing.execute(
                    "select id from documents where kind='correction-candidate' "
                    "and json_extract(body,'$.source_id')=? and json_extract(body,'$.session_id')=? "
                    "and json_extract(body,'$.user_message.id')=? limit 1",
                    (source_id, user["session_id"], user["id"]),
                ).fetchone()
            if old:
                stats["selected"] += 1
                continue
            # A nearby marker alone cannot establish a correction. Require an operation or claim.
            preceding = [
                dict(x)
                for x in c.execute(
                    "select id,role,substr(content,1,4000) content,timestamp from messages "
                    "where session_id=? and id<? and timestamp<=? order by id desc limit 12",
                    (user["session_id"], user["id"], user["timestamp"]),
                )
            ]
            tool_ids = [x["id"] for x in preceding if x["role"] == "tool"]
            claims = [
                x for x in preceding if x["role"] == "assistant" and (x["content"] or "").strip()
            ]
            claim = claims[0] if claims else None
            if not tool_ids and not (claim and CLAIM.search(claim["content"])):
                stats["insufficient_evidence"] += 1
                continue
            candidate = CorrectionCandidate(
                id=digest(["correction-discovery.v2", source_id, user["session_id"], user["id"]]),
                source_id=source_id,
                session_id=user["session_id"],
                case_id=None,
                operation=None,
                preceding_tool_ids=tool_ids,
                assistant_claim=claim,
                user_message=user,
                selection_reason="Correction marker after nearby tool; causal linkage unconfirmed"
                if tool_ids
                else "Correction marker after assistant completion/verification claim",
            )
            stats["selected"] += 1
            stats["added"] += store.put("correction-candidate", candidate)
    return stats


def candidates(store, status=None, *, case_id=None, offset=0, limit=100, review_offset=0):
    """SQL-bounded queue. Agent reviews never remove work from the operator queue.

    Deferred links are a projection of immutable observations, not invented history.
    Retraction-of-retraction is evaluated newest first, independently per authority.
    """
    if offset < 0 or review_offset < 0 or not 1 <= limit <= 10000:
        raise ValueError("Invalid pagination")
    sql = """
    with recursive reviews as materialized (
      select body, json_extract(body,'$.candidate_id') cid,
      row_number() over(partition by json_extract(body,'$.candidate_id') order by rowid desc) n
      from documents where kind='correction-review'
      and json_extract(body,'$.reviewer_kind') != 'agent'
    ), states(cid,n,retracted,state) as (
      select id,0,'[]','pending' from documents where kind='correction-candidate'
      union all
      select s.cid,r.n,
        case when json_extract(r.body,'$.id') not in (select value from json_each(s.retracted))
          and json_extract(r.body,'$.retracts') is not null
        then json_insert(s.retracted,'$[#]',json_extract(r.body,'$.retracts')) else s.retracted end,
        case when s.state='pending' and json_extract(r.body,'$.decision')!='retracted'
          and json_extract(r.body,'$.id') not in (select value from json_each(s.retracted))
        then json_extract(r.body,'$.decision') else s.state end
      from states s join reviews r on r.cid=s.cid and r.n=s.n+1
    ), linked as (
      select d.rowid ordinal,d.body,
        coalesce(json_extract(d.body,'$.case_id'), (
          select json_extract(o.body,'$.case_id') from documents o join documents r
          on r.kind='run' and r.id=json_extract(o.body,'$.case_id')
          where o.kind='source-observation'
          and json_extract(r.body,'$.source.source_id')=json_extract(d.body,'$.source_id')
          and json_extract(o.body,'$.session_id')=json_extract(d.body,'$.session_id')
          and json_extract(o.body,'$.message_id') in
            (select value from json_each(d.body,'$.preceding_tool_ids'))
          and json_extract(o.body,'$.observed_status')='fail'
          order by json_extract(o.body,'$.message_id') desc limit 1
        )) linked_case,
        (select state from states where cid=d.id order by n desc limit 1) state
      from documents d where kind='correction-candidate'
    ), page as (
      select * from linked where (? is null or state=?)
        and (? is null or linked_case=?) order by ordinal limit ? offset ?
    )
    select p.body,p.linked_case,p.state,r.body,
      (select json_group_array(json(h.body)) from (
       select body from documents where kind='correction-review'
       and json_extract(body,'$.candidate_id')=json_extract(p.body,'$.id')
       order by rowid limit 100 offset ?) h)
    from page p left join documents r on r.kind='run' and r.id=p.linked_case
    """
    with store.connect() as c:
        rows = c.execute(
            sql, (status, status, case_id, case_id, limit, offset, review_offset)
        ).fetchall()
    result = []
    for body, linked_case, state, run_body, history in rows:
        item = json.loads(body)
        item["case_id"] = linked_case
        if run_body and not item["operation"]:
            run = json.loads(run_body)
            item["operation"] = {
                "source_record": run["source"],
                "observed_status": run["observed_status"],
                "exit_code": run["exit_code"],
            }
        result.append(
            {
                **item,
                "effective_review_status": state,
                "reviews": json.loads(history),
                "reviews_offset": review_offset,
                "reviews_next_offset": review_offset + 100
                if len(json.loads(history)) == 100
                else None,
                "label_authority": "operator assertion; agent proposals separate; not authenticated ground truth",
            }
        )
    return result


def review(store, candidate_id, decision, note, reviewer="operator", retracts=None):
    store.get("correction-candidate", candidate_id)
    if (decision == "retracted") != bool(retracts):
        raise ValueError(
            "Retraction requires a target and only a retracted decision may target a review"
        )
    if retracts and store.get("correction-review", retracts)["candidate_id"] != candidate_id:
        raise ValueError("Review retraction must stay within one candidate")
    if (
        retracts
        and reviewer == "agent"
        and store.get("correction-review", retracts)["reviewer_kind"] != "agent"
    ):
        raise ValueError("Agent cannot retract operator review")
    record = CorrectionReview(
        id=uuid.uuid4().hex,
        candidate_id=candidate_id,
        decision=decision,
        reviewer_kind=reviewer,
        note=note,
        timestamp_seconds=time.time(),
        retracts=retracts,
    )
    store.put("correction-review", record)
    return record.model_dump()
