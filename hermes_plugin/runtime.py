"""Lazy managed backend, using only the documented storage seam from Hermes."""

import fcntl
import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager

from .hooks import Capture
from .schemas import SCHEMAS

VERSION = "0.5.0"
RESPONSE_LIMIT = 65536
LOG_LIMIT = 1048576


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

    def fingerprint(self, source=None):
        source = source or self.source
        files = [
            source / "pyproject.toml",
            source / "uv.lock",
            *sorted(
                p
                for p in (source / "src").rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
            ),
            *[
                source / name
                for name in ("README.md", "LICENSE", "NOTICE", "RELEASE.json")
                if (source / name).is_file()
            ],
        ]
        h = hashlib.sha256()
        for file in files:
            if file.is_symlink():
                raise ValueError("Refusing symlink installation source")
            h.update(file.relative_to(source).as_posix().encode())
            h.update(b"\0")
            h.update(file.read_bytes())
            h.update(b"\0")
        return h.hexdigest()

    @staticmethod
    def private_dir(path):
        if path.is_symlink():
            raise ValueError("Refusing symlink managed directory")
        path.mkdir(mode=0o700, exist_ok=True)
        path.chmod(0o700)
        return path

    @staticmethod
    def private_file(path):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)
        return os.fdopen(fd, "wb")

    @contextmanager
    def installation_lock(self):
        fd = os.open(self.root() / "runtime.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def environment(self):
        root = self.root()
        work = self.private_dir(root / "workspaces")
        env = {**os.environ, "HERMES_HOME": str(root.parent.parent), "TMPDIR": str(work)}
        for key in tuple(env):
            if key.startswith(("UV_", "PYTHON", "PIP_")) or key in ("VIRTUAL_ENV", "CONDA_PREFIX"):
                env.pop(key)
        env["PYTHONNOUSERSITE"] = "1"
        return env

    def run_process(
        self, command, *, payload=None, timeout=120, env=None, log=None, output_limit=RESPONSE_LIMIT
    ):
        """Drain pipes in bounded chunks; neither RAM nor a spool file grows unchecked."""
        if payload is not None and len(payload) > LOG_LIMIT:
            raise ValueError("Backend request exceeded limit")
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.root(),
            env=env or self.environment(),
            start_new_session=True,
            umask=0o077,
        )
        output = bytearray()
        produced = log.tell() if log is not None else 0
        deadline = time.monotonic() + timeout
        try:
            with selectors.DefaultSelector() as selector:
                for pipe in (process.stdout, process.stderr):
                    os.set_blocking(pipe.fileno(), False)
                    selector.register(pipe, selectors.EVENT_READ)
                pending = memoryview(payload or b"")
                if pending:
                    os.set_blocking(process.stdin.fileno(), False)
                    selector.register(process.stdin, selectors.EVENT_WRITE)
                else:
                    process.stdin.close()
                while selector.get_map():
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Managed process timed out; inspect private jobs log")
                    for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                        pipe = key.fileobj
                        if pipe is process.stdin:
                            try:
                                pending = pending[os.write(pipe.fileno(), pending[:8192]) :]
                            except BrokenPipeError:
                                pending = memoryview(b"")
                            if not pending:
                                selector.unregister(pipe)
                                pipe.close()
                            continue
                        chunk = os.read(pipe.fileno(), 8192)
                        if not chunk:
                            selector.unregister(pipe)
                            pipe.close()
                            continue
                        remaining = LOG_LIMIT - produced
                        if log is not None:
                            log.write(chunk[:remaining])
                            log.flush()
                        produced += len(chunk)
                        if produced > LOG_LIMIT:
                            raise ValueError(
                                "Managed process output exceeded limit; inspect private jobs log"
                            )
                        if pipe is process.stdout:
                            if len(output) + len(chunk) > output_limit:
                                raise ValueError(
                                    "Backend response exceeded limit; use standalone CLI for full evidence"
                                )
                            output.extend(chunk)
                process.wait(timeout=max(0.01, deadline - time.monotonic()))
            if process.returncode:
                raise RuntimeError(
                    "Managed process failed; inspect private jobs log and run hermes afterforge setup"
                )
            return bytes(output)
        finally:
            # Kill the whole group even if the parent exited but descendants kept pipes open.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            for pipe in (process.stdin, process.stdout, process.stderr):
                pipe.close()

    def invoke(self, command, request=None, timeout=120):
        jobs = self.private_dir(self.root() / "jobs")
        with self.private_file(jobs / "backend.log") as log:
            return json.loads(
                self.run_process(
                    command,
                    payload=json.dumps(request).encode() if request is not None else None,
                    timeout=timeout,
                    log=log,
                )
            )

    def installation(self):
        marker = json.loads((self.root() / "runtime-install.json").read_text())
        if not isinstance(marker, dict):
            raise ValueError("Invalid installation marker")
        return marker

    def generation(self, marker):
        name = marker.get("generation", "")
        if marker.get("schema_version") != 2 or not re.fullmatch(r"[0-9a-f]{32}", name):
            raise ValueError("Invalid managed runtime generation")
        parent = self.root() / "runtimes"
        path = parent / name
        if parent.is_symlink() or path.is_symlink() or (path / "environment").is_symlink():
            raise ValueError("Refusing symlink managed runtime")
        return path

    def executable(self):
        try:
            marker = self.installation()
        except FileNotFoundError:
            marker = {}
        if "schema_version" in marker:
            return self.generation(marker) / "environment/bin/python"
        if (self.root() / "runtime").is_symlink():
            raise ValueError("Refusing symlink runtime")
        return self.root() / "runtime/bin/python"

    def ready(self):
        try:
            marker = self.installation()
            executable = self.executable()
            if not executable.is_file() or not os.access(executable, os.X_OK):
                return False
            if marker.get("schema_version") == 2:
                installed = json.loads(
                    (self.generation(marker) / "resolved-manifest.json").read_text()
                )
                return marker == installed and marker.get("doctor_passed") is True
            # Keep a working pre-generation installation available during migration.
            return marker.get("plugin_version") in ("0.4.0", VERSION) and bool(
                marker.get("source_digest")
            )
        except (OSError, ValueError, KeyError, TypeError):
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
            marker = self.installation()
            result["update_available"] = (
                marker.get("source_digest") != self.fingerprint()
                or marker.get("plugin_version") != VERSION
                or marker.get("schema_version") != 2
            )
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
        with self.installation_lock():
            return self.setup_locked()

    def setup_locked(self):
        root = self.root()
        for name in ("data", "source-snapshots", "workspaces", "exports", "jobs"):
            self.private_dir(root / name)
        uv = shutil.which("uv")
        if not uv:
            raise RuntimeError("Install uv, then run hermes fixlab setup")
        if (root / "runtime").is_symlink():
            raise ValueError("Refusing a symlink runtime")
        # Never rename a venv: generated console-script shebangs contain absolute paths.
        # The one atomic marker replacement publishes a fully verified generation.
        generations = self.private_dir(root / "runtimes")
        stage = self.private_dir(generations / uuid.uuid4().hex)
        published = False
        try:
            digest = self.fingerprint()
            source = self.private_dir(stage / "source")
            for name in (
                "pyproject.toml",
                "uv.lock",
                "README.md",
                "LICENSE",
                "NOTICE",
                "RELEASE.json",
            ):
                if (self.source / name).is_file():
                    shutil.copyfile(self.source / name, source / name)
            shutil.copytree(
                self.source / "src",
                source / "src",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            if self.fingerprint(source) != digest:
                raise ValueError("Installation source changed during snapshot; retry setup")
            env = self.environment()
            env["UV_PROJECT_ENVIRONMENT"] = str(stage / "environment")
            env["UV_CACHE_DIR"] = str(self.private_dir(root / "uv-cache"))
            common = [
                "--locked",
                "--no-dev",
                "--no-default-groups",
                "--project",
                str(source),
                "--python",
                "3.11",
                "--no-config",
                "--no-progress",
            ]
            with self.private_file(root / "jobs/setup.log") as log:

                def run(command):
                    # The shared setup log is bounded across all installation subprocesses.
                    return self.run_process(
                        command, env=env, log=log, timeout=600, output_limit=LOG_LIMIT
                    )

                uv_version = run([uv, "--version"]).decode().strip()
                requirements = run(
                    [
                        uv,
                        "export",
                        *common,
                        "--format",
                        "requirements.txt",
                        "--no-emit-project",
                        "--no-header",
                    ]
                )
                with self.private_file(stage / "requirements.lock") as file:
                    file.write(requirements)
                run([uv, "sync", *common, "--no-editable"])
                python = str(stage / "environment/bin/python")
                doctor = json.loads(
                    run([python, "-m", "agent_fix_lab.cli", "--home", str(root / "data"), "doctor"])
                )
                if doctor.get("package_version") != VERSION or set(
                    doctor.get("components", {})
                ) != {"triage", "petrichor", "correction-aware-learning"}:
                    raise RuntimeError("Managed runtime doctor failed; previous runtime retained")
                packages = json.loads(
                    run(
                        [
                            python,
                            "-c",
                            (
                                "import importlib.metadata as m,json; print(json.dumps(sorted("
                                "[{'name':d.metadata['Name'],'version':d.version} for d in m.distributions()],"
                                "key=lambda d:d['name'].lower())))"
                            ),
                        ]
                    )
                )
            if self.fingerprint() != digest:
                raise ValueError("Installation source changed during setup; retry setup")
            marker = {
                "schema_version": 2,
                "generation": stage.name,
                "plugin_version": VERSION,
                "application_version": doctor["package_version"],
                "source_digest": digest,
                "doctor_passed": True,
                "installer": uv_version,
                "packages": packages,
                "lock_sha256": hashlib.sha256((source / "uv.lock").read_bytes()).hexdigest(),
                "requirements_sha256": hashlib.sha256(requirements).hexdigest(),
            }
            raw = json.dumps(marker, sort_keys=True).encode()
            with self.private_file(stage / "resolved-manifest.json") as file:
                file.write(raw)
                file.flush()
                os.fsync(file.fileno())
            # A private sibling temporary marker also handles process interruption safely.
            fd, temporary = tempfile.mkstemp(prefix=".runtime-install-", dir=root)
            try:
                with os.fdopen(fd, "wb") as file:
                    file.write(raw)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary, root / "runtime-install.json")
                published = True
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            return {"runtime_ready": True, "installation": marker, "doctor": doctor}
        finally:
            if not published:
                # An asynchronous exception can arrive after replace succeeds but before
                # the Python flag is set. Never delete the generation the marker selects.
                try:
                    published = self.installation().get("generation") == stage.name
                except FileNotFoundError:
                    published = False
                except (OSError, ValueError):
                    # Uncertain ownership: retain rather than destroy a possibly live env.
                    published = True
                if not published:
                    shutil.rmtree(stage)

    def remove(self, confirm):
        with self.installation_lock():
            root = self.root()
            if not confirm or not (root / "runtime-install.json").is_file():
                raise ValueError(
                    "Owned runtime removal requires --confirm; application data is retained"
                )
            marker = self.installation()
            if "schema_version" in marker:
                self.generation(marker)
            for name in ("runtime", "runtimes", "uv-cache"):
                if (root / name).is_symlink():
                    raise ValueError("Refusing symlink managed directory")
            for name in ("runtime", "runtimes", "uv-cache"):
                if (root / name).exists():
                    shutil.rmtree(root / name)
            # Retain the ownership marker until cleanup completes so interrupted removal
            # can be retried. Readiness is false as soon as the executable is removed.
            (root / "runtime-install.json").unlink()
            return {"runtime_removed": True, "data_retained": True}

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
                    self.capture.complete(completed)
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

    def backend(self, operation, args):
        """Shared application bridge for explicit terminal/slash workflows."""
        try:
            if not self.ready():
                raise RuntimeError("Run hermes afterforge setup before using the workflow")
            return self.invoke(
                [str(self.executable()), "-m", "agent_fix_lab.plugin_bridge"],
                {"home": str(self.root() / "data"), "operation": operation, "args": args},
                timeout=self.config()[1],
            )
        except Exception as exc:
            return {
                "success": False,
                "status": "inconclusive",
                "error": {
                    "code": type(exc).__name__,
                    "message": "Workflow unavailable; inspect setup/doctor and supplied identifiers",
                },
            }

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
                    data = policy.status(root)
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
            elif action in ("demo", "review", "retained-plan", "retained-check"):
                mapping = {
                    "demo": ("synthetic_demo", ()),
                    "review": ("review_queue", ("offset", "limit")),
                    "retained-plan": ("retained_plan", ("recipe_id", "target_revision")),
                    "retained-check": ("retained_check", ("plan_id", "approve_digest", "reviewed")),
                }
                operation, fields = mapping[action]
                result = self.backend(operation, {field: getattr(args, field) for field in fields})
            elif action in ("current-check-plan", "verify-current"):
                if not self.ready():
                    raise RuntimeError("Run hermes fixlab setup before checking")
                payload = {"recipe_id": args.recipe_id}
                if action == "verify-current":
                    payload["approve_digest"] = args.approve_digest
                result = self.invoke(
                    [str(self.executable()), "-m", "agent_fix_lab.plugin_bridge"],
                    {
                        "home": str(self.root() / "data"),
                        "operation": action.replace("-", "_"),
                        "args": payload,
                    },
                    timeout=self.config()[1],
                )
            elif action == "setup":
                result = {"success": True, "data": self.setup()}
            elif action == "uninstall-runtime":
                result = {"success": True, "data": self.remove(args.confirm)}
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
                    cwd=self.root(),
                    env=self.environment(),
                    umask=0o077,
                )
                return
            else:
                name = {"doctor": "status", "export": "report", "scan": "scan"}[action]
                payload = {"case_id": args.case_id} if action == "export" else {}
                result = json.loads(self.handle("fixlab_" + name, payload))
            print(json.dumps(result, indent=2))
            if result.get("success") is not True or (
                action in ("verify-current", "retained-check")
                and result.get("data", {}).get("status") != "pass"
            ):
                raise SystemExit(1)
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
