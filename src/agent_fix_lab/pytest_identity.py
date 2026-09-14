"""Runner-owned pytest hook: bounded identities, never repr of arbitrary objects.

Copied into the isolated assertion directory, not installed into the host.
Unsupported fixture/parameter values make equivalence unavailable. This observes
arguments, not arbitrary globals or I/O. The runner separately requires a
reviewed declared-v1 contract; this report alone cannot certify equivalence.
"""

import hashlib
import json
import math
import os
from pathlib import Path

_STATE = {"schema_version": 1, "collection": [], "inputs": [], "complete": True}


def freeze(value, depth=0, budget=None):
    if budget is None:
        budget = [4096]
    budget[0] -= 1
    if budget[0] < 0:
        raise ValueError("Input identity node budget exceeded")
    if depth > 12:
        raise ValueError("Nested input")
    kind = type(value)
    if value is None or kind in (bool, int, str):
        if len(str(value)) > 16384:
            raise ValueError("Large input")
        return [kind.__name__, value]
    if kind is float and math.isfinite(value):
        return ["float", value.hex()]
    if kind in (list, tuple) and len(value) <= 1024:
        return [kind.__name__, [freeze(item, depth + 1, budget) for item in value]]
    if kind is dict and len(value) <= 1024 and all(type(key) is str for key in value):
        return ["dict", [[key, freeze(value[key], depth + 1, budget)] for key in sorted(value)]]
    raise ValueError("Unsupported input identity")


def identity(item):
    return "test_regression.py::" + "::".join(item.nodeid.split("::")[1:])


def hashed(value):
    raw = json.dumps(value, sort_keys=True).encode()
    if len(raw) > 262144:
        raise ValueError("Large input identity")
    return hashlib.sha256(raw).hexdigest()


def pytest_collection_finish(session):
    if len(session.items) > 10000:
        _STATE["complete"] = False
        return
    try:
        _STATE["collection"] = [identity(item) for item in session.items]
        _STATE["parameters"] = hashed(
            [
                freeze(getattr(getattr(item, "callspec", None), "params", {}))
                for item in session.items
            ]
        )
    except (ValueError, TypeError, RecursionError):
        _STATE["complete"] = False


def pytest_runtest_call(item):
    if len(_STATE["inputs"]) >= 10000:
        _STATE["complete"] = False
        return
    try:
        _STATE["inputs"].append(
            [
                identity(item),
                hashed(
                    freeze({key: value for key, value in item.funcargs.items() if key != "request"})
                ),
            ]
        )
    except (ValueError, TypeError, RecursionError):
        _STATE["complete"] = False


def pytest_sessionfinish(session, exitstatus):
    _STATE["complete"] = _STATE["complete"] and len(_STATE["inputs"]) == len(_STATE["collection"])
    raw = json.dumps(_STATE)
    if len(raw.encode()) > 1048576:
        raw = '{"complete": false}'
    Path(os.environ["AFTERFORGE_INPUT_REPORT"]).write_text(raw)
