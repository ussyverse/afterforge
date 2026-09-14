"""Synthetic current-check execution tests; no private histories or inference."""

import json
from pathlib import Path

import pytest

from agent_fix_lab import current_check
from agent_fix_lab.cli import main
from agent_fix_lab.models import digest


def register(lab, regression):
    return lab.add_recipe({**regression, "case_id": lab.list_cases()[0]["id"]}, reviewed=True)


def test_current_check_cli_executes(lab, regression, capsys):
    recipe = register(lab, regression)
    prefix = ["--home", str(lab.store.root)]
    assert main([*prefix, "current-check-plan", recipe["id"]]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["status"] == "not-run"
    assert (
        main([*prefix, "verify-current", recipe["id"], "--approve-digest", plan["recipe_digest"]])
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "pass"
    assert receipt["revision"] == regression["corrected_revision"]
    assert lab.store.get("result", receipt["result_id"])["status"] == "pass"
    assert receipt["live_environment_verified"] is False


def test_current_check_rejects_without_execution(lab, regression, monkeypatch):
    recipe = register(lab, regression)

    def forbidden(*args):
        pytest.fail("unapproved or dirty code executed")

    monkeypatch.setattr(current_check, "execute", forbidden)
    with pytest.raises(ValueError, match="approval"):
        current_check.verify(lab, recipe["id"], "wrong")
    (Path(regression["repository"]) / "untracked.py").write_text("# synthetic")
    with pytest.raises(ValueError, match="clean"):
        current_check.verify(lab, recipe["id"], digest(recipe))
    assert not lab.store.all("current-check-authorization")


def test_change_during_check_is_inconclusive(lab, regression, monkeypatch):
    recipe = register(lab, regression)
    original = current_check.execute

    def changing(*args):
        result = original(*args)
        (Path(regression["repository"]) / "implementation.py").write_text("# changed during check")
        return result

    monkeypatch.setattr(current_check, "execute", changing)
    receipt = current_check.verify(lab, recipe["id"], digest(recipe))
    assert receipt["observed_status"] == "pass"
    assert receipt["status"] == "inconclusive"
    assert receipt["checkout_unchanged_at_endpoints"] is False
