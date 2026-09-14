"""Synthetic guided release acceptance; no model inference or personal history."""

import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from fastapi.testclient import TestClient

from agent_fix_lab import bundles, corrections
from agent_fix_lab.cli import main
from agent_fix_lab.current_check import retained_check, retained_plan
from agent_fix_lab.plugin_bridge import dispatch
from agent_fix_lab.runner import git
from agent_fix_lab.service import Lab
from agent_fix_lab.store import Store
from agent_fix_lab.web import create_app


def correction_history(path):
    with sqlite3.connect(path) as c:
        c.executemany(
            "insert into messages values(?,?,?,?,?,?,?,?,?)",
            [(7, "s", "assistant", "I verified everything", None, None, 8, 1, 0)]
            + [
                (i, "s", "user", "That is wrong; I asked for a check", None, None, 8, 1, 0)
                for i in range(8, 13)
            ],
        )


def test_shared_scan_same_timestamp_and_deferred_link(history, tmp_path):
    correction_history(history)
    lab = Lab(Store(tmp_path / "fresh"))
    first = lab.scan(history, "mapped-profile", before=10, limit=1, after_id=6)
    assert first["corrections"]["scanned_users"] == 1
    for _ in range(5):
        lab.scan(history, "mapped-profile", before=10, limit=1)
    rows = corrections.candidates(lab.store)
    assert len(rows) == 5 and all(r["case_id"] is None for r in rows)
    originals = lab.store.all("correction-candidate")
    lab.scan(history, "mapped-profile", before=10, after_id=0, limit=1)
    linked = corrections.candidates(lab.store)
    assert all(r["case_id"] and r["operation"]["exit_code"] == 3 for r in linked)
    assert lab.store.all("correction-candidate") == originals
    repeated = lab.scan(
        history, "mapped-profile", before=10, limit=100, correction_cursor={"timestamp": 0, "id": 0}
    )
    assert repeated["corrections"]["added"] == 0
    assert repeated["corrections"]["next_cursor"] == {"timestamp": 8.0, "id": 12}


def test_operator_queue_agent_proposals_and_retractions(lab, history):
    correction_history(history)
    corrections.scan(lab.store, history, "fixture", 10)
    candidate = corrections.candidates(lab.store)[0]
    agent = dispatch(
        lab.store.root,
        "review_correction",
        {"candidate_id": candidate["id"], "decision": "accepted", "note": "Agent proposal"},
    )
    assert agent["reviewer_kind"] == "agent"
    assert len(corrections.candidates(lab.store, "pending")) == 5
    accepted = corrections.review(lab.store, candidate["id"], "accepted", "Inspected")
    assert len(corrections.candidates(lab.store, "pending")) == 4
    with pytest.raises(ValueError, match="Agent"):
        corrections.review(lab.store, candidate["id"], "retracted", "No", "agent", accepted["id"])
    retraction = corrections.review(
        lab.store, candidate["id"], "retracted", "Withdraw", retracts=accepted["id"]
    )
    assert len(corrections.candidates(lab.store, "pending")) == 5
    corrections.review(
        lab.store, candidate["id"], "retracted", "Restore", retracts=retraction["id"]
    )
    assert corrections.candidates(lab.store, "accepted")[0]["id"] == candidate["id"]


def test_draft_real_redgreen_portable_later_commit(tmp_path):
    lab = Lab(Store(tmp_path / "lab"))
    draft = lab.synthetic_demo()
    assert draft["recipe"]["schema_version"] == 2
    assert draft["recipe"]["input_contract"] == "unknown"
    assert not draft["reconstruction"] and not draft["execution_authorized"]
    assert Path(draft["recipe"]["test_file"]).read_text() == draft["assertion"]
    frozen = draft["recipe"]["frozen_inputs"][0]
    assert hashlib.sha256(frozen["content"].encode("utf-8")).hexdigest() == frozen["sha256"]
    with pytest.raises(ValueError, match="declaration"):
        lab.authorize_draft(draft["id"], draft["draft_digest"], reviewed=True)
    recipe = lab.authorize_draft(
        draft["id"], draft["draft_digest"], reviewed=True, declared_inputs=True
    )
    assert recipe["input_contract"] == "declared-v1"
    assert (
        lab.authorize_draft(draft["id"], draft["draft_digest"], reviewed=True, declared_inputs=True)
        == recipe
    )
    result = lab.run(recipe["id"])
    assert result["comparison"]["status"] == "pass", result
    assert [r["status"] for r in result["results"]] == ["fail", "pass"]
    bundle = tmp_path / "portable.json"
    bundles.export_bundle(
        lab,
        recipe["id"],
        bundle,
        problem="Synthetic exit code classification",
        expected="Nonzero exits fail",
        failure="nonzero must fail",
        files=["implementation.py"],
        approved=True,
    )
    fresh = Lab(Store(tmp_path / "imported"))
    imported = bundles.import_bundle(fresh, bundle, reviewed=True)
    assert fresh.run(imported["recipe_id"])["comparison"]["status"] == "pass"
    repo = Path(recipe["repository"])
    (repo / "README.txt").write_text("Synthetic later commit\n")
    git(repo, "add", "README.txt")
    git(repo, "commit", "-qm", "Synthetic later target")
    target = git(repo, "rev-parse", "HEAD").decode().strip()
    (repo / "implementation.py").write_text("raise RuntimeError('LIVE EDIT MUST NOT EXECUTE')\n")
    (repo / ".git/info/exclude").write_text("ignored/\n")
    (repo / "ignored").mkdir()
    (repo / "ignored/cache").write_text("irrelevant")
    with pytest.raises(ValueError, match="path-specific review"):
        retained_plan(lab, recipe["id"], target)
    plan = retained_plan(
        lab,
        recipe["id"],
        target,
        {"README.txt": "Reviewed documentation only, not a regression input"},
    )
    with pytest.raises(ValueError, match="reviewed target"):
        retained_check(lab, plan["id"], plan["plan_digest"])
    receipt = retained_check(lab, plan["id"], plan["plan_digest"], reviewed=True)
    assert receipt["status"] == "pass" and receipt["revision"] == target
    assert not receipt["live_environment_verified"]
    assert receipt["recipe_id"] != recipe["id"]
    assert lab.store.get("recipe", recipe["id"]) == recipe
    assert lab.store.get("regression-draft", draft["id"])["recipe"]["input_contract"] == "unknown"
    for old in result["results"]:
        assert lab.store.get("result", old["id"]) == old


def test_legacy_recipe_not_upgraded(lab, regression):
    regression.pop("schema_version")
    regression.pop("input_contract")
    recipe = lab.add_recipe({**regression, "case_id": lab.list_cases()[0]["id"]}, reviewed=True)
    assert recipe["schema_version"] == 1 and recipe["input_contract"] == "unknown"
    assert lab.run(recipe["id"])["comparison"]["status"] == "inconclusive"
    with pytest.raises(ValueError, match="declared-v1"):
        retained_plan(lab, recipe["id"], recipe["corrected_revision"])


def test_retained_unknown_inputs_cannot_pass(tmp_path, monkeypatch):
    from agent_fix_lab import current_check

    lab = Lab(Store(tmp_path / "lab"))
    draft = lab.synthetic_demo()
    recipe = lab.authorize_draft(
        draft["id"], draft["draft_digest"], reviewed=True, declared_inputs=True
    )
    plan = retained_plan(lab, recipe["id"], recipe["corrected_revision"])
    execute = current_check.execute

    def missing_identity(recipe, variant):
        return execute(recipe, variant).model_copy(
            update={"input_unknowns": ["Synthetic missing identity"], "frozen_input_digest": None}
        )

    monkeypatch.setattr(current_check, "execute", missing_identity)
    assert (
        retained_check(lab, plan["id"], plan["plan_digest"], reviewed=True)["status"]
        == "inconclusive"
    )


def test_draft_changed_assertion_requires_new_review(tmp_path):
    lab = Lab(Store(tmp_path / "lab"))
    draft = lab.synthetic_demo()
    Path(draft["recipe"]["test_file"]).write_text("def test_fake(): assert True\n")
    with pytest.raises(ValueError):
        lab.authorize_draft(draft["id"], draft["draft_digest"], reviewed=True, declared_inputs=True)
    assert lab.store.all("recipe") == []


def test_sql_bounded_pages_without_store_all(lab, history, monkeypatch):
    correction_history(history)
    corrections.scan(lab.store, history, "fixture", 10)
    case = lab.list_cases()[0]
    run = lab.store.get("run", case["run_id"])
    lab.store.put_many(("case", {**case, "id": f"synthetic-{i}"}) for i in range(1200))
    lab.store.put_many(
        (
            "annotation",
            {"id": f"a-{i}", "case_id": case["id"], "text": "synthetic", "retracts": None},
        )
        for i in range(120)
    )
    monkeypatch.setattr(lab.store, "all", lambda *_: pytest.fail("Unbounded Store.all called"))
    assert len(lab.list_cases(offset=1190, limit=5)) == 5
    assert lab.list_cases(offset=1190, limit=5)[0]["summary"] == run["output"][:180]
    detail = lab.detail(case["id"], offset=10, limit=5)
    assert len(detail["interpretations"]) == 5
    assert len(corrections.candidates(lab.store, offset=2, limit=2)) == 2
    assert len(dispatch(lab.store.root, "list_cases", {"offset": 1000, "limit": 3})["cases"]) == 3


def test_legacy_candidates_and_review_history_are_preserved(lab, history):
    correction_history(history)
    legacy = {
        "id": "legacy-candidate",
        "source_id": "fixture",
        "session_id": "s",
        "case_id": lab.list_cases(status="fail")[0]["id"],
        "operation": None,
        "assistant_claim": None,
        "user_message": {"id": 8, "content": "Synthetic legacy correction"},
        "parser": "corrections.v1",
        "review_status": "pending",
    }
    lab.store.put("correction-candidate", legacy)
    corrections.review(lab.store, legacy["id"], "accepted", "Legacy operator review")
    assert corrections.scan(lab.store, history, "fixture", 10)["added"] == 4
    assert lab.store.get("correction-candidate", legacy["id"]) == legacy
    assert corrections.candidates(lab.store, "accepted")[0]["id"] == legacy["id"]
    for i in range(105):
        corrections.review(
            lab.store, legacy["id"], "rejected", f"Synthetic agent proposal {i}", reviewer="agent"
        )
    first = corrections.candidates(lab.store, "accepted")[0]
    assert len(first["reviews"]) == 100 and first["reviews_next_offset"] == 100
    assert len(corrections.candidates(lab.store, "accepted", review_offset=100)[0]["reviews"]) == 6


def test_scan_lock_dryrun_and_independent_mapping(lab, history):
    with lab.store.workflow_lock("scan"), pytest.raises(ValueError, match="already running"):
        lab.scan(history, "fixture", limit=1)
    initial = len(lab.store.all("case"))
    lab.scan(history, "fixture", limit=100, dry_run=True)
    assert lab.store.all("scan-cursor") == []
    lab.scan(history, "fixture", limit=100)
    assert len(lab.store.all("case")) == initial
    lab.scan(history, "independent-copy-explicit", limit=100)
    assert len(lab.store.all("case")) == initial * 2


def test_annotations_retraction_beyond_page_is_effective(lab):
    case_id = lab.list_cases()[0]["id"]
    original = lab.annotate(case_id, "Synthetic operator assertion")
    lab.store.put_many(
        (
            "annotation",
            {
                "id": f"scale-{i}",
                "case_id": case_id,
                "author_kind": "operator",
                "text": "Synthetic scale fixture",
                "retracts": None,
            },
        )
        for i in range(10010)
    )
    lab.annotate(case_id, "Withdraw synthetic assertion", retracts=original["id"])
    assert original["id"] not in {
        r["id"] for r in lab.detail(case_id, limit=5)["effective_interpretations"]
    }
    with pytest.raises(ValueError, match="Agent"):
        lab.annotate(
            case_id, "Not operator authority", author="agent-proposed", retracts=original["id"]
        )


def test_cli_demo_draft_authorization_and_exit_codes(tmp_path, capsys):
    home = ["--home", str(tmp_path / "cli")]
    assert main([*home, "demo"]) == 0
    draft = json.loads(capsys.readouterr().out)
    assert (
        main(
            [
                *home,
                "authorize-draft",
                draft["id"],
                "--approve-digest",
                draft["draft_digest"],
                "--reviewed",
            ]
        )
        == 2
    )
    capsys.readouterr()
    assert (
        main(
            [
                *home,
                "authorize-draft",
                draft["id"],
                "--approve-digest",
                draft["draft_digest"],
                "--reviewed",
                "--declared-inputs",
            ]
        )
        == 0
    )
    recipe = json.loads(capsys.readouterr().out)
    process = subprocess.run(
        [sys.executable, "-m", "agent_fix_lab.cli", *home, "run", recipe["id"]],
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["comparison"]["status"] == "pass"
    assert (
        main(
            [
                *home,
                "retained-plan",
                recipe["id"],
                "--target-revision",
                recipe["corrected_revision"],
            ]
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)
    assert (
        main(
            [
                *home,
                "retained-check",
                plan["id"],
                "--approve-digest",
                plan["plan_digest"],
                "--reviewed",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "pass"


def test_browser_api_guided_contract_and_source_mapping(lab, history, monkeypatch):
    with TestClient(create_app(lab)) as client:
        page = client.get("/guided")
        assert "Afterforge" in page.text and "AFTERFORGE" not in page.text
        token = page.text.split('name="afl-token" content="')[1].split('"')[0]
        headers = {"x-afl-token": token}
        assert client.post("/api/demo", json={}).status_code == 403
        draft = client.post("/api/demo", json={}, headers=headers).json()
        view = client.get(f"/api/guided/{draft['case_id']}").json()
        assert view["drafts"][0]["draft_digest"] == draft["draft_digest"]
        assert view["next_action"] == "review draft"
        bad = client.post(
            f"/api/drafts/{draft['id']}/authorize",
            json={"approve_digest": "wrong", "reviewed": True, "declared_inputs": True},
            headers=headers,
        )
        assert bad.status_code == 400
    monkeypatch.delenv("AFTERFORGE_SOURCE_ID", raising=False)
    with pytest.raises(ValueError, match="mapping"):
        dispatch(lab.store.root, "scan", {"source": str(history), "limit": 1})
    monkeypatch.setenv("AFTERFORGE_SOURCE_ID", "fixture")
    assert (
        dispatch(lab.store.root, "scan", {"source": str(history), "limit": 1})["source_id"]
        == "fixture"
    )


@pytest.mark.parametrize("repeat", range(3))
def test_guided_fresh_browser(tmp_path, repeat, history):
    chromium = os.environ.get("AFL_CHROMIUM")
    if not chromium:
        pytest.skip("Set AFL_CHROMIUM to an existing approved Chromium; never install a browser")
    from playwright.sync_api import sync_playwright

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    correction_history(history)
    host_home = tmp_path / "synthetic-host"
    host_home.mkdir()
    shutil.copyfile(history, host_home / "state.db")
    env = {
        **os.environ,
        "AGENT_FIX_LAB_HOME": str(tmp_path / f"browser-{repeat}"),
        "HERMES_HOME": str(host_home),
        "AFTERFORGE_SOURCE_ID": "synthetic-browser-profile",
    }
    server = subprocess.Popen(
        [
            os.environ.get("AFL_BROWSER_PYTHON", sys.executable),
            "-m",
            "uvicorn",
            "agent_fix_lab.web:default_app",
            "--factory",
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        url = f"http://127.0.0.1:{port}"
        for _ in range(100):
            if server.poll() is not None:
                pytest.fail("Fresh browser server exited")
            try:
                with urlopen(url + "/guided", timeout=1) as response:
                    assert response.status == 200
                break
            except OSError:
                time.sleep(0.05)
        else:
            pytest.fail("Server readiness timed out")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=chromium, headless=True, args=["--no-sandbox"]
            )
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url + "/guided")
            page.wait_for_selector('body[data-state="ready"]')
            page.click("#demo")
            page.locator("#title", has_text="SYNTHETIC").wait_for()
            proposal = json.loads(page.locator("#proposal").text_content())
            page.click("#scan")
            page.locator("#queue article").first.wait_for()
            card = page.locator("#queue article").first
            card.get_by_role("button", name="Accept as operator", exact=True).click()
            page.wait_for_selector('body[data-state="error"]')
            card.locator("textarea").fill("Synthetic operator inspected the linked process fact")
            card.get_by_role("button", name="Accept as operator", exact=True).click()
            page.wait_for_selector('body[data-state="ready"]')
            page.select_option("#queue-state", "accepted")
            page.locator("#queue article").first.get_by_role(
                "button", name="Open linked case", exact=True
            ).click()
            page.wait_for_selector('body[data-state="ready"]')
            page.locator("#draft-panel summary").click()
            for field, value in {
                "repository": proposal["recipe"]["repository"],
                "faulty": proposal["recipe"]["faulty_revision"],
                "corrected": proposal["recipe"]["corrected_revision"],
                "function": "classify",
                "expected": "Synthetic nonzero process exit must fail",
                "failure": "nonzero must fail",
            }.items():
                page.fill("#" + field, value)
            page.get_by_role("button", name="Create actual draft files", exact=True).click()
            page.wait_for_selector('body[data-state="ready"]')
            assert "classify" in page.locator("#assertion").text_content()
            page.check("#reviewed")
            page.check("#declared")
            page.click("#authorize")
            page.wait_for_selector("#run:enabled")
            page.click("#run")
            page.wait_for_selector('#comparison[data-status="pass"]')
            proposal = json.loads(page.locator("#proposal").text_content())
            page.fill("#target", proposal["recipe"]["corrected_revision"])
            page.click("#plan")
            page.wait_for_selector("#retain:enabled")
            page.check("#target-reviewed")
            page.click("#retain")
            page.wait_for_selector('#retained[data-status="pass"]')
            repo = Path(proposal["recipe"]["repository"])
            (repo / "README.txt").write_text("Synthetic later browser commit\n")
            git(repo, "add", "README.txt")
            git(repo, "commit", "-qm", "Synthetic browser later target")
            target = git(repo, "rev-parse", "HEAD").decode().strip()
            (repo / "implementation.py").write_text("raise RuntimeError('LIVE EDIT')\n")
            page.fill("#target", target)
            page.click("#plan")
            page.wait_for_selector('body[data-state="error"]')
            assert "review" in page.locator("#notice").text_content()
            page.fill(
                "#data-changes",
                json.dumps({"README.txt": "Reviewed documentation, not a regression input"}),
            )
            page.click("#plan")
            page.wait_for_selector('body[data-state="ready"]')
            page.check("#target-reviewed")
            page.click("#retain")
            page.wait_for_selector('body[data-state="ready"]')
            receipt = json.loads(page.locator("#retained").text_content())
            assert receipt["revision"] == target and receipt["status"] == "pass"
            assert not receipt["live_environment_verified"]
            if directory := os.environ.get("AFL_SCREENSHOT_DIR"):
                output = Path(directory)
                output.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(output / f"guided-{repeat}.png"), full_page=True)
            assert not errors
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
