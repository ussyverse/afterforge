# Data model and version boundaries — 0.5.1

The application SQLite document store retains `PRAGMA user_version=1`; individual contract versions evolve separately. `documents` has append sequence, kind, stable ID and canonical JSON. Atomic insertion rejects changed content under an existing identity; identical insertion is idempotent. Unknown fields/versions fail explicitly. No Hermes writer is instantiated during import and its schema is never migrated.

| Record | Current contract | Authority |
| --- | --- | --- |
| SourceRecord / Run / Case | Base model v1; `hermes.sqlite.v4` parser | Source namespace, session/message/call IDs, lineage, payload digest, bounded facts and unknowns; process outcome separate from symptoms |
| Legacy reconciliation | `legacy-exact-observation.v1` | Explicitly reviewed exact retained observation only; `transfers_case_authority=false` |
| Annotation / CorrectionCandidate / CorrectionReview | Immutable source-derived and review documents | Author/reviewer kind is caller-declared; reviews/retractions append, original candidate stays pending |
| ConfigurationSnapshot | Selected allowlisted field set and normalized logical path | Comparable local configuration evidence, not reconstructed historical configuration |
| Recipe | v2; v1 reader retained | Explicit reviewed revisions/assertion/limits and `input_contract=declared-v1` or unknown |
| FrozenInput | logical_path, UTF-8 content, SHA-256 | Reviewed fixture bytes separate from either subject revision |
| ReproductionResult | v3; v1/v2 readers retained | Fresh process evidence, recipe/runtime digests, collected identities and frozen-input digest; unknowns explicit |
| Comparison | References both immutable result IDs | Matched intended failure plus corrected pass only with sufficient compatible evidence |
| Portable bundle | `agent-fix-lab.regression.v2`; v1 reader retained | Sanitized selected code/assertion/frozen inputs, checksums and declared provenance, not execution authorization |
| Managed runtime marker | schema v2 | Generation, source/lock/requirements digests, package versions and doctor result; no model-efficacy claim |
| Reminder policy | contract v2 | Message/scope/implementation/case digest and generation-bound local approval; no automatic authority transfer |

## History identity and reconciliation

Canonical v4 identity uses explicit source and lineage, call identity when available, and conservative observation distinctions. A `call_1` in unrelated roots is not one incident. Parent/compaction observations may legitimately refer to the same incident; missing calls and conflicts cannot invent equality. Generic repeated output does not prove recurrence or causal repair. Dataset grouping is a separate, potentially more conservative analysis.

`history.reconcile_legacy_identity` accepts a legacy Run and a bounded source-scoped page of v4 candidates. It compares source_id, session_id, message_id, tool_call_id, tool_name and payload_digest. Exactly one matching retained observation plus explicit reviewer attribution can produce linked-observation. Partial-page absence stays unresolved. Persist its returned document separately; it does not mutate either input. Discarded legacy observations and annotation/split applicability remain unknown. Reimport actual source rather than synthesizing a split from a reused call ID.

## Regression identity

Recipe v2 includes frozen_inputs and path-specific reviewed_data_changes. `declared-v1` means inspected deterministic code, supported typed pytest values and frozen bytes; it is not inferred dependency closure. External ArtifactReference fixtures remain unsupported. Ambient filesystem/network/clock/random/environment dependencies, hidden mutable globals or fixture side effects cannot be certified by changing a flag.

Result v3 adds input_contract/input_unknowns, recipe/runtime digests, collection_identities and frozen_input_digest. Custom pytest IDs do not hide changed typed parameter values. Unsupported values or absent identity evidence mean equivalence is unavailable. A new recipe review creates new authority; loading/rerunning a legacy recipe does not upgrade the old record. A later-commit retained check must create a new reviewed binding and receipt while preserving historical recipes/results.

The inspected source-host schemas are 26 and 30, separately from application/model versions. Schema 30 inspection is not automatic adapter support; consult [host matrix](native-plugin.md) and final validation. Unix timestamps are seconds; message IDs are identities, not timestamps. Source mapping across profiles and surfaces must be explicit, never inferred solely from `state.db`.