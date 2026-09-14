"""Export a reproducible native release from committed source, never the worktree.

All application/adapter/skill files ship byte-for-byte, alongside build metadata,
lockfile, legal notices and privacy documentation. Development-only material is
retained at the recorded source commit. No scanner-dependent filtering exists.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import tomllib
import urllib.request
from pathlib import Path

FILES = {
    "plugin.yaml",
    "__init__.py",
    "pyproject.toml",
    "uv.lock",
    "LICENSE",
    "NOTICE",
    "docs/privacy.md",
    "docs/interventions.md",
}
ROOTS = ("src/", "hermes_plugin/", "skills/")


def git(repo, *args, **kwargs):
    return subprocess.check_output(["git", "-C", str(repo), *args], **kwargs)


def repository_slug(value=None):
    value = value or os.environ.get("GITHUB_REPOSITORY", "ussyverse/afterforge")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("Expected GitHub owner/repository")
    return value


def source_version(path):
    # Export is not certification: malformed/legacy metadata remains visibly
    # unknown and must fail doctor/certification, never acquire a guessed version.
    try:
        return tomllib.loads(path.read_text())["project"]["version"]
    except (tomllib.TOMLDecodeError, KeyError):
        return None


def export(repo, revision, output, repository=None):
    revision = git(repo, "rev-parse", revision + "^{commit}").decode().strip()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Release output must be empty; nothing is overwritten")
    output.mkdir(parents=True, exist_ok=True)
    entries = git(repo, "ls-tree", "-rz", "--full-tree", revision).split(b"\0")
    hashes = {}
    for entry in entries:
        if not entry:
            continue
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        name = raw_name.decode()
        if (
            name not in FILES
            and not name.startswith(ROOTS)
            and name != "packaging/plugin-readme.md"
        ):
            continue
        if mode not in ("100644", "100755") or kind != "blob":
            raise ValueError("Release inputs must be regular files")
        destination = "README.md" if name == "packaging/plugin-readme.md" else name
        body = git(repo, "cat-file", "blob", oid)
        target = output / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        target.chmod(0o755 if mode == "100755" else 0o644)
        hashes[destination] = {"source": name, "sha256": hashlib.sha256(body).hexdigest()}
    if not FILES.issubset(hashes) or "README.md" not in hashes:
        raise ValueError("Incomplete committed release inputs")
    provenance = {
        "format_version": 1,
        "source_repository": "https://github.com/" + repository_slug(repository),
        "source_commit": revision,
        "version": source_version(output / "pyproject.toml"),
        "files": hashes,
    }
    (output / "RELEASE.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    return revision


def commit(repo, revision, output, previous=None):
    # A separate index protects the caller's working tree and staging area.
    with tempfile.TemporaryDirectory() as temp:
        env = {
            **os.environ,
            "GIT_INDEX_FILE": str(Path(temp) / "index"),
            "GIT_WORK_TREE": str(output.resolve()),
        }
        git(repo, "read-tree", "--empty", env=env)
        git(repo, "add", "--all", "--", str(output.resolve()), env=env)
        tree = git(repo, "write-tree", env=env).decode().strip()
    timestamp = git(repo, "show", "-s", "--format=%ct", revision).decode().strip()
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Afterforge release",
        "GIT_COMMITTER_NAME": "Afterforge release",
        "GIT_AUTHOR_EMAIL": "release@example.invalid",
        "GIT_COMMITTER_EMAIL": "release@example.invalid",
        "GIT_AUTHOR_DATE": f"{timestamp} +0000",
        "GIT_COMMITTER_DATE": f"{timestamp} +0000",
    }
    parents = ["-p", revision]
    if previous:
        parents += ["-p", previous]
    return (
        git(
            repo,
            "commit-tree",
            tree,
            *parents,
            env=env,
            input=f"Native distribution from {revision}\n".encode(),
        )
        .decode()
        .strip()
    )


def successful_run(repository, run_id, source, workflow):
    """Require completed exact-source CI, not a branch name or an earlier green run."""
    if not str(run_id).isdigit():
        raise ValueError("Expected numeric Actions run ID")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/actions/runs/{run_id}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + os.environ["GH_TOKEN"],
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        run = json.load(response)
    if not (
        run["head_sha"] == source
        and run["status"] == "completed"
        and run["conclusion"] == "success"
        and run["path"] == f".github/workflows/{workflow}.yml"
        and run["event"] in {"push", "workflow_dispatch"}
        and run["repository"]["full_name"] == repository
        and run["head_repository"]["full_name"] == repository
    ):
        raise ValueError("Required exact-source CI has not succeeded")
    return run["html_url"]


def native_distribution_sha(repository, run_id):
    """Read the exact immutable artifact from the already verified native run."""
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run(
            [
                "gh",
                "run",
                "download",
                str(run_id),
                "--repo",
                repository,
                "--name",
                "native-distribution",
                "--dir",
                directory,
            ],
            check=True,
            timeout=120,
            stdout=subprocess.DEVNULL,
        )
        value = (Path(directory) / "release.sha").read_text().strip()
        if not re.fullmatch(r"[a-f0-9]{40}", value):
            raise ValueError("Invalid native distribution artifact")
        return value


def stable_locator(repo, release, repository, app_run, native_run):
    """Validate downloaded native evidence against the exact distribution Git tree.

    Download the successful run's artifact independently: a same-source rebuilt
    distribution is not necessarily the distribution that native CI installed.
    No network publication happens here.
    """
    release = git(repo, "rev-parse", release + "^{commit}").decode().strip()
    raw = git(repo, "show", f"{release}:RELEASE.json")
    manifest = json.loads(raw)
    source = manifest["source_commit"]
    if manifest["source_repository"] != "https://github.com/" + repository:
        raise ValueError("Distribution repository mismatch")
    source_names = git(repo, "ls-tree", "-rz", "--name-only", source).decode().split("\0")
    expected = {
        "README.md" if name == "packaging/plugin-readme.md" else name: name
        for name in source_names
        if name in FILES or name.startswith(ROOTS) or name == "packaging/plugin-readme.md"
    }
    if {name: entry["source"] for name, entry in manifest["files"].items()} != expected:
        raise ValueError("Incomplete source projection in distribution manifest")
    checksums = {}
    for name, entry in manifest["files"].items():
        body = git(repo, "show", f"{release}:{name}")
        original = git(repo, "show", f"{source}:{entry['source']}")
        checksum = hashlib.sha256(body).hexdigest()
        if body != original or checksum != entry["sha256"]:
            raise ValueError("Distribution does not match committed source")
        checksums[name] = checksum
    names = set(git(repo, "ls-tree", "-rz", "--name-only", release).decode().split("\0")) - {""}
    if names != set(checksums) | {"RELEASE.json"}:
        raise ValueError("Unexpected distribution contents")
    version = tomllib.loads(git(repo, "show", f"{release}:pyproject.toml").decode())["project"][
        "version"
    ]
    if version != manifest["version"]:
        raise ValueError("Distribution version mismatch")
    checksums["RELEASE.json"] = hashlib.sha256(raw).hexdigest()
    ci = {
        "application": successful_run(repository, app_run, source, "validation"),
        "native": successful_run(repository, native_run, source, "native-plugin"),
    }
    if native_distribution_sha(repository, native_run) != release:
        raise ValueError("Distribution was not the exact native-tested artifact")
    return {
        "format_version": 1,
        "repository": repository,
        "version": version,
        "source_commit": source,
        "distribution_commit": release,
        "checksums": checksums,
        "ci": ci,
        "install": f"hermes plugins install {repository} --ref {release} --enable",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument(
        "--previous", help="Previous release commit for a fast-forward release branch"
    )
    parser.add_argument("--sha-file", type=Path)
    parser.add_argument("--repository", default=repository_slug())
    parser.add_argument("--certify", metavar="DISTRIBUTION_SHA")
    parser.add_argument("--app-run-id")
    parser.add_argument("--native-run-id")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    repository = repository_slug(args.repository)
    if args.certify:
        locator = stable_locator(
            repo, args.certify, repository, args.app_run_id, args.native_run_id
        )
        args.output.write_text(json.dumps(locator, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"certified": args.certify, "locator": str(args.output)}))
        return
    revision = export(repo, args.revision, args.output.resolve(), repository)
    result = {"source_commit": revision}
    if args.commit:
        result["release_commit"] = commit(repo, revision, args.output, args.previous)
        if args.sha_file:
            args.sha_file.write_text(result["release_commit"] + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
