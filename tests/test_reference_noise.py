"""Synthetic reference envelopes and repeated observations; no personal history."""

import sqlite3

import pytest

from agent_fix_lab import corrections

START = "[CONTEXT COMPACTION — REFERENCE ONLY]"
END = "--- END OF CONTEXT SUMMARY — respond to the message below, not the summary above ---"


@pytest.mark.parametrize("speech", ["", "That is wrong; I asked for actual tests."])
def test_complete_reference_preserves_speech(lab, history, speech):
    text = START + "\nSynthetic historical text: that is wrong\n" + END + "\n" + speech
    with sqlite3.connect(history) as c:
        c.execute('insert into messages values(7,"s","assistant","Completed",null,null,7,1,0)')
        c.execute('insert into messages values(8,"s","user",?,null,null,8,1,0)', (text,))
    result = corrections.scan(lab.store, history, "synthetic", 10)
    assert result["added"] == bool(speech)
    if speech:
        assert corrections.candidates(lab.store)[0]["user_message"]["content"] == text


@pytest.mark.parametrize(
    "text", [START + "\nThat is wrong", "I asked you to finish, not plan.", "That is wrong\n" + END]
)
def test_incomplete_or_ordinary_correction_survives(lab, history, text):
    with sqlite3.connect(history) as c:
        c.execute('insert into messages values(7,"s","assistant","Completed",null,null,7,1,0)')
        c.execute('insert into messages values(8,"s","user",?,null,null,8,1,0)', (text,))
    assert corrections.scan(lab.store, history, "synthetic", 10)["added"] == 1


def test_exact_repeat_does_not_multiply_queue(lab, history):
    with sqlite3.connect(history) as c:
        c.execute('insert into messages values(7,"s","assistant","Completed",null,null,7,1,0)')
        for i in (8, 9):
            c.execute(
                'insert into messages values(?,"s","user","That is wrong",null,null,8,1,0)', (i,)
            )
    assert corrections.scan(lab.store, history, "synthetic", 10, after=7, limit=1)["added"] == 1
    assert corrections.scan(lab.store, history, "synthetic", 10, after=8, after_id=8)["added"] == 0
    assert corrections.scan(lab.store, history, "independent-source", 10)["added"] == 1
