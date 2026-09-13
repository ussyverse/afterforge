"""Conservative correction candidates; role chronology is not identity authentication."""

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
    parser: Literal["corrections.v1"] = "corrections.v1"


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


def scan(store, path, source_id, before, after=0, limit=500):
    if not 1 <= limit <= 10000:
        raise ValueError("limit must be between 1 and 10000")
    runs = [r for r in store.all("run") if r["source"]["source_id"] == source_id]
    stats = {
        "scanned_users": 0,
        "selected": 0,
        "added": 0,
        "insufficient_evidence": 0,
        "unsupported": ["authenticated human identity", "cross-session causal pairing"],
        "parser": "corrections.v1",
    }
    with snapshot(path) as c:
        validate_schema(c)
        for row in c.execute(
            "select id,session_id,role,substr(content,1,4000) content,timestamp "
            'from messages where role="user" and timestamp>=? and timestamp<? '
            "order by timestamp,id limit ?",
            (after, before, limit),
        ):
            stats["scanned_users"] += 1
            user = dict(row)
            if not MARKER.search(user["content"] or ""):
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
            ids = {x["id"] for x in preceding}
            failed = [
                r
                for r in runs
                if r["observed_status"] == "fail"
                and r["source"]["session_id"] == user["session_id"]
                and r["source"]["message_id"] in ids
            ]
            operation = max(failed, key=lambda r: r["source"]["message_id"]) if failed else None
            claims = [
                x for x in preceding if x["role"] == "assistant" and (x["content"] or "").strip()
            ]
            claim = claims[0] if claims else None
            if not operation and not (claim and CLAIM.search(claim["content"])):
                stats["insufficient_evidence"] += 1
                continue
            candidate = CorrectionCandidate(
                id=digest([source_id, user["id"], operation["id"] if operation else claim["id"]]),
                source_id=source_id,
                session_id=user["session_id"],
                case_id=operation["id"] if operation else None,
                operation={
                    "source_record": operation["source"],
                    "observed_status": operation["observed_status"],
                    "exit_code": operation["exit_code"],
                }
                if operation
                else None,
                assistant_claim=claim,
                user_message=user,
                selection_reason="Correction marker after nearby failed operation"
                if operation
                else "Correction marker after assistant completion/verification claim",
            )
            stats["selected"] += 1
            stats["added"] += store.put("correction-candidate", candidate)
    return stats


def candidates(store, status=None):
    result = []
    reviews = store.all("correction-review")
    for candidate in store.all("correction-candidate"):
        history = [r for r in reviews if r["candidate_id"] == candidate["id"]]
        retracted = set()
        for r in reversed(history):
            if r["id"] not in retracted and r["retracts"]:
                retracted.add(r["retracts"])
        effective = [
            r for r in history if r["id"] not in retracted and r["decision"] != "retracted"
        ]
        state = effective[-1]["decision"] if effective else "pending"
        if not status or status == state:
            result.append(
                {
                    **candidate,
                    "effective_review_status": state,
                    "reviews": history,
                    "label_authority": "reviewer assertion; not authenticated ground truth",
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
