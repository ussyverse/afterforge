"""Synthetic native-adapter contracts; actual manager lifecycle is a separate host test."""

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "afl_native_test", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
)
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)
Runtime = __import__(spec.name + ".hermes_plugin.runtime", fromlist=["Runtime"]).Runtime
SCHEMAS = __import__(spec.name + ".hermes_plugin.schemas", fromlist=["SCHEMAS"]).SCHEMAS


class State:
    def __init__(self):
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


class Context:
    def __init__(self):
        self.state = State()
        self.settings = {}
        self.tools = {}
        self.hooks = {}
        self.skills = {}
        self.commands = {}

    def get_config(self, key, default=None):
        return self.settings.get(key, default)

    def register_tool(self, **kw):
        self.tools[kw["name"]] = kw

    def register_hook(self, name, fn):
        self.hooks[name] = fn

    def register_command(self, name, fn, **kw):
        self.commands[name] = fn

    def register_cli_command(self, **kw):
        self.cli = kw

    def register_skill(self, name, path):
        self.skills[name] = path


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    ctx = Context()
    obj = Runtime(ctx, ROOT)
    monkeypatch.setattr(obj, "root", lambda: tmp_path)
    return obj


def test_registration_lightweight():
    ctx = Context()
    plugin.register(ctx)
    assert len(ctx.tools) == 8 and set(ctx.hooks) == {
        "post_tool_call",
        "on_session_end",
        "pre_verify",
    }
    assert ctx.cli["name"] == "fixlab" and "fixlab" in ctx.commands
    assert ctx.skills["regression-workflow"].is_file() and ctx.state.data == {}


@pytest.mark.parametrize("name", list(SCHEMAS))
def test_tool_errors_never_escape(runtime, name):
    result = json.loads(runtime.handle(name, {"unknown": "SECRET_CANARY"}, future=True))
    assert result["success"] is False and "SECRET_CANARY" not in json.dumps(result)


def test_missing_and_outdated_runtime(runtime):
    assert json.loads(runtime.handle("fixlab_status", {}))["data"]["runtime_ready"] is False
    assert "setup" in runtime.handle("fixlab_scan", {})
    root = runtime.root()
    (root / "runtime/bin").mkdir(parents=True)
    (root / "runtime/bin/python").write_text("broken")
    (root / "runtime-install.json").write_text(
        json.dumps({"source_digest": "old", "plugin_version": "0.2.0"})
    )
    assert not runtime.ready()


@pytest.mark.parametrize(
    "key,value", [("capture", "yes"), ("scan_limit", False), ("scan_limit", 201), ("timeout", 1)]
)
def test_config_validation(runtime, key, value):
    runtime.ctx.settings[key] = value
    assert json.loads(runtime.handle("fixlab_status", {}))["success"] is False


def test_hooks_minimize_and_deduplicate(runtime):
    hook = runtime.capture
    for _ in range(20):
        hook.post_tool_call(
            session_id="s",
            tool_call_id="c",
            tool_name="terminal",
            args={"password": "SECRET_CANARY"},
            result={"exit_code": 1, "error": "SECRET_CANARY"},
        )
    hook.on_session_end(session_id="s", future="SECRET_CANARY")
    rows = hook.snapshot()
    assert len(rows) == 1 and rows["s"]["eligible"] and rows["s"]["status"] == "fail"
    assert "SECRET_CANARY" not in json.dumps(rows) and runtime.ctx.state.data == {}
    for i in range(100):
        hook.on_session_end(session_id=f"s{i}")
    assert len(hook.snapshot()) == 32


def test_hook_nonblocking(runtime):
    hook = runtime.capture
    hook.lock.acquire()
    start = time.monotonic()
    try:
        hook.post_tool_call(session_id="s", result="x" * 1000000)
    finally:
        hook.lock.release()
    assert time.monotonic() - start < 0.2 and hook.snapshot() == {}


def test_slash_and_cli_registration():
    import argparse

    ctx = Context()
    plugin.register(ctx)
    assert json.loads(ctx.commands["fixlab"]("review"))["success"]
    parser = argparse.ArgumentParser()
    ctx.cli["setup_fn"](parser)
    assert parser.parse_args(["setup"]).fixlab_action == "setup"
    assert parser.parse_args(["uninstall-runtime", "--confirm"]).confirm


def test_bridge_reuses_source_schema_check(tmp_path):
    import sqlite3

    from agent_fix_lab.plugin_bridge import dispatch

    source = tmp_path / "source.db"
    sqlite3.connect(source).close()
    with pytest.raises(ValueError, match="Unsupported Hermes"):
        dispatch(tmp_path / "lab", "scan", {"source": str(source), "limit": 2})
