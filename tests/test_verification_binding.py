"""Synthetic callback-to-shadow binding contracts."""

import importlib.util
import json
from pathlib import Path

import pytest

from agent_fix_lab.cli import main
from agent_fix_lab.verification_binding import bind_assess


@pytest.fixture
def request_data():
    spec = importlib.util.spec_from_file_location(
        "binding_capture", Path(__file__).resolve().parents[1] / "hermes_plugin/hooks.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    capture = module.Capture()
    capture.post_tool_call(
        tool_name="terminal",
        session_id="synthetic",
        tool_call_id="test-call",
        result={"exit_code": 1},
    )
    capture.post_tool_call(
        tool_name="terminal",
        session_id="synthetic",
        tool_call_id="search-call",
        result={"exit_code": 0},
    )
    return {
        "revision": "synthetic-v2",
        "draft_kind": "success",
        "reviewed": True,
        "obligations": [{"id": "tests", "scope": "project"}],
        "capture": capture.process_evidence("synthetic"),
        "bindings": [
            {
                "sequence": 1,
                "tool_call_id": "test-call",
                "obligation_id": "tests",
                "scope": "project",
                "revision": "synthetic-v2",
            }
        ],
    }


def test_real_callback_binding_and_cli(request_data, tmp_path, capsys):
    result = bind_assess(request_data)
    assert result["verification_status"] == "fail"
    assert result["shadow_decision"] == "would-request-continuation"
    file = tmp_path / "synthetic.json"
    file.write_text(json.dumps(request_data))
    assert main(["verification-shadow", "--captured-bindings", "--file", str(file)]) == 0
    assert json.loads(capsys.readouterr().out) == result


@pytest.mark.parametrize("change", ["call", "sequence", "scope", "duplicate", "review"])
def test_rejected_binding(request_data, change):
    binding = request_data["bindings"][0]
    if change == "call":
        binding["tool_call_id"] = "search-call"
    elif change == "sequence":
        binding["sequence"] = 99
    elif change == "scope":
        binding["scope"] = "other"
    elif change == "duplicate":
        request_data["bindings"] *= 2
    else:
        request_data["reviewed"] = False
    with pytest.raises(ValueError):
        bind_assess(request_data)


@pytest.mark.parametrize("truncated", [False, True])
def test_best_effort_never_certifies_success(request_data, truncated):
    request_data["capture"]["events"][0]["process_status"] = "pass"
    request_data["capture"]["truncated"] = truncated
    result = bind_assess(request_data)
    assert result["verification_status"] == "inconclusive"
    assert not result["positive_certification"]
    assert not result["response_modified"]


def test_stale_revision_and_blocker(request_data):
    request_data["bindings"][0]["revision"] = "old"
    assert bind_assess(request_data)["verification_status"] == "not-run"
    request_data["draft_kind"] = "blocker"
    assert bind_assess(request_data)["shadow_decision"] == "no-objection"
