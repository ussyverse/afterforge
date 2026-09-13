"""Bounded, WAL-consistent Hermes SQLite import without loading SessionDB writers."""

import json
import sqlite3
import tempfile
from pathlib import Path
from contextlib import contextmanager

from .adapters import process_facts, symptoms
from .models import SourceRecord, Run, Case, digest

PARSER = "hermes.sqlite.v1"


@contextmanager
def snapshot(path):
    path = Path(path).expanduser().resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="afl-snapshot-") as directory:
        target = Path(directory) / "source.sqlite"
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as source:
            with sqlite3.connect(target) as destination:
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
    # Installed schema v26 is verified; refuse unknown future versions.
    tables = {r[0] for r in c.execute("select name from sqlite_master where type='table'")}
    if "schema_version" in tables:
        version = c.execute("select version from schema_version").fetchone()[0]
        if version != 26:
            raise ValueError(f"Unsupported Hermes schema version: {version}")
    return cols


def parse_payload(content):
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
    }
    with snapshot(path) as c:
        cols = validate_schema(c)
        sessions = {r["id"]: dict(r) for r in c.execute("select * from sessions")}

        def group(s):
            seen = set()
            while s in sessions and s not in seen:
                seen.add(s)
                p = sessions[s].get("parent_session_id")
                if not p or p not in sessions:
                    break
                s = p
            return (
                digest(sorted(seen))
                if s in seen and sessions.get(s, {}).get("parent_session_id") in seen
                else digest(s)
            )

        args = [after, before]
        where = 'role="tool" and timestamp>=? and timestamp<?'
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
            "from messages where " + where + " order by timestamp,id limit ?"
        )
        for row in c.execute(query, [*args, limit]):
            stats["scanned"] += 1
            r = dict(row)
            s = sessions.get(r["session_id"], {})
            payload, malformed = parse_payload(r["content"])
            if malformed:
                stats["non_json"] += 1
            truncated = (r["original_length"] or 0) > 65536
            if truncated:
                stats["truncated"] += 1
            code, status = process_facts(payload)
            output = str(payload.get("output", payload.get("error", r["content"] or "")))
            # Identity is stable across snapshot copies, compaction duplicates and re-imports.
            event = r.get("tool_call_id") or str(r["id"])
            identifier = digest([source_id, group(r["session_id"]), event])[:32]
            try:
                old = store.get("run", identifier)
            except KeyError:
                old = None
            if old:
                stats["duplicates"] += 1
                continue
            try:
                conf = json.loads(s.get("model_config") or "{}")
            except (TypeError, ValueError):
                conf = {}
            if not isinstance(conf, dict):
                conf = {}
            source = SourceRecord(
                id=identifier,
                source_id=source_id,
                source_revision=source_revision,
                session_id=r["session_id"],
                message_id=r["id"],
                tool_call_id=r.get("tool_call_id"),
                tool_name=r.get("tool_name"),
                timestamp_seconds=r["timestamp"],
                parent_session_id=s.get("parent_session_id"),
                delegated_from=conf.get("delegated_from")
                if isinstance(conf.get("delegated_from"), str)
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
                store.put_many([("run", run), ("case", case)])
            stats["added_cases"] += 1
    return stats
