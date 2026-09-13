"""Synthetic host callback evidence, not model behavioral trials."""

import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "capture_test", Path(__file__).resolve().parents[1] / "hermes_plugin/hooks.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Capture = module.Capture


def test_unrelated_success_preserves_failure_without_claiming_verification():
    capture = Capture()
    for code in (1, 0):
        capture.post_tool_call(
            tool_name="terminal",
            session_id="synthetic",
            result={"exit_code": code, "output": "private text"},
        )
    result = capture.process_evidence("synthetic")
    assert [event["process_status"] for event in result["events"]] == ["fail", "pass"]
    assert result["verification_status"] == "inconclusive"
    assert result["obligation_binding"] == "not-run"
    assert "private text" not in json.dumps(result)
    result["events"].clear()
    assert len(capture.process_evidence("synthetic")["events"]) == 2
    capture.on_session_end(session_id="synthetic")
    assert len(capture.process_evidence("synthetic")["events"]) == 2


def test_bounded_eviction_and_truncation():
    capture = Capture()
    for _ in range(70):
        capture.post_tool_call(tool_name="terminal", session_id="first", result={"exit_code": 0})
    result = capture.process_evidence("first")
    assert len(result["events"]) == 64 and result["truncated"]
    for index in range(33):
        capture.post_tool_call(tool_name="terminal", session_id=f"session-{index}")
    assert capture.process_evidence("first")["coverage"] == "unavailable"
    assert len(capture.outcomes) == 32


def test_contention_disabled_and_malformed_results():
    capture = Capture()
    with capture.lock:
        capture.post_tool_call(
            tool_name="terminal", session_id="synthetic", result={"exit_code": 0}
        )
    assert capture.process_evidence("synthetic")["events"] == []
    capture.enabled = False
    capture.post_tool_call(tool_name="terminal", session_id="synthetic")
    assert capture.process_evidence("synthetic")["events"] == []
    capture.enabled = True
    for result in ("bad json", {"exit_code": False}, {"exit_code": "0"}):
        capture.post_tool_call(tool_name="terminal", session_id="synthetic", result=result)
    assert all(
        e["process_status"] == "inconclusive"
        for e in capture.process_evidence("synthetic")["events"]
    )
