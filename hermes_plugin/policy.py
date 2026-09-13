"""Versioned, explicitly approved one-shot reminder lifecycle. No test execution."""

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

MESSAGE = (
    "Before final delivery, check required verification for the current edits. "
    "Do not treat unrelated command success or tests from before the edits as proof. "
    "If required checks failed, continue repair or clearly report the blocker. "
    "If they passed, finish normally; do not rerun solely because of this reminder."
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def candidate(scope):
    scope = Path(scope)
    if not scope.is_absolute() or scope.is_symlink() or not scope.is_dir():
        raise ValueError("Scope must be an existing absolute project directory")
    return {
        "version": 1,
        "kind": "verification-reminder",
        "scope": str(scope.resolve()),
        "message": MESSAGE,
    }


def directive(policy, coding=False, attempt=0, changed_paths=None, **kwargs):
    if (
        policy.get("version") != 1
        or policy.get("kind") != "verification-reminder"
        or policy.get("message") != MESSAGE
    ):
        return None
    if coding is not True or type(attempt) is not int or attempt != 0:
        return None
    if not isinstance(changed_paths, list) or not 1 <= len(changed_paths) <= 256:
        return None
    scope = Path(policy["scope"])
    if not scope.is_absolute():
        return None
    for value in changed_paths:
        if not isinstance(value, str) or len(value) > 4096:
            return None
        path = Path(value)
        if not path.is_absolute() or ".." in path.parts or not path.is_relative_to(scope):
            return None
    return {"action": "continue", "message": MESSAGE}


def evaluate(policy):
    """Deterministic integration contract, explicitly not model efficacy."""
    scope = policy["scope"]
    positive = directive(policy, coding=True, attempt=0, changed_paths=[scope + "/synthetic.py"])
    controls = [
        directive(policy, coding=False, changed_paths=[scope + "/synthetic.py"]),
        directive(policy, coding=True, attempt=1, changed_paths=[scope + "/synthetic.py"]),
        directive(policy, coding=True, changed_paths=["relative.py"]),
        directive(policy, coding=True, changed_paths=[]),
        directive(policy, coding=True, changed_paths=[scope + "/../outside.py"]),
    ]
    return {
        "candidate_digest": digest(policy),
        "status": "pass" if positive and not any(controls) else "fail",
        "evaluation_kind": "synthetic-hook-contract",
        "behavioral_efficacy": "not-run",
    }


@contextmanager
def locked(root):
    root = Path(root)
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    with (root / "lifecycle.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield root


def read(root):
    path = Path(root) / "lifecycle.json"
    if not path.exists():
        return {"generation": 0, "active": None, "events": []}
    if path.stat().st_size > 262144:
        raise ValueError("Lifecycle file too large")
    return json.loads(path.read_text())


def transition(directory, action, expected_generation, policy=None, approved_digest=None):
    with locked(directory) as root:
        state = read(root)
        if state["generation"] != expected_generation:
            raise ValueError("State changed; inspect before retrying")
        if len(state["events"]) >= 128:
            raise ValueError("Lifecycle event limit reached")
        previous = state["active"]
        if action == "activate":
            if policy != candidate(policy["scope"]) or approved_digest != digest(policy):
                raise ValueError("Approval must bind the exact supported candidate")
            receipt = evaluate(policy)
            if receipt["status"] != "pass":
                raise ValueError("Candidate failed contract evaluation")
            active = {
                "policy": policy,
                "digest": approved_digest,
                "evaluation": receipt,
                "authority": "local-caller-declared",
            }
        elif action == "rollback":
            if not state["events"]:
                raise ValueError("No transition to roll back")
            active = state["events"][-1]["previous"]
        else:
            raise ValueError("Unsupported lifecycle action")
        state["generation"] += 1
        state["active"] = active
        state["events"].append(
            {"action": action, "previous": previous, "generation": state["generation"]}
        )
        fd, tmp = tempfile.mkstemp(dir=root)
        try:
            with os.fdopen(fd, "w") as output:
                json.dump(state, output)
                output.flush()
                os.fsync(output.fileno())
            os.replace(tmp, root / "lifecycle.json")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return state


def hook(root, **kwargs):
    try:
        active = read(root)["active"]
        if active and digest(active["policy"]) == active["digest"]:
            result = directive(active["policy"], **kwargs)
            receipt = {
                "policy_digest": active["digest"],
                "session_digest": digest(str(kwargs.get("session_id", ""))),
                "coding": kwargs.get("coding") is True,
                "attempt": kwargs.get("attempt"),
                "directive_emitted": result is not None,
                "evidence_kind": "hook-invocation-not-model-efficacy",
            }
            fd, temporary = tempfile.mkstemp(dir=root)
            try:
                with os.fdopen(fd, "w") as output:
                    json.dump(receipt, output)
                os.replace(
                    temporary,
                    Path(root) / ("last-directive.json" if result else "last-abstention.json"),
                )
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            return result
    except Exception:
        return None
    return None
