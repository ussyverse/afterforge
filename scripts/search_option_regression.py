"""Synthetic regression against an explicit Hermes source file and real rg/grep.

No model, credentials, transcript commands, live profile or mocked search results.
The local shell implements the documented terminal backend execute() interface.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SUBJECT = None


class LocalShell:
    def __init__(self, cwd):
        self.cwd = str(cwd)

    def execute(self, command, cwd=None, timeout=30, **kwargs):
        result = subprocess.run(
            ["bash", "-c", command],
            cwd=cwd or self.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {"output": result.stdout, "returncode": result.returncode}


class SearchRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="afl-search-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / "sample.txt"
        self.file.write_text("Synthetic fixture.\n--example-option\nordinary-control\n--version\n")
        self.ops = SUBJECT.ShellFileOperations(LocalShell(self.root))

    def search(self, pattern, **kwargs):
        return self.ops.search(pattern, path=str(self.file), **kwargs)

    def test_minimal_leading_option_is_pattern(self):
        result = self.search("--example-option")
        self.assertIsNone(result.error)
        self.assertEqual(
            [(m.line_number, m.content) for m in result.matches], [(2, "--example-option")]
        )

    def test_control_regex_semantics(self):
        result = self.search("ordinary-[a-z]+")
        self.assertIsNone(result.error)
        self.assertEqual([m.content for m in result.matches], ["ordinary-control"])

    def test_control_no_match(self):
        result = self.search("unmatched_synthetic_needle")
        self.assertIsNone(result.error)
        self.assertEqual(result.total_count, 0)

    def test_control_invalid_regex_stays_error(self):
        result = self.search("(")
        self.assertIsNotNone(result.error)
        self.assertEqual(result.total_count, 0)

    def test_control_glob_and_modes(self):
        files = self.ops.search("*.txt", path=str(self.root), target="files")
        self.assertIsNone(files.error)
        self.assertEqual(files.files, [str(self.file)])
        self.assertEqual(self.search("ordinary", output_mode="count").counts, {str(self.file): 1})
        self.assertEqual(self.search("ordinary", output_mode="files_only").files, [str(self.file)])

    def test_relevant_css_alternation_modes(self):
        css = self.root / "style.css"
        css.write_text("--accent: blue;\n--surface: white;\n")
        for mode in ("content", "count", "files_only"):
            with self.subTest(mode=mode):
                result = self.ops.search(
                    "--accent|--surface", path=str(self.root), file_glob="*.css", output_mode=mode
                )
                self.assertIsNone(result.error)
                if mode == "content":
                    self.assertEqual(
                        [m.content for m in result.matches],
                        ["--accent: blue;", "--surface: white;"],
                    )
                elif mode == "count":
                    self.assertEqual(result.counts, {str(css): 2})
                else:
                    self.assertEqual(result.files, [str(css)])

    def test_relevant_recognized_flag_is_not_executed(self):
        result = self.search("--version")
        self.assertIsNone(result.error)
        self.assertEqual([m.content for m in result.matches], ["--version"])

    def test_relevant_grep_fallback(self):
        self.ops._command_cache.update(rg=False, grep=True)
        result = self.search("--example-option")
        self.assertIsNone(result.error)
        self.assertEqual([m.content for m in result.matches], ["--example-option"])

    def test_relevant_zero_match_probes(self):
        for contents, pattern, expected_hint in (
            ("--Accent\n", "--accent", "case-insensitive"),
            ("--value[0]\n", "--value[0]", "literal"),
        ):
            with self.subTest(hint=expected_hint):
                self.file.write_text(contents)
                result = self.search(pattern)
                self.assertIsNone(result.error)
                self.assertEqual(result.total_count, 0)
                self.assertIn(expected_hint, result.warning or "")
        hidden = self.root / ".hidden"
        hidden.mkdir()
        (hidden / "sample.txt").write_text("--hidden-needle\n")
        result = self.ops.search("--hidden-needle", path=str(self.root))
        self.assertIsNone(result.error)
        self.assertEqual(result.total_count, 0)
        self.assertIn("hidden", result.warning or "")

    def test_relevant_actual_tool_wrapper(self):
        from tools import file_tools

        with patch.object(file_tools, "_get_file_ops", return_value=self.ops):
            result = json.loads(
                file_tools.search_tool(
                    "--example-option", path=str(self.file), task_id="synthetic-option-regression"
                )
            )
        self.assertNotIn("error", result)
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["matches"][0]["content"], "--example-option")
        self.assertEqual(result["matches"][0]["line"], 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-root", type=Path, required=True)
    parser.add_argument("--subject", type=Path, required=True)
    parser.add_argument("--suite", choices=("baseline", "all"), default="all")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if not shutil.which("rg") or not shutil.which("grep"):
        raise RuntimeError(
            "Real rg and grep are required; missing tools are not a baseline failure"
        )
    sys.dont_write_bytecode = True
    with tempfile.TemporaryDirectory(prefix="afl-search-home-") as home:
        os.environ["HERMES_HOME"] = home
        sys.path.insert(0, str(args.host_root.resolve()))
        spec = importlib.util.spec_from_file_location("tools.file_operations", args.subject)
        global SUBJECT
        SUBJECT = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = SUBJECT
        spec.loader.exec_module(SUBJECT)
        names = unittest.defaultTestLoader.getTestCaseNames(SearchRegression)
        if args.suite == "baseline":
            names = [n for n in names if n.startswith(("test_minimal_", "test_control_"))]
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.TestSuite(SearchRegression(n) for n in names)
        )
        receipt = {
            "suite": args.suite,
            "synthetic": True,
            "tests_run": result.testsRun,
            "test_names": names,
            "failed_tests": [t._testMethodName for t, _ in result.failures],
            "error_tests": [t._testMethodName for t, _ in result.errors],
            "skipped": len(result.skipped),
            "success": result.wasSuccessful(),
            "subject_sha256": hashlib.sha256(args.subject.read_bytes()).hexdigest(),
            "regression_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
