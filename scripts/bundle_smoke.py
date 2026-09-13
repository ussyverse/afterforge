"""Round-trip an explicitly reviewed reduction through the installed CLI."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from agent_fix_lab.bundles import export_bundle
from agent_fix_lab.service import Lab
from agent_fix_lab.store import Store


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--recipe-file", type=Path, required=True)
    p.add_argument("--output-directory", type=Path, required=True)
    p.add_argument("--file", action="append", required=True)
    p.add_argument("--python", default=sys.executable)
    args = p.parse_args()
    root = args.output_directory.resolve()
    root.mkdir(parents=True, exist_ok=False)
    lab = Lab(Store(args.home))
    recipe = lab.add_recipe(json.loads(args.recipe_file.read_text()), reviewed=True)
    bundle = root / "regression.json"
    export_bundle(
        lab,
        recipe["id"],
        bundle,
        problem="Reviewed reduced regression; original implementation unknown",
        expected=recipe["expected_behavior"],
        failure=recipe["intended_failure"],
        files=args.file,
        approved=True,
    )
    command = [args.python, "-m", "agent_fix_lab.cli", "--home", str(root / "fresh-lab")]

    def call(*arguments):
        return json.loads(subprocess.check_output([*command, *arguments]))

    assert call("bundle-validate", str(bundle))["status"] == "valid"
    imported = call("bundle-import", str(bundle), "--reviewed")
    result = call("run", imported["recipe_id"])
    assert result["comparison"]["status"] == "pass"
    assert [r["status"] for r in result["results"]] == ["fail", "pass"]
    (root / "result.json").write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            {
                "bundle_roundtrip": "passed",
                "faulty": "fail",
                "corrected": "pass",
                "provenance": recipe["provenance"],
                "original_revisions": "unknown",
            }
        )
    )


if __name__ == "__main__":
    main()
