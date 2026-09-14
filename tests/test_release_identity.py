"""Synthetic identity collisions, independent sources and conflicting evidence."""

import sqlite3
from copy import deepcopy

import pytest

from agent_fix_lab.history import import_hermes, reconcile_legacy_identity
from agent_fix_lab.store import Store


def test_unrelated_root_reusing_call_is_not_duplicate(history, tmp_path):
    store = Store(tmp_path / "identity")
    import_hermes(store, history, source_id="synthetic", before=10)
    with sqlite3.connect(history) as connection:
        connection.execute("insert into sessions values('unrelated',null,'{}',0)")
        connection.execute(
            "insert into messages select 7,'unrelated',role,content,tool_call_id,"
            "tool_name,7,1,0 from messages where id=2"
        )
    result = import_hermes(store, history, source_id="synthetic", before=10)
    assert result["added_cases"] == 1
    assert len(store.all("case")) == 5
    assert import_hermes(store, history, source_id="synthetic", before=10)["added_cases"] == 0


def test_conflicting_payload_is_not_duplicate(history, tmp_path):
    store = Store(tmp_path / "identity")
    import_hermes(store, history, source_id="synthetic", before=10)
    with sqlite3.connect(history) as connection:
        connection.execute(
            "insert into messages select 7,session_id,role,'{\"exit_code\":0}',tool_call_id,"
            "tool_name,7,1,0 from messages where id=2"
        )
    assert import_hermes(store, history, source_id="synthetic", before=10)["added_cases"] == 1


def test_missing_calls_are_message_scoped(history, tmp_path):
    with sqlite3.connect(history) as connection:
        connection.execute("update messages set tool_call_id=null where id in (2,3)")
    store = Store(tmp_path / "identity")
    assert import_hermes(store, history, source_id="one", before=10)["added_cases"] == 5
    assert import_hermes(store, history, source_id="two", before=10)["added_cases"] == 5
    assert import_hermes(store, history, source_id="one", before=10)["added_cases"] == 0


def test_explicit_legacy_reconciliation_preserves_evidence(history, tmp_path):
    store = Store(tmp_path / "reconcile")
    import_hermes(store, history, source_id="synthetic", before=10)
    current = store.all("run")[0]
    old = deepcopy(current)
    old["id"] = old["source"]["id"] = "legacy"
    old["source"]["parser"] = "hermes.sqlite.v2"
    store.put("run", old)
    original = deepcopy(old)
    pending = reconcile_legacy_identity(old, [current])
    assert pending["status"] == "unresolved"
    linked = reconcile_legacy_identity(old, [current], reviewed=True, reviewer="synthetic operator")
    assert linked["canonical_run_id"] == current["id"]
    assert linked["transfers_case_authority"] is False
    assert "discarded_legacy_observations" in linked["unknown"]
    store.put("identity-reconciliation", linked)
    store.put("identity-reconciliation", linked)
    assert store.get("run", "legacy") == original == old
    assert len(store.all("identity-reconciliation")) == 1
    assert (
        reconcile_legacy_identity(old, [], reviewed=True, reviewer="operator")["status"]
        == "unresolved"
    )
    with pytest.raises(ValueError, match="reviewer"):
        reconcile_legacy_identity(old, [current], reviewed=True)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", "another"),
        ("session_id", "another"),
        ("payload_digest", "another"),
        ("message_id", 999),
        ("tool_name", "another"),
    ],
)
def test_reconciliation_does_not_invent_cross_source_or_call_links(history, tmp_path, field, value):
    store = Store(tmp_path / "reconcile")
    import_hermes(store, history, source_id="synthetic", before=10)
    current = store.all("run")[0]
    old = deepcopy(current)
    old["source"]["parser"] = "hermes.sqlite.v1"
    old["source"][field] = value
    result = reconcile_legacy_identity(old, [current], reviewed=True, reviewer="operator")
    assert result["canonical_run_id"] is None


def test_ambiguous_reconciliation_never_splits(history, tmp_path):
    store = Store(tmp_path / "reconcile")
    import_hermes(store, history, source_id="synthetic", before=10)
    current = store.all("run")[0]
    old = deepcopy(current)
    old["source"]["parser"] = "hermes.sqlite.v3"
    other = deepcopy(current)
    other["id"] = "ambiguous"
    result = reconcile_legacy_identity(old, [current, other], reviewed=True, reviewer="operator")
    assert result["status"] == "unresolved" and result["canonical_run_id"] is None


def test_delegation_cycle_is_entry_independent(history, tmp_path):
    with sqlite3.connect(history) as connection:
        connection.execute(
            "update sessions set parent_session_id=null, model_config=? where id='s'",
            ('{"delegated_from":"child"}',),
        )
        connection.execute("update sessions set parent_session_id=null where id='child'")
    store = Store(tmp_path / "cycle")
    assert import_hermes(store, history, source_id="synthetic", before=10)["added_cases"] == 4
    assert import_hermes(store, history, source_id="synthetic", before=10)["added_cases"] == 0
