"""Exercise packaged assets on a fresh loopback server; no sleeps for UI state."""

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def workflow(url, recipe, query, screenshot=None):
    errors, failed = [], []
    with sync_playwright() as pw:
        options = {"headless": True}
        if os.environ.get("AFL_CHROMIUM"):
            options["executable_path"] = os.environ["AFL_CHROMIUM"]
        browser = pw.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1360, "height": 1000})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("response", lambda r: failed.append(r.status) if r.status >= 400 else None)
        page.on("requestfailed", lambda r: failed.append(r.failure))

        def ready(operation):
            expect(page.locator("body")).to_have_attribute("data-state", "ready", timeout=30000)
            expect(page.locator("body")).to_have_attribute("data-completed", operation)

        page.goto(url)
        ready("list")
        page.locator("#search").fill(query)
        ready("list")
        page.locator("#cases .case").first.click()
        ready("detail")
        expect(page.locator("#case-title")).to_contain_text("FAIL")
        expect(page.locator("#output")).not_to_be_empty()
        page.locator("#correction").fill(
            "Agent-proposed browser verification; not historical human evidence"
        )
        page.locator("#expected").fill(recipe["expected_behavior"])
        page.locator("#annotation-form button").click()
        ready("annotation")
        expect(page.locator("#annotations")).to_contain_text('"author_kind": "operator"')
        expect(page.locator("#annotations")).to_contain_text("browser verification")
        page.get_by_text("Select compatible configuration evidence", exact=True).click()
        fields = json.dumps({"python_version": sys.version.split()[0]})
        page.locator("#baseline-json").fill(fields)
        page.locator("#current-json").fill(fields)
        page.locator("#baseline-form button").click()
        ready("baseline")
        expect(page.locator("#config")).to_contain_text("diff")
        page.get_by_text("Create a reviewed reproduction recipe", exact=True).click()
        for element, key in [
            ("repo", "repository"),
            ("faulty", "faulty_revision"),
            ("corrected", "corrected_revision"),
            ("test-file", "test_file"),
            ("recipe-expected", "expected_behavior"),
            ("failure", "intended_failure"),
        ]:
            page.locator("#" + element).fill(recipe[key])
        page.locator("#reviewed").check()
        page.locator("#recipe-form button").click()
        ready("recipe")
        page.locator("#run").click()
        ready("run")
        expect(page.locator("#results")).to_have_attribute("data-comparison", "pass")
        result = json.loads(page.locator("#results").inner_text())
        assert [r["status"] for r in result["results"]] == ["fail", "pass"]
        assert all(r["tests"] > 0 and r["errors"] == 0 for r in result["results"])
        with page.expect_download() as download:
            page.locator("#export").click()
        ready("export")
        report = json.loads(Path(download.value.path()).read_text())
        assert report["shadow_only"] and "source_records" in report["excluded"]
        if screenshot:
            page.screenshot(path=str(screenshot), full_page=True)
        # Expected security failures use APIRequestContext, not the page's success traffic.
        token = page.locator('meta[name="afl-token"]').get_attribute("content")
        assert (
            page.request.post(
                url + "/api/recipes",
                data={"recipe": recipe, "reviewed": False},
                headers={"X-AFL-Token": token},
            ).status
            == 400
        )
        assert page.request.post(url + "/api/recipes/unknown/run", data={}).status == 403
        # Deliberately return an older detail response after a newer selection.
        page.locator("#search").fill("")
        ready("list")
        first = page.locator("#cases .case").nth(0).get_attribute("data-case-id")
        second = page.locator("#cases .case").nth(1).get_attribute("data-case-id")
        pending = []

        def hold(route):
            response = route.fetch()
            pending.append((route, response))

        page.route(url + "/api/cases/" + first, hold)
        with page.expect_request(url + "/api/cases/" + first):
            page.locator("#cases .case").nth(0).click()
        page.locator("#cases .case").nth(1).click()
        ready("detail")
        expect(page.locator("#detail")).to_have_attribute("data-case-id", second)
        assert pending
        pending[0][0].fulfill(response=pending[0][1])
        expect(page.locator("body")).to_have_attribute("data-discarded-details", "1")
        expect(page.locator("#detail")).to_have_attribute("data-case-id", second)
        page.unroute(url + "/api/cases/" + first)

        # Synthetic malicious text is transported by a test route, not stored in the dataset.
        def malicious(route):
            response = route.fetch()
            data = response.json()
            data["observations"]["output"] = '<img src=x onerror="window.AFL_XSS=1">'
            route.fulfill(response=response, json=data)

        page.route(url + "/api/cases/" + first, malicious)
        page.locator("#cases .case").nth(0).click()
        ready("detail")
        expect(page.locator("#output")).to_contain_text("<img")
        assert page.locator("#output img").count() == 0
        assert page.evaluate("window.AFL_XSS === undefined")
        page.locator("#search").fill("nonexistent-case-control")
        ready("list")
        expect(page.locator("#cases")).to_have_attribute("data-state", "empty")
        assert not errors and not failed, (errors, failed)
        browser.close()
    return {
        "status": "passed",
        "console_errors": 0,
        "failed_workflow_requests": 0,
        "security_rejections": 2,
        "comparison": "pass",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--recipe-file", type=Path, required=True)
    p.add_argument("--query", default="KeyError")
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--screenshot", type=Path)
    args = p.parse_args()
    results = []
    with tempfile.TemporaryDirectory(prefix="afl-browser-") as tmp:
        for _ in range(args.repeat):
            with socket.socket() as listener, (Path(tmp) / "server.log").open("w+") as log:
                listener.bind(("127.0.0.1", 0))
                listener.listen()
                port = listener.getsockname()[1]
                env = {**os.environ, "AGENT_FIX_LAB_HOME": str(args.home.resolve())}
                env.pop("PYTHONPATH", None)
                server = subprocess.Popen(
                    [
                        args.python,
                        "-m",
                        "uvicorn",
                        "agent_fix_lab.web:default_app",
                        "--factory",
                        "--fd",
                        str(listener.fileno()),
                    ],
                    cwd=tmp,
                    env=env,
                    pass_fds=(listener.fileno(),),
                    stdout=log,
                    stderr=log,
                )
                try:
                    url = f"http://127.0.0.1:{port}"
                    deadline = time.monotonic() + 15
                    while True:
                        try:
                            urllib.request.urlopen(url + "/api/cases", timeout=1).close()
                            break
                        except OSError:
                            if server.poll() is not None or time.monotonic() > deadline:
                                log.seek(0)
                                raise RuntimeError(log.read())
                            time.sleep(0.05)  # bounded server readiness, never UI synchronization
                    results.append(
                        workflow(
                            url,
                            json.loads(args.recipe_file.read_text()),
                            args.query,
                            args.screenshot,
                        )
                    )
                finally:
                    server.terminate()
                    server.wait(timeout=10)
    print(json.dumps({"fresh_server_runs": results}, indent=2))


if __name__ == "__main__":
    main()
