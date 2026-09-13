"""Pure, versioned shadow assessment of caller-declared verification evidence.

No transcript parsing, command execution, host hooks or response modification.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import digest


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Obligation(Strict):
    id: str = Field(min_length=1, max_length=128)
    scope: str = Field(min_length=1, max_length=256)


class Check(Strict):
    sequence: int = Field(ge=0)
    obligation_id: str = Field(min_length=1, max_length=128)
    scope: str = Field(min_length=1, max_length=256)
    revision: str = Field(min_length=1, max_length=128)
    status: Literal["pass", "fail", "inconclusive", "not-run"]
    purpose: Literal["required", "baseline", "unrelated"] = "required"


class Evidence(Strict):
    schema_version: Literal[1] = 1
    revision: str = Field(min_length=1, max_length=128)
    draft_kind: Literal["success", "blocker", "continuation", "unknown"]
    obligations: list[Obligation] = Field(max_length=64)
    checks: list[Check] = Field(max_length=512)


def assess(values):
    evidence = Evidence.model_validate(values)
    ids = [item.id for item in evidence.obligations]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate obligation IDs")
    sequences = [item.sequence for item in evidence.checks]
    if len(set(sequences)) != len(sequences):
        raise ValueError("Duplicate check sequence numbers")
    results = []
    for obligation in evidence.obligations:
        matching = [
            check
            for check in evidence.checks
            if check.obligation_id == obligation.id
            and check.scope == obligation.scope
            and check.revision == evidence.revision
            and check.purpose == "required"
        ]
        latest = max(matching, key=lambda check: check.sequence) if matching else None
        results.append(
            {
                "obligation_id": obligation.id,
                "status": latest.status if latest else "not-run",
                "sequence": latest.sequence if latest else None,
            }
        )
    statuses = {item["status"] for item in results}
    status = (
        "fail"
        if "fail" in statuses
        else "inconclusive"
        if "inconclusive" in statuses
        else "not-run"
        if not statuses or "not-run" in statuses
        else "pass"
    )
    if evidence.draft_kind in ("blocker", "continuation"):
        decision = "no-objection"
    elif evidence.draft_kind == "unknown" or not results:
        decision = "abstain"
    else:
        decision = "no-objection" if status == "pass" else "would-request-continuation"
    return {
        "schema_version": 1,
        "policy_version": "verification-shadow-v1",
        "input_digest": digest(evidence.model_dump()),
        "verification_status": status,
        "obligations": results,
        "shadow_decision": decision,
        "mode": "shadow",
        "evidence_authority": "caller-declared",
        "behavioral_trials": "not-run",
        "response_modified": False,
        "promotion_authorized": False,
    }
