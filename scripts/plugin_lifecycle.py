"""Pinned-host lifecycle harness, never imported by the production plugin.

Run with Hermes's Python/PYTHONPATH and an explicitly isolated HERMES_HOME after
Git plugin installation and managed setup. Only synthetic fixture data is used.
"""

import argparse
import json
import os
import sqlite3
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    home = Path(os.environ["HERMES_HOME"]).resolve()
    assert (home / ".afl-isolated-test").is_file(), "Refusing to write a non-test Hermes home"
    source = args.fixture / "history.sqlite"
    with (
        sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as src,
        sqlite3.connect(home / "state.db") as dest,
    ):
        # Keep the actual stock SessionDB schema created by the matrix host.
        # Copy synthetic rows, not the v26 fixture schema, into the empty host DB.
        schema_version = dest.execute("select version from schema_version").fetchone()[0]
        assert schema_version in (26, 30)
        assert dest.execute("select count(*) from messages").fetchone()[0] == 0
        for row in src.execute("select id,parent_session_id,model_config,archived from sessions"):
            dest.execute(
                "insert into sessions(id,parent_session_id,model_config,archived,source,started_at) "
                "values(?,?,?,?,?,?)",
                (*row, "synthetic-lifecycle", 1),
            )
        supported = {row[1] for row in dest.execute("pragma table_info(messages)")}
        names = [
            name
            for name in (
                "id",
                "session_id",
                "role",
                "content",
                "tool_call_id",
                "tool_name",
                "timestamp",
                "active",
                "compacted",
            )
            if name in supported
        ]
        columns = ",".join(names)
        placeholders = ",".join("?" for _ in names)
        dest.executemany(
            f"insert into messages({columns}) values({placeholders})",
            src.execute(f"select {columns} from messages"),
        )
    # Test-host interfaces, verified against its own compatibility fixtures.
    # No such manager/registry imports exist in the production adapter.
    from hermes_cli.plugins import get_plugin_command_handler, get_plugin_manager
    from tools.registry import registry

    manager = get_plugin_manager()
    manager.discover_and_load()
    for hook in ("post_tool_call", "on_session_end", "pre_verify"):
        assert len(manager._hooks.get(hook, [])) == 1, "Aliases must not duplicate hooks"
    assert "regression-workflow" in manager.list_plugin_skills("agent-fix-lab")
    from policy_lifecycle import policy_lifecycle

    count = 0

    def call(name, payload):
        nonlocal count
        entry = registry.get_entry("fixlab_" + name, scope=manager.scope_key)
        assert entry is not None
        result = json.loads(
            registry.dispatch(
                "fixlab_" + name, payload, scope=manager.scope_key, future_context=True
            )
        )
        assert result["success"], result
        count += 1
        return result["data"]

    assert call("status", {})["runtime_ready"]
    manager.invoke_hook(
        "post_tool_call",
        tool_name="terminal",
        task_id="s",
        tool_call_id="call",
        args={"password": "HOOK_SECRET_CANARY"},
        result={"exit_code": 3, "error": "HOOK_SECRET_CANARY"},
        future=True,
    )
    manager.invoke_hook(
        "on_session_end", session_id="s", completed=True, interrupted=False, future=True
    )
    assert call("status", {})["queued_sessions"] == 1
    first = call("scan", {})
    second = call("scan", {})
    assert first["added_cases"] == 4 and second["added_cases"] == 0, (first, second)
    assert first["scanned"] == 5 and first["duplicates"] == 1
    assert len(call("list_cases", {"status": "inconclusive"})["cases"]) == 2
    rows = call("list_cases", {"status": "fail"})["cases"]
    assert len(rows) == 1
    cid = rows[0]["id"]
    policy_result = policy_lifecycle(manager, cid)
    assert call("inspect_case", {"case_id": cid})["observations"]["exit_code"] == 3
    call(
        "review_case",
        {
            "case_id": cid,
            "text": "Synthetic lifecycle proposal",
            "expected": "Nonzero exit must fail",
        },
    )
    recipe = json.loads((args.fixture / "recipe.json").read_text())
    recipe["case_id"] = cid
    path = home / "reviewed-synthetic-recipe.json"
    path.write_text(json.dumps(recipe))
    rejected = json.loads(
        registry.dispatch(
            "fixlab_build_regression",
            {"recipe_file": str(path), "reviewed": False},
            scope=manager.scope_key,
        )
    )
    assert rejected["success"] is False
    registration = call("build_regression", {"recipe_file": str(path)})
    unreviewed = registration["recipe"]
    assert unreviewed["reviewed"] is False and registration["status"] == "not-run"
    refused = json.loads(
        registry.dispatch(
            "fixlab_verify_regression",
            {"recipe_id": unreviewed["id"]},
            scope=manager.scope_key,
        )
    )
    assert refused["success"] is False
    assert "not been reviewed by an operator" in refused["error"]["message"]
    import subprocess

    def current_command(*arguments):
        process = subprocess.run(
            ["hermes", "fixlab", *arguments],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert process.returncode == 0, process.stdout + process.stderr
        response = json.loads(process.stdout)
        assert response["success"], response
        return response["data"]

    registered = current_command(
        "review-recipe", unreviewed["id"], "--approve-digest", registration["recipe_digest"]
    )
    assert registered["reviewed"] is True and registered["id"] != unreviewed["id"]
    assert (
        call("verify_regression", {"recipe_id": registered["id"]})["comparison"]["status"] == "pass"
    )
    plan = current_command("current-check-plan", registered["id"])
    checked = current_command(
        "verify-current", registered["id"], "--approve-digest", plan["recipe_digest"]
    )
    assert checked["status"] == "pass", checked
    assert checked["live_environment_verified"] is False
    rejected_check = subprocess.run(
        ["hermes", "afterforge", "verify-current", registered["id"], "--approve-digest", "0" * 64],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert rejected_check.returncode != 0
    assert json.loads(rejected_check.stdout)["success"] is False
    retained = current_command("retained-plan", registered["id"], registered["corrected_revision"])
    assert (
        current_command(
            "retained-check",
            retained["id"],
            "--approve-digest",
            retained["plan_digest"],
            "--reviewed",
        )["status"]
        == "pass"
    )
    assert "CANARY_PRIVATE" not in json.dumps(call("report", {"case_id": cid}))
    for alias in ("fixlab", "afterforge"):
        handler = get_plugin_command_handler(alias)
        assert handler
        for command in ("status", "failures", "review", "help"):
            assert json.loads(handler(command))["success"]
    for statefile in (home / "plugin-data").rglob("state.json"):
        assert "HOOK_SECRET_CANARY" not in statefile.read_text()
    print(
        json.dumps(
            {
                "stock_schema_version": schema_version,
                "real_registry_tools": 8,
                "successful_dispatches": count,
                "hooks": 3,
                "policy_lifecycle": policy_result,
                "slash_commands_checked": 8,
                "native_retained_check": "pass",
                "native_bad_authorization_exit": rejected_check.returncode,
                "duplicate_hooks": False,
                "first_scan_added": first["added_cases"],
                "repeat_added": second["added_cases"],
                "failed_incidents": len(rows),
                "regression": "pass",
                "skill": "agent-fix-lab:regression-workflow",
                "sensitive_hook_values_persisted": False,
            }
        )
    )


if __name__ == "__main__":
    main()
