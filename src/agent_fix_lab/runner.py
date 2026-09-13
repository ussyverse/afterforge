"""Reviewed pytest runner. Workspace/environment isolation, not an OS security sandbox."""

import hashlib
import io
import os
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from .models import Recipe, ReproductionResult, Comparison


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def resolve_recipe(recipe):
    repo = Path(recipe.repository).expanduser().resolve(strict=True)
    if git(repo, "rev-parse", "--show-toplevel").decode().strip() != str(repo):
        raise ValueError("Recipe repository must be its Git root")
    test = Path(recipe.test_file).expanduser().resolve(strict=True)
    if test.suffix != ".py" or len(test.read_bytes()) > 262144:
        raise ValueError("Reviewed assertion must be a Python file <=256KiB")
    sha = hashlib.sha256(test.read_bytes()).hexdigest()
    if sha != recipe.test_sha256:
        raise ValueError("Reviewed test changed; review again")
    if recipe.dependencies != ["pytest"]:
        raise ValueError(
            "Only the isolated runner pytest dependency is supported; vendor reviewed fixtures"
        )
    values = recipe.model_dump()
    for name in ("faulty_revision", "corrected_revision"):
        value = values[name]
        if value.startswith("-") or not value:
            raise ValueError("Invalid revision")
        values[name] = git(repo, "rev-parse", "--verify", value + "^{commit}").decode().strip()
    values.update(repository=str(repo), test_file=str(test))
    return Recipe(**values)


def unpack_revision(repo, revision, workspace):
    blob = git(repo, "archive", "--format=tar", revision)
    if len(blob) > 50 * 1024 * 1024:
        raise ValueError("Repository archive exceeds 50MiB runner limit")
    with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
        total = 0
        for item in archive.getmembers():
            path = Path(item.name)
            if path.is_absolute() or ".." in path.parts or item.issym() or item.islnk():
                raise ValueError("Archive traversal or links are not allowed")
            total += item.size
            if total > 100 * 1024 * 1024:
                raise ValueError("Expanded archive exceeds runner limit")
            if item.isfile():
                dest = workspace / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.extractfile(item).read())


def classify_result(code, xml_path, output, stopped):
    if stopped:
        return "inconclusive", stopped, (0, 0, 0, 0), ""
    try:
        tree = ET.parse(xml_path)
        cases = tree.findall(".//testcase")
        failures = tree.findall(".//testcase/failure")
        errors = tree.findall(".//testcase/error")
        skipped = tree.findall(".//testcase/skipped")
        counts = len(cases), len(failures), len(errors), len(skipped)
        evidence = "\n".join((x.text or "") + x.attrib.get("message", "") for x in failures)
    except (OSError, ET.ParseError):
        return "inconclusive", "Missing or unreadable pytest process report", (0, 0, 0, 0), ""
    if not cases or errors or skipped or code not in (0, 1):
        return (
            "inconclusive",
            "No tests, collection/setup error, skip or abnormal exit",
            counts,
            evidence,
        )
    if code == 0 and not failures:
        return "pass", "Collected assertions passed", counts, evidence
    if code == 1 and failures:
        return "fail", "Collected assertions failed", counts, evidence
    return "inconclusive", "Contradictory process evidence", counts, evidence


def execute(recipe, variant):
    if not recipe.reviewed:
        raise ValueError("Recipe has not been explicitly reviewed")
    recipe = resolve_recipe(recipe)
    revision = getattr(recipe, variant + "_revision")
    started = time.time()
    dirty = hashlib.sha256(git(recipe.repository, "diff", "HEAD", "--binary")).hexdigest()
    with tempfile.TemporaryDirectory(prefix="afl-run-") as directory:
        base = Path(directory)
        workspace = base / "project"
        workspace.mkdir()
        unpack_revision(recipe.repository, revision, workspace)
        assertion_dir = base / "assertions"
        assertion_dir.mkdir()
        assertion = assertion_dir / "test_regression.py"
        assertion.write_bytes(Path(recipe.test_file).read_bytes())
        report = base / "report.xml"
        outpath = base / "output.log"
        # No user config, autoloaded plugins, shell, or inherited credential environment.
        env = {
            "PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin",
            "HOME": str(base),
            "TMPDIR": str(base),
            "LANG": "C.UTF-8",
            "TZ": "UTC",
            "PYTHONPATH": str(workspace) + os.pathsep + str(workspace / "src"),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONHASHSEED": "0",
        }
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-c",
            "/dev/null",
            "--confcutdir",
            str(assertion_dir),
            "--junitxml",
            str(report),
            str(assertion),
        ]
        stopped = None
        with outpath.open("wb") as output_file:
            process = subprocess.Popen(
                command,
                cwd=workspace,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=output_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                while process.poll() is None:
                    if time.time() - started > recipe.timeout_seconds:
                        stopped = "timeout"
                        break
                    if outpath.stat().st_size > recipe.output_limit_bytes:
                        stopped = "output-limit"
                        break
                    time.sleep(0.02)
            finally:
                # Kill descendants even when their parent has already exited.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
        raw = outpath.read_bytes()[: recipe.output_limit_bytes + 1]
        if len(raw) > recipe.output_limit_bytes:
            stopped = "output-limit"
        try:
            output = raw[: recipe.output_limit_bytes].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            stopped = "unreadable-output"
            output = raw[: recipe.output_limit_bytes].decode("utf-8", errors="replace")
        status, reason, counts, failure_evidence = classify_result(
            process.returncode, report, output, stopped
        )
        if (
            variant == "faulty"
            and status == "fail"
            and recipe.intended_failure not in failure_evidence
        ):
            status, reason = "inconclusive", "Failure did not match reviewed intended assertion"
        output = output.replace(str(base), "<workspace>")
        return ReproductionResult(
            id=uuid.uuid4().hex,
            recipe_id=recipe.id,
            variant=variant,
            revision=revision,
            dirty_diff_sha256=dirty,
            test_sha256=recipe.test_sha256,
            timestamp_seconds=started,
            duration_seconds=time.time() - started,
            command=["python", "-m", "pytest", "reviewed:test_regression.py"],
            exit_code=process.returncode,
            status=status,
            reason=reason,
            output=output,
            tests=counts[0],
            failures=counts[1],
            errors=counts[2],
            skipped=counts[3],
        )


def compare(recipe, faulty=None, corrected=None):
    values = {
        "recipe_id": recipe.id,
        "faulty_result_id": faulty.id if faulty else None,
        "corrected_result_id": corrected.id if corrected else None,
    }
    if not faulty or not corrected:
        return Comparison(**values, reason="Both fresh implementations must be run")
    compatible = (
        faulty.test_sha256 == corrected.test_sha256 == recipe.test_sha256
        and faulty.recipe_id == corrected.recipe_id == recipe.id
        and faulty.revision == recipe.faulty_revision
        and corrected.revision == recipe.corrected_revision
        and faulty.tests == corrected.tests
        and faulty.tests > 0
    )
    if not compatible or "inconclusive" in (faulty.status, corrected.status):
        return Comparison(
            **values, status="inconclusive", reason="Incomplete or incompatible evidence"
        )
    if faulty.status == "fail" and corrected.status == "pass":
        return Comparison(
            **values,
            status="pass",
            reason="Derived regression verified"
            if recipe.provenance == "derived"
            else "Reviewed assertion fails before and passes after",
        )
    return Comparison(
        **values, status="fail", reason="Required red/green contrast was not observed"
    )
