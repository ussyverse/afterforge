"""Small, precise native tool schemas. No application imports."""

ID = {"type": "string", "minLength": 1, "maxLength": 128, "pattern": "^[A-Za-z0-9_.:-]+$"}
TEXT = {"type": "string", "maxLength": 4000}
SPECS = {
    "status": (
        "Check managed runtime availability, queued sessions and legacy skill migration before using Fix Lab.",
        {},
        [],
    ),
    "scan": (
        "Import a bounded page of actual Hermes history. Hooks only queue metadata; this performs read-only WAL-consistent ingestion.",
        {"session_id": ID},
        [],
    ),
    "list_cases": (
        "Find previous cases; use pagination rather than requesting all private evidence.",
        {
            "query": TEXT,
            "status": {"enum": ["fail", "pass", "inconclusive", "not-run"]},
            "offset": {"type": "integer", "minimum": 0, "maximum": 100000},
            "limit": {"type": "integer", "minimum": 1, "maximum": 25},
        },
        [],
    ),
    "inspect_case": (
        "Inspect observed failure evidence, unknowns and correction candidates separately from interpretations.",
        {"case_id": ID},
        ["case_id"],
    ),
    "review_case": (
        "Record an agent-proposed correction/expectation, or review a pending candidate. Never claims authenticated human authorship.",
        {
            "case_id": ID,
            "candidate_id": ID,
            "text": TEXT,
            "expected": TEXT,
            "decision": {"enum": ["accepted", "rejected", "retracted"]},
            "retracts": ID,
        },
        ["text"],
    ),
    "build_regression": (
        "Associate an inspected existing pytest recipe with a case. No automatic reduction or execution of historical commands. Explicit local review is mandatory.",
        {"recipe_file": {"type": "string", "maxLength": 4096}, "reviewed": {"type": "boolean"}},
        ["recipe_file", "reviewed"],
    ),
    "verify_regression": (
        "Run an already reviewed pytest recipe against its two frozen revisions. Inspect code first; not an OS sandbox.",
        {"recipe_id": ID},
        ["recipe_id"],
    ),
    "report": (
        "Return a compact privacy-minimized count/status report, not raw conversation text.",
        {"case_id": ID},
        ["case_id"],
    ),
}
SCHEMAS = {
    f"fixlab_{name}": {
        "name": f"fixlab_{name}",
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }
    for name, (description, properties, required) in SPECS.items()
}
