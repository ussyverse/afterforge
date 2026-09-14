"""Synthetic private runtime fixtures, including real locked uv installs (no browser/host)."""

import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from test_plugin import ROOT, Context, Runtime


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    root = tmp_path / "profile/plugin-data/agent-fix-lab"
    root.mkdir(parents=True, mode=0o700)
    obj = Runtime(Context(), ROOT)
    monkeypatch.setattr(obj, "root", lambda: root)
    return obj


@pytest.mark.parametrize("fd", [1, 2])
def test_production_output_is_bounded(runtime, fd):
    start = time.monotonic()
    with pytest.raises(ValueError, match="exceeded limit"):
        runtime.invoke(
            [sys.executable, "-c", f"import os\nwhile True: os.write({fd}, b'x'*8192)"], timeout=5
        )
    assert time.monotonic() - start < 5
    log = runtime.root() / "jobs/backend.log"
    assert log.stat().st_size <= 1048576
    assert log.stat().st_mode & 0o777 == 0o600


def test_timeout_kills_descendant_holding_pipes(runtime):
    start = time.monotonic()
    with pytest.raises(RuntimeError, match="timed out"):
        runtime.invoke(
            [sys.executable, "-c", "import os,time\nif os.fork() == 0: time.sleep(30)"], timeout=0.2
        )
    assert time.monotonic() - start < 3


def test_private_log_before_production_and_sanitized_error(runtime):
    log = runtime.root() / "jobs/backend.log"
    command = [
        sys.executable,
        "-c",
        (
            "import os,sys; from pathlib import Path; "
            f"assert Path({str(log)!r}).stat().st_mode & 0o777 == 0o600; "
            "sys.stderr.write('SYNTHETIC_PRIVATE_CANARY'); sys.exit(9)"
        ),
    ]
    with pytest.raises(RuntimeError, match="private jobs log") as exc:
        runtime.invoke(command)
    assert "SYNTHETIC_PRIVATE_CANARY" not in str(exc.value)
    assert log.read_text() == "SYNTHETIC_PRIVATE_CANARY"


def test_invoke_handles_bidirectional_backpressure_and_host_isolation(runtime, monkeypatch):
    before = dict(os.environ)
    for name in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PIP_TARGET"):
        monkeypatch.setenv(name, "synthetic-host-environment")
    result = runtime.invoke(
        [
            sys.executable,
            "-c",
            (
                "import json,os,sys; sys.stderr.write('x'*100000); sys.stderr.flush(); "
                "value=json.load(sys.stdin); "
                "print(json.dumps({'size':len(value['input']),'home':os.environ['HERMES_HOME'],"
                "'isolated':all(k not in os.environ for k in "
                "['PYTHONPATH','PYTHONHOME','VIRTUAL_ENV','UV_PROJECT_ENVIRONMENT','PIP_TARGET'])}))"
            ),
        ],
        {"input": "x" * 200000},
    )
    assert result == {"size": 200000, "home": str(runtime.root().parent.parent), "isolated": True}
    assert os.environ["VIRTUAL_ENV"] == "synthetic-host-environment"
    monkeypatch.undo()
    assert dict(os.environ) == before


@pytest.mark.parametrize("name", ["runtime", "runtimes", "jobs", "uv-cache"])
def test_symlink_managed_directories_rejected(runtime, tmp_path, name):
    outside = tmp_path / "unowned"
    outside.mkdir()
    sentinel = outside / "keep"
    sentinel.write_text("synthetic retained data")
    (runtime.root() / name).symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        runtime.setup()
    assert sentinel.read_text() == "synthetic retained data"
    assert not (runtime.root() / "runtime-install.json").exists()


def test_private_log_symlink_rejected(runtime, tmp_path):
    outside = tmp_path / "keep"
    outside.write_text("retained")
    (runtime.root() / "jobs").mkdir()
    (runtime.root() / "jobs/backend.log").symlink_to(outside)
    with pytest.raises(OSError):
        runtime.invoke([sys.executable, "-c", "print('{}')"])
    assert outside.read_text() == "retained"


@pytest.mark.parametrize("operation", ["setup", "remove"])
def test_installation_file_lock_serializes_processes(runtime, operation, monkeypatch):
    # A separate OS process holds the same lock, not merely a Python thread mutex.
    lock = runtime.root() / "runtime.lock"
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import fcntl,sys; "
                f"f=open({str(lock)!r},'w'); fcntl.flock(f,fcntl.LOCK_EX); "
                "print('locked',flush=True); sys.stdin.read(1)"
            ),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    entered = threading.Event()
    monkeypatch.setattr(runtime, "setup_locked", lambda: entered.set())
    try:
        assert process.stdout.readline().strip() == "locked"
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                runtime.setup if operation == "setup" else lambda: runtime.remove(False)
            )
            time.sleep(0.1)
            assert not future.done() and not entered.is_set()
            process.stdin.write("x")
            process.stdin.flush()
            if operation == "setup":
                future.result(timeout=5)
                assert entered.is_set()
            else:
                with pytest.raises(ValueError, match="confirm"):
                    future.result(timeout=5)
    finally:
        process.kill() if process.poll() is None else None
        process.wait()
        process.stdin.close()
        process.stdout.close()


def test_real_locked_install_upgrade_failures_and_removal(runtime, tmp_path, monkeypatch):
    """Exercise uv, installed doctor/entrypoints, failed lock/doctor/publication, and migration."""
    source = tmp_path / "synthetic-install-source"
    source.mkdir()
    for name in ("pyproject.toml", "uv.lock", "README.md", "LICENSE", "NOTICE"):
        shutil.copyfile(ROOT / name, source / name)
    shutil.copytree(ROOT / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__"))
    runtime.source = source
    # The supported runtime selects its own writable cache, regardless of a hostile host override.
    monkeypatch.setenv("UV_CACHE_DIR", "/synthetic-read-only-cache")
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", str(tmp_path / "host-must-not-exist"))
    initial_environment = dict(os.environ)
    root = runtime.root()
    (root / "data").mkdir()
    retained = root / "data/synthetic-evidence.txt"
    retained.write_text("immutable synthetic evidence")
    result = runtime.setup()
    assert result["runtime_ready"] and runtime.ready()
    assert not runtime.status()["update_available"]
    manifest = result["installation"]
    assert manifest["application_version"] == "0.5.0"
    assert manifest["installer"].startswith("uv ")
    generation = runtime.generation(manifest)
    requirements = (generation / "requirements.lock").read_bytes()
    assert b"--hash=sha256:" in requirements and b"annotated-types==" in requirements
    assert b"36a391039b286a5571c91574267efe644d8ec1fe" in requirements
    assert manifest["requirements_sha256"] == hashlib.sha256(requirements).hexdigest()
    assert manifest["lock_sha256"] == hashlib.sha256((source / "uv.lock").read_bytes()).hexdigest()
    packages = {row["name"].lower(): row["version"] for row in manifest["packages"]}
    assert packages["agent-fix-lab"] == "0.5.0" and "annotated-types" in packages
    assert "playwright" not in packages and "ruff" not in packages
    assert dict(os.environ) == initial_environment
    assert not (tmp_path / "host-must-not-exist").exists()
    python = runtime.executable()
    marker = (root / "runtime-install.json").read_bytes()
    for path in (
        root / "runtime-install.json",
        generation / "resolved-manifest.json",
        generation / "requirements.lock",
        root / "jobs/setup.log",
        root / "runtime.lock",
    ):
        assert path.stat().st_mode & 0o777 == 0o600

    def old_still_works():
        assert (root / "runtime-install.json").read_bytes() == marker
        assert runtime.executable() == python and runtime.ready()
        doctor = runtime.invoke([str(python), "-m", "agent_fix_lab.cli", "doctor"])
        assert doctor["package_version"] == "0.5.0"
        assert list((root / "runtimes").iterdir()) == [generation]
        assert retained.read_text() == "immutable synthetic evidence"

    # Real uv --locked rejects metadata drift instead of resolving new dependencies.
    project = source / "pyproject.toml"
    original_project = project.read_text()
    project.write_text(original_project.replace("fastapi==0.141.1", "fastapi==0.1.0"))
    with pytest.raises(RuntimeError, match="Managed process failed"):
        runtime.setup()
    old_still_works()
    assert runtime.status()["update_available"]
    project.write_text(original_project)

    # A successful install with a broken doctor must never become ready.
    cli = source / "src/agent_fix_lab/cli.py"
    original_cli = cli.read_text()
    cli.write_text("raise RuntimeError('SYNTHETIC_DOCTOR_FAILURE')\n" + original_cli)
    with pytest.raises(RuntimeError, match="Managed process failed"):
        runtime.setup()
    old_still_works()
    cli.write_text(original_cli)

    # Interruption immediately before commit leaves the pointer and old executable intact.
    module = sys.modules[Runtime.__module__]
    replace = module.os.replace

    def interrupt(src, dst):
        if Path(dst) == root / "runtime-install.json":
            raise KeyboardInterrupt("synthetic interruption")
        return replace(src, dst)

    with monkeypatch.context() as patcher:
        patcher.setattr(module.os, "replace", interrupt)
        with pytest.raises(KeyboardInterrupt):
            runtime.setup()
    old_still_works()

    # A real successful second generation retains executable entrypoints in both generations.
    second = runtime.setup()
    assert second["installation"]["generation"] != manifest["generation"]
    assert runtime.ready() and python.exists()
    for executable in (python.parent / "afterforge", runtime.executable().parent / "agent-fix-lab"):
        assert runtime.invoke([str(executable), "doctor"])["package_version"] == "0.5.0"

    def interrupt_after_commit(src, dst):
        result = replace(src, dst)
        if Path(dst) == root / "runtime-install.json":
            raise KeyboardInterrupt("synthetic interruption after atomic commit")
        return result

    with monkeypatch.context() as patcher:
        patcher.setattr(module.os, "replace", interrupt_after_commit)
        with pytest.raises(KeyboardInterrupt):
            runtime.setup()
    assert runtime.ready(), "Committed generation must survive interruption after os.replace"
    assert (
        runtime.invoke([str(runtime.executable()), "-m", "agent_fix_lab.cli", "doctor"])[
            "package_version"
        ]
        == "0.5.0"
    )
    with pytest.raises(ValueError, match="confirm"):
        runtime.remove(False)
    assert runtime.ready()
    assert runtime.remove(True) == {"runtime_removed": True, "data_retained": True}
    assert not runtime.ready() and not (root / "runtimes").exists()
    assert not (root / "uv-cache").exists()
    assert retained.read_text() == "immutable synthetic evidence"


def test_legacy_runtime_remains_usable_until_explicit_removal(runtime):
    legacy = runtime.root() / "runtime/bin"
    legacy.mkdir(parents=True)
    (legacy / "python").symlink_to(sys.executable)
    (runtime.root() / "runtime-install.json").write_text(
        json.dumps({"plugin_version": "0.4.0", "source_digest": "synthetic-legacy-digest"})
    )
    assert runtime.ready()
    assert runtime.invoke([str(runtime.executable()), "-c", "print('{\"legacy\":true}')"]) == {
        "legacy": True
    }
    runtime.remove(True)
    assert not legacy.exists() and Path(sys.executable).is_file()
