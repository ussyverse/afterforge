"""Synthetic bounds and identity controls for correction discovery v4."""

import pytest

from agent_fix_lab.corrections import REFERENCE_END, REFERENCE_START, reference_evidence


@pytest.mark.parametrize(
    "text",
    [
        REFERENCE_START + "\nThat is wrong",  # incomplete
        REFERENCE_START + "\n" + REFERENCE_START + "\n" + REFERENCE_END,  # nested
        "quoted " + REFERENCE_START + "\nThat is wrong\n" + REFERENCE_END,
        REFERENCE_START + "\n" + "x" * 65536 + "\n" + REFERENCE_END,
    ],
)
def test_ambiguous_reference_retained(text):
    assert reference_evidence(text) == (text, 0)


def test_surrounding_speech_and_crlf():
    text = (
        "I asked for tests.\r\n"
        + REFERENCE_START
        + "\r\nold\r\n"
        + REFERENCE_END
        + "\r\nThat is wrong."
    )
    assert reference_evidence(text) == ("I asked for tests.\r\nThat is wrong.", 1)
