"""Synthetic reminder lifecycle contracts, not an efficacy benchmark."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "policy_test", Path(__file__).resolve().parents[1] / "hermes_plugin/policy.py"
)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def test_approval_restart_and_rollback(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    root = tmp_path / "state"
    item = policy.candidate(str(project))
    assert policy.evaluate(item)["status"] == "pass"
    payload = {"coding": True, "attempt": 0, "changed_paths": [str(project / "a.py")]}
    assert policy.hook(root, **payload) is None
    with pytest.raises(ValueError):
        policy.transition(root, "activate", 0, item, "unapproved")
    state = policy.transition(root, "activate", 0, item, policy.digest(item))
    assert state["generation"] == 1
    assert policy.hook(root, **payload)["action"] == "continue"
    # Every hook reloads persisted state rather than relying on process-local approval.
    assert policy.read(root)["active"]["digest"] == policy.digest(item)
    assert policy.hook(root, **{**payload, "attempt": 1}) is None
    with pytest.raises(ValueError):
        policy.transition(root, "rollback", 0)
    policy.transition(root, "rollback", 1)
    assert policy.hook(root, **payload) is None


def test_untrusted_message_and_scope_rejected(tmp_path):
    item = policy.candidate(str(tmp_path))
    item["message"] = "arbitrary instructions"
    with pytest.raises(ValueError):
        policy.transition(tmp_path / "state", "activate", 0, item, policy.digest(item))
    assert policy.directive(item, coding=True, changed_paths=[str(tmp_path / "a.py")]) is None
    with pytest.raises(ValueError):
        policy.candidate("relative")


def test_corrupt_state_abstains(tmp_path):
    (tmp_path / "lifecycle.json").write_text("invalid")
    assert policy.hook(tmp_path, coding=True, changed_paths=["/synthetic.py"]) is None
