"""Audit exact Git index blobs (not working-tree approximations)."""

import re
import subprocess
from pathlib import PurePosixPath


def audit():
    paths = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
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
        body = subprocess.check_output(["git", "show", ":" + name])
        if b"\0" in body:
            problems.append((name, "unreviewed binary"))
        for pattern in patterns:
            if re.search(pattern, body):
                problems.append((name, "sensitive-content pattern"))
    if problems:
        raise SystemExit(str(problems))
    print(
        f"Index privacy audit: {count} text files, zero excluded artifacts or sensitive-pattern matches"
    )


if __name__ == "__main__":
    audit()
