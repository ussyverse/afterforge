"""Create explicitly synthetic browser inputs; never reads personal Hermes history."""

import argparse
import importlib.util
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    args = p.parse_args()
    root = args.directory.resolve()
    root.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location(
        "afl_fixture", Path(__file__).resolve().parents[1] / "tests/conftest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    history = module.history.__wrapped__(root)
    lab = module.lab.__wrapped__(root, history)
    recipe = module.regression.__wrapped__(root)
    recipe["case_id"] = lab.list_cases(status="fail")[0]["id"]
    (root / "recipe.json").write_text(json.dumps(recipe, indent=2))
    print(
        json.dumps(
            {
                "provenance": "synthetic fixtures",
                "home": str(root / "lab"),
                "recipe_file": str(root / "recipe.json"),
                "query": "Unfamiliar",
            }
        )
    )


if __name__ == "__main__":
    main()
