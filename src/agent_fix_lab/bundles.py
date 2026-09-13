"""Portable reviewed source projections. Never exports original conversations."""

import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import Field

from .adapters import selected_config
from .models import Case, Contract, Recipe, Run, SourceRecord, Status, digest
from .runner import git, resolve_recipe

README = (
    "Inspect every source and assertion before import --reviewed. This bundle contains "
    "selected code, not historical transcripts. Use agent-fix-lab bundle-validate FILE, "
    "then bundle-import FILE --reviewed, then run the returned recipe ID. "
    "Execution is local trusted pytest, not an OS sandbox. Original historical revisions "
    "may be unknown; imported source projections get new local Git commits."
)


class Bundle(Contract):
    format: Literal["agent-fix-lab.regression.v1"] = "agent-fix-lab.regression.v1"
    case_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    problem: str = Field(min_length=1, max_length=4000)
    expected_behavior: str = Field(min_length=1, max_length=4000)
    intended_failure: str = Field(min_length=1, max_length=2000)
    provenance: Literal["derived", "synthetic"]
    original_historical_revisions: Literal["unknown"] = "unknown"
    source_revisions: dict[str, str]
    source_files: dict[str, dict[str, str]]
    assertion: str
    dependencies: Literal["pytest"] = "pytest"
    command: Literal["python -m pytest reviewed-assertion"] = "python -m pytest reviewed-assertion"
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    output_limit_bytes: int = Field(default=65536, ge=1024, le=1048576)
    baseline: dict = Field(default_factory=dict)
    current_configuration: dict = Field(default_factory=dict)
    observed_status: Status
    result_status: Status = "not-run"
    reviewed_at_export: Literal[True] = True
    redaction_manifest: list[str]
    readme: str = README
    checksums: dict[str, str]
    integrity: str


def safe_path(value):
    p = PurePosixPath(value)
    if (
        not value
        or p.is_absolute()
        or ".." in p.parts
        or str(p) != value
        or any(x.startswith(".") for x in p.parts)
        or "\\" in value
        or ":" in value
        or p.suffix not in {".py", ".json", ".txt"}
    ):
        raise ValueError("Unsafe bundle source path")
    return p


def privacy_check(text):
    # Additional guard, not proof that arbitrary code contains no proprietary data.
    patterns = [
        r"/home/[\w-]+/",
        r"/Users/[\w-]+/",
        r"gh[pousr]_[A-Za-z0-9]{20,}",
        r"-----BEGIN .*PRIVATE KEY",
        r"(?i)(password|api_key|secret)\s*[=:]\s*[\"\'][^\"\']{8,}",
    ]
    if any(re.search(p, text) for p in patterns):
        raise ValueError("Bundle contains excluded personal-path or secret-like content")


def file_checksums(body):
    files = {"assertion.py": body["assertion"]}
    for variant, mapping in body["source_files"].items():
        for name, content in mapping.items():
            files[variant + "/" + name] = content
    return {k: hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()}


def validate(path):
    if Path(path).stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Bundle exceeds 2MiB limit")
    raw = Path(path).read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("Bundle exceeds 2MiB limit")
    data = Bundle.model_validate_json(raw).model_dump()
    if set(data["source_files"]) != {"faulty", "corrected"} or set(data["source_revisions"]) != {
        "faulty",
        "corrected",
    }:
        raise ValueError("Bundle requires both source variants")
    if not data["assertion"].strip() or len(data["assertion"]) > 262144:
        raise ValueError("Missing or oversized assertion")
    for variant, files in data["source_files"].items():
        if not files or len(files) > 50:
            raise ValueError("Each variant requires 1..50 selected source files")
        for name, content in files.items():
            safe_path(name)
            if len(content) > 262144:
                raise ValueError("Oversized source file")
        if not re.fullmatch("[a-f0-9]{40,64}", data["source_revisions"][variant]):
            raise ValueError("Invalid source revision identity")
    if data["baseline"] != selected_config(data["baseline"]) or data[
        "current_configuration"
    ] != selected_config(data["current_configuration"]):
        raise ValueError("Configuration contains excluded fields")
    if data["checksums"] != file_checksums(data):
        raise ValueError("Bundle file checksum mismatch")
    if data["integrity"] != digest({k: v for k, v in data.items() if k != "integrity"}):
        raise ValueError("Bundle manifest integrity mismatch")
    privacy_check(raw.decode())
    return data


def export_bundle(
    lab, recipe_id, destination, *, problem, expected, failure, files, approved=False
):
    if not approved:
        raise ValueError("Explicit sanitized source/description review is required for export")
    recipe = resolve_recipe(Recipe(**lab.store.get("recipe", recipe_id)))
    if not recipe.reviewed:
        raise ValueError("Recipe must be reviewed before export")
    if not files or len(files) > 50:
        raise ValueError("Select 1..50 non-secret source/fixture files")
    sources = {}
    for variant in ("faulty", "corrected"):
        revision = getattr(recipe, variant + "_revision")
        mapping = {}
        for name in files:
            safe_path(name)
            mode = git(recipe.repository, "ls-tree", revision, "--", name).decode().split(" ")[0]
            if mode not in ("100644", "100755"):
                raise ValueError("Bundle sources must be regular tracked files, not links")
            mapping[name] = git(recipe.repository, "show", revision + ":" + name).decode("utf-8")
        sources[variant] = mapping
    detail = lab.detail(recipe.case_id)
    body = Bundle(
        case_id=digest(recipe.case_id),
        problem=problem,
        expected_behavior=expected,
        intended_failure=failure,
        provenance="synthetic" if recipe.provenance == "synthetic" else "derived",
        source_revisions={"faulty": recipe.faulty_revision, "corrected": recipe.corrected_revision},
        source_files=sources,
        assertion=Path(recipe.test_file).read_text(),
        observed_status=detail["observations"]["observed_status"],
        result_status=lab.comparison(recipe_id)["status"],
        timeout_seconds=recipe.timeout_seconds,
        output_limit_bytes=recipe.output_limit_bytes,
        redaction_manifest=[
            "original conversation omitted",
            "source session/message IDs omitted",
            "historical tool outputs omitted",
            "annotations omitted",
            "local paths omitted",
            "only explicitly approved code files included",
            "descriptions supplied separately and reviewed",
            "configuration omitted unless allowlisted",
        ],
        checksums={},
        integrity="",
    ).model_dump()
    baselines = [b for b in lab.store.all("baseline") if b["case_id"] == recipe.case_id]
    if baselines:
        body["baseline"] = selected_config(baselines[-1]["baseline"]["fields"])
        body["current_configuration"] = selected_config(baselines[-1]["current"]["fields"])
    body["checksums"] = file_checksums(body)
    body["integrity"] = digest({k: v for k, v in body.items() if k != "integrity"})
    privacy_check(json.dumps(body))
    destination = Path(destination)
    # Exclusive creation prevents overwriting other evidence. Full validation precedes delivery.
    with tempfile.TemporaryDirectory() as tmp:
        candidate = Path(tmp) / "bundle.json"
        candidate.write_text(json.dumps(body, indent=2))
        validate(candidate)
        with destination.open("x", encoding="utf-8") as out:
            out.write(candidate.read_text())
    os.chmod(destination, 0o600)
    return {"path": str(destination), "case_id": body["case_id"], "integrity": body["integrity"]}


def import_bundle(lab, path, reviewed=False):
    data = validate(path)
    key = data["integrity"]
    try:
        return lab.store.get("bundle-import", key)
    except KeyError:
        pass
    root = lab.store.root / "bundles" / key
    root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Interrupted filesystem preparation is discarded only inside our unique temporary directory.
    with tempfile.TemporaryDirectory(dir=root.parent, prefix="preparing-") as temporary:
        tmp = Path(temporary)
        repo = tmp / "repository"
        repo.mkdir()
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(tmp),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        }

        def command(*args):
            return (
                subprocess.check_output(
                    ["git", "-C", str(repo), "-c", "core.hooksPath=/dev/null", *args],
                    env=env,
                    stderr=subprocess.PIPE,
                )
                .decode()
                .strip()
            )

        command("init", "-q", "--template=")
        command("config", "user.name", "Agent Fix Lab bundle")
        command("config", "user.email", "bundle@example.invalid")
        revisions = {}
        previous = set()
        for variant in ("faulty", "corrected"):
            for old in previous:
                (repo / old).unlink()
            for name, content in data["source_files"][variant].items():
                dest = repo / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content)
            previous = set(data["source_files"][variant])
            command("add", ".")
            command("commit", "-qm", variant, "--allow-empty")
            revisions[variant] = command("rev-parse", "HEAD")
        (tmp / "assertion.py").write_text(data["assertion"])
        (tmp / "README.txt").write_text(data["readme"])
        if not root.exists():
            root.mkdir(mode=0o700)
            (tmp / "repository").rename(root / "repository")
            (tmp / "assertion.py").rename(root / "assertion.py")
            (tmp / "README.txt").rename(root / "README.txt")
    cid = data["case_id"]
    source = SourceRecord(
        id=cid,
        source_id="bundle:" + key,
        parser="bundle.v1",
        session_id=cid,
        message_id=0,
        timestamp_seconds=0,
        payload_digest=key,
    )
    run = Run(
        id=cid,
        source=source,
        capture_source="bundle-projection",
        observed_status=data["observed_status"],
        output=data["problem"],
        unknown=["original_historical_revision", "private_provenance_omitted"],
    )
    case = Case(id=cid, run_id=cid, incident_group=cid, provenance=data["provenance"])
    recipe = Recipe(
        id=key,
        case_id=cid,
        repository=str(root / "repository"),
        faulty_revision=revisions["faulty"],
        corrected_revision=revisions["corrected"],
        test_file=str(root / "assertion.py"),
        test_sha256=data["checksums"]["assertion.py"],
        expected_behavior=data["expected_behavior"],
        intended_failure=data["intended_failure"],
        reviewed=reviewed,
        provenance=data["provenance"],
        timeout_seconds=data["timeout_seconds"],
        output_limit_bytes=data["output_limit_bytes"],
    )
    record = {
        "schema_version": 1,
        "id": key,
        "case_id": cid,
        "recipe_id": key,
        "reviewed": reviewed,
        "status": "not-run",
        "source_revisions": data["source_revisions"],
        "original_historical_revisions": "unknown",
    }
    documents = [("recipe", recipe), ("bundle-import", record)]
    try:
        lab.store.get("case", cid)
    except KeyError:
        documents += [("case", case), ("run", run)]
    lab.store.put_many(documents)
    return record
