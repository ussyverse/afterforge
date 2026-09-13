"""Export a reproducible native release from committed source, never the worktree.

All application/adapter/skill files ship byte-for-byte, alongside build metadata,
lockfile, legal notices and privacy documentation. Development-only material is
retained at the recorded source commit. No scanner-dependent filtering exists.
"""

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

FILES = {
    "plugin.yaml",
    "__init__.py",
    "pyproject.toml",
    "uv.lock",
    "LICENSE",
    "NOTICE",
    "docs/privacy.md",
}
ROOTS = ("src/", "hermes_plugin/", "skills/")


def git(repo, *args, **kwargs):
    return subprocess.check_output(["git", "-C", str(repo), *args], **kwargs)


def export(repo, revision, output):
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
        "source_repository": "https://github.com/ussyverse/agent-fix-lab",
        "source_commit": revision,
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
        "GIT_AUTHOR_NAME": "Agent Fix Lab release",
        "GIT_COMMITTER_NAME": "Agent Fix Lab release",
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument(
        "--previous", help="Previous release commit for a fast-forward release branch"
    )
    parser.add_argument("--sha-file", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    revision = export(repo, args.revision, args.output.resolve())
    result = {"source_commit": revision}
    if args.commit:
        result["release_commit"] = commit(repo, revision, args.output, args.previous)
        if args.sha_file:
            args.sha_file.write_text(result["release_commit"] + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
