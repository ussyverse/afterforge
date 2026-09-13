"""Real browser proposal/evaluation/review flow using browser_fixture's toy code."""

import json
import tempfile
from pathlib import Path

from playwright.sync_api import expect


def intervention_workflow(page, url, recipe):
    token = page.locator('meta[name="afl-token"]').get_attribute("content")
    headers = {"X-AFL-Token": token}
    case = page.request.get(url + "/api/cases?status=fail").json()[0]["id"]
    with tempfile.TemporaryDirectory(prefix="afl-intervention-controls-") as directory:
        suite = []
        target = None
        for role, assertion in (
            ("target", None),
            ("successful-control", 'assert classify(0) == "pass"'),
            ("negative-control", 'assert classify(0) != "fail"'),
        ):
            values = {**recipe, "case_id": case}
            if assertion:
                file = Path(directory) / (role + ".py")
                file.write_text(
                    "from implementation import classify\ndef test_control():\n    "
                    + assertion
                    + "\n"
                )
                values["test_file"] = str(file)
            response = page.request.post(
                url + "/api/recipes", data={"recipe": values, "reviewed": True}, headers=headers
            )
            assert response.ok, response.text()
            registered = response.json()
            target = target or registered
            suite.append(
                {
                    "recipe_id": registered["id"],
                    "role": role,
                    "baseline": "fail" if role == "target" else "pass",
                }
            )
        proposal = {
            "case_ids": [case],
            "surface": "code",
            "scope": "synthetic-browser-test",
            "hypothesis": "Process status classifier needs correction",
            "rationale": "Narrow code repair instead of a global instruction",
            "candidate_text": '<img src=x onerror="window.AFL_PROPOSAL_XSS=1">',
            "base_revision": target["faulty_revision"],
            "candidate_revision": target["corrected_revision"],
            "suite": suite,
        }
        page.goto(url + "/interventions")
        expect(page.locator("#propose button")).to_be_enabled()
        page.locator("#proposal-json").fill(json.dumps(proposal))
        page.locator("#propose button").click()
        expect(page.locator("#evaluate-button")).to_be_enabled()
        expect(page.locator("#detail")).to_contain_text("Process status classifier")
        assert page.locator("#detail img").count() == 0
        assert page.evaluate("window.AFL_PROPOSAL_XSS === undefined")
        page.locator("#authorized").check()
        page.locator("#evaluate-button").click()
        expect(page.locator("#evaluation-id")).not_to_have_value("", timeout=60000)
        expect(page.locator("#review-button")).to_be_enabled()
        data = json.loads(page.locator("#detail").inner_text())
        assert data["evaluations"][-1]["status"] == "pass"
        assert data["evaluations"][-1]["behavioral_trials"] == "not-run"
        page.locator("#note").fill("Inspected synthetic evidence; no deployment approved")
        page.locator("#review-button").click()
        expect(page.locator("#detail")).to_contain_text('"accept-evidence"')
        data = json.loads(page.locator("#detail").inner_text())
        assert data["reviews"][-1]["promotion_authorized"] is False
        assert data["activation"] == "unsupported"
