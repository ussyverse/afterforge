"""Synthetic release regressions; no host or historical data required."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_plugin import Context, Runtime, plugin


def test_outcomes_bound_independently_of_pending():
    capture = Runtime(Context(), None).capture
    for index in range(100):
        capture.record(f"session-{index}")
        # Reproduce successful scan draining hints while retaining evidence.
        with capture.lock:
            capture.pending.clear()
    assert len(capture.outcomes) == 32


def test_capture_cleanup_preserves_newer_callback():
    capture = Runtime(Context(), None).capture
    capture.record("session")
    completed = capture.snapshot()
    capture.record("session", status="fail")
    capture.complete(completed)
    assert capture.snapshot()["session"]["status"] == "fail"
    capture.complete(capture.snapshot())
    assert capture.snapshot() == {}
    assert len(capture.process_evidence("session")["events"]) == 2


def test_outcomes_use_write_recency():
    capture = Runtime(Context(), None).capture
    for index in range(32):
        capture.record(f"s{index}")
    capture.record("s0")
    capture.record("new")
    assert capture.process_evidence("s0")["events"]
    assert not capture.process_evidence("s1")["events"]


def test_capture_concurrent_acknowledgement_and_snapshots():
    capture = Runtime(Context(), None).capture

    def worker(index):
        for _ in range(100):
            capture.record(f"s{index}")
            snapshot = capture.snapshot()
            capture.complete(snapshot)
            evidence = capture.process_evidence(f"s{index}")
            assert len(evidence["events"]) <= 64
            assert evidence["verification_status"] == "inconclusive"

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(worker, range(40)))
    assert len(capture.outcomes) <= 32
    assert len(capture.snapshot()) <= 32


def test_capture_generation_survives_identical_clock(monkeypatch):
    capture = Runtime(Context(), None).capture
    monkeypatch.setattr("time.time", lambda: 1)
    capture.record("session", ended=True)
    completed = capture.snapshot()
    capture.record("session", ended=True)
    capture.complete(completed)
    assert capture.snapshot()


@pytest.mark.parametrize(
    "response",
    [
        {"success": False, "error": {"message": "Run setup"}},
        {"success": True, "data": {"status": "inconclusive"}},
        {"success": True, "data": {"status": "fail"}},
    ],
)
def test_registered_terminal_verification_nonzero(monkeypatch, capsys, response):
    ctx = Context()
    plugin.register(ctx)
    monkeypatch.setattr(Runtime, "ready", lambda self: True)
    monkeypatch.setattr(Runtime, "root", lambda self: plugin.Path("."))
    monkeypatch.setattr(Runtime, "invoke", lambda *a, **k: response)
    parser = argparse.ArgumentParser()
    ctx.cli["setup_fn"](parser)
    args = parser.parse_args(["verify-current", "a" * 32, "--approve-digest", "b" * 64])
    with pytest.raises(SystemExit) as error:
        ctx.cli["handler_fn"](args)
    assert error.value.code == 1
    assert json.loads(capsys.readouterr().out) == response
