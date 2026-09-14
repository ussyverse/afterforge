"""Synthetic false-green example: assertion bytes/count stay identical."""

from pathlib import Path

import pytest
from conftest import git

from agent_fix_lab.models import Recipe
from agent_fix_lab.runner import compare, execute


@pytest.mark.parametrize("custom_ids", [False, True])
def test_changed_parameter_values_are_not_a_verified_fix(lab, regression, custom_ids):
    repo = Path(regression["repository"])
    revisions = []
    for value in (-1, 1):
        (repo / "implementation.py").write_text(f"CASES = [{value}]\n")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "synthetic input change")
        revisions.append(git(repo, "rev-parse", "HEAD"))
    ids = ', ids=["same"]' if custom_ids else ""
    Path(regression["test_file"]).write_text(
        "import pytest\nfrom implementation import CASES\n"
        f'@pytest.mark.parametrize("value", CASES{ids})\n'
        'def test_positive(value):\n    assert value > 0, "positive required"\n'
    )
    recipe = Recipe(
        **lab.add_recipe(
            {
                **regression,
                "case_id": lab.list_cases()[0]["id"],
                "faulty_revision": revisions[0],
                "corrected_revision": revisions[1],
                "intended_failure": "positive required",
            },
            reviewed=True,
        )
    )
    faulty, corrected = execute(recipe, "faulty"), execute(recipe, "corrected")
    assert (faulty.status, corrected.status) == ("fail", "pass")
    assert faulty.tests == corrected.tests == 1
    assert compare(recipe, faulty, corrected).status == "inconclusive"


def test_legacy_results_do_not_gain_equivalence(lab, regression):
    recipe = Recipe(
        **lab.add_recipe(
            {
                **regression,
                "case_id": lab.list_cases()[0]["id"],
            },
            reviewed=True,
        )
    )
    faulty, corrected = execute(recipe, "faulty"), execute(recipe, "corrected")
    assert compare(recipe, faulty, corrected).status == "pass"
    legacy = faulty.model_copy(
        update={
            "schema_version": 1,
            "capture_source": "local-runner.v1",
            "frozen_input_digest": None,
            "collection_identities": [],
        }
    )
    assert compare(recipe, legacy, corrected).status == "inconclusive"


def test_unsupported_fixture_identity_abstains(lab, regression):
    assertion = Path(regression["test_file"])
    assertion.write_text(
        assertion.read_text()
        + "\nimport pytest\n@pytest.fixture\ndef opaque():\n    return object()\n"
        + "def test_opaque(opaque):\n    assert opaque is not None\n"
    )
    recipe = Recipe(
        **lab.add_recipe(
            {
                **regression,
                "case_id": lab.list_cases()[0]["id"],
            },
            reviewed=True,
        )
    )
    faulty, corrected = execute(recipe, "faulty"), execute(recipe, "corrected")
    assert (faulty.status, corrected.status) == ("fail", "pass")
    assert compare(recipe, faulty, corrected).status == "inconclusive"
