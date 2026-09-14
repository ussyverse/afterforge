"""Prove a pinned real-host regression red/green without modifying that host."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

BASELINE_SHA256 = "f78960962d844315019e4f835f5116f6bbdaa41ff30d8b1e52901f521bbfb0b1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-python", type=Path, required=True)
    parser.add_argument("--host-root", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, required=True, help="New private directory; never reused"
    )
    args = parser.parse_args()
    source = args.host_root.resolve() / "tools/file_operations.py"
    if sha(source) != BASELINE_SHA256:
        raise RuntimeError(
            "Host source differs from the reproduced baseline; re-establish the baseline"
        )
    os.umask(0o077)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    (out / "home").mkdir()
    repo = Path(__file__).resolve().parents[1]
    regression = repo / "scripts/search_option_regression.py"
    repair = repo / "patches/hermes-search-option-boundary.patch"
    environment = {
        "PATH": os.environ["PATH"],
        "HOME": str(out / "home"),
        "HERMES_HOME": str(out / "home"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    receipts = {}
    for label, suite in (("baseline", "baseline"), ("candidate", "all")):
        subject = out / label / "tools/file_operations.py"
        subject.parent.mkdir(parents=True)
        shutil.copy2(source, subject)
        if label == "candidate":
            for options in (("--check",), ()):
                subprocess.run(
                    ["git", "apply", *options, str(repair)],
                    cwd=subject.parents[1],
                    env=environment,
                    check=True,
                )
        receipt_path = out / f"{label}.json"
        command = [
            str(args.host_python.resolve()),
            "-B",
            str(regression),
            "--host-root",
            str(args.host_root.resolve()),
            "--subject",
            str(subject),
            "--suite",
            suite,
            "--receipt",
            str(receipt_path),
        ]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=environment,
            timeout=120,
            check=False,
        )
        (out / f"{label}.log").write_text(result.stdout)
        print(result.stdout)
        receipt = json.loads(receipt_path.read_text())
        assert receipt["regression_sha256"] == sha(regression)
        assert receipt["subject_sha256"] == sha(subject)
        assert not receipt["error_tests"] and not receipt["skipped"], receipt
        if label == "baseline":
            assert result.returncode == 1 and receipt["tests_run"] == 5, receipt
            assert receipt["failed_tests"] == ["test_minimal_leading_option_is_pattern"], receipt
            assert "Search failed: rg: unrecognized flag --example-option" in result.stdout
        else:
            assert result.returncode == 0 and receipt["tests_run"] == 10, receipt
            assert receipt["success"] and not receipt["failed_tests"], receipt
        receipts[label] = receipt
    assert sha(source) == BASELINE_SHA256, "Source changed while testing"
    summary = {
        "verified": True,
        "live_source_unchanged": True,
        "baseline": receipts["baseline"],
        "candidate": receipts["candidate"],
        "patch_sha256": sha(repair),
        "inference": False,
        "historical_content_replayed": False,
    }
    (out / "verification.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        "Verified: one expected baseline failure, four passing controls, ten passing repaired tests; host untouched."
    )


if __name__ == "__main__":
    main()
