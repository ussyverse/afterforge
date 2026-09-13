"""Nonblocking, bounded in-memory hints. Never persists arguments or output."""

import json
import re
import threading
import time


def identifier(value):
    return (
        value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value) else None
    )


class Capture:
    def __init__(self):
        self.pending = {}
        self.lock = threading.Lock()
        self.enabled = True

    def record(self, session, tool=None, call=None, status="inconclusive", ended=False):
        session = identifier(session)
        if not self.enabled or not session or not self.lock.acquire(blocking=False):
            return
        try:
            prior = self.pending.get(session, {})
            if ended:
                status = prior.get("status", status)
            self.pending[session] = {
                "session_id": session,
                "tool_name": identifier(tool) or prior.get("tool_name"),
                "tool_call_id": identifier(call) or prior.get("tool_call_id"),
                "status": status,
                "error_type": "tool-error" if status == "fail" else None,
                "timestamp_seconds": time.time(),
                "pending_import": True,
                "eligible": ended or prior.get("eligible", False),
            }
            while len(self.pending) > 32:
                self.pending.pop(next(iter(self.pending)))
        finally:
            self.lock.release()

    def post_tool_call(
        self, tool_name="", result=None, task_id="", session_id="", tool_call_id="", **kwargs
    ):
        try:
            if not isinstance(tool_name, str) or tool_name.startswith("fixlab_"):
                return
            payload = result
            if isinstance(result, str) and len(result) <= 4096:
                try:
                    payload = json.loads(result)
                except ValueError:
                    payload = None
            status = "inconclusive"
            if isinstance(payload, dict):
                code = payload.get("exit_code")
                if (
                    payload.get("error")
                    or payload.get("success") is False
                    or (type(code) is int and code != 0)
                ):
                    status = "fail"
                elif type(code) is int and code == 0:
                    status = "pass"
            self.record(session_id or task_id, tool_name, tool_call_id, status)
        except Exception:
            pass

    def on_session_end(self, session_id="", task_id="", **kwargs):
        try:
            self.record(session_id or task_id, ended=True)
        except Exception:
            pass

    def snapshot(self):
        with self.lock:
            return dict(self.pending)
