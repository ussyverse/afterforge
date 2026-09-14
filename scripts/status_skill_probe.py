"""Exercise real Hermes skill loading and CLI pre-agent assembly without inference.

Run with the project environment; supply a separate supported Hermes interpreter
and checkout. Only newly created temporary synthetic profiles are touched.
"""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from agent_fix_lab import status_evidence as se

PROBE = """
import hashlib, json
from agent.skill_commands import build_preloaded_skills_prompt
from cli import HermesCLI
prompt, loaded, missing = build_preloaded_skills_prompt(['afterforge-status-evidence-v1'])
if loaded:
    class Joined:
        def join(self, timeout): pass
    instance = HermesCLI.__new__(HermesCLI)
    instance._preload_skills_finalized = False
    instance._preload_skills_thread = Joined()
    instance._preload_skills_error = None
    instance._preload_skills_result = (prompt, loaded, missing)
    instance.system_prompt = 'synthetic base'
    HermesCLI.finalize_preloaded_skills(instance)
    assert instance.system_prompt.endswith(prompt)
    assert instance.preloaded_skills == loaded
print(json.dumps({'loaded':loaded, 'missing':missing, 'prompt':prompt}))
"""


def probe(home: Path, python: str, host: Path) -> dict:
    env = os.environ.copy()
    for key in ("HERMES_PROFILE", "HERMES_ACTIVE_PROFILE", "HERMES_PLATFORM"):
        env.pop(key, None)
    env.update(HERMES_HOME=str(home), PYTHONPATH=str(host))
    process = subprocess.run(
        [python, "-c", PROBE],
        cwd=host,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if process.returncode:
        raise RuntimeError(process.stderr)
    return json.loads(process.stdout.strip().splitlines()[-1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-python", required=True)
    parser.add_argument("--host-root", required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="status-skill-probe-") as temporary:
        root = Path(temporary).resolve()
        workspace = root / "workspace"
        workspace.mkdir()
        home = root / "home"
        state = se.initialize(home, workspace, workspace)
        absent = probe(home, args.host_python, args.host_root)
        assert absent["loaded"] == []
        se.transition(home, "enable", approved_digest=state["approval_digest"])
        active = probe(home, args.host_python, args.host_root)
        assert active["loaded"] == [se.SKILL_NAME] and not active["missing"]
        from agent_fix_lab.status_evidence_metrics import body

        assert body(se.render(workspace, workspace)) in active["prompt"]
        # Also verify the host's own disabled-skill setting blocks explicit preloading.
        config = json.loads((home / "config.yaml").read_text())
        config["skills"] = {"disabled": [se.SKILL_NAME]}
        (home / "config.yaml").write_text(json.dumps(config))
        assert probe(home, args.host_python, args.host_root)["loaded"] == []
        del config["skills"]
        (home / "config.yaml").write_text(json.dumps(config))
        se.transition(home, "disable")
        assert probe(home, args.host_python, args.host_root)["loaded"] == []
        se.transition(home, "enable", approved_digest=state["approval_digest"])
        se.transition(home, "remove")
        assert probe(home, args.host_python, args.host_root)["loaded"] == []
        print(
            json.dumps(
                {
                    "procedure_version": se.VERSION,
                    "procedure_sha256": state["procedure_sha256"],
                    "default_absent": True,
                    "enabled_exact_body": True,
                    "cli_pre_agent_assembly": True,
                    "native_disabled_blocked": True,
                    "disabled_absent": True,
                    "removed_absent": True,
                    "model_calls": 0,
                }
            )
        )


if __name__ == "__main__":
    main()
