import copy
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_fix_lab import interventions as iv
from agent_fix_lab.cli import main
from agent_fix_lab.web import create_app


@pytest.fixture
def proposal(lab, regression, tmp_path):
    case = lab.list_cases(status="fail")[0]["id"]
    target = lab.add_recipe({**regression, "case_id": case}, reviewed=True)
    entries = [{"recipe_id": target["id"], "role": "target", "baseline": "fail"}]
    for role, assertion in (
        ("successful-control", 'assert classify(0) == "pass"'),
        ("negative-control", 'assert classify(0) != "fail"'),
    ):
        file = tmp_path / (role + ".py")
        file.write_text(
            "from implementation import classify\ndef test_control():\n    " + assertion + "\n"
        )
        recipe = lab.add_recipe(
            {**regression, "case_id": case, "test_file": str(file)}, reviewed=True
        )
        entries.append({"recipe_id": recipe["id"], "role": role, "baseline": "pass"})
    return {
        "case_ids": [case],
        "surface": "code",
        "scope": "synthetic-project",
        "hypothesis": "Nonzero exit was treated as success",
        "rationale": "Prefer a process classifier fix, not a global prompt",
        "candidate_text": "Use the exit code; never execute this proposal text",
        "base_revision": regression["faulty_revision"],
        "candidate_revision": regression["corrected_revision"],
        "suite": entries,
    }


def test_real_proposal_suite_review_and_no_activation(lab, proposal):
    draft = iv.propose(lab, proposal)
    evaluation = iv.evaluate(lab, draft["id"], draft["candidate_digest"], reviewed=True)
    assert evaluation["status"] == "pass"
    assert evaluation["checks"][0]["observed"] == {"faulty": "fail", "corrected": "pass"}
    assert all(
        c["observed"] == {"faulty": "pass", "corrected": "pass"} for c in evaluation["checks"][1:]
    )
    receipt = iv.review(
        lab,
        draft["id"],
        evaluation["id"],
        draft["candidate_digest"],
        "accept-evidence",
        "Reviewed synthetic suite",
    )
    assert receipt["promotion_authorized"] is False
    assert receipt["authority"] == "local-caller-declared"
    detail = iv.inspect(lab, draft["id"])
    assert detail["activation"] == "unsupported" and len(detail["reviews"]) == 1
    assert evaluation["behavioral_trials"] == "not-run"
    with pytest.raises(ValueError, match="immutable"):
        lab.store.put("intervention", {**draft, "candidate_digest": "forged"})


@pytest.mark.parametrize(
    "change", ["missing-control", "duplicate", "revision", "unreviewed", "extra-field"]
)
def test_reject_invalid_candidate(lab, proposal, change):
    values = copy.deepcopy(proposal)
    if change == "missing-control":
        values["suite"][-1]["role"] = "related"
    elif change == "duplicate":
        values["suite"][-1]["recipe_id"] = values["suite"][0]["recipe_id"]
    elif change == "revision":
        values["candidate_revision"] = "a" * 40
    elif change == "unreviewed":
        recipe = lab.store.get("recipe", values["suite"][0]["recipe_id"])
        recipe = lab.add_recipe(recipe, reviewed=False)
        values["suite"][0]["recipe_id"] = recipe["id"]
    else:
        values["promotion_authorized"] = True
    with pytest.raises(ValueError):
        iv.propose(lab, values)
    assert lab.store.all("intervention") == []


def test_review_required_before_any_execution(lab, proposal, monkeypatch):
    draft = iv.propose(lab, proposal)
    monkeypatch.setattr(lab, "run", lambda *_: pytest.fail("Unauthorized execution"))
    for digest, reviewed in ((draft["candidate_digest"], False), ("wrong", True)):
        with pytest.raises(ValueError):
            iv.evaluate(lab, draft["id"], digest, reviewed=reviewed)
    assert lab.store.all("intervention-evaluation-authorization") == []


def test_changed_assertions_remain_inconclusive(lab, proposal):
    draft = iv.propose(lab, proposal)
    recipe = lab.store.get("recipe", proposal["suite"][0]["recipe_id"])
    Path(recipe["test_file"]).write_text("def test_fake():\n    assert True\n")
    evaluation = iv.evaluate(lab, draft["id"], draft["candidate_digest"], reviewed=True)
    assert evaluation["status"] == "inconclusive"
    with pytest.raises(ValueError, match="unsuccessful"):
        iv.review(
            lab, draft["id"], evaluation["id"], draft["candidate_digest"], "accept-evidence", "no"
        )
    assert (
        iv.review(
            lab, draft["id"], evaluation["id"], draft["candidate_digest"], "reject", "stale test"
        )["decision"]
        == "reject"
    )


def test_control_regression_rejected(lab, proposal):
    # Bind a genuinely failing control before the proposal is frozen.
    old = lab.store.get("recipe", proposal["suite"][-1]["recipe_id"])
    Path(old["test_file"]).write_text(
        'def test_control():\n    assert False, "control regression"\n'
    )
    updated = lab.add_recipe({**old, "intended_failure": "control regression"}, reviewed=True)
    proposal["suite"][-1]["recipe_id"] = updated["id"]
    draft = iv.propose(lab, proposal)
    result = iv.evaluate(lab, draft["id"], draft["candidate_digest"], reviewed=True)
    assert result["status"] == "fail" and result["promotion_authorized"] is False


def test_cli_and_web_surface(lab, proposal, tmp_path, capsys):
    path = tmp_path / "proposal.json"
    path.write_text(json.dumps(proposal))
    assert main(["--home", str(lab.store.root), "intervention-propose", "--file", str(path)]) == 0
    draft = json.loads(capsys.readouterr().out)
    assert main(["--home", str(lab.store.root), "intervention-list"]) == 0
    assert json.loads(capsys.readouterr().out)["total"] == 1
    with TestClient(create_app(lab)) as client:
        page = client.get("/interventions")
        assert page.status_code == 200 and "No activation" in page.text
        token = re.search('name="afl-token" content="([^"]+)"', page.text)[1]
        headers = {"X-AFL-Token": token}
        assert client.post("/api/interventions", json=proposal).status_code == 403
        assert client.get("/api/interventions?limit=99").status_code == 400
        response = client.post(
            "/api/interventions/" + draft["id"] + "/evaluate",
            headers=headers,
            json={"candidate_digest": draft["candidate_digest"], "reviewed": True},
        )
        assert response.status_code == 200, response.text
        evaluation = response.json()
        assert evaluation["status"] == "pass"
        review = {
            "candidate_digest": draft["candidate_digest"],
            "evaluation_id": evaluation["id"],
            "decision": "accept-evidence",
            "note": "Inspected",
        }
        endpoint = "/api/interventions/" + draft["id"] + "/review"
        assert (
            client.post(endpoint, json={**review, "approved": True}, headers=headers).status_code
            == 400
        )
        assert (
            client.post(endpoint, json=review, headers=headers).json()["promotion_authorized"]
            is False
        )
        other = iv.propose(lab, {**proposal, "candidate_text": "Different proposal"})
        assert (
            client.post(
                "/api/interventions/" + other["id"] + "/review", json=review, headers=headers
            ).status_code
            == 400
        )
