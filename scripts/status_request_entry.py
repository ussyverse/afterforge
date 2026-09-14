"""Isolated Hermes CLI bootstrap with a final serialized Codex request observer.

Invoke only in a newly approved research home. Host modules are patched in this
child process, never on disk. Offline mode replaces transport/auth resolution,
not CLI, skill loading, agent request assembly, or provider transformations.
"""

import argparse
import contextvars
import functools
import importlib.metadata
import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path

# Import the dependency-free observer without installing Afterforge in Hermes.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "agent_fix_lab"))
from status_request_observer import assess, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation-config", type=Path, required=True)
    parser.add_argument("--host-root", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--missing-observer", action="store_true")
    parser.add_argument("cli_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    cfg = json.loads(args.observation_config.read_text())
    home = Path(os.environ["HERMES_HOME"]).resolve()
    if not (home / ".afterforge-status-evidence.json").is_file():
        raise ValueError("Require an initialized isolated experimental home")
    if args.observation_config.resolve().is_relative_to(home / "skills"):
        raise ValueError("Observer configuration must not be discoverable as a skill")
    expected = Path(cfg["approved_body_file"]).read_text()
    if sha(expected.encode()) != cfg["approved_body_sha256"]:
        raise ValueError("Approved body changed")
    evidence = Path(cfg["evidence_file"])
    fd = os.open(evidence, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    lock = threading.Lock()
    state = {"outcome": "unknown", "root_session": None, "task_requests": 0, "tools": 0}
    task = contextvars.ContextVar("afterforge_task_request", default=None)

    def record(event):
        payload = {
            "attempt": cfg["attempt"],
            "host_identity": cfg["host_identity"],
            "procedure_version": cfg["procedure_version"],
            "procedure_sha256": cfg["procedure_sha256"],
            "approved_body_sha256": cfg["approved_body_sha256"],
            "enabled": cfg["enabled"],
            "monotonic_ns": time.monotonic_ns(),
            **event,
        }
        with lock:
            os.write(fd, (json.dumps(payload) + "\n").encode())
            os.fsync(fd)

    def fail(reason):
        record({"event": "gate-blocked", "outcome": "unknown", "reason": reason})
        os._exit(86)  # Fail closed even inside a host worker; isolated child only.

    record({"event": "observer-start", "outcome": "unknown"})
    sys.path.insert(0, str(args.host_root.resolve()))
    import agent.codex_runtime as codex
    import agent.tool_executor as executor
    import httpx
    import run_agent

    original_conversation = run_agent.AIAgent.run_conversation

    @functools.wraps(original_conversation)
    def conversation(agent, *a, **kw):
        if state["root_session"] is None:
            state["root_session"] = agent.session_id
        return original_conversation(agent, *a, **kw)

    run_agent.AIAgent.run_conversation = conversation
    original_stream = codex.run_codex_stream

    @functools.wraps(original_stream)
    def stream(agent, *a, **kw):
        root = agent.session_id == state["root_session"] and not getattr(
            agent, "is_subagent", False
        )
        token = task.set(
            {"session_sha256": sha(agent.session_id.encode()), "model": agent.model}
            if root
            else None
        )
        try:
            result = original_stream(agent, *a, **kw)
            if root and state["outcome"] not in ("verified-present", "verified-absent"):
                fail("no-verified-task-request-before-response")
            return result
        finally:
            task.reset(token)

    codex.run_codex_stream = stream
    for name in (
        "execute_tool_calls_concurrent",
        "execute_tool_calls_sequential",
        "execute_tool_calls_segmented",
    ):
        original = getattr(executor, name)

        def guarded(agent, *a, _original=original, **kw):
            if agent.session_id == state["root_session"]:
                if state["outcome"] not in ("verified-present", "verified-absent"):
                    fail("no-verified-request-before-tool")
                if state["tools"] == 0:
                    record({"event": "first-task-tool-gate", "outcome": state["outcome"]})
                state["tools"] += 1
            return _original(agent, *a, **kw)

        setattr(executor, name, guarded)

    original_send = httpx.Client._send_single_request

    def send(client, request):
        context = task.get()
        is_codex = (
            request.url.host == "chatgpt.com" and request.url.path == "/backend-api/codex/responses"
        )
        if not context:
            record({"event": "auxiliary-or-infrastructure-request", "outcome": "unknown"})
            return original_send(client, request)
        if not is_codex:
            fail("unexpected-task-provider-path")
        if state["task_requests"]:
            return original_send(client, request)
        state["task_requests"] += 1
        try:
            raw = request.content
            complete = isinstance(raw, bytes) and int(
                request.headers.get("content-length", -1)
            ) == len(raw)
        except (httpx.RequestNotRead, ValueError):
            raw, complete = None, False
        verdict = assess(
            raw,
            expected,
            cfg["enabled"],
            complete=complete,
            model=cfg["model"],
            query_sha256=cfg["query_sha256"],
        )
        request_id = uuid.uuid4().hex
        record(
            {
                "event": "first-task-request",
                "request_id": request_id,
                **context,
                **verdict,
                "httpx_version": importlib.metadata.version("httpx"),
                "boundary": "httpx.Client._send_single_request; post-Codex/SDK serialization",
            }
        )
        state["outcome"] = verdict["outcome"]
        wanted = "verified-present" if cfg["enabled"] else "verified-absent"
        if state["outcome"] != wanted:
            fail("first-task-request-" + state["outcome"])
        try:
            response = original_send(client, request)
        except Exception:  # noqa: BLE001 -- fail closed without logging payloads
            state["outcome"] = "unknown"
            fail("transport-failed-after-observation")
        if request.content != raw:
            state["outcome"] = "mismatch"
            fail("request-mutated-at-boundary")
        record(
            {
                "event": "request-submitted",
                "request_id": request_id,
                "request_sha256": sha(raw),
                "outcome": state["outcome"],
            }
        )
        return response

    if not args.missing_observer:
        httpx.Client._send_single_request = send

    if args.offline:
        # Synthetic auth resolver only; no provider credentials are read or sent.
        import hermes_cli.runtime_provider as runtime

        runtime.resolve_runtime_provider = lambda *a, **kw: {
            "provider": "openai-codex",
            "api_mode": "codex_responses",
            "base_url": "https://chatgpt.com/backend-api/codex",
            "api_key": "synthetic-offline-not-a-credential",
            "source": "synthetic-offline",
        }
        import socket

        socket.socket.connect = lambda *a, **kw: (_ for _ in ()).throw(
            RuntimeError("offline network denied")
        )
        stub_tasks = 0

        def transport(request):
            nonlocal stub_tasks
            raw = request.content
            payload = json.loads(raw) if raw else {}
            context = task.get()
            if context:
                stub_tasks += 1
                record(
                    {
                        "event": "stub-final-request",
                        "request_sha256": sha(raw),
                        "task": True,
                        "ordinal": stub_tasks,
                    }
                )
            else:
                record({"event": "stub-final-request", "request_sha256": sha(raw), "task": False})
            if context and stub_tasks == 1:
                item = {
                    "type": "function_call",
                    "id": "fc_synthetic",
                    "call_id": "call_synthetic",
                    "name": "read_file",
                    "arguments": json.dumps({"path": cfg["probe_read_path"]}),
                }
            else:
                item = {
                    "type": "message",
                    "id": "msg_synthetic",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Synthetic offline response."}],
                }
            response = {
                "id": "resp_synthetic",
                "object": "response",
                "created_at": 0,
                "status": "completed",
                "model": payload.get("model", cfg["model"]),
                "output": [item],
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            }
            events = [
                {"type": "response.output_item.done", "output_index": 0, "item": item},
                {"type": "response.completed", "response": response},
            ]
            sse = "".join("data: " + json.dumps(e) + "\n\n" for e in events)
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=sse)

        mock = httpx.MockTransport(transport)
        httpx.Client._transport_for_url = lambda self, url: mock
        # Explicit auxiliary control through the same HTTPX boundary, outside task context.
        with httpx.Client() as client:
            client.post(
                "https://chatgpt.com/backend-api/codex/responses",
                json={
                    "model": cfg["model"],
                    "instructions": "Synthetic title request",
                    "input": [],
                    "stream": True,
                },
            )

    from hermes_cli.main import main as hermes_main

    cli_args = args.cli_args[1:] if args.cli_args[:1] == ["--"] else args.cli_args
    sys.argv = ["hermes", *cli_args]
    try:
        hermes_main()
    finally:
        record(
            {
                "event": "observer-end",
                "outcome": state["outcome"],
                "task_requests_observed": state["task_requests"],
            }
        )
        os.close(fd)


if __name__ == "__main__":
    main()
