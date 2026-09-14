"""Synthetic final-request classification; real transport contracts are in CI probe."""

import json
from collections import Counter
from pathlib import Path

import pytest

from agent_fix_lab.status_evidence import procedure
from agent_fix_lab.status_evidence_metrics import body
from agent_fix_lab.status_request_observer import MARKER, assess, sha

QUERY = "Synthetic offline status question"
BODY = body(procedure())


def request(instructions):
    return {
        "model": "gpt-5.6-luna",
        "instructions": instructions,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": QUERY}]}],
    }


def grade(payload, enabled=True, complete=True):
    raw = json.dumps(payload).encode() if isinstance(payload, dict) else payload
    return assess(
        raw,
        BODY,
        enabled,
        complete=complete,
        model="gpt-5.6-luna",
        query_sha256=sha(QUERY.encode()),
    )


def test_exact_body_and_complete_absence():
    assert grade(request("base\n" + BODY))["outcome"] == "verified-present"
    assert grade(request("base"), False)["outcome"] == "verified-absent"
    assert grade(request("base\n" + BODY), False)["outcome"] == "mismatch"


@pytest.mark.parametrize(
    "payload", [None, b"", b"{", b"null", b"[]", {}, request(None), request(""), request(" ")]
)
@pytest.mark.parametrize("enabled", [False, True])
def test_missing_partial_or_failed_observation_is_unknown(payload, enabled):
    assert grade(payload, enabled)["outcome"] == "unknown"


def test_partial_capture_never_verifies_absence():
    assert grade(request("base"), False, complete=False)["outcome"] == "unknown"


@pytest.mark.parametrize(
    "instructions",
    [MARKER, BODY.replace("eight individual", "eighty individual"), BODY + "\n" + BODY, "base"],
)
def test_marker_changed_duplicate_or_absent_candidate_mismatches(instructions):
    assert grade(request(instructions))["outcome"] == "mismatch"


def test_auxiliary_query_not_task_identity_and_model_mismatch():
    payload = request(BODY)
    payload["input"][0]["content"][0]["text"] = "Generate a title for " + QUERY
    assert grade(payload)["outcome"] == "unknown"
    payload = request(BODY)
    payload["model"] = "another-model"
    assert grade(payload)["outcome"] == "mismatch"


def test_additional_instruction_field_cannot_prove_absence():
    payload = request("base")
    payload["input"].append({"role": "system", "content": BODY})
    assert grade(payload, False)["outcome"] == "unknown"


def test_assessor_does_not_mutate_or_retain_content():
    payload = request("base\n" + BODY)
    raw = json.dumps(payload).encode()
    before = sha(raw)
    result = grade(raw)
    assert sha(raw) == before
    assert result["request_sha256"] == before
    text = json.dumps(result)
    assert QUERY not in text and BODY not in text
    assert "headers" not in result and "instructions" not in result
    assert result["approved_body_sha256"] == sha(BODY.encode())


def test_v2_protocol_inherits_only_unexecuted_order_and_frozen_behavior():
    root = Path(__file__).resolve().parents[1]
    old_path = root / "docs/experiments/status-evidence-v1-protocol.json"
    old = json.loads(old_path.read_text())
    new = json.loads((root / "docs/experiments/status-evidence-v2-protocol.json").read_text())
    assert new["parent_public_protocol_sha256"] == sha(old_path.read_bytes())
    assert new["order"] == old["order"][2:]
    assert new["attempts"] == 22 and new["scenario_count"] == 11
    for key in ("limits", "cost_gates", "grading", "procedure_sha256", "model", "reasoning"):
        assert new[key] == old[key]
    assert dict(Counter(c["category"] for c in new["cases"])) == new["category_counts"]
    assert new["category_counts"]["wrong-version"] == 1
    for relative, expected in new["implementation_sha256"].items():
        assert sha((root / relative).read_bytes()) == expected
