"""Codex client-boundary evidence v2. No request bodies/headers retained.

This module observes an already serialized, buffered HTTP request. It does not
reconstruct provider input, attest model attention, or authorize a deployment.
"""

import hashlib
import json

SCHEMA = "status-request-observation-v2"
MARKER = "Afterforge bounded status evidence, version 1"
SKILL_NAME = "afterforge-status-evidence-v1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assess(
    raw: bytes | None,
    expected_body: str,
    enabled: bool,
    *,
    complete: bool,
    model: str,
    query_sha256: str,
) -> dict:
    result = {"schema": SCHEMA, "outcome": "unknown", "reason": "unobserved-or-incomplete"}
    if not complete or not isinstance(raw, bytes) or not raw:
        return result
    try:
        request = json.loads(raw)
    except (ValueError, UnicodeError):
        return {**result, "reason": "invalid-json"}
    if not isinstance(request, dict):
        return result
    instructions = request.get("instructions")
    inputs = request.get("input")
    if (
        not isinstance(instructions, str)
        or not instructions.strip()
        or not isinstance(inputs, list)
    ):
        return {**result, "reason": "missing-instruction-or-input-field"}
    if not isinstance(request.get("model"), str):
        return {**result, "reason": "missing-model"}
    if any(
        isinstance(item, dict) and item.get("role") in ("system", "developer") for item in inputs
    ):
        return {**result, "reason": "unexpected-secondary-instruction-field"}
    user_texts = []
    for item in inputs:
        if not isinstance(item, dict) or item.get("role") != "user":
            continue
        content = item.get("content")
        if isinstance(content, str):
            user_texts.append(content)
        elif isinstance(content, list):
            parts = [
                p.get("text")
                for p in content
                if isinstance(p, dict) and p.get("type") in ("input_text", "text")
            ]
            if parts and all(isinstance(p, str) for p in parts):
                user_texts.append("".join(parts))
    if not any(sha(text.encode()) == query_sha256 for text in user_texts):
        return {**result, "reason": "task-query-identity-not-matched"}
    if request.get("model") != model:
        return {**result, "outcome": "mismatch", "reason": "model-mismatch"}
    result.update(
        request_sha256=sha(raw),
        request_bytes=len(raw),
        model=model,
        instructions_sha256=sha(instructions.encode()),
        instructions_chars=len(instructions),
        approved_body_sha256=sha(expected_body.encode()),
    )
    if not expected_body or MARKER not in expected_body:
        return {**result, "reason": "invalid-approved-body"}
    present = instructions.count(expected_body) == 1 and instructions.count(MARKER) == 1
    marker = MARKER in instructions or SKILL_NAME in instructions
    if enabled:
        return {
            **result,
            "outcome": "verified-present" if present else "mismatch",
            "reason": "complete-approved-body" if present else "approved-body-not-exact",
        }
    return {
        **result,
        "outcome": "mismatch" if marker else "verified-absent",
        "reason": "unexpected-procedure" if marker else "complete-request-without-procedure",
    }
