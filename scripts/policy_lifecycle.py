"""Host-only synthetic policy lifecycle, with separate CLI processes."""

import json
import os
import subprocess
from pathlib import Path


def policy_lifecycle(manager):
    home = Path(os.environ["HERMES_HOME"])
    assert (home / ".afl-isolated-test").exists()
    project = home / "synthetic-policy-project"
    project.mkdir(exist_ok=True)

    def command(*args):
        raw = subprocess.check_output(["hermes", "fixlab", "policy", *args], text=True)
        result = json.loads(raw)
        assert result["success"], result
        return result["data"]

    proposed = command("propose", "--scope", str(project))
    digest = proposed["evaluation"]["candidate_digest"]
    assert proposed["evaluation"]["behavioral_efficacy"] == "not-run"
    payload = {"coding": True, "attempt": 0, "changed_paths": [str(project / "synthetic.py")]}
    assert not any(manager.invoke_hook("pre_verify", **payload))
    command("activate", "--scope", str(project), "--approve-digest", digest, "--generation", "0")
    # Different CLI process sees persisted activation; manager reloads policy on each hook.
    assert command("status")["active"]["digest"] == digest
    results = manager.invoke_hook("pre_verify", **payload)
    assert any(isinstance(item, dict) and item.get("action") == "continue" for item in results)
    assert not any(manager.invoke_hook("pre_verify", **{**payload, "attempt": 1}))
    command("rollback", "--generation", "1")
    assert command("status")["active"] is None
    command("rollback", "--generation", "2")
    assert command("status")["active"] is None
    assert command("status")["generation"] == 2
    assert not any(manager.invoke_hook("pre_verify", **payload))
    return {"status": "pass", "kind": "synthetic-host-lifecycle", "behavioral_efficacy": "not-run"}
