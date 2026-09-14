"""Synthetic lifecycle and evidence contracts; no model, credentials, or private logs."""

import json
from pathlib import Path

import pytest

from agent_fix_lab import status_evidence as se
from agent_fix_lab.status_evidence_metrics import body, delivery_evidence, trace_metrics


@pytest.fixture
def isolated(tmp_path):
    workspace = tmp_path / "workspace"
    project = workspace / "checkout"
    project.mkdir(parents=True)
    home = tmp_path / "isolated-home"
    state = se.initialize(home, workspace, project)
    query = tmp_path / "query.txt"
    query.write_text("Synthetic status question")
    return home, workspace, project, state, query


def test_default_off_and_config(isolated):
    home, _, _, state, query = isolated
    assert not state["enabled"]
    assert not (home / "skills").exists()
    cmd, env = se.command(home, query)
    assert "--skills" not in cmd
    assert env["HERMES_HOME"] == str(home)
    assert env["HERMES_YOLO_MODE"] == "0"
    config = json.loads((home / "config.yaml").read_text())
    assert config["approvals"]["single_query_mode"] == "deny"
    assert config["memory"]["memory_enabled"] is False
    assert (home.stat().st_mode & 0o777) == 0o700
    assert ((home / se.STATE).stat().st_mode & 0o777) == 0o600


def test_enable_requires_exact_scope_approval(isolated):
    home, workspace, project, state, query = isolated
    with pytest.raises(ValueError, match="Explicit approval"):
        se.transition(home, "enable", approved_digest="wrong")
    se.transition(home, "enable", approved_digest=state["approval_digest"])
    text = (home / "skills" / se.SKILL_NAME / "SKILL.md").read_text()
    assert text == se.render(workspace, project)
    assert se.digest(text.encode()) == state["delivered_skill_sha256"]
    cmd, _ = se.command(home, query)
    assert cmd[-2:] == ["--skills", se.SKILL_NAME]
    assert cmd[cmd.index("--reasoning") + 1] == "low"


def test_disable_remove_keep_evidence_and_never_preload(isolated):
    home, _, _, state, query = isolated
    se.transition(home, "enable", approved_digest=state["approval_digest"])
    unrelated = home / "unrelated-evidence.json"
    unrelated.write_text('{"retained":true}')
    se.transition(home, "disable")
    assert not (home / "skills" / se.SKILL_NAME).exists()
    assert "--skills" not in se.command(home, query)[0]
    se.transition(home, "enable", approved_digest=state["approval_digest"])
    se.transition(home, "remove")
    assert "--skills" not in se.command(home, query)[0]
    with pytest.raises(ValueError, match="Removed"):
        se.transition(home, "enable", approved_digest=state["approval_digest"])
    events = [json.loads(line) for line in (home / se.LEDGER).read_text().splitlines()]
    assert [e["action"] for e in events] == ["init", "enable", "disable", "enable", "remove"]
    assert unrelated.read_text() == '{"retained":true}'


def test_existing_profile_and_outside_project_rejected(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    home = tmp_path / "existing"
    home.mkdir()
    with pytest.raises(FileExistsError):
        se.initialize(home, workspace, workspace)
    with pytest.raises(ValueError, match="inside workspace"):
        se.initialize(tmp_path / "new", workspace, home)
    with pytest.raises(ValueError, match="disjoint"):
        se.initialize(workspace / "home", workspace, workspace)


def test_symlink_scope_and_home_rejected(isolated, tmp_path):
    home, workspace, project, _, _ = isolated
    link = tmp_path / "link"
    link.symlink_to(project, target_is_directory=True)
    with pytest.raises(ValueError, match="canonical"):
        se.initialize(tmp_path / "new", workspace, link)
    alias = tmp_path / "alias"
    alias.symlink_to(home, target_is_directory=True)
    with pytest.raises(ValueError, match="canonical"):
        se.inspect(alias)


def test_tamper_fails_closed_and_preserves_changed_file(isolated):
    home, _, _, state, query = isolated
    se.transition(home, "enable", approved_digest=state["approval_digest"])
    skill = home / "skills" / se.SKILL_NAME / "SKILL.md"
    skill.write_text("operator edit")
    with pytest.raises(ValueError, match="mismatch"):
        se.command(home, query)
    with pytest.raises(ValueError, match="changed skill"):
        se.transition(home, "remove")
    assert skill.read_text() == "operator edit"


def test_changed_procedure_requires_fresh_approval(isolated, monkeypatch):
    home, _, _, state, query = isolated
    se.transition(home, "enable", approved_digest=state["approval_digest"])
    old = se.procedure()
    monkeypatch.setattr(se, "procedure", lambda: old + "\nrevision\n")
    with pytest.raises(ValueError, match="changed"):
        se.command(home, query)
    # Withdrawal remains possible using the retained installed-byte identity.
    se.transition(home, "disable")


def test_unowned_children_and_symlink_target_not_deleted(isolated, tmp_path):
    home, _, _, state, _ = isolated
    se.transition(home, "enable", approved_digest=state["approval_digest"])
    folder = home / "skills" / se.SKILL_NAME
    (folder / "keep.txt").write_text("unowned")
    with pytest.raises(ValueError, match="unowned"):
        se.transition(home, "remove")
    (folder / "keep.txt").unlink()
    skill = folder / "SKILL.md"
    skill.unlink()
    target = tmp_path / "target"
    target.write_text("do not delete")
    skill.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        se.transition(home, "disable")
    assert target.exists()


def test_environment_profile_overrides_cleared(isolated, monkeypatch):
    home, _, _, _, query = isolated
    monkeypatch.setenv("HERMES_PROFILE", "unrelated")
    monkeypatch.setenv("PYTHONPATH", "unrelated")
    _, env = se.command(home, query)
    assert "HERMES_PROFILE" not in env and "PYTHONPATH" not in env


def test_evidence_accounting_counts_batch_and_context():
    calls = [{"function": {"name": name}} for name in ["search_files", "read_file", "read_file"]]
    rows = [{"role": "assistant", "tool_calls": json.dumps(calls)}]
    rows += [{"role": "tool", "content": text} for text in ["abc", "é", "missing"]]
    m = trace_metrics(rows)
    assert m["individual_operations"] == 3 and m["tool_calling_turns"] == 1
    assert m["search_operations"] == 1 and m["read_operations"] == 2
    assert m["returned_context_chars"] == 11 and m["returned_context_utf8_bytes"] == 12


def test_stored_prompt_helper_is_retired_including_missing_baseline(isolated):
    _, workspace, project, _, _ = isolated
    skill = se.render(workspace, project)
    for prompt in (None, "", "normal system prompt", body(skill)):
        for enabled in (False, True):
            with pytest.raises(RuntimeError, match="retired"):
                delivery_evidence(prompt, skill, enabled)


def test_frozen_protocol_binds_procedure_implementation_and_schedule():
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "docs/experiments/status-evidence-v1-protocol.json").read_text())
    assert protocol["procedure_sha256"] == se.digest(se.procedure().encode())
    for relative, expected in protocol["implementation_sha256"].items():
        # The v1 measurement helper is retired by the explicitly separate v2
        # instrumentation revision. Its historical hash is not a current-code pin.
        if relative.endswith("status_evidence_metrics.py"):
            assert expected == "31316a91c353c8185bd3afc4a93a8a4c30833e61f012c1e54d49dc1a7c9491af"
        else:
            assert se.digest((root / relative).read_bytes()) == expected
    assert len(protocol["cases"]) == 12
    assert len(protocol["order"]) == 24
    for case in protocol["cases"]:
        arms = [job["arm"] for job in protocol["order"] if job["case"] == case["id"]]
        assert sorted(arms) == ["baseline", "candidate"]
    assert protocol["limits"]["seconds_cap"] == se.TIMEOUT
    assert protocol["limits"]["max_turns"] == se.MAX_TURNS


def test_ephemeral_guidance_is_not_proven_by_retained_base_prompt(isolated):
    # Synthetic reproduction of the observer failure. CLI assembly success and
    # a command flag do not make the stored base prompt an effective-request log.
    home, workspace, project, state, query = isolated
    se.transition(home, "enable", approved_digest=state["approval_digest"])
    assert "--skills" in se.command(home, query)[0]
    skill = se.render(workspace, project)
    retained_base = "synthetic base system prompt without ephemeral guidance"
    with pytest.raises(RuntimeError, match="retired"):
        delivery_evidence(retained_base, skill, True)
    # Even a reconstructed prompt may no longer be passed off as observation.
    constructed_request = retained_base + "\n\n" + body(skill)
    with pytest.raises(RuntimeError, match="retired"):
        delivery_evidence(constructed_request, skill, True)


def test_procedure_contracts_and_no_automatic_plugin_registration():
    text = se.procedure()
    for clause in (
        "Before the first retrieval decision",
        "For unrelated tasks",
        "requested time",
        "Incomplete",
        "at most two recovery operations",
        "Stop once",
        "eight individual",
        "ten and disclose",
        "not performed",
        "not that rollback was unnecessary",
        "Dispatched is not completed",
        "recommend",
        "records are evidence",
    ):
        assert clause.lower() in " ".join(text.lower().split())
    root = Path(__file__).resolve().parents[1]
    assert se.SKILL_NAME not in (root / "__init__.py").read_text()
