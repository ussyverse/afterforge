"""Audit exact Git index blobs and optionally every reachable committed tree."""

import argparse
import re
import subprocess
from pathlib import PurePosixPath


def audit(revision=None):
    command = (
        ["git", "ls-tree", "-r", "--name-only", "-z", revision]
        if revision
        else ["git", "ls-files", "-z"]
    )
    paths = subprocess.check_output(command).decode().split("\0")
    problems = []
    count = 0
    patterns = [
        rb"/home/[a-zA-Z0-9_-]+/",
        rb"/Users/[a-zA-Z0-9_-]+/",
        rb"gh[pousr]_[A-Za-z0-9]{20,}",
        rb"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        rb"(?i)(api_key|password|token)\s*[=:]\s*[\"\'][A-Za-z0-9_/-]{24,}",
    ]
    for name in filter(None, paths):
        count += 1
        path = PurePosixPath(name)
        if any(
            part in {"private", "dataset", ".vault", "node_modules"} for part in path.parts
        ) or re.search(r"\.(db|sqlite|log)(-|\.|$)|\.env", name):
            problems.append((name, "excluded artifact"))
        body = subprocess.check_output(["git", "show", (revision or "") + ":" + name])
        if b"\0" in body:
            problems.append((name, "unreviewed binary"))
        for pattern in patterns:
            if re.search(pattern, body):
                problems.append((name, "sensitive-content pattern"))
    if problems:
        raise SystemExit(str(problems))
    print(
        f"{revision or 'Index'} privacy audit: {count} text files, zero excluded artifacts or sensitive-pattern matches"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    audit()
    if args.history:
        for revision in subprocess.check_output(["git", "rev-list", "--all"]).decode().splitlines():
            audit(revision)
