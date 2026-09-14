"""Synthetic reductions of inspected stock producer shapes, not trusted origins."""

import pytest

from agent_fix_lab.corrections import notification_evidence

REPORT = (
    "[IMPORTANT: Background process proc_abc123 completed normally (exit code 0).\n"
    "Command: synthetic description\nOutput:\nI asked for a check.]"
)


@pytest.mark.parametrize(
    "status",
    [
        "completed normally (exit code 0)",
        "exited (exit code -9)",
        "terminated by process.kill (exit code -15, SIGTERM)",
        "failed to start (exit code None)",
        "marked lost because the process backend disappeared (exit code ?)",
        'matched watch pattern "synthetic"',
    ],
)
def test_supported_status_shapes_are_not_attributed(status):
    text = REPORT.replace("completed normally (exit code 0)", status)
    if status.startswith("matched"):
        text = text.replace("Output:", "Matched output:")
    remaining, reason, count = notification_evidence(text)
    assert remaining == ""
    assert count == 1
    assert reason.startswith("UNCERTAIN:")
    assert "origin unavailable" in reason


@pytest.mark.parametrize(
    "surrounding",
    [
        "I asked you to fix the worker's incorrect implementation.",
        "That's wrong: the automated report overlooked the missing validation.",
        "Please start a new task: improve the navigation.",
    ],
)
@pytest.mark.parametrize("placement", ["before", "after"])
def test_surrounding_speech_is_preserved(surrounding, placement):
    text = surrounding + "\n" + REPORT if placement == "before" else REPORT + "\n" + surrounding
    remaining, reason, count = notification_evidence(text)
    assert remaining.strip() == surrounding
    assert count == 1
    assert reason.startswith("UNCERTAIN:")


def test_full_blockquote_is_not_correction_evidence():
    text = "\n".join("> " + line for line in REPORT.splitlines())
    remaining, _, count = notification_evidence(text)
    assert not remaining.strip()
    assert count == 1


@pytest.mark.parametrize(
    "text",
    [REPORT[:-1], REPORT.replace("Command:", "Invocation:"), REPORT.replace("Output:\n", "")],
)
def test_malformed_shape_stays_uncertain_without_exclusion(text):
    remaining, reason, count = notification_evidence(text)
    assert remaining == text
    assert count == 0
    assert reason.startswith("UNCERTAIN:")


def test_plain_worker_correction_is_not_suppressed():
    text = "I asked you to correct the worker output, not simply repeat its report."
    remaining, _, count = notification_evidence(text)
    assert remaining == text
    assert count == 0


def test_long_unterminated_report_is_not_excluded():
    text = REPORT[:-1] + "x" * 65536
    remaining, reason, count = notification_evidence(text)
    assert remaining == text
    assert count == 0
    assert "bound exceeded" in reason
