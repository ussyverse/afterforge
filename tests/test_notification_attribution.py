"""Synthetic notification reductions; never execute embedded report text."""

import sqlite3

import pytest

from agent_fix_lab import corrections
from agent_fix_lab.store import Store


@pytest.fixture
def history(tmp_path):
    """Self-contained synthetic source, also usable as a frozen retained regression."""
    path = tmp_path / "history.sqlite"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
        create table schema_version(version integer);
        insert into schema_version values(26);
        create table sessions(id text primary key,parent_session_id text,model_config text,
            archived integer);
        create table messages(id integer primary key,session_id text,role text,content text,
            tool_call_id text,tool_name text,timestamp real,active integer,compacted integer);
        insert into sessions values('s',null,'{}',0);
        insert into messages values(6,'s','assistant','I verified the build',null,null,6,1,0);
        """)
    return path


def add_message(history, content):
    with sqlite3.connect(history) as conn:
        conn.execute(
            "insert into messages values(?,?,?,?,?,?,?,?,?)",
            (7, "s", "user", content, None, None, 8, 1, 0),
        )


@pytest.mark.parametrize("status", ["completed normally (exit code 0)", "exited (exit code -9)"])
def test_notification_marker_is_not_selected(history, tmp_path, status):
    add_message(
        history,
        f"[IMPORTANT: Background process proc_abc123 {status}.\n"
        "Command: synthetic non-executable description\n"
        "Output:\nI asked for a check; actually, all checks passed.\n]",
    )
    store = Store(tmp_path / "notifications")
    stats = corrections.scan(store, history, "synthetic", 10)
    assert stats["selected"] == 0, "notification report must not become a correction"
    assert store.all("correction-candidate") == []
    assert stats["excluded_notification_like"] == 1
    assert stats["next_cursor"] == {"timestamp": 8.0, "id": 7}
    assert stats["parser"] == "corrections.v4"


@pytest.mark.parametrize(
    "content",
    [
        "I asked you to build a dashboard, not stop after inspection.",
        "I asked for this; the build completed and passed; thank you.",
        (
            "I asked about this quoted report: [IMPORTANT: Background process proc_abc123 "
            "completed normally (exit code 0).\nOutput: done]"
        ),
        "[IMPORTANT: Background process discussion] I asked for a check.",
        None,
    ],
)
def test_narrow_filter_controls(history, tmp_path, content):
    add_message(history, content)
    store = Store(tmp_path / "controls")
    stats = corrections.scan(store, history, "synthetic", 10)
    assert stats["selected"] == (0 if content is None else 1)


def test_legacy_notification_and_review_remain_immutable(history, tmp_path):
    content = (
        "[IMPORTANT: Background process proc_abc123 completed normally (exit code 0).\n"
        "Command: synthetic\nOutput:\nI asked for a check.\n]"
    )
    add_message(history, content)
    store = Store(tmp_path / "legacy")
    candidate = corrections.CorrectionCandidate(
        id="legacy-synthetic",
        source_id="synthetic",
        session_id="s",
        case_id=None,
        operation=None,
        assistant_claim=None,
        user_message={"id": 7, "content": content},
        selection_reason="Synthetic legacy marker",
        parser="corrections.v2",
    )
    store.put("correction-candidate", candidate)
    corrections.review(store, candidate.id, "accepted", "Synthetic prior operator declaration")
    originals = store.all("correction-candidate"), store.all("correction-review")
    stats = corrections.scan(store, history, "synthetic", 10)
    assert stats["added"] == 0
    assert (store.all("correction-candidate"), store.all("correction-review")) == originals
    assert corrections.candidates(store, "accepted")[0]["id"] == candidate.id
    assert stats["selected"] == 0, "legacy retention must not endorse notification attribution"


def test_parser_versions_explicit():
    fields = {
        "id": "synthetic",
        "source_id": "synthetic",
        "session_id": "s",
        "case_id": None,
        "operation": None,
        "assistant_claim": None,
        "user_message": {},
        "selection_reason": "Synthetic",
    }
    for version in ("corrections.v1", "corrections.v2", "corrections.v3", "corrections.v4"):
        assert corrections.CorrectionCandidate(**fields, parser=version).parser == version
    with pytest.raises(ValueError):
        corrections.CorrectionCandidate(**fields, parser="corrections.v5")


@pytest.mark.parametrize(
    "speech,selected",
    [
        ("That's wrong: the worker skipped validation.", 1),
        ("I asked you to fix the worker output, not repeat it.", 1),
        ("Please start a new task: improve the navigation.", 0),
        ("", 0),
    ],
)
def test_full_quoted_report_then_surrounding_speech(history, tmp_path, speech, selected):
    content = (
        "> [IMPORTANT: Background process proc_abc123 completed normally (exit code 0).\n"
        "> Command: synthetic\n> Output:\n> [synthetic truncation marker]\n"
        "> I asked for a check.]\n" + speech
    )
    add_message(history, content)
    store = Store(tmp_path / "quoted")
    stats = corrections.scan(store, history, "synthetic", 10)
    assert stats["selected"] == selected
    assert stats["excluded_attributed_notification"] == 0
    assert stats["uncertain_notification_rows"] == 1
    if selected:
        candidate = store.all("correction-candidate")[0]
        assert candidate["user_message"]["content"] == content
        assert "UNCERTAIN" in candidate["selection_reason"]
        corrections.review(store, candidate["id"], "accepted", "Synthetic review")
        review = store.all("correction-review")[0]
        corrections.review(
            store, candidate["id"], "retracted", "Synthetic retraction", retracts=review["id"]
        )
        before = store.all("correction-candidate"), store.all("correction-review")
        assert corrections.scan(store, history, "synthetic", 10)["added"] == 0
        assert before == (store.all("correction-candidate"), store.all("correction-review"))
        assert corrections.candidates(store, "pending")[0]["id"] == candidate["id"]
