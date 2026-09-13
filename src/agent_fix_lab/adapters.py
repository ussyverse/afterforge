"""Explicit adapters to commit-pinned libraries; no upstream CLI status inference."""

import json
import re
from pathlib import PurePosixPath

from triage.extractor import ErrorExtractor
from petrichor.db import SoilDB
from petrichor.soil import SoilMemory
from petrichor.diff import compute_diff
from correction_aware_learning import (
    append_trace_context,
    append_outcome_event,
    EventType,
    EvidenceSource,
    Polarity,
)

from .models import digest


def symptoms(text):
    return [e.to_dict() for e in ErrorExtractor(context_size=3).extract_from_text(text)]


def process_facts(payload):
    code = payload.get("exit_code")
    code = code if type(code) is int else None
    explicit_error = bool(payload.get("error")) or payload.get("success") is False
    status = (
        "fail"
        if explicit_error or (code is not None and code != 0)
        else ("pass" if code == 0 else "inconclusive")
    )
    return code, status


CONFIG_KEYS = {"python_version", "pytest_version", "platform", "project_kind"}


def selected_config(fields):
    # Restrictive field/value projection: never accept arbitrary env/config text.
    result = {}
    for k, v in fields.items():
        if k not in CONFIG_KEYS or not isinstance(v, str):
            continue
        if k.endswith("_version") and re.fullmatch(r"\d+\.\d+(?:\.\d+)?", v):
            result[k] = v
        elif k == "platform" and v in {"linux", "darwin", "win32"}:
            result[k] = v
        elif k == "project_kind" and v == "python":
            result[k] = v
    return result


def configuration_snapshot(root, logical_path, fields):
    path = PurePosixPath(logical_path)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("Configuration path must be a relative logical path")
    safe = selected_config(fields)
    if not safe:
        raise ValueError("No permitted configuration evidence")
    db = SoilDB(str(root))
    db.initialize()
    layer = SoilMemory(db).snapshot_text("/logical/" + str(path), json.dumps(safe, sort_keys=True))
    return {
        "logical_path": str(path),
        "fields": safe,
        "hash": layer.content_hash,
        "layer_id": layer.layer_id,
        "capture": "current-selected-fields",
    }


def configuration_difference(baseline, current):
    if not baseline or not current:
        return {"status": "inconclusive", "reason": "Missing configuration baseline"}
    if baseline["logical_path"] != current["logical_path"] or set(baseline["fields"]) != set(
        current["fields"]
    ):
        return {"status": "inconclusive", "reason": "Incompatible paths or field coverage"}
    return {
        "status": "pass",
        "diff": compute_diff(
            json.dumps(baseline["fields"], sort_keys=True, indent=2),
            json.dumps(current["fields"], sort_keys=True, indent=2),
        ),
    }


def structural_annotation(root, annotation):
    # Content stays in lab storage. Proposals are operator-labelled, never historical user evidence.
    case_id = annotation.case_id
    path = root / "correction.sqlite"
    append_trace_context(path, trace_id=case_id, session_id=None, created_at=0)
    return append_outcome_event(
        path,
        event_id=annotation.id,
        trace_id=case_id,
        event_type=EventType.ASSUMPTION_INVALIDATED,
        source=EvidenceSource.OPERATOR,
        polarity=Polarity.NEUTRAL,
        confidence=0.5,
        created_at=annotation.timestamp_seconds,
        evidence_digest="sha256:" + digest(annotation.model_dump()),
    )
