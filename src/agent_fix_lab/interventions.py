"""Immutable intervention proposals and recipe-level evaluations, never deployment.

Candidate text is inert evidence. Only existing reviewed recipes execute. A pass
here is not a behavioral trial, human authentication, or promotion authorization.
"""

import hashlib
import sys
import time
import uuid
from pathlib import Path
from typing import Literal

from pydantic import Field

from .models import Contract, digest

SHA = r"^[0-9a-f]{40}$"


class SuiteEntry(Contract):
    recipe_id: str = Field(min_length=1, max_length=128)
    role: Literal[
        "target", "related", "successful-control", "negative-control", "unrelated", "held-out"
    ]
    baseline: Literal["pass", "fail"]
    candidate: Literal["pass"] = "pass"


class Proposal(Contract):
    case_ids: list[str] = Field(min_length=1, max_length=20)
    surface: Literal[
        "code", "tool-schema", "skill", "verification-policy", "configuration", "routing", "memory"
    ]
    scope: str = Field(min_length=1, max_length=256)
    hypothesis: str = Field(min_length=1, max_length=4000)
    rationale: str = Field(min_length=1, max_length=4000)
    candidate_text: str = Field(min_length=1, max_length=16000)
    base_revision: str = Field(pattern=SHA)
    candidate_revision: str = Field(pattern=SHA)
    suite: list[SuiteEntry] = Field(min_length=3, max_length=20)


def propose(lab, values):
    if not isinstance(values, dict):
        raise ValueError("Proposal must be a JSON object")  # noqa: TRY004 — CLI/web validation contract
    proposal = Proposal(**values).model_dump()
    if proposal["base_revision"] == proposal["candidate_revision"]:
        raise ValueError("Baseline and candidate revisions must differ")
    if len(set(proposal["case_ids"])) != len(proposal["case_ids"]):
        raise ValueError("Duplicate motivating cases")
    for case in proposal["case_ids"]:
        lab.store.get("case", case)
    entries = proposal["suite"]
    if len({x["recipe_id"] for x in entries}) != len(entries):
        raise ValueError("A recipe cannot be relabeled as multiple controls")
    roles = {x["role"] for x in entries}
    if not {"target", "successful-control", "negative-control"}.issubset(roles):
        raise ValueError("Target, successful and negative controls are required")
    frozen = []
    for entry in entries:
        recipe = lab.store.get("recipe", entry["recipe_id"])
        if not recipe["reviewed"]:
            raise ValueError("Every suite recipe must already be reviewed")
        if (recipe["faulty_revision"], recipe["corrected_revision"]) != (
            proposal["base_revision"],
            proposal["candidate_revision"],
        ):
            raise ValueError("Suite revisions must match the proposed candidate")
        if entry["role"] == "target":
            if entry["baseline"] != "fail" or recipe["case_id"] not in proposal["case_ids"]:
                raise ValueError("Target must reproduce a motivating failure")
        elif (
            entry["role"] in ("successful-control", "negative-control", "unrelated")
            and entry["baseline"] != "pass"
        ):
            raise ValueError("Preservation controls must pass before and after")
        frozen.append({**entry, "recipe_digest": digest(recipe)})
    record = {
        "id": uuid.uuid4().hex,
        "schema_version": 1,
        "created_at": time.time(),
        "proposal": proposal,
        "candidate_digest": digest(proposal),
        "suite": frozen,
        "suite_digest": digest(frozen),
        "status": "proposed",
        "promotion_authorized": False,
        "causality": "hypothesis-not-established",
    }
    lab.store.put("intervention", record)
    return record


def evaluate(lab, identifier, candidate_digest, *, reviewed=False):
    record = lab.store.get("intervention", identifier)
    if reviewed is not True or candidate_digest != record["candidate_digest"]:
        raise ValueError("Review the exact candidate digest before executing its suite")
    # Validate the whole frozen suite before any code runs.
    for entry in record["suite"]:
        recipe = lab.store.get("recipe", entry["recipe_id"])
        if not recipe["reviewed"] or digest(recipe) != entry["recipe_digest"]:
            raise ValueError("Frozen reviewed recipe changed")
    grader_digest = digest(
        {
            name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
            for name in ("interventions.py", "runner.py", "service.py", "models.py")
        }
    )
    authorization = {
        "id": uuid.uuid4().hex,
        "schema_version": 1,
        "intervention_id": identifier,
        "candidate_digest": candidate_digest,
        "suite_digest": record["suite_digest"],
        "created_at": time.time(),
        "authority": "local-caller-declared",
        "purpose": "recipe-evaluation-only",
    }
    lab.store.put("intervention-evaluation-authorization", authorization)
    checks = []
    for entry in record["suite"]:
        try:
            run = lab.run(entry["recipe_id"])
            results = {r["variant"]: r for r in run["results"]}
            observed = {v: results[v]["status"] for v in ("faulty", "corrected")}
            # Target additionally needs the core's matched-failure comparison.
            uncertain = any(s in ("inconclusive", "not-run") for s in observed.values())
            passed = observed == {"faulty": entry["baseline"], "corrected": "pass"}
            if entry["role"] == "target":
                passed = passed and run["comparison"]["status"] == "pass"
            checks.append(
                {
                    "recipe_id": entry["recipe_id"],
                    "role": entry["role"],
                    "observed": observed,
                    "result_ids": [r["id"] for r in run["results"]],
                    "status": "inconclusive" if uncertain else "pass" if passed else "fail",
                }
            )
        except (ValueError, KeyError, OSError) as exc:
            checks.append(
                {
                    "recipe_id": entry["recipe_id"],
                    "role": entry["role"],
                    "status": "inconclusive",
                    "error": type(exc).__name__,
                }
            )
    statuses = {x["status"] for x in checks}
    result = {
        "id": uuid.uuid4().hex,
        "schema_version": 1,
        "intervention_id": identifier,
        "candidate_digest": candidate_digest,
        "suite_digest": record["suite_digest"],
        "authorization_id": authorization["id"],
        "created_at": time.time(),
        "status": "fail"
        if "fail" in statuses
        else "inconclusive"
        if "inconclusive" in statuses
        else "pass",
        "checks": checks,
        "evaluation_kind": "deterministic-recipe-suite",
        "python_version": sys.version.split()[0],
        "grader_digest": grader_digest,
        "behavioral_trials": "not-run",
        "promotion_authorized": False,
    }
    lab.store.put("intervention-evaluation", result)
    return result


def review(lab, identifier, evaluation_id, candidate_digest, decision, note):
    if (
        decision not in ("accept-evidence", "reject")
        or not isinstance(note, str)
        or not 1 <= len(note.strip()) <= 4000
    ):
        raise ValueError("Explicit evidence decision and bounded note required")
    record = lab.store.get("intervention", identifier)
    evaluation = lab.store.get("intervention-evaluation", evaluation_id)
    if (
        evaluation["intervention_id"] != identifier
        or candidate_digest != record["candidate_digest"]
        or evaluation["candidate_digest"] != candidate_digest
        or evaluation["suite_digest"] != record["suite_digest"]
    ):
        raise ValueError("Review does not match this immutable candidate and evaluation")
    if decision == "accept-evidence" and evaluation["status"] != "pass":
        raise ValueError("Cannot accept unsuccessful evaluation evidence")
    result = {
        "id": uuid.uuid4().hex,
        "schema_version": 1,
        "intervention_id": identifier,
        "evaluation_id": evaluation_id,
        "candidate_digest": candidate_digest,
        "suite_digest": record["suite_digest"],
        "created_at": time.time(),
        "decision": decision,
        "note": note,
        "authority": "local-caller-declared",
        "promotion_authorized": False,
    }
    lab.store.put("intervention-review", result)
    return result


def inspect(lab, identifier):
    record = lab.store.get("intervention", identifier)
    return {
        **record,
        "evaluations": [
            x
            for x in lab.store.all("intervention-evaluation")
            if x["intervention_id"] == identifier
        ][-20:],
        "reviews": [
            x for x in lab.store.all("intervention-review") if x["intervention_id"] == identifier
        ][-20:],
        "activation": "unsupported",
        "behavioral_improvement": "not-demonstrated",
    }


def listing(lab, offset=0, limit=10):
    if type(offset) is not int or type(limit) is not int or offset < 0 or not 1 <= limit <= 25:
        raise ValueError("Invalid pagination")
    rows = lab.store.all("intervention")
    return {
        "items": [
            {k: row[k] for k in ("id", "candidate_digest", "status", "created_at")}
            for row in rows[offset : offset + limit]
        ],
        "total": len(rows),
        "next_offset": offset + limit if offset + limit < len(rows) else None,
    }
