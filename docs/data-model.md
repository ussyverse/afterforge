# Data model and versions

Application database `PRAGMA user_version=1`; Pydantic contract `schema_version=1`. Unknown versions/extra model fields fail explicitly rather than migrate or guess. The source Hermes database must have an explicit schema version 26. Units are Unix seconds in fields named `timestamp_seconds`; message IDs are identities, not timestamps.

SQLite `documents` has an append sequence, kind, stable ID and canonical JSON. `put_many` is atomic and rejects changed content under an existing identity. Repeated identical insertion is a no-op. Source observations and derived annotations are separate documents.

- SourceRecord: source namespace, parser version, session/message/tool-call IDs, parent/delegation IDs, archived/compacted flags, time and payload digest.
- Run: process status/exit code, capture source, bounded output, symptoms/context, duplicate source records and explicitly unknown fields. Bundle projections have their own capture-source value and do not masquerade as historical captures.
- Case: stable run identity, incident group, historical/dogfood cohort, development/held-out/unassigned split and real/derived/synthetic provenance.
- Annotation: author-kind declaration, expected behavior, text, time, optional retraction target. Effective state is computed without destroying the history.
- CorrectionCandidate: inferred selection, failed-operation and assistant-claim references, subsequent user-role record, rationale/confidence, permanently pending original record. Effective review status is computed from separate CorrectionReview documents. Reviewer identity is declared, not authenticated.
- ConfigurationSnapshot/baseline: selected non-secret fields, logical path, content hash and compatible field-set comparison. Missing historical configuration remains unknown.
- Recipe: repository/revisions, test SHA-256, expected behavior/intended failure, reviewed flag, timeout/output limits, pytest dependency and provenance. External fixture references are rejected; commit inspected fixtures.
- Reproduction: new UUID, variant, revision/test/diff identities, interpreter/runtime fields, direct process capture, exit code, status, test counts, failure text and bounded output.
- Comparison: references to both fresh results and a justified pass/fail/inconclusive/not-run classification.
- Bundle: `agent-fix-lab.regression.v1`, selected source variants, one shared assertion, sanitized metadata, original-revision uncertainty, per-file and manifest checksums. See recipes-and-bundles.md.

Historical tool-call duplicate identity is stronger than output similarity. Every compacted observation is retained even when linked to an existing case. Dataset grouping may be more conservative than incident deduplication and is not an automatic recurrence-strengthening operation.

Changing a parser does not overwrite already imported facts. A future migration must explicitly version/relate derived records and preserve original provenance.
