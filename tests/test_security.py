import io
import json
import re
import sqlite3
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_fix_lab.cli import parser
from agent_fix_lab.history import import_hermes
from agent_fix_lab.models import Recipe
from agent_fix_lab.runner import classify_result, compare, execute, unpack_revision
from agent_fix_lab.web import create_app


def test_controlled_environment_and_ignored_untracked_files(lab, regression, monkeypatch):
    monkeypatch.setenv("AFL_SECRET_CANARY", "excluded-private-value")
    (Path(regression["repository"]) / "private-untracked.txt").write_text("private")
    Path(regression["test_file"]).write_text(
        'import os\nfrom pathlib import Path\ndef test_env():\n assert "AFL_SECRET_CANARY" not in os.environ\n assert not Path("private-untracked.txt").exists()\n assert Path.cwd() != Path.home()\n'
    )
    recipe = Recipe(**lab.add_recipe({**regression, "case_id": lab.list_cases()[0]["id"]}, True))
    assert execute(recipe, "corrected").status == "pass"


def test_output_limit(lab, regression):
    Path(regression["test_file"]).write_text(
        'import os\ndef test_output():\n os.write(1,b"x"*200000)\n assert False, "output"\n'
    )
    recipe = Recipe(
        **lab.add_recipe(
            {**regression, "case_id": lab.list_cases()[0]["id"], "output_limit_bytes": 1024}, True
        )
    )
    result = execute(recipe, "corrected")
    assert result.status == "inconclusive" and result.reason == "output-limit"
    assert len(result.output.encode()) <= 1024


@pytest.mark.parametrize("revision", ["--help", "does-not-exist", "HEAD;touch unsafe"])
def test_revision_is_not_shell(lab, regression, revision):
    with pytest.raises(ValueError):
        lab.add_recipe(
            {**regression, "case_id": lab.list_cases()[0]["id"], "faulty_revision": revision}, True
        )


def test_weakened_reviewed_assertion_never_verifies(lab, regression):
    recipe = Recipe(**lab.add_recipe({**regression, "case_id": lab.list_cases()[0]["id"]}, True))
    Path(recipe.test_file).write_text("def test_weakened(): assert True")
    with pytest.raises(ValueError, match="changed"):
        execute(recipe, "corrected")
    revised = Recipe(**lab.add_recipe({**regression, "case_id": recipe.case_id}, True))
    assert (
        compare(revised, execute(revised, "faulty"), execute(revised, "corrected")).status == "fail"
    )


@pytest.mark.parametrize(
    "name,link", [("../escape.py", False), ("/escape.py", False), ("linked.py", True)]
)
def test_archive_path_security(tmp_path, monkeypatch, name, link):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        item = tarfile.TarInfo(name)
        if link:
            item.type = tarfile.SYMTYPE
            item.linkname = "../outside"
        tar.addfile(item)
    monkeypatch.setattr("agent_fix_lab.runner.git", lambda *args: buf.getvalue())
    with pytest.raises(ValueError):
        unpack_revision(tmp_path, "revision", tmp_path / "workspace")


def test_missing_and_unreadable_process_reports(tmp_path):
    assert classify_result(0, tmp_path / "missing", "", None)[0] == "inconclusive"
    report = tmp_path / "bad.xml"
    report.write_text("not xml")
    assert classify_result(0, report, "", None)[0] == "inconclusive"


def test_cohort_and_limits(lab, history):
    before = len(lab.list_cases(cohort="historical"))
    import_hermes(lab.store, history, source_id="new-source", before=10, cohort="dogfood")
    assert len(lab.list_cases(cohort="historical")) == before
    assert len(lab.list_cases(cohort="dogfood")) == before
    for limit in (0, 10001):
        with pytest.raises(ValueError):
            import_hermes(lab.store, history, source_id="fixture", before=10, limit=limit)


def test_partial_large_record_explicitly_incomplete(lab, history):
    with sqlite3.connect(history) as c:
        c.execute(
            'insert into messages values(9,"s","tool",?,"large","terminal",9,1,0)',
            (json.dumps({"output": "x" * 70000, "exit_code": 1}),),
        )
    stats = import_hermes(lab.store, history, source_id="fixture", before=10)
    assert stats["truncated"] == 1
    case = next(c for c in lab.list_cases() if "full_output" in c["unknown"])
    assert case["status"] == "inconclusive"


def test_web_body_limits_csrf_csp(lab):
    with TestClient(create_app(lab)) as c:
        page = c.get("/")
        token = re.search('name="afl-token" content="([^"]+)"', page.text)[1]
        assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
        assert (
            c.post("/api/recipes", content=b"x" * 70000, headers={"X-AFL-Token": token}).status_code
            == 413
        )
        assert (
            c.post(
                "/api/recipes",
                json={},
                headers={"X-AFL-Token": token, "Origin": "https://evil.invalid"},
            ).status_code
            == 403
        )
        assert (
            c.post(
                "/api/recipes",
                json={},
                headers={"X-AFL-Token": token, "Sec-Fetch-Site": "cross-site"},
            ).status_code
            == 403
        )
        assert (
            c.post(
                "/api/recipes",
                content="not-json",
                headers={"X-AFL-Token": token, "Content-Type": "application/json"},
            ).status_code
            == 422
        )


def test_cli_no_remote_bind_option():
    with pytest.raises(SystemExit):
        parser().parse_args(["serve", "--host", "0.0.0.0"])


@pytest.mark.parametrize(
    "action",
    [
        "drop table schema_version",
        "delete from schema_version",
        "insert into schema_version values(26)",
    ],
)
def test_missing_or_ambiguous_source_version(lab, history, action):
    with sqlite3.connect(history) as c:
        c.execute(action)
    with pytest.raises(ValueError, match="Unsupported Hermes schema"):
        import_hermes(lab.store, history, source_id="fixture", before=10)


def test_install_remove_and_collision(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts/install_hermes.py"
    command = [
        sys.executable,
        str(script),
        "--hermes-home",
        str(tmp_path / "hermes"),
        "--lab-home",
        str(tmp_path / "lab"),
        "--executable",
        sys.executable,
    ]
    subprocess.run(command, check=True, capture_output=True)
    assert subprocess.run(command, check=False, capture_output=True).returncode != 0
    subprocess.run(
        [sys.executable, str(script), "--hermes-home", str(tmp_path / "hermes"), "--remove"],
        check=True,
        capture_output=True,
    )
    assert not (tmp_path / "hermes/skills/agent-fix-lab").exists()
