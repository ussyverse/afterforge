import re

from fastapi.testclient import TestClient

from agent_fix_lab.web import create_app


def test_browser_api_workflow(lab, regression):
    with TestClient(create_app(lab)) as client:
        page = client.get("/")
        assert page.status_code == 200 and "Agent Fix Lab" in page.text
        token = re.search('name="afl-token" content="([^"]+)"', page.text)[1]
        headers = {"X-AFL-Token": token}
        case = client.get("/api/cases").json()[0]["id"]
        assert (
            client.post(f"/api/cases/{case}/annotations", json={"text": "bad"}).status_code == 403
        )
        response = client.post(
            f"/api/cases/{case}/annotations",
            json={"text": "reviewed", "expected": "correct status"},
            headers=headers,
        )
        assert response.status_code == 200
        recipe = client.post(
            "/api/recipes",
            json={"recipe": {**regression, "case_id": case}, "reviewed": True},
            headers=headers,
        )
        assert recipe.status_code == 200
        response = client.post(
            "/api/recipes/" + recipe.json()["id"] + "/run", json={}, headers=headers
        )
        assert response.json()["comparison"]["status"] == "pass"
        assert "CANARY_PRIVATE" not in client.get(f"/api/cases/{case}/export").text
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/assets/secret").status_code == 404
        assert client.get("/api/cases/nonexistent").status_code == 404
        assert client.get("/", headers={"Origin": "https://evil.invalid"}).status_code == 403
        assert client.get("/", headers={"Host": "evil.invalid"}).status_code == 400
        assert (
            client.post(
                "/api/recipes", json={"recipe": {}, "reviewed": False}, headers=headers
            ).status_code
            == 400
        )
        assert (
            client.post(
                f"/api/cases/{case}/annotations", json={"unexpected": "bad"}, headers=headers
            ).status_code
            == 400
        )
