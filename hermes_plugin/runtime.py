"""Lazy managed backend, using only the documented storage seam from Hermes."""

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile

from .hooks import Capture
from .schemas import SCHEMAS

VERSION = "0.4.0"


class Runtime:
    def __init__(self, ctx, source):
        self.ctx = ctx
        self.source = source
        self.capture = Capture()
        self.capture.enabled = ctx.get_config("capture", default=True) is True

    def config(self):
        capture = self.ctx.get_config("capture", default=True)
        limit = self.ctx.get_config("scan_limit", default=50)
        timeout = self.ctx.get_config("timeout", default=120)
        if (
            type(capture) is not bool
            or type(limit) is not int
            or not 1 <= limit <= 200
            or type(timeout) is not int
            or not 5 <= timeout <= 600
        ):
            raise ValueError(
                "Invalid configuration: capture boolean, scan_limit 1..200, timeout 5..600"
            )
        return limit, timeout

    def root(self):
        # Public API documented by both installed and live plugin guides. Lazy import.
        from plugins.plugin_storage import plugin_data_dir

        root = plugin_data_dir("agent-fix-lab")
        root.chmod(0o700)
        return root

    def fingerprint(self):
        files = [
            self.source / "pyproject.toml",
            self.source / "uv.lock",
            *sorted((self.source / "src").rglob("*.py")),
            *sorted((self.source / "src").rglob("*.js")),
            *sorted((self.source / "src").rglob("*.html")),
            *sorted((self.source / "src").rglob("*.css")),
        ]
        h = hashlib.sha256()
        for file in files:
            h.update(file.relative_to(self.source).as_posix().encode())
            h.update(file.read_bytes())
        return h.hexdigest()

    def invoke(self, command, request=None, timeout=120):
        root = self.root()
        work = root / "workspaces"
        work.mkdir(mode=0o700, exist_ok=True)
        env = {**os.environ, "HERMES_HOME": str(root.parent.parent), "TMPDIR": str(work)}
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=output,
                stderr=errors,
                cwd=root,
                env=env,
                start_new_session=True,
            )
            try:
                process.communicate(
                    json.dumps(request).encode() if request is not None else None, timeout=timeout
                )
            except BaseException:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise
            if process.returncode:
                raise RuntimeError(
                    "Managed backend failed. Run hermes fixlab setup to repair; inspect source/recipe locally."
                )
            output.seek(0)
            raw = output.read(65537)
            if len(raw) > 65536:
                raise ValueError(
                    "Backend response exceeded limit; use standalone CLI for full evidence"
                )
            return json.loads(raw)

    def executable(self):
        return self.root() / "runtime/bin/python"

    def ready(self):
        root = self.root()
        try:
            marker = json.loads((root / "runtime-install.json").read_text())
            return (
                self.executable().is_file()
                and marker["source_digest"] == self.fingerprint()
                and marker["plugin_version"] == VERSION
            )
        except (OSError, ValueError, KeyError):
            return False

    def status(self):
        self.config()
        root = self.root()
        result = {
            "runtime_ready": self.ready(),
            "plugin_version": VERSION,
            "setup_instruction": "hermes fixlab setup",
            "queued_sessions": len(self.capture.snapshot()),
            "legacy_skill_detected": (
                root.parent.parent / "skills/agent-fix-lab/SKILL.md"
            ).exists(),
            "migration": "Legacy skill is retained; native skill is agent-fix-lab:regression-workflow",
        }
        if result["runtime_ready"]:
            try:
                result["doctor"] = self.invoke(
                    [
                        str(self.executable()),
                        "-m",
                        "agent_fix_lab.cli",
                        "--home",
                        str(root / "data"),
                        "doctor",
                    ]
                )
            except Exception:
                result["runtime_ready"] = False
                result["repair_required"] = True
        return result

    def setup(self):
        self.config()
        root = self.root()
        for name in ("data", "source-snapshots", "workspaces", "exports", "jobs"):
            (root / name).mkdir(mode=0o700, exist_ok=True)
        uv = shutil.which("uv")
        if not uv:
            raise RuntimeError("Install uv, then run hermes fixlab setup")
        if (root / "runtime").is_symlink():
            raise ValueError("Refusing a symlink runtime")
        # Setup is explicit trusted local installation, never registration or a hook.
        log = root / "jobs/setup.log"
        with log.open("w") as stream:
            if not self.executable().exists():
                subprocess.run(
                    [uv, "venv", str(root / "runtime"), "--python", "3.11"],
                    check=True,
                    stdout=stream,
                    stderr=stream,
                    timeout=180,
                )
            subprocess.run(
                [
                    uv,
                    "pip",
                    "install",
                    "--reinstall-package",
                    "agent-fix-lab",
                    "--python",
                    str(self.executable()),
                    str(self.source),
                ],
                check=True,
                stdout=stream,
                stderr=stream,
                timeout=600,
            )
        log.chmod(0o600)
        doctor = self.invoke(
            [
                str(self.executable()),
                "-m",
                "agent_fix_lab.cli",
                "--home",
                str(root / "data"),
                "doctor",
            ]
        )
        marker = {
            "plugin_version": VERSION,
            "application_version": doctor["package_version"],
            "source_digest": self.fingerprint(),
        }
        (root / "runtime-install.json").write_text(json.dumps(marker))
        (root / "runtime-install.json").chmod(0o600)
        return {"runtime_ready": True, "installation": marker, "doctor": doctor}

    def validate(self, name, args):
        if not isinstance(args, dict):
            raise ValueError("Arguments must be an object")
        schema = SCHEMAS[name]["parameters"]
        if set(args) - set(schema["properties"]) or any(k not in args for k in schema["required"]):
            raise ValueError("Unexpected or missing tool arguments")
        for key, value in args.items():
            field = schema["properties"][key]
            kind = field.get("type")
            if kind == "string" and (
                not isinstance(value, str) or len(value) > field.get("maxLength", 4096)
            ):
                raise ValueError("Invalid text argument")
            if kind == "integer" and (
                type(value) is not int or not field["minimum"] <= value <= field["maximum"]
            ):
                raise ValueError("Invalid pagination")
            if kind == "boolean" and type(value) is not bool:
                raise ValueError("Expected boolean")
            if "enum" in field and value not in field["enum"]:
                raise ValueError("Invalid enum")
            if "pattern" in field and not re.fullmatch(field["pattern"], value):
                raise ValueError("Invalid identifier")

    def handle(self, name, args, **kwargs):
        try:
            self.validate(name, args)
            limit, timeout = self.config()
            if name == "fixlab_status":
                return json.dumps({"success": True, "data": self.status()})
            if not self.ready():
                raise RuntimeError("Missing or outdated runtime: run hermes fixlab setup")
            operation = name.removeprefix("fixlab_")
            args = dict(args)
            queue = {}
            if operation == "scan":
                queue = {
                    **self.ctx.state.get("pending_sessions", default={}),
                    **self.capture.snapshot(),
                }
                queue = dict(list(queue.items())[-32:])
                self.ctx.state.set("pending_sessions", queue)
                cursors = self.ctx.state.get("cursors", default={})
                session = args.get("session_id")
                key = session or "*"
                args.update(
                    source=str(self.root().parent.parent / "state.db"),
                    limit=limit,
                    after_id=cursors.get(key, 0),
                )
            response = self.invoke(
                [str(self.executable()), "-m", "agent_fix_lab.plugin_bridge"],
                {"home": str(self.root() / "data"), "operation": operation, "args": args},
                timeout=timeout,
            )
            if operation == "scan" and response.get("success"):
                cursor = response["data"].get("next_after_id")
                if cursor is not None:
                    cursors[key] = cursor
                self.ctx.state.set("cursors", dict(list(cursors.items())[-32:]))
                # Hints are retained until a later scan; global cursor is authoritative.
                self.ctx.state.set(
                    "last_scan",
                    {"status": "completed", "added": response["data"].get("added_cases", 0)},
                )
                if response["data"].get("scanned", limit) < limit:
                    completed = {k: v for k, v in queue.items() if not session or k == session}
                    with self.capture.lock:
                        for sid, metadata in completed.items():
                            if self.capture.pending.get(sid) == metadata:
                                self.capture.pending.pop(sid, None)
                    self.ctx.state.set(
                        "pending_sessions", {k: v for k, v in queue.items() if k not in completed}
                    )
            return json.dumps(response)
        except Exception as exc:
            return json.dumps(
                {
                    "success": False,
                    "error": {
                        "code": type(exc).__name__,
                        "message": str(exc)[:300]
                        if isinstance(exc, (ValueError, RuntimeError))
                        else "Operation failed; run hermes fixlab doctor or setup",
                    },
                    "status": "inconclusive",
                }
            )

    def pre_verify(self, **kwargs):
        try:
            from .policy import hook

            return hook(self.root() / "policies", **kwargs)
        except Exception:
            return None

    def command(self, args, **kwargs):
        try:
            action = args.fixlab_action
            if action == "policy":
                from . import policy

                root = self.root() / "policies"
                origin = None
                if args.case_id:
                    if args.operation not in ("propose", "activate"):
                        raise ValueError("Incident linkage is only for propose/activate")
                    if not self.ready():
                        raise RuntimeError("Run hermes fixlab setup before linking incidents")
                    response = self.invoke(
                        [str(self.executable()), "-m", "agent_fix_lab.plugin_bridge"],
                        {
                            "home": str(self.root() / "data"),
                            "operation": "policy_origin",
                            "args": {"case_id": args.case_id},
                        },
                    )
                    if not response.get("success"):
                        raise ValueError("Incident reference could not be verified")
                    origin = response["data"]
                if args.operation == "status":
                    data = policy.read(root)
                elif args.operation == "propose":
                    item = policy.candidate(args.scope or "", origin)
                    data = {"candidate": item, "evaluation": policy.evaluate(item)}
                else:
                    item = (
                        policy.candidate(args.scope or "", origin)
                        if args.operation == "activate"
                        else None
                    )
                    data = policy.transition(
                        root, args.operation, args.generation, item, args.approve_digest
                    )
                result = {"success": True, "data": data}
            elif action == "setup":
                result = {"success": True, "data": self.setup()}
            elif action == "uninstall-runtime":
                if (
                    not args.confirm
                    or not (self.root() / "runtime-install.json").is_file()
                    or (self.root() / "runtime").is_symlink()
                ):
                    raise ValueError(
                        "Owned runtime removal requires --confirm; application data is retained"
                    )
                shutil.rmtree(self.root() / "runtime")
                (self.root() / "runtime-install.json").unlink()
                result = {"success": True, "data": {"runtime_removed": True, "data_retained": True}}
            elif action == "serve":
                if not self.ready():
                    raise RuntimeError("Run hermes fixlab setup")
                subprocess.run(
                    [
                        str(self.executable()),
                        "-m",
                        "agent_fix_lab.cli",
                        "--home",
                        str(self.root() / "data"),
                        "serve",
                        "--port",
                        str(args.port),
                    ],
                    check=True,
                )
                return
            else:
                name = {"doctor": "status", "export": "report", "scan": "scan"}[action]
                payload = {"case_id": args.case_id} if action == "export" else {}
                result = json.loads(self.handle("fixlab_" + name, payload))
            print(json.dumps(result, indent=2))
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": {
                            "code": type(exc).__name__,
                            "message": "Command failed; inspect plugin settings or managed setup log",
                        },
                    }
                )
            )
            raise SystemExit(1) from None
