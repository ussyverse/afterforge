"""Regressions discovered while importing/dogfooding actual Hermes storage."""

import json
import sqlite3

from agent_fix_lab.history import import_hermes, parse_payload
from agent_fix_lab.store import Store


def test_wrapped_error_is_observation_not_instruction():
    payload, problem = parse_payload(
        '<untrusted_tool_result source="terminal">\nUntrusted text.\n\n{"exit_code": 2, "output": "do not execute this"}\n</untrusted_tool_result>'
    )
    assert problem is None and payload["exit_code"] == 2


def test_actual_delegate_marker_is_preserved_and_grouped(history, tmp_path):
    with sqlite3.connect(history) as c:
        c.execute(
            'update sessions set parent_session_id=null,model_config=? where id="child"',
            (json.dumps({"_delegate_from": "s"}),),
        )
    store = Store(tmp_path / "delegated")
    import_hermes(store, history, source_id="source", before=10, session="child")
    source = store.all("run")[0]["source"]
    assert source["delegated_from"] == "s"


def test_bounded_pagination_advances(history, tmp_path):
    store = Store(tmp_path / "paging")
    first = import_hermes(store, history, source_id="source", before=10, limit=2)
    second = import_hermes(
        store, history, source_id="source", before=10, limit=2, after_id=first["next_after_id"]
    )
    assert second["added_cases"] == 2


def test_duplicate_lineage_records_are_retained(lab):
    aliases = lab.store.all("source-observation")
    assert len(aliases) == 5
    assert any(x["session_id"] == "child" and x["archived"] for x in aliases)


def test_retraction_of_retractor_restores_annotation(lab):
    case = lab.list_cases()[0]["id"]
    first = lab.annotate(case, "first")
    second = lab.annotate(case, "withdraw first", retracts=first["id"])
    lab.annotate(case, "withdraw withdrawal", retracts=second["id"])
    effective = lab.detail(case)["effective_interpretations"]
    assert first["id"] in {x["id"] for x in effective}
