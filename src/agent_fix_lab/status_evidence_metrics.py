"""Trace accounting and delivery checks; no semantic-success inference from exit 0."""

import json


def body(skill: str) -> str:
    if skill.startswith("---\n"):
        return skill.split("---", 2)[2].strip()
    return skill.strip()


def delivery_evidence(system_prompt: str | None, skill: str, enabled: bool) -> dict:
    raise RuntimeError(
        "Stored-prompt delivery_evidence is retired: it cannot attest ephemeral guidance. "
        "Use status_request_observer.assess on a complete observed client request; "
        "outcomes are verified-present, verified-absent, mismatch, or unknown."
    )


def trace_metrics(rows: list[dict]) -> dict:
    operations, returned_bytes, chars, turns = [], 0, 0, 0
    for row in rows:
        calls = row.get("tool_calls")
        if calls:
            turns += 1
            calls = json.loads(calls) if isinstance(calls, str) else calls
            for call in calls:
                function = call.get("function", {})
                operations.append(function.get("name", "unknown"))
        if row.get("role") == "tool":
            content = row.get("content") or ""
            content = (
                content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            )
            chars += len(content)
            returned_bytes += len(content.encode("utf-8"))
    return {
        "individual_operations": len(operations),
        "search_operations": operations.count("search_files"),
        "read_operations": operations.count("read_file"),
        "terminal_operations": operations.count("terminal"),
        "other_operations": sum(
            n not in ("search_files", "read_file", "terminal") for n in operations
        ),
        "tool_calling_turns": turns,
        "returned_context_chars": chars,
        "returned_context_utf8_bytes": returned_bytes,
        "context_measure": "retained tool-result payloads including envelopes, not model token count",
    }
