"""Synthetic observer payloads matching inspected stock host API."""

from pathlib import Path

import pytest
from test_plugin import Context, Runtime


@pytest.mark.parametrize(
    "fields,expected",
    [
        ({"status": "error"}, "fail"),
        ({"status": "blocked"}, "fail"),
        ({"error_type": "tool_error"}, "fail"),
        ({"status": "ok"}, "inconclusive"),
        ({"status": "future-value"}, "inconclusive"),
    ],
)
def test_structured_host_status(fields, expected):
    runtime = Runtime(Context(), Path(__file__).resolve().parents[1])
    runtime.capture.post_tool_call(
        tool_name="terminal", result="x" * 5000, session_id="synthetic", **fields
    )
    assert runtime.capture.process_evidence("synthetic")["events"][0]["process_status"] == expected
    assert "x" * 20 not in str(runtime.capture.snapshot())
