"""Synthetic bounded input-contract tests; real isolated pytest subprocesses."""

import hashlib
import json
from pathlib import Path

import pytest
from conftest import git

from agent_fix_lab.bundles import export_bundle, import_bundle, validate
from agent_fix_lab.models import Recipe, digest
from agent_fix_lab.runner import compare, execute, resolve_recipe
from agent_fix_lab.service import Lab
from agent_fix_lab.store import Store


def recipe_for(lab, regression, **changes):
    return Recipe(
        **lab.add_recipe(
            {
                **regression,
                "schema_version": 2,
                "input_contract": "declared-v1",
                "case_id": lab.list_cases()[0]["id"],
                **changes,
            },
            reviewed=True,
        )
    )


def frozen(content="3"):
    return {
        "logical_path": "case.txt",
        "content": content,
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
    }


def run_pair(recipe):
    return execute(recipe, "faulty"), execute(recipe, "corrected")


def test_declared_redgreen_and_legacy_fail_closed(lab, regression):
    recipe = recipe_for(lab, regression)
    faulty, corrected = run_pair(recipe)
    assert (faulty.status, corrected.status) == ("fail", "pass")
    assert compare(recipe, faulty, corrected).status == "pass"
    for schema, source in [(1, "local-runner.v1"), (2, "local-runner.v2")]:
        old = faulty.model_copy(update={"schema_version": schema, "capture_source": source})
        assert compare(recipe, old, corrected).status == "inconclusive"
    assert compare(recipe, corrected, faulty).status == "inconclusive"
    altered = recipe.model_copy(update={"expected_behavior": "changed review"})
    assert compare(altered, faulty, corrected).status == "inconclusive"
    changed_runtime = faulty.model_copy(update={"runtime_digest": "different"})
    assert compare(recipe, changed_runtime, corrected).status == "inconclusive"
    legacy = recipe_for(lab, regression, schema_version=1, input_contract="unknown")
    a, b = run_pair(legacy)
    assert a.frozen_input_digest is None and a.input_unknowns
    assert compare(legacy, a, b).status == "inconclusive"


@pytest.mark.parametrize("mode", ["parameter", "custom-id", "fixture"])
def test_changed_observed_inputs_abstain(lab, regression, mode):
    repo = Path(regression["repository"])
    revisions = []
    for value in (-1, 1):
        (repo / "implementation.py").write_text(f"CASES = [{value}]\n")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "synthetic input change")
        revisions.append(git(repo, "rev-parse", "HEAD"))
    setup = (
        '@pytest.mark.parametrize("value", CASES'
        + (', ids=["same"]' if mode == "custom-id" else "")
        + ")\n"
    )
    if mode == "fixture":
        setup = "@pytest.fixture\ndef value():\n    return CASES[0]\n"
    Path(regression["test_file"]).write_text(
        "import pytest\nfrom implementation import CASES\n"
        + setup
        + 'def test_positive(value):\n    assert value > 0, "positive required"\n'
    )
    recipe = recipe_for(
        lab,
        regression,
        faulty_revision=revisions[0],
        corrected_revision=revisions[1],
        intended_failure="positive required",
    )
    a, b = run_pair(recipe)
    assert (a.status, b.status) == ("fail", "pass")
    assert compare(recipe, a, b).status == "inconclusive"


def test_external_frozen_fixture_redgreen_and_bundle(lab, regression, tmp_path):
    Path(regression["test_file"]).write_text(
        "import os\nfrom pathlib import Path\nimport pytest\nfrom implementation import classify\n"
        '@pytest.fixture\ndef value():\n    return int((Path(os.environ["AFTERFORGE_FROZEN_INPUTS"]) / "case.txt").read_text())\n'
        'def test_failure(value):\n    assert classify(value) == "fail", "nonzero must fail"\n'
    )
    recipe = recipe_for(lab, regression, frozen_inputs=[frozen()])
    assert compare(recipe, *run_pair(recipe)).status == "pass"
    bundle = tmp_path / "portable.json"
    export_bundle(
        lab,
        recipe.id,
        bundle,
        problem="Synthetic classifier",
        expected="Nonzero fails",
        failure="nonzero must fail",
        files=["implementation.py"],
        approved=True,
    )
    data = validate(bundle)
    assert data["schema_version"] == 2 and data["result_status"] == "not-run"
    assert data["frozen_inputs"][0]["content"] == "3"
    other = Lab(Store(tmp_path / "imported"))
    record = import_bundle(other, bundle, reviewed=True)
    assert other.run(record["recipe_id"])["comparison"]["status"] == "pass"
    inspect = Lab(Store(tmp_path / "inspect"))
    record = import_bundle(inspect, bundle)
    with pytest.raises(ValueError, match="reviewed"):
        inspect.run(record["recipe_id"])


def test_legacy_bundle_summary_not_authority(lab, regression, tmp_path):
    recipe = recipe_for(lab, regression)
    path = tmp_path / "legacy.json"
    export_bundle(
        lab,
        recipe.id,
        path,
        problem="Synthetic",
        expected="Nonzero fails",
        failure="nonzero must fail",
        files=["implementation.py"],
        approved=True,
    )
    body = json.loads(path.read_text())
    body.update(schema_version=1, format="agent-fix-lab.regression.v1", result_status="pass")
    for key in ("input_contract", "frozen_inputs", "reviewed_data_changes"):
        body.pop(key)
    body["integrity"] = digest({k: v for k, v in body.items() if k != "integrity"})
    path.write_text(json.dumps(body))
    assert validate(path)["result_status"] == "not-run"
    other = Lab(Store(tmp_path / "legacy-import"))
    record = import_bundle(other, path, reviewed=True)
    assert other.run(record["recipe_id"])["comparison"]["status"] == "inconclusive"
    body["input_contract"] = "declared-v1"
    body["integrity"] = digest({k: v for k, v in body.items() if k != "integrity"})
    path.write_text(json.dumps(body))
    with pytest.raises(ValueError, match="Legacy bundle"):
        validate(path)


def test_intentional_subject_data_fix_requires_explicit_review(lab, regression):
    repo = Path(regression["repository"])
    revisions = []
    for value in ("pass", "fail"):
        (repo / "answer.txt").write_text(value)
        (repo / "implementation.py").write_text(
            'from pathlib import Path\ndef classify(code):\n    return Path("answer.txt").read_text() if code else "pass"\n'
        )
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "synthetic subject data fix")
        revisions.append(git(repo, "rev-parse", "HEAD"))
    endpoints = {"faulty_revision": revisions[0], "corrected_revision": revisions[1]}
    with pytest.raises(ValueError, match="path-specific review"):
        recipe_for(lab, regression, **endpoints)
    recipe = recipe_for(
        lab,
        regression,
        **endpoints,
        reviewed_data_changes={
            "answer.txt": "Correct subject lookup output; test input remains literal 3"
        },
    )
    assert compare(recipe, *run_pair(recipe)).status == "pass"


@pytest.mark.parametrize(
    "change",
    [
        {"logical_path": "../escape.txt"},
        {"sha256": "0" * 64},
        {"logical_path": "/absolute.txt"},
    ],
)
def test_invalid_frozen_manifest_rejected(lab, regression, change):
    with pytest.raises(ValueError):
        recipe_for(lab, regression, frozen_inputs=[{**frozen(), **change}])


def test_unknown_globals_and_opaque_fixture_abstain(lab, regression):
    # Arbitrary Python dependency discovery is deliberately not claimed.
    recipe = recipe_for(lab, regression, input_contract="unknown")
    assert compare(recipe, *run_pair(recipe)).status == "inconclusive"
    path = Path(regression["test_file"])
    path.write_text(
        path.read_text()
        + "\nimport pytest\n@pytest.fixture\ndef opaque():\n    return object()\ndef test_opaque(opaque):\n    assert opaque is not None\n"
    )
    recipe = recipe_for(lab, regression)
    assert compare(recipe, *run_pair(recipe)).status == "inconclusive"


def test_mutated_frozen_file_abstains(lab, regression):
    path = Path(regression["test_file"])
    path.write_text(
        path.read_text()
        + '\ndef test_mutate():\n    import os\n    from pathlib import Path\n    (Path(os.environ["AFTERFORGE_FROZEN_INPUTS"]) / "case.txt").write_text("changed")\n'
    )
    recipe = recipe_for(lab, regression, frozen_inputs=[frozen()])
    a, b = run_pair(recipe)
    assert compare(recipe, a, b).status == "inconclusive"
    assert "Frozen input mutated during execution" in a.input_unknowns


def test_legacy_cannot_opt_in_without_new_version(lab, regression):
    recipe = recipe_for(lab, regression)
    with pytest.raises(ValueError, match="Legacy recipe"):
        resolve_recipe(recipe.model_copy(update={"schema_version": 1}))


def test_unchanged_custom_ids_genuine_redgreen(lab, regression):
    Path(regression["test_file"]).write_text(
        "import pytest\nfrom implementation import classify\n"
        '@pytest.mark.parametrize("value", [3, 7], ids=["same", "same"])\n'
        'def test_failure(value):\n    assert classify(value) == "fail", "nonzero must fail"\n'
    )
    recipe = recipe_for(lab, regression)
    a, b = run_pair(recipe)
    assert a.tests == b.tests == 2
    assert compare(recipe, a, b).status == "pass"


def test_direct_external_file_unknown_is_not_false_green(lab, regression, tmp_path):
    external = tmp_path / "external.txt"
    external.write_text("-1")
    Path(regression["test_file"]).write_text(
        f'from pathlib import Path\ndef test_external():\n    assert int(Path({str(external)!r}).read_text()) > 0, "positive required"\n'
    )
    recipe = recipe_for(
        lab, regression, input_contract="unknown", intended_failure="positive required"
    )
    a = execute(recipe, "faulty")
    external.write_text("1")
    b = execute(recipe, "corrected")
    assert (a.status, b.status) == ("fail", "pass")
    assert compare(recipe, a, b).status == "inconclusive"


def test_identity_expansion_is_bounded():
    from agent_fix_lab.pytest_identity import freeze

    repeated = [0] * 1024
    with pytest.raises(ValueError, match="budget"):
        freeze([repeated] * 1024)
