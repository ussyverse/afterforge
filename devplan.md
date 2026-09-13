# Development record

The existing implementation and private evidence were retained during continuation.

1. Discovery: inspected installed Hermes, schema 26, bounded WAL-consistent history and seven reference revisions. Recorded private manifests and selected 53 actual tool observations.
2. Vertical slice: import → observations → annotation/configuration → reviewed pytest → comparison → safe summary. Preserved milestone 6932ab8.
3. Dogfood hardening: five failing tests reproduced wrapped payload, delegation, pagination, compaction and retraction issues. Fixed them; suite reached 31 passes.
4. Browser continuation: fixed application out-of-order responses and stale smoke-test completion assumptions. Added operation states, mutation locks, fresh-server wheel tests and explicit stale-response/XSS probes. Three consecutive real-case workflows passed.
5. Correction and portability: pending candidate scan/review/retraction, selected-source bundles, validation/checksums, fresh-import review and actual red/green execution. Security suite reached 64 passes.
6. Delivery: pinned Actions workflow, documentation, isolated-wheel/clean-checkout checks, installed-skill verification and exact-index audit. Final result is recorded in docs/validation.md and handoff.md.

No frozen source observation was rewritten to improve a result. A separate grouping audit explains the weak holdout; no held-out failure was manufactured. Further work should first acquire genuinely independent sessions and reviewed labels before making evaluation claims.
