"""Proposed safe reductions; no claim to reconstruct an old Hermes revision."""

import json
from pathlib import Path


def profile_home(home, profile):
    # HERMES_HOME is already resolved for the running profile.
    return Path(home)


def search_output(payload):
    if "matches_text" in payload:
        return payload["matches_text"]
    if "matches" in payload:
        return payload["matches"]
    if payload.get("total_count") == 0:
        return ""
    raise ValueError("Unknown search output shape")


def decode_response(text):
    try:
        return {"status": "parsed", "value": json.loads(text)}
    except (ValueError, TypeError):
        return {"status": "inconclusive", "reason": "Response is not JSON"}
