"""Synthetic verification-obligation controls; no model or personal history."""

import json

import pytest

from agent_fix_lab.cli import main
from agent_fix_lab.verification import assess


def evidence(status="fail", **changes):
    return {
        "revision": "synthetic-revision-2",
        "draft_kind": "success",
        "obligations": [{"id": "tests", "scope": "project"}],
        "checks": [
            {
                "sequence": 1,
                "obligation_id": "tests",
                "scope": "project",
                "revision": "synthetic-revision-2",
                "status": status,
            }
        ],
        **changes,
    }


@pytest.mark.parametrize("status", ["pass", "fail", "inconclusive", "not-run"])
def test_four_states(status):
    result = assess(evidence(status))
    assert result["verification_status"] == status
    assert result["shadow_decision"] == (
        "no-objection" if status == "pass" else "would-request-continuation"
    )
    assert not result["response_modified"] and not result["promotion_authorized"]
    assert result["behavioral_trials"] == "not-run"


@pytest.mark.parametrize(
    "change",
    [
        {"revision": "old"},
        {"scope": "other"},
        {"purpose": "baseline"},
        {"purpose": "unrelated"},
        {"obligation_id": "search"},
    ],
)
def test_unrelated_success_cannot_erase_failure(change):
    value = evidence()
    value["checks"].append({**value["checks"][0], "sequence": 2, "status": "pass", **change})
    assert assess(value)["verification_status"] == "fail"


def test_fresh_success_supersedes_failure_order_independent():
    value = evidence()
    value["checks"].insert(0, {**value["checks"][0], "sequence": 2, "status": "pass"})
    assert assess(value)["verification_status"] == "pass"
    value["revision"] = "new-edit"
    assert assess(value)["verification_status"] == "not-run"


@pytest.mark.parametrize("kind", ["blocker", "continuation", "unknown"])
def test_honest_failure_and_unknown_claim(kind):
    result = assess(evidence(draft_kind=kind))
    assert result["verification_status"] == "fail"
    assert result["shadow_decision"] == ("abstain" if kind == "unknown" else "no-objection")


def test_all_obligations_required():
    value = evidence("pass")
    value["obligations"].append({"id": "lint", "scope": "project"})
    assert assess(value)["verification_status"] == "not-run"
    assert assess(evidence(obligations=[]))["shadow_decision"] == "abstain"


@pytest.mark.parametrize(
    "change", ["duplicate-id", "duplicate-sequence", "extra", "coercion", "version"]
)
def test_invalid_input(change):
    value = evidence()
    if change == "duplicate-id":
        value["obligations"] *= 2
    elif change == "duplicate-sequence":
        value["checks"] *= 2
    elif change == "extra":
        value["activate"] = True
    elif change == "coercion":
        value["checks"][0]["sequence"] = "1"
    else:
        value["schema_version"] = 2
    with pytest.raises(ValueError):
        assess(value)


def test_cli_is_read_only_and_bounded(tmp_path, capsys):
    file = tmp_path / "synthetic.json"
    home = tmp_path / "must-not-create"
    file.write_text(json.dumps(evidence()))
    args = ["--home", str(home), "verification-shadow", "--file", str(file)]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["verification_status"] == "fail"
    assert not home.exists()
    file.write_text(" " * 262145)
    assert main(args) == 2
    assert "256 KiB" in capsys.readouterr().err
