"""Explicit caller-reviewed bindings for passive outcomes; no inferred authority."""

from typing import Literal

from pydantic import Field

from .models import digest
from .verification import Obligation, Strict, assess


class Event(Strict):
    sequence: int = Field(ge=0)
    tool_name: str | None
    tool_call_id: str | None
    process_status: Literal["pass", "fail", "inconclusive", "not-run"]


class Capture(Strict):
    schema_version: Literal[1]
    events: list[Event] = Field(max_length=64)
    truncated: bool
    coverage: Literal["best-effort", "unavailable"]
    verification_status: Literal["inconclusive"]
    obligation_binding: Literal["not-run"]
    response_modified: Literal[False]


class Binding(Strict):
    sequence: int = Field(ge=0)
    tool_call_id: str = Field(min_length=1, max_length=128)
    obligation_id: str = Field(min_length=1, max_length=128)
    scope: str = Field(min_length=1, max_length=256)
    revision: str = Field(min_length=1, max_length=128)


class Request(Strict):
    schema_version: Literal[1] = 1
    revision: str = Field(min_length=1, max_length=128)
    draft_kind: Literal["success", "blocker", "continuation", "unknown"]
    obligations: list[Obligation] = Field(max_length=64)
    capture: Capture
    bindings: list[Binding] = Field(max_length=64)
    reviewed: Literal[True]


def bind_assess(values):
    request = Request.model_validate(values)
    events = {event.sequence: event for event in request.capture.events}
    if len(events) != len(request.capture.events):
        raise ValueError("Duplicate captured sequence")
    seen = set()
    checks = []
    obligations = {(item.id, item.scope) for item in request.obligations}
    for binding in request.bindings:
        if binding.sequence in seen:
            raise ValueError("A captured event may bind only once")
        seen.add(binding.sequence)
        if (binding.obligation_id, binding.scope) not in obligations:
            raise ValueError("Unknown obligation or scope")
        event = events.get(binding.sequence)
        if event is None or event.tool_call_id != binding.tool_call_id:
            raise ValueError("Missing or mismatched captured tool call")
        checks.append(
            {
                "sequence": binding.sequence,
                "obligation_id": binding.obligation_id,
                "scope": binding.scope,
                "revision": binding.revision,
                "status": event.process_status,
            }
        )
    result = assess(
        {
            "revision": request.revision,
            "draft_kind": request.draft_kind,
            "obligations": [item.model_dump() for item in request.obligations],
            "checks": checks,
        }
    )
    # Passive hooks can drop events on contention. No positive certification is
    # possible even when the retained, explicitly bound observations all passed.
    if result["verification_status"] == "pass":
        result["verification_status"] = "inconclusive"
        if request.draft_kind == "success":
            result["shadow_decision"] = "would-request-continuation"
    result.update(
        {
            "binding_version": 1,
            "binding_digest": digest(request.model_dump()),
            "evidence_authority": "caller-reviewed-binding",
            "capture_coverage": request.capture.coverage,
            "capture_truncated": request.capture.truncated,
            "positive_certification": False,
        }
    )
    return result
