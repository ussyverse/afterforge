"""Synthetic contract fixtures only: NOT recorded or measured Jev output."""

import hashlib
import json

import pytest

from agent_fix_lab import jev


def fixture():
    return {
        "model": "jev-test-double",
        "usage": {"input_tokens": 10, "output_tokens": 0},
        "answers": {
            "failure_kind": {
                "type": "choice",
                "choice": "verification_gap",
                "confidence": 0.9,
                "probabilities": {k: 1.0 if k == "verification_gap" else 0.0 for k in jev.LABELS},
            },
            "completion_supported": {"type": "noul", "noul": 0.1},
            "explicit_correction": {"type": "noul", "noul": 0.8},
        },
    }


def test_advisory():
    r = jev.interpret(fixture(), jev.payload("Synthetic test failed, agent said complete."))
    assert r["authority"] == "none" and r["requires_human_review"]
    assert r["threshold_status"] == "uncalibrated_do_not_automate"


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -0.1, 1.1, "0.5", None])
def test_invalid_probabilities(value):
    r = fixture()
    r["answers"]["explicit_correction"]["noul"] = value
    with pytest.raises(jev.JevError):
        jev.interpret(r, jev.payload("synthetic"))


@pytest.mark.parametrize("kind", ["missing", "sum", "label", "model", "type", "usage", "winner"])
def test_malformed(kind):
    r = fixture()
    if kind == "missing":
        del r["answers"]["explicit_correction"]
    if kind == "sum":
        r["answers"]["failure_kind"]["probabilities"]["tool_failure"] = 0.5
    if kind == "label":
        r["answers"]["failure_kind"]["choice"] = "deploy"
    if kind == "model":
        r["model"] = None
    if kind == "type":
        r["answers"]["completion_supported"]["type"] = "choice"
    if kind == "usage":
        r["usage"] = {"input_tokens": -1}
    if kind == "winner":
        r["answers"]["failure_kind"]["choice"] = "tool_failure"
    with pytest.raises(jev.JevError):
        jev.interpret(r, jev.payload("synthetic"))


def test_preview_no_network(tmp_path, capsys, monkeypatch):
    p = tmp_path / "summary"
    p.write_text("Synthetic event")
    monkeypatch.setattr(jev, "send", lambda *a: pytest.fail("unexpected network"))
    assert jev.main([str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "preview_no_network"


def test_approval_and_key_precede_connection():
    req = jev.payload("synthetic")
    digest = hashlib.sha256(jev.encoded(req)).hexdigest()
    for key, approval in [("test-key", "bad"), ("", digest)]:
        with pytest.raises(jev.JevError):
            jev.send(req, key, approval, lambda *a, **k: pytest.fail("network"))


def test_transport_contract():
    captured = {}

    class Connection:
        def __init__(self, host, timeout):
            captured.update(host=host, timeout=timeout)

        def request(self, method, path, body, headers):
            captured.update(method=method, path=path, body=json.loads(body), headers=headers)

        def getresponse(self):
            return self

        status = 200

        def read(self, n):
            return json.dumps(fixture()).encode()

        def close(self):
            captured["closed"] = True

    req = jev.payload("synthetic")
    digest = hashlib.sha256(jev.encoded(req)).hexdigest()
    assert jev.send(req, "test-only", digest, Connection)["mode"] == "shadow_only"
    assert captured["host"] == "api.typesafe.ai" and captured["path"] == "/v1/systemone"
    assert captured["body"] == req and captured["closed"]


@pytest.mark.parametrize("status", [301, 401, 422, 429, 529])
def test_errors_no_retry(status):
    calls = []

    class Connection:
        def __init__(self, *a, **k):
            calls.append(1)

        def request(self, *a, **k):
            pass

        def getresponse(self):
            return self

        def close(self):
            pass

    Connection.status = status
    req = jev.payload("synthetic")
    with pytest.raises(jev.JevError):
        jev.send(req, "test", hashlib.sha256(jev.encoded(req)).hexdigest(), Connection)
    assert len(calls) == 1
