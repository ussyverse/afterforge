import json
import sqlite3
from pathlib import Path

import pytest
from correction_aware_learning import historical_events
from pydantic import ValidationError

from agent_fix_lab.adapters import (
    configuration_difference,
    process_facts,
    selected_config,
    symptoms,
)
from agent_fix_lab.history import import_hermes, snapshot
from agent_fix_lab.models import Annotation, Recipe, digest
from agent_fix_lab.runner import compare, execute
from agent_fix_lab.store import Store


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"exit_code": 0}, (0, "pass")),
        ({"exit_code": 1}, (1, "fail")),
        ({"exit_code": None}, (None, "inconclusive")),
        ({"exit_code": False}, (None, "inconclusive")),
        ({"exit_code": "0"}, (None, "inconclusive")),
        ({"error": "bad"}, (None, "fail")),
        ({"success": False}, (None, "fail")),
        ({"success": True}, (None, "inconclusive")),
        ({"exit_code": 0, "error": "contradiction"}, (0, "fail")),
    ],
)
def test_status(payload, expected):
    assert process_facts(payload) == expected


def test_triage_unrecognized_never_overrides_process():
    assert symptoms("opaque unfamiliar text") == []
    assert process_facts({"output": "opaque unfamiliar text", "exit_code": 7}) == (7, "fail")
    assert symptoms('Traceback (most recent call last):\n  File "x.py", line 3\nValueError: bad')


def test_incremental_lineage_and_unknown(lab, history):
    assert len(lab.list_cases()) == 4
    detail = lab.detail(lab.list_cases(status="fail")[0]["id"])
    assert detail["observations"]["source"]["compacted"] is True
    stats = import_hermes(lab.store, history, source_id="fixture", before=10)
    assert stats["added_cases"] == 0 and stats["duplicates"] == 5
    assert len(lab.list_cases(status="inconclusive")) == 2
    assert all("exit_code" in c["unknown"] for c in lab.list_cases(status="inconclusive"))


def test_filters_dry_run_and_partial(history, tmp_path):
    store = Store(tmp_path / "other")
    stats = import_hermes(store, history, source_id="fixture", before=4, after=2, dry_run=True)
    assert stats["added_cases"] == 2 and store.all("case") == []
    import_hermes(store, history, source_id="fixture", before=10, limit=2)
    import_hermes(store, history, source_id="fixture", before=10, after=4)
    assert len(store.all("case")) == 4


def test_schema_fail_closed(history, tmp_path):
    with sqlite3.connect(history) as c:
        c.execute("update schema_version set version=999")
    with pytest.raises(ValueError, match="schema version"):
        import_hermes(Store(tmp_path / "new"), history, source_id="fixture", before=10)
    path = tmp_path / "unsupported"
    path.mkdir()
    with sqlite3.connect(path / "lab.sqlite") as c:
        c.execute("pragma user_version=55")
    with pytest.raises(ValueError, match="schema"):
        Store(path)


def test_wal_snapshot(history):
    c = sqlite3.connect(history)
    c.execute("pragma journal_mode=wal")
    c.execute('insert into sessions values("wal",null,"{}",0)')
    c.commit()
    with snapshot(history) as read:
        assert read.execute('select id from sessions where id="wal"').fetchone()[0] == "wal"
    c.close()


def test_transaction_rollback(lab):
    original = lab.store.all("case")[0]
    with pytest.raises(ValueError, match="Conflicting"):
        lab.store.put_many(
            [("x", {"id": "new"}), ("case", {**original, "provenance": "synthetic"})]
        )
    assert lab.store.all("x") == []


def test_models_versions_and_identity():
    assert digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2})
    with pytest.raises(ValidationError):
        Annotation(
            schema_version=2,
            id="x",
            case_id="x",
            timestamp_seconds=0,
            author_kind="operator",
            text="text",
        )
    with pytest.raises(ValidationError):
        Annotation(
            id="x", case_id="x", timestamp_seconds=float("nan"), author_kind="operator", text="text"
        )


def test_annotation_retraction_and_structural_boundary(lab):
    case = lab.list_cases()[0]["id"]
    before = lab.detail(case)["observations"]
    note = lab.annotate(case, "CANARY_PRIVATE correction", "expected", "agent-proposed")
    lab.annotate(case, "retracted inaccurate interpretation", retracts=note["id"])
    assert lab.detail(case)["observations"] == before
    assert len(lab.detail(case)["effective_interpretations"]) == 1
    events = historical_events(lab.store.root / "correction.sqlite")
    assert len(events) == 2 and all(str(e.source) == "operator" for e in events)
    assert b"CANARY_PRIVATE" not in (lab.store.root / "correction.sqlite").read_bytes()
    with pytest.raises(ValueError, match="attribution"):
        lab.annotate(case, "inferred correction", author="historical-user")


def test_petrichor_and_privacy(lab):
    case = lab.list_cases()[0]["id"]
    result = lab.baseline(
        case,
        "runtime.json",
        {"python_version": "3.11.0", "password": "CANARY_PRIVATE"},
        {"python_version": "3.12.0", "password": "CANARY_PRIVATE"},
    )
    assert "3.12.0" in result["diff"]
    assert b"CANARY_PRIVATE" not in (lab.store.root / ".petrichor/soil.db").read_bytes()
    assert selected_config({"python_version": "CANARY_PRIVATE"}) == {}
    assert configuration_difference(None, {})["status"] == "inconclusive"
    assert (
        configuration_difference(
            {"logical_path": "a", "fields": {}}, {"logical_path": "b", "fields": {}}
        )["status"]
        == "inconclusive"
    )
    with pytest.raises(ValueError):
        lab.baseline(case, "../../secret", {"python_version": "3.11"}, {"python_version": "3.12"})


def test_full_workflow(lab, regression):
    case = lab.list_cases(status="fail")[0]["id"]
    lab.annotate(case, "Preserve process exit", "nonzero must fail")
    recipe = lab.add_recipe({**regression, "case_id": case}, reviewed=True)
    assert lab.comparison(recipe["id"])["status"] == "not-run"
    result = lab.run(recipe["id"])
    assert result["comparison"]["status"] == "pass"
    assert [r["status"] for r in result["results"]] == ["fail", "pass"]
    assert all(r["tests"] == 2 for r in result["results"])
    export = json.dumps(lab.export(case))
    assert "CANARY_PRIVATE" not in export and str(lab.store.root) not in export
    assert "shadow_only" in export


@pytest.mark.parametrize(
    "text,reason",
    [
        ("", "No tests"),
        ("import nonexistent_module\n", "collection/setup"),
        ("import pytest\ndef test_skip():\n    pytest.skip()\n", "skip"),
        ("import time\ndef test_wait():\n    time.sleep(5)\n", "timeout"),
    ],
)
def test_inconclusive_never_fix(lab, regression, text, reason):
    Path(regression["test_file"]).write_text(text)
    recipe = lab.add_recipe(
        {
            **regression,
            "case_id": lab.list_cases()[0]["id"],
            # Only the timeout case needs a short deadline. Other cases must
            # reach collection on slow CI rather than testing startup speed.
            "timeout_seconds": 1 if reason == "timeout" else 20,
        },
        reviewed=True,
    )
    result = execute(Recipe(**recipe), "corrected")
    assert result.status == "inconclusive"
    assert reason.lower() in result.reason.lower()


def test_bridge_registration_is_unreviewed_until_operator_review(lab, regression, tmp_path):
    from agent_fix_lab.plugin_bridge import dispatch

    case = lab.list_cases()[0]["id"]
    recipe_file = tmp_path / "recipe.json"
    recipe_file.write_text(json.dumps({**regression, "case_id": case}))
    # A model-supplied reviewed=True is ignored: registration never yields a runnable recipe.
    registered = dispatch(
        lab.store.root, "build_regression", {"recipe_file": str(recipe_file), "reviewed": True}
    )
    unreviewed = registered["recipe"]
    assert unreviewed["reviewed"] is False
    assert registered["recipe_digest"] == digest(unreviewed)
    with pytest.raises(ValueError, match="not been reviewed by an operator"):
        dispatch(lab.store.root, "verify_regression", {"recipe_id": unreviewed["id"]})
    with pytest.raises(ValueError, match="digest"):
        lab.review_recipe(unreviewed["id"], "0" * 64)
    reviewed = lab.review_recipe(unreviewed["id"], registered["recipe_digest"])
    assert reviewed["reviewed"] is True and reviewed["id"] != unreviewed["id"]
    # Immutable original, idempotent review, and only the reviewed copy runs.
    assert lab.store.get("recipe", unreviewed["id"])["reviewed"] is False
    assert lab.review_recipe(unreviewed["id"], registered["recipe_digest"]) == reviewed
    assert lab.run(reviewed["id"])["comparison"]["status"] == "pass"


def test_review_and_fixture_integrity(lab, regression):
    case = lab.list_cases()[0]["id"]
    recipe = Recipe(**lab.add_recipe({**regression, "case_id": case}))
    with pytest.raises(ValueError, match="reviewed"):
        execute(recipe, "corrected")
    recipe = recipe.model_copy(update={"reviewed": True})
    Path(regression["test_file"]).write_text("def test_leak(): pass")
    with pytest.raises(ValueError, match="changed"):
        execute(recipe, "corrected")


def test_wrong_failure_not_verified(lab, regression):
    recipe = Recipe(
        **lab.add_recipe(
            {
                **regression,
                "case_id": lab.list_cases()[0]["id"],
                "intended_failure": "not the assertion",
            },
            reviewed=True,
        )
    )
    old = execute(recipe, "faulty")
    new = execute(recipe, "corrected")
    assert old.status == "inconclusive" and compare(recipe, old, new).status == "inconclusive"
