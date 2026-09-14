"""Bounded, WAL-consistent Hermes SQLite import without loading SessionDB writers."""

import json
import math
import sqlite3
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path

from .adapters import process_facts, symptoms
from .models import Case, Run, SourceRecord, digest

PARSER = "hermes.sqlite.v4"


def reconcile_legacy_identity(legacy, candidates, *, reviewed=False, reviewer=None):
    """Return an append-only reconciliation document; never mutate either input.

    Coordinator supplies a bounded, source-scoped page of fresh v4 Runs and
    persists this document separately. Only the EXACT surviving original
    observation can link. A legacy global-call merge may have lost other roots:
    this links the retained observation, NOT the old case's annotations, split,
    corrections or recurrence count. Lost observations remain unknown and must
    be reimported from source; never synthesize a split from a call ID.
    No match on a partial page is unresolved, not proof of absence.
    """
    legacy = Run.model_validate(legacy)
    if legacy.source.parser not in {"hermes.sqlite.v1", "hermes.sqlite.v2", "hermes.sqlite.v3"}:
        raise ValueError("Expected a legacy Hermes run")
    if len(candidates) > 10000:
        raise ValueError("Reconciliation page exceeds 10000 runs")
    if reviewed and (not reviewer or not reviewer.strip()):
        raise ValueError("Explicit reconciliation review requires reviewer attribution")
    fields = (
        "source_id",
        "session_id",
        "message_id",
        "tool_call_id",
        "tool_name",
        "payload_digest",
    )
    matches = set()
    for value in candidates:
        candidate = Run.model_validate(value)
        if candidate.source.parser != PARSER:
            raise ValueError("Reconciliation candidates must use current parser")
        if all(
            getattr(candidate.source, field) == getattr(legacy.source, field) for field in fields
        ):
            matches.add(candidate.id)
    status = "linked-observation" if len(matches) == 1 and reviewed else "unresolved"
    body = {
        "schema_version": 1,
        "strategy": "legacy-exact-observation.v1",
        "legacy_run_id": legacy.id,
        "legacy_digest": digest(legacy.model_dump()),
        "candidate_ids": sorted(matches),
        "status": status,
        "reviewer": reviewer if reviewed else None,
        "canonical_run_id": next(iter(matches)) if status == "linked-observation" else None,
        "unknown": ["discarded_legacy_observations", "annotation_and_split_applicability"],
        "transfers_case_authority": False,
    }
    return {"id": digest(body), **body}


@contextmanager
def snapshot(path):
    path = Path(path).expanduser().resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="afl-snapshot-") as directory:
        target = Path(directory) / "source.sqlite"
        with (
            closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as source,
            closing(sqlite3.connect(target)) as destination,
        ):
            source.backup(destination, pages=256)
        c = sqlite3.connect(target.as_uri() + "?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
        try:
            if c.execute("pragma quick_check").fetchone()[0] != "ok":
                raise ValueError("Source snapshot integrity failure")
            yield c
        finally:
            c.close()


def validate_schema(c):
    cols = {r["name"] for r in c.execute("pragma table_info(messages)")}
    if not {"id", "session_id", "role", "content", "timestamp"}.issubset(cols):
        raise ValueError("Unsupported Hermes messages schema")
    if not {"id", "parent_session_id"}.issubset(
        {r["name"] for r in c.execute("pragma table_info(sessions)")}
    ):
        raise ValueError("Unsupported Hermes sessions schema")
    # Pinned stock hosts use v26/v30 with the required columns checked above.
    # Refuse other versions rather than assuming future schema compatibility.
    tables = {r[0] for r in c.execute("select name from sqlite_master where type='table'")}
    if "schema_version" not in tables:
        raise ValueError("Unsupported Hermes schema: missing explicit schema_version")
    if "schema_version" in tables:
        versions = c.execute("select version from schema_version").fetchall()
        if len(versions) != 1:
            raise ValueError("Unsupported Hermes schema: ambiguous or missing version row")
        version = versions[0][0]
        if version not in (26, 30):
            raise ValueError(f"Unsupported Hermes schema version: {version}")
    return cols


def parse_payload(content):
    # Decode only a complete JSON object inside the known Hermes envelope.
    if isinstance(content, str) and content.startswith("<untrusted_tool_result "):
        start = content.find("\n{")
        end = content.rfind("\n</untrusted_tool_result>")
        if start >= 0 and end > start:
            content = content[start + 1 : end]
    try:
        payload = json.loads(content or "")
    except (ValueError, TypeError):
        return {"output": content or ""}, "non-json"
    if not isinstance(payload, dict):
        return {"output": content or ""}, "non-object"
    return payload, None


def import_hermes(
    store,
    path,
    *,
    source_id,
    before,
    after=0,
    after_id=0,
    session=None,
    limit=500,
    dry_run=False,
    cohort="historical",
    selection=None,
    source_revision=None,
):
    if not 1 <= limit <= 10000:
        raise ValueError("limit must be between 1 and 10000")
    stats = {
        "scanned": 0,
        "added_cases": 0,
        "duplicates": 0,
        "malformed": 0,
        "non_json": 0,
        "truncated": 0,
        "dry_run": dry_run,
        "parser": PARSER,
        "next_after_id": after_id,
    }
    with snapshot(path) as c:
        cols = validate_schema(c)
        session_cols = {r["name"] for r in c.execute("pragma table_info(sessions)")}
        selected_cols = sorted(
            session_cols & {"id", "parent_session_id", "model_config", "archived"}
        )
        sessions = {
            r["id"]: dict(r)
            for r in c.execute("select " + ",".join(selected_cols) + " from sessions")
        }
        for entry in sessions.values():
            try:
                config = json.loads(entry.get("model_config") or "{}")
            except (ValueError, TypeError):
                config = {}
            entry["delegated_from"] = (
                (config.get("_delegate_from") or config.get("delegated_from"))
                if isinstance(config, dict)
                else None
            )

        def group(s):
            seen = []
            while s in sessions:
                if s in seen:
                    # Only cycle members determine identity, not the entry path.
                    return digest(["cycle", sorted(seen[seen.index(s) :])])
                seen.append(s)
                p = sessions[s].get("parent_session_id") or sessions[s].get("delegated_from")
                if not isinstance(p, str) or not p:
                    break
                s = p
            return digest(s)

        args = [after, before, after_id]
        where = 'role="tool" and timestamp>=? and timestamp<? and id>?'
        if session:
            where += " and session_id=?"
            args.append(session)
        if selection is not None:
            ids = list(selection)
            if not ids:
                return stats
            where += " and id in (" + ",".join("?" for _ in ids) + ")"
            args.extend(ids)
        # Avoid fetching unlimited blobs. Oversized records remain explicitly incomplete.
        projections = [
            "substr(content,1,65536) as content" if x == "content" else x
            for x in sorted(cols)
            if x
            not in {
                "reasoning",
                "reasoning_content",
                "reasoning_details",
                "codex_reasoning_items",
                "codex_message_items",
                "api_content",
                "tool_calls",
            }
        ]
        query = (
            "select " + ",".join(projections) + ",length(content) as original_length "
            "from messages where " + where + " order by id limit ?"
        )
        for row in c.execute(query, [*args, limit]):
            stats["scanned"] += 1
            r = dict(row)
            stats["next_after_id"] = r["id"]
            if (
                r["session_id"] not in sessions
                or not isinstance(r["timestamp"], (int, float))
                or not math.isfinite(r["timestamp"])
            ):
                stats["malformed"] += 1
                continue
            s = sessions.get(r["session_id"], {})
            payload, malformed = parse_payload(r["content"])
            if malformed:
                stats["non_json"] += 1
            truncated = (r["original_length"] or 0) > 65536
            if truncated:
                stats["truncated"] += 1
            code, status = process_facts(payload)
            output = str(payload.get("output", payload.get("error", r["content"] or "")))
            # Calls are only scoped within explicit lineage, never across source roots.
            # Different observed bytes are separate evidence, not a successful overwrite.
            # Missing calls cannot establish compaction equivalence.
            event = (
                ["call", r["tool_call_id"]]
                if r.get("tool_call_id") and not truncated
                else ["message", r["session_id"], r["id"]]
            )
            identifier = digest(
                [
                    PARSER,
                    source_id,
                    group(r["session_id"]),
                    event,
                    r.get("tool_name"),
                    digest(r["content"]),
                ]
            )[:32]
            observation = {
                "schema_version": 1,
                "id": digest(
                    [
                        PARSER,
                        source_id,
                        r["id"],
                        r.get("active", 1),
                        r.get("compacted", 0),
                        digest(r["content"]),
                    ]
                ),
                "case_id": identifier,
                "message_id": r["id"],
                "session_id": r["session_id"],
                "parser": PARSER,
                "active": bool(r.get("active", 1)),
                "compacted": bool(r.get("compacted", 0)),
                "archived": bool(s.get("archived", 0)),
                "payload_digest": digest(r["content"]),
                "timestamp_seconds": r["timestamp"],
                "output": output[:65536],
                "exit_code": code,
                "observed_status": status,
            }
            try:
                old = store.get("run", identifier)
            except KeyError:
                old = None
            if old:
                stats["duplicates"] += 1
                if not dry_run:
                    store.put("source-observation", observation)
                continue
            try:
                conf = json.loads(s.get("model_config") or "{}")
            except (TypeError, ValueError):
                conf = {}
            if not isinstance(conf, dict):
                conf = {}
            source = SourceRecord(
                id=identifier,
                parser=PARSER,
                source_id=source_id,
                source_revision=source_revision,
                session_id=r["session_id"],
                message_id=r["id"],
                tool_call_id=r.get("tool_call_id"),
                tool_name=r.get("tool_name"),
                timestamp_seconds=r["timestamp"],
                parent_session_id=s.get("parent_session_id"),
                delegated_from=s.get("delegated_from")
                if isinstance(s.get("delegated_from"), str)
                else None,
                active=bool(r.get("active", 1)),
                compacted=bool(r.get("compacted", 0)),
                archived=bool(s.get("archived", 0)),
                payload_digest=digest(r["content"]),
            )
            context = [
                dict(x)
                for x in c.execute(
                    "select id,role,substr(content,1,2000) as content from messages "
                    "where session_id=? and id<? order by id desc limit 2",
                    (r["session_id"], r["id"]),
                )
            ]
            run = Run(
                id=identifier,
                source=source,
                observed_status=status,
                exit_code=code,
                output=output[:65536],
                symptoms=symptoms(output[:65536]),
                context=context,
            )
            missing = list(run.unknown)
            if code is None:
                missing.append("exit_code")
            if truncated:
                missing.append("full_output")
            run = run.model_copy(update={"unknown": missing})
            sel = (selection or {}).get(r["id"], {})
            case = Case(
                id=identifier,
                run_id=identifier,
                incident_group=digest(sel.get("group", group(r["session_id"]))),
                split=sel.get("split", "unassigned"),
                cohort=cohort,
            )
            if not dry_run:
                store.put_many([("run", run), ("case", case), ("source-observation", observation)])
            stats["added_cases"] += 1
    return stats
