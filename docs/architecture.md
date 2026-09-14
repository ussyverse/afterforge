# Afterforge architecture — 0.5.1

The standalone `agent_fix_lab` package is independent of Hermes runtime imports. CLI and web call the shared Lab service; the installed wheel contains its browser assets, with no CDN/frontend server dependency. A thin standard-library native adapter delegates to an explicitly installed private backend. Aliases register around one Runtime, not duplicate tools/hooks.

## Boundaries

| Component | Responsibility | Does not establish |
| --- | --- | --- |
| history.py | Read-only SQLite backup for WAL-consistent snapshots; explicit schema checks; bounded v4 source/lineage observations | Independent incident identity from a repeated call ID or generic output |
| corrections.py / service | Conservative candidate discovery, append-only review/retraction, shared workflow operations | Authenticated human correction, causal repair or execution approval |
| adapters.py | Pinned Triage symptoms; Petrichor selected-field hashes/diffs; structural correction-aware-learning relations | Process success from symptom absence, historical configuration from a current snapshot, active learning |
| runner.py / pytest_identity.py | Committed archive execution, recipe v2 declared inputs, result v3 collection/typed-input/runtime evidence | An OS sandbox, automatic Python dependency proof, live-worktree/environment certification |
| bundles.py | v2 selected-source/frozen-input projection, strict validation, fresh local import | Trusted code from checksums or inherited execution authority |
| current_check.py | Digest-reviewed committed-check receipts, immutable historical evidence | Authority to silently bind old approval to a new commit |
| hermes_plugin/runtime.py | Serialized uv locked staged setup/removal, resolved manifests, atomic doctor readiness, bounded private output | Permission to modify Hermes's own environment |
| hermes_plugin/hooks.py / policy.py | Independently bounded metadata capture and opt-in fixed reminder | Complete verification coverage or model efficacy |

The shared guided scan/review/draft/retained-check services and SQL-bounded pagination are being integrated. Treat that path as a release acceptance gate until the final packaged workflow and scale tests pass; do not duplicate behavior in frontend or native adapters.

## Identity and persistence

SQLite documents are versioned, append-only and immutable under an existing ID. Explicit source mapping must be reused across native/CLI/browser reads of the same logical profile store; filenames and copied paths do not establish sameness. v4 canonical identity incorporates lineage and preserves legitimate compaction links without global call-ID merges. Reconciliation can link only a retained exact observation and never transfers old annotation/split/recurrence authority or invents lost source evidence.

Corrections have their own resumable cursor, separate from tool import; same-time pagination and deferred linking must not discard a candidate merely because its nearby tool record arrives later. Effective review state is computed from immutable receipts. Pending/accepted/rejected and pass/fail/inconclusive/not-run remain separate dimensions.

## Runner and transport

Reviewed pytest executes directly, not through a shell, in temporary tracked-source archives. Environment filtering, disabled plugin autoload, timeouts, bounded output and process-group cleanup reduce accidental interference but are not hostile-code isolation. Regression input bytes are materialized separately from subject code and exposed through AFTERFORGE_FROZEN_INPUTS. Collection and typed parameter digests supplement—not replace—the caller's declared deterministic-input review. Old evidence never acquires newer authority on load.

Native JSON success reports operation completion, not verification success. Native terminal failures/nonpassing checks must exit nonzero. Capture outcomes have an independent 32-session LRU and 64-event/session cap; pending-hint consumption does not remove the bound. Best-effort/truncated capture remains inconclusive for positive certification.

## Browser security and consistency

Loopback bind; Host/Origin/Fetch-Site guards, per-launch mutation tokens, bounded bodies, restrictive CSP, no CORS, and text-only rendering of untrusted history. Same-user malware is outside this local security boundary. Request generations reject stale list/detail responses and mutations are single-flight. Browser tests use actual completion state and fresh packaged servers, not arbitrary sleeps.

## Distribution

Committed runtime blobs plus lock/legal/privacy material form a reproducible distribution with RELEASE.json. Candidate publication is separate from stable certification. Both exact-source CI workflows and the exact-distribution native matrix must pass before atomic stable-pointer/locator advancement. See [release](release.md), [data model](data-model.md), [privacy](privacy.md) and [sources](sources.md).