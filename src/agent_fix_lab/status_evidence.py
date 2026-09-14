"""Explicit, default-off skill delivery in newly created isolated Hermes homes.

No integration with native policy state or automatic tool selection. Same-user
processes are trusted; this is not an OS sandbox or a race-proof filesystem guard.
"""

import argparse
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

VERSION = "status-evidence-v1"
SKILL_NAME = "afterforge-status-evidence-v1"
STATE = ".afterforge-status-evidence.json"
LEDGER = ".afterforge-status-events.jsonl"
MAX_TURNS = 12
TIMEOUT = 240


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def procedure() -> str:
    return Path(__file__).with_name("status_evidence_skill.md").read_text(encoding="utf-8")


def canonical(path: Path, *, exists: bool = True) -> Path:
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts or path.resolve() != path:
        raise ValueError("Require an absolute canonical path without symlinks")
    if any(c in str(path) for c in "\n\r\x00`!${}"):
        raise ValueError("Unsafe scope characters")
    if exists and not path.is_dir():
        raise ValueError("Directory does not exist")
    return path


def _atomic(path: Path, content: str) -> None:
    if path.is_symlink():
        raise ValueError("Refuse symlink metadata")
    fd, temporary = tempfile.mkstemp(prefix=".status-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _skill(home: Path) -> Path:
    return home / "skills" / SKILL_NAME / "SKILL.md"


def render(workspace: Path, project: Path) -> str:
    return (
        procedure()
        + "\nApproved workspace (absolute): "
        + str(workspace)
        + "\nStarting project (absolute): "
        + str(project)
        + "\nDo not expand this workspace scope.\n"
    )


def _identity(workspace: Path, project: Path) -> dict:
    body = render(workspace, project)
    identity = {
        "version": VERSION,
        "workspace": str(workspace),
        "project": str(project),
        "procedure_sha256": digest(procedure().encode()),
        "delivered_skill_sha256": digest(body.encode()),
    }
    identity["approval_digest"] = digest(json.dumps(identity, sort_keys=True).encode())
    return identity


def initialize(home: Path, workspace: Path, project: Path) -> dict:
    home = canonical(home, exists=False)
    workspace, project = canonical(workspace), canonical(project)
    if not project.is_relative_to(workspace):
        raise ValueError("Project must be inside workspace")
    if home.is_relative_to(workspace) or workspace.is_relative_to(home):
        raise ValueError("Isolated home and workspace must be disjoint")
    # mkdir(exist_ok=False) intentionally refuses ALL existing profiles, live or not.
    home.mkdir(mode=0o700)
    state = {**_identity(workspace, project), "enabled": False, "removed": False, "generation": 0}
    config = {
        "model": {"default": "gpt-5.6-luna", "provider": "openai-codex"},
        "agent": {"max_turns": MAX_TURNS, "reasoning_effort": "low"},
        "terminal": {"backend": "local", "cwd": str(project), "timeout": 60},
        "approvals": {"mode": "manual", "single_query_mode": "deny", "unattended_mode": "deny"},
        "memory": {"memory_enabled": False, "user_profile_enabled": False},
        "curator": {"enabled": False},
        "compression": {"enabled": False},
        "security": {"redact_secrets": True},
    }
    _atomic(home / "config.yaml", json.dumps(config, indent=2))  # JSON is valid YAML.
    _atomic(home / STATE, json.dumps(state, indent=2))
    _atomic(home / LEDGER, json.dumps({"action": "init", **state}) + "\n")
    return state


@contextmanager
def locked(home: Path):
    home = canonical(home)
    lock = home / ".afterforge-status.lock"
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield home
    finally:
        os.close(fd)


def inspect(home: Path) -> dict:
    home = canonical(home)
    path = home / STATE
    if path.is_symlink():
        raise ValueError("Refuse symlink state")
    state = json.loads(path.read_text())
    for field in ("workspace", "project"):
        canonical(Path(state[field]))
    return state


def _record(home: Path, action: str, state: dict) -> None:
    # Lock held by caller; retain historical approvals and removal events.
    fd = os.open(home / LEDGER, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps({"action": action, **state}) + "\n")
    _atomic(home / STATE, json.dumps(state, indent=2))


def _withdraw(home: Path, state: dict) -> None:
    target = _skill(home)
    for parent in (target.parent.parent, target.parent):
        if parent.is_symlink():
            raise ValueError("Refuse symlink skill directory")
    if target.is_symlink():
        raise ValueError("Refuse symlink skill")
    if target.exists():
        if digest(target.read_bytes()) != state["delivered_skill_sha256"]:
            raise ValueError("Refuse deletion of changed skill")
        if set(target.parent.iterdir()) != {target}:
            raise ValueError("Refuse removal with unowned skill files")
        target.unlink()
        target.parent.rmdir()


def transition(home: Path, action: str, *, approved_digest: str | None = None) -> dict:
    if action not in ("enable", "disable", "remove"):
        raise ValueError("Unknown transition")
    with locked(home):
        state = inspect(home)
        if action == "enable":
            expected = _identity(Path(state["workspace"]), Path(state["project"]))
            if state["removed"] or any(state[k] != v for k, v in expected.items()):
                raise ValueError("Removed or changed procedure: initialize a new isolated home")
            if approved_digest != state["approval_digest"]:
                raise ValueError("Explicit approval of exact procedure and scope required")
            target = _skill(home)
            for parent in (target.parent.parent, target.parent):
                if parent.is_symlink():
                    raise ValueError("Refuse symlink skill directory")
            if target.exists() or target.is_symlink():
                if not state["enabled"] or target.is_symlink():
                    raise ValueError("Refuse replacing existing skill")
                if digest(target.read_bytes()) != state["delivered_skill_sha256"]:
                    raise ValueError("Changed installed skill")
            else:
                target.parent.mkdir(parents=True, mode=0o700)
                _atomic(target, render(Path(state["workspace"]), Path(state["project"])))
            state["enabled"] = True
        else:
            _withdraw(home, state)
            state["enabled"] = False
            state["removed"] = action == "remove" or state["removed"]
        state["generation"] += 1
        _record(home, action, state)
        return state


def command(home: Path, query_file: Path, *, hermes: str = "hermes") -> tuple[list[str], dict]:
    state = inspect(home)
    project = canonical(Path(state["project"]))
    workspace = canonical(Path(state["workspace"]))
    if not project.is_relative_to(workspace):
        raise ValueError("Project escaped approved workspace")
    cmd = [
        hermes,
        "chat",
        "--query-file",
        str(Path(query_file).resolve()),
        "--quiet",
        "--provider",
        "openai-codex",
        "--model",
        "gpt-5.6-luna",
        "--reasoning",
        "low",
        "--toolsets",
        "terminal,file",
        "--max-turns",
        str(MAX_TURNS),
        "--in",
        str(project),
    ]
    if state["enabled"]:
        expected = _identity(workspace, project)
        if state["removed"] or any(state[k] != v for k, v in expected.items()):
            raise ValueError("Procedure or scope changed since approval")
        target = _skill(home)
        if (
            target.resolve() != target
            or digest(target.read_bytes()) != state["delivered_skill_sha256"]
        ):
            raise ValueError("Installed skill mismatch")
        cmd += ["--skills", SKILL_NAME]
    elif _skill(home).exists() or _skill(home).is_symlink():
        raise ValueError("Disabled state has discoverable procedure")
    env = os.environ.copy()
    for key in (
        "HERMES_PROFILE",
        "HERMES_ACTIVE_PROFILE",
        "HERMES_ACCEPT_HOOKS",
        "PYTHONPATH",
        "AFTERFORGE_SOURCE_ID",
        "HERMES_YOLO_MODE",
        "HERMES_PLATFORM",
        "HERMES_SESSION_PLATFORM",
    ):
        env.pop(key, None)
    env.update(HERMES_HOME=str(home), HERMES_YOLO_MODE="0", PYTHONDONTWRITEBYTECODE="1")
    return cmd, env


def run(home: Path, query_file: Path, *, hermes: str = "hermes") -> int:
    # Hold lifecycle lock until process completion; no wrapper disable/run race.
    with locked(home):
        cmd, env = command(home, query_file, hermes=hermes)
        child = subprocess.Popen(cmd, env=env, cwd=inspect(home)["project"], start_new_session=True)
        try:
            return child.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
            return 124


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "inspect", "enable", "disable", "remove", "run"])
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--approve-digest")
    parser.add_argument("--query-file", type=Path)
    parser.add_argument("--hermes", default="hermes")
    args = parser.parse_args()
    if args.action == "init":
        if args.workspace is None or args.project is None:
            parser.error("init requires --workspace and --project")
        result = initialize(args.home, args.workspace, args.project)
    elif args.action == "inspect":
        result = inspect(args.home)
    elif args.action == "run":
        if args.query_file is None:
            parser.error("run requires --query-file")
        raise SystemExit(run(args.home, args.query_file, hermes=args.hermes))
    else:
        result = transition(args.home, args.action, approved_digest=args.approve_digest)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
