import json
import sqlite3

import pytest

from agent_fix_lab import bundles, corrections
from agent_fix_lab.service import Lab
from agent_fix_lab.store import Store


def test_candidate_chronology_review_and_retraction(lab, history):
    with sqlite3.connect(history) as c:
        c.execute(
            'insert into messages values(7,"s","assistant","I fixed it and verified everything",null,null,7,1,0)'
        )
        c.execute(
            'insert into messages values(8,"s","user","That is wrong; I asked for a real check",null,null,8,1,0)'
        )
    stats = corrections.scan(lab.store, history, "fixture", 10)
    assert stats["added"] == 1
    assert corrections.scan(lab.store, history, "fixture", 10)["added"] == 0
    candidate = corrections.candidates(lab.store)[0]
    assert candidate["review_status"] == "pending" and candidate["operation"]["exit_code"] == 3
    assert candidate["assistant_claim"]["id"] == 7 and candidate["user_message"]["id"] == 8
    a = corrections.review(lab.store, candidate["id"], "accepted", "Reviewed", "human-declared")
    b = corrections.review(lab.store, candidate["id"], "retracted", "Withdraw", retracts=a["id"])
    assert corrections.candidates(lab.store)[0]["effective_review_status"] == "pending"
    corrections.review(lab.store, candidate["id"], "retracted", "Restore", retracts=b["id"])
    assert corrections.candidates(lab.store)[0]["effective_review_status"] == "accepted"
    assert lab.detail(candidate["case_id"])["observations"]["exit_code"] == 3


def test_no_marker_no_candidates_and_limits(lab, history):
    assert corrections.scan(lab.store, history, "fixture", 10)["added"] == 0
    with pytest.raises(ValueError):
        corrections.scan(lab.store, history, "fixture", 10, limit=10001)


def make_bundle(lab, regression, tmp_path):
    recipe = lab.add_recipe({**regression, "case_id": lab.list_cases(status="fail")[0]["id"]}, True)
    path = tmp_path / "portable.json"
    bundles.export_bundle(
        lab,
        recipe["id"],
        path,
        problem="Nonzero status was lost",
        expected="Nonzero must fail",
        failure="nonzero must fail",
        files=["implementation.py"],
        approved=True,
    )
    return path


def test_bundle_clean_roundtrip(lab, regression, tmp_path):
    path = make_bundle(lab, regression, tmp_path)
    data = bundles.validate(path)
    text = path.read_text()
    assert "CANARY_PRIVATE" not in text and str(lab.store.root) not in text
    assert "source_records" not in text and data["original_historical_revisions"] == "unknown"
    fresh = Lab(Store(tmp_path / "fresh"))
    imported = bundles.import_bundle(fresh, path, reviewed=True)
    assert bundles.import_bundle(fresh, path, reviewed=True) == imported
    outcome = fresh.run(imported["recipe_id"])
    assert outcome["comparison"]["status"] == "pass"
    assert [r["status"] for r in outcome["results"]] == ["fail", "pass"]


@pytest.mark.parametrize("change", ["checksum", "version", "path", "command", "extra", "config"])
def test_bundle_rejects_tampering(lab, regression, tmp_path, change):
    path = make_bundle(lab, regression, tmp_path)
    data = json.loads(path.read_text())
    if change == "checksum":
        data["assertion"] += "\n# changed"
    elif change == "version":
        data["schema_version"] = 77
    elif change == "path":
        data["source_files"]["faulty"]["../escape.py"] = "pass"
    elif change == "command":
        data["command"] = "sh -c malicious"
    elif change == "extra":
        data["raw_history"] = "excluded"
    else:
        data["baseline"] = {"password": "secret"}
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        bundles.validate(path)


def test_bundle_requires_both_reviews(lab, regression, tmp_path):
    path = make_bundle(lab, regression, tmp_path)
    fresh = Lab(Store(tmp_path / "fresh"))
    imported = bundles.import_bundle(fresh, path)
    with pytest.raises(ValueError, match="reviewed"):
        fresh.run(imported["recipe_id"])
    with pytest.raises(ValueError, match="review"):
        bundles.export_bundle(
            lab,
            "unknown",
            tmp_path / "no.json",
            problem="p",
            expected="e",
            failure="f",
            files=["implementation.py"],
        )


@pytest.mark.parametrize(
    "path",
    [
        "/absolute.py",
        "../outside.py",
        "a/../../b.py",
        ".env",
        ".git/config",
        "C:\\file.py",
        "x//f.py",
    ],
)
def test_bundle_paths(path):
    with pytest.raises(ValueError):
        bundles.safe_path(path)


def test_bundle_secret_guard():
    with pytest.raises(ValueError):
        bundles.privacy_check('password="an-excluded-credential"')
