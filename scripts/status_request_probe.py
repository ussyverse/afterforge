"""Offline real-CLI/Codex/SDK request-boundary contracts. Synthetic data only."""

import argparse
import json
import os
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from agent_fix_lab import status_evidence as se
from agent_fix_lab.status_evidence_metrics import body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-python", required=True)
    parser.add_argument("--host-root", required=True, type=Path)
    args = parser.parse_args()
    entry = Path(__file__).with_name("status_request_entry.py")
    outcomes = {}
    with tempfile.TemporaryDirectory(prefix="status-request-probe-") as temporary:
        root = Path(temporary).resolve()
        for mode in (
            "enabled",
            "baseline",
            "disabled",
            "removed",
            "changed-body",
            "marker-only",
            "missing-observer",
        ):
            case = root / mode
            workspace = case / "workspace"
            workspace.mkdir(parents=True)
            settings = workspace / "settings.json"
            settings.write_text('{"synthetic":true}')
            home = case / "home"
            state = se.initialize(home, workspace, workspace)
            if mode != "baseline":
                se.transition(home, "enable", approved_digest=state["approval_digest"])
            if mode in ("disabled", "removed"):
                se.transition(home, "disable" if mode == "disabled" else "remove")
            enabled = se.inspect(home)["enabled"]
            query = case / "query.txt"
            query.write_text("Synthetic offline task: read settings.json and report its content.")
            rendered_body = body(se.render(workspace, workspace))
            approved = case / "approved.txt"
            approved.write_text(rendered_body)
            cfg = {
                "attempt": mode,
                "host_identity": "pinned-offline-synthetic",
                "procedure_version": se.VERSION,
                "procedure_sha256": se.digest(se.procedure().encode()),
                "approved_body_file": str(approved),
                "approved_body_sha256": se.digest(rendered_body.encode()),
                "evidence_file": str(case / "observation.jsonl"),
                "enabled": enabled,
                "model": "gpt-5.6-luna",
                "query_sha256": se.digest(query.read_bytes()),
                "probe_read_path": str(settings),
            }
            config = case / "observer.json"
            config.write_text(json.dumps(cfg))
            command, _ = se.command(home, query)
            if mode in ("changed-body", "marker-only"):
                skill = home / "skills" / se.SKILL_NAME / "SKILL.md"
                text = skill.read_text()
                skill.write_text(
                    text.replace("eight individual", "eighty individual")
                    if mode == "changed-body"
                    else text.split("---", 2)[0]
                    + "---\nname: "
                    + se.SKILL_NAME
                    + "\ndescription: Synthetic marker-only test\n---\n# Afterforge bounded status evidence, version 1\n"
                )
            env = {
                k: os.environ[k]
                for k in ("PATH", "HOME", "USER", "LANG", "TERM")
                if k in os.environ
            }
            env.update(HERMES_HOME=str(home), PYTHONPATH=str(args.host_root), HERMES_YOLO_MODE="0")
            cmd = [
                args.host_python,
                str(entry),
                "--host-root",
                str(args.host_root),
                "--observation-config",
                str(config),
                "--offline",
            ]
            if mode == "missing-observer":
                cmd.append("--missing-observer")
            process = subprocess.run(
                cmd + ["--", *command[1:]],
                env=env,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            events = [
                json.loads(line) for line in (case / "observation.jsonl").read_text().splitlines()
            ]
            first = [e for e in events if e["event"] == "first-task-request"]
            tool_gates = [e for e in events if e["event"] == "first-task-tool-gate"]
            if mode in ("changed-body", "marker-only", "missing-observer"):
                assert process.returncode == 86, (mode, process.returncode, process.stderr[-3000:])
                assert not tool_gates
                assert (first[0]["outcome"] == "mismatch") if first else mode == "missing-observer"
                outcomes[mode] = "mismatch" if first else "unknown"
            else:
                assert process.returncode == 0, (mode, process.returncode, process.stderr[-3000:])
                assert len(first) == 1, (mode, events, process.stdout[-2000:])
                want = "verified-present" if enabled else "verified-absent"
                assert first[0]["outcome"] == want, (mode, events)
                assert tool_gates and first[0]["monotonic_ns"] < tool_gates[0]["monotonic_ns"]
                submitted = next(e for e in events if e["event"] == "request-submitted")
                stub = next(e for e in events if e["event"] == "stub-final-request" and e["task"])
                assert (
                    submitted["request_sha256"]
                    == first[0]["request_sha256"]
                    == stub["request_sha256"]
                )
                assert any(e["event"] == "stub-final-request" and not e["task"] for e in events)
                with sqlite3.connect((home / "state.db").as_uri() + "?mode=ro", uri=True) as db:
                    stored = db.execute("select prompt from system_prompts").fetchall()
                assert stored and all(
                    "Afterforge bounded status evidence" not in r[0] for r in stored
                )
                outcomes[mode] = want
            print(json.dumps({"case": mode, "outcome": outcomes[mode]}), flush=True)
    print(
        json.dumps(
            {
                "offline_request_boundary": "passed",
                "cases": outcomes,
                "provider_credentials": False,
                "network_inference": False,
                "procedure_sha256": se.digest(se.procedure().encode()),
            }
        )
    )


if __name__ == "__main__":
    main()
