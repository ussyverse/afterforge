import json
import sqlite3
import subprocess

import pytest

from agent_fix_lab.history import import_hermes
from agent_fix_lab.service import Lab
from agent_fix_lab.store import Store


@pytest.fixture
def history(tmp_path):
    path = tmp_path / "history.sqlite"
    with sqlite3.connect(path) as c:
        c.executescript("""
        create table schema_version(version integer); insert into schema_version values(26);
        create table sessions(id text primary key,parent_session_id text,model_config text,archived integer);
        create table messages(id integer primary key,session_id text,role text,content text,
            tool_call_id text,tool_name text,timestamp real,active integer,compacted integer);
        insert into sessions values('s',null,'{}',0);
        insert into sessions values('child','s','{"delegated_from":"s"}',1);
        """)
        rows = [
            (1, "s", "user", "CANARY_PRIVATE human context", None, None, 1, 1, 0),
            (
                2,
                "s",
                "tool",
                json.dumps({"output": "Unfamiliar bad result CANARY_PRIVATE", "exit_code": 3}),
                "call",
                "terminal",
                2,
                0,
                1,
            ),
            (
                3,
                "child",
                "tool",
                json.dumps({"output": "Unfamiliar bad result CANARY_PRIVATE", "exit_code": 3}),
                "call",
                "terminal",
                3,
                1,
                0,
            ),
            (
                4,
                "s",
                "tool",
                json.dumps({"output": "all good", "exit_code": 0}),
                "ok",
                "terminal",
                4,
                1,
                0,
            ),
            (
                5,
                "s",
                "tool",
                json.dumps({"output": "No exit code"}),
                "unknown",
                "terminal",
                5,
                1,
                0,
            ),
            (6, "s", "tool", '{"partial":', "partial", "terminal", 6, 1, 0),
        ]
        c.executemany("insert into messages values(?,?,?,?,?,?,?,?,?)", rows)
    return path


@pytest.fixture
def lab(tmp_path, history):
    app = Lab(Store(tmp_path / "lab"))
    import_hermes(app.store, history, source_id="fixture", before=10)
    return app


def git(repo, *args):
    return (
        subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.STDOUT)
        .decode()
        .strip()
    )


@pytest.fixture
def regression(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "implementation.py").write_text('def classify(code):\n    return "pass"\n')
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "faulty synthetic fixture")
    faulty = git(repo, "rev-parse", "HEAD")
    (repo / "implementation.py").write_text(
        'def classify(code):\n    return "pass" if code == 0 else "fail"\n'
    )
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "corrected synthetic fixture")
    corrected = git(repo, "rev-parse", "HEAD")
    test = tmp_path / "test_assertion.py"
    test.write_text(
        'from implementation import classify\ndef test_failure():\n    assert classify(3) == "fail", "nonzero must fail"\ndef test_control():\n    assert classify(0) == "pass"\n'
    )
    return {
        "schema_version": 2,
        "input_contract": "declared-v1",
        "repository": str(repo),
        "faulty_revision": faulty,
        "corrected_revision": corrected,
        "test_file": str(test),
        "expected_behavior": "Nonzero process exit fails",
        "intended_failure": "nonzero must fail",
        "provenance": "synthetic",
    }
