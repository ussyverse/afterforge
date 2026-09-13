"""Versioned contracts. Timestamps are Unix seconds, never inferred from IDs."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["pass", "fail", "inconclusive", "not-run"]


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    schema_version: Literal[1] = 1


class SourceRecord(Contract):
    id: str
    source_id: str
    parser: str = "hermes.sqlite.v1"
    source_revision: str | None = None
    session_id: str
    message_id: int
    tool_call_id: str | None = None
    tool_name: str | None = None
    timestamp_seconds: float
    parent_session_id: str | None = None
    delegated_from: str | None = None
    active: bool = True
    compacted: bool = False
    archived: bool = False
    payload_digest: str
    logical_project: str | None = None


class Run(Contract):
    id: str
    source: SourceRecord
    observed_status: Status
    exit_code: int | None = None
    capture_source: Literal["historical-tool"] = "historical-tool"
    output: str
    symptoms: list[dict] = Field(default_factory=list)
    context: list[dict] = Field(default_factory=list)
    configuration: dict = Field(default_factory=dict)
    unknown: list[str] = Field(
        default_factory=lambda: [
            "historical_revision",
            "dirty_diff",
            "dependencies",
            "expected_behavior",
        ]
    )


class Annotation(Contract):
    id: str
    case_id: str
    timestamp_seconds: float
    author_kind: Literal["operator", "agent-proposed", "historical-user"]
    text: str = Field(min_length=1, max_length=10000)
    expected_behavior: str | None = Field(default=None, max_length=10000)
    retracts: str | None = None
    evidence_message_id: int | None = None


class ArtifactReference(Contract):
    sha256: str
    logical_path: str
    provenance: Literal["real", "derived", "synthetic", "fresh"]


class Case(Contract):
    id: str
    run_id: str
    incident_group: str
    cohort: Literal["historical", "dogfood"] = "historical"
    provenance: Literal["real", "derived", "synthetic"] = "real"
    split: Literal["development", "held-out", "unassigned"] = "unassigned"


class Recipe(Contract):
    id: str
    case_id: str
    repository: str
    faulty_revision: str
    corrected_revision: str
    test_file: str
    test_sha256: str
    expected_behavior: str = Field(min_length=1)
    intended_failure: str = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=lambda: ["pytest"])
    fixture_inputs: list[ArtifactReference] = Field(default_factory=list)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    output_limit_bytes: int = Field(default=65536, ge=1024, le=1048576)
    reviewed: bool = False
    provenance: Literal["derived", "real", "synthetic"] = "derived"


class ReproductionResult(Contract):
    id: str
    recipe_id: str
    variant: Literal["faulty", "corrected"]
    revision: str
    dirty_diff_sha256: str
    test_sha256: str
    timestamp_seconds: float
    duration_seconds: float
    command: list[str]
    exit_code: int | None
    status: Status
    reason: str
    output: str
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    capture_source: Literal["local-runner.v1"] = "local-runner.v1"


class Comparison(Contract):
    recipe_id: str
    faulty_result_id: str | None = None
    corrected_result_id: str | None = None
    status: Status = "not-run"
    reason: str
