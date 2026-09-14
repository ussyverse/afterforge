# Agent Fix Lab → Afterforge 0.5.0

The existing repository was renamed to https://github.com/ussyverse/afterforge with the same GitHub identity and public visibility. AGENTS.md now records the public-visibility requirement following explicit user authorization; its other maintainer instructions remain intact. Public source does not authorize publication of private histories, credentials, local paths or detailed outputs. Preserve history; no force-push, replacement repository or visibility change is needed.

## Stable identities for one migration release

| Surface | New product entry | Retained identity/alias |
| --- | --- | --- |
| Standalone command | afterforge | agent-fix-lab |
| Terminal native command | hermes afterforge | hermes fixlab |
| Session command | /afterforge | /fixlab |
| Python distribution/import | unchanged | agent-fix-lab / agent_fix_lab |
| Plugin/toolset ID | unchanged | agent-fix-lab |
| Model tools | unchanged | fixlab_* |
| Bundled skill | unchanged | agent-fix-lab:regression-workflow |
| Data/config environment fallback | unchanged | AGENT_FIX_LAB_HOME and existing AFL_* controls |
| Default data / plugin-data directory | unchanged | agent-fix-lab |
| Portable format namespace | unchanged | agent-fix-lab.regression.v1/v2 |

Aliases point to the same implementation and storage. Never create a second plugin, duplicate hooks or automatically move/merge data just for branding. HERMES_HOME is already profile-resolved. An optional new environment name, if exposed by the final implementation, must retain the old fallback; consult CLI help/code rather than guessing one.

## Installed upgrade checklist

1. Stop owned browser jobs and privately back up evidence with SQLite/WAL consistency. Record the current plugin pin, runtime marker, data home and reminder generation privately. Do not publish those paths or contents.
2. Inspect the certified 0.5.0 stable locator: exact source/distribution commits, checksums and both successful CI links. A candidate SHA or old locator is not final approval.
3. Replace source using `hermes plugins install ussyverse/afterforge --force --ref NEW_DISTRIBUTION_SHA --enable` after normal stock scanner review. The plugin ID stays agent-fix-lab. No scanner weakening or dangerous-verdict bypass is permitted.
4. Run `hermes afterforge setup`, then `hermes afterforge doctor` and legacy `hermes fixlab doctor`. Locked staging must publish readiness only after doctor and keep the prior usable generation on failed/interrupted setup. Inspect failure diagnostics privately; do not delete the old runtime to hide a failed upgrade.
5. Verify the same evidence, old aliases, skill and exactly one hook registration set. Scan/review using an explicit source mapping shared by native/CLI/browser. Snapshots of one store may reuse a namespace; independent copies may not infer sameness from a filename.
6. Inspect reminder status. Changed adapter/entrypoint fingerprint invalidates old approval naturally. Re-propose and explicitly approve only after reviewing message, scope, implementation and optional case linkage. Old v1 or mismatched v2 approval remains inert; rollback cannot bypass reapproval.
7. Exercise a fresh reviewed regression, new portable import and later-commit retained check. Preserve historical receipts and confirm new authority is separately recorded. Teardown must retain evidence.

These are release acceptance requirements, not a claim that final installed migration has already passed. See [validation](validation.md).

## Immutable evidence compatibility

### Unreleased correction attribution candidate

Correction parser `corrections.v3` inspects up to 65,536 characters for complete
background-process envelopes, with command/output fields and balanced square
brackets. Completion, termination, lost/start-failure and watch-match variants
follow the inspected pinned stock producers. Markdown blockquotes are supported;
speech outside recognized spans remains eligible for ordinary marker discovery.
Unbalanced, truncated and unsupported shapes remain explicitly UNCERTAIN.
This is notification-shaped abstention, never authenticated origin attribution.
`excluded_notification_like` counts whole-message abstentions; the separate
`excluded_attributed_notification` counter is zero because this adapter supplies
no authenticated origin evidence. Uncertain-row and ignored-span counters expose
the distinction, and every scanned row still advances the cursor. Arbitrary
producer output is unescaped: balanced brackets are a conservative supported
subset, not an NLP guarantee. New requests can still be semantic false positives;
selected messages remain pending hypotheses, not automatic corrections.

New candidates use the v3 discovery identity. Existing v1/v2 candidates and reviews
remain byte-identical, readable, and in their existing queue state; a rescan does
not delete or automatically reject previously selected notifications, nor create
duplicate candidates for previously retained ordinary messages. An explicit bounded
rescan in a separate private store can compare discovery behavior. An operator must
review old queue entries separately. No database schema rewrite, release-tag change,
production activation, or model-learning claim is implied by this local candidate.

History parser v4 corrects global-call-ID merging with source/lineage identity. Original v1/v2/v3 observations remain readable. Explicit reconciliation can link only an exact retained observation to a reviewed v4 candidate. It cannot recover discarded source rows, invent a split, transfer annotation/cohort/review authority or certify recurrence. Reimport real available source and keep unresolved loss explicit.

Recipe v2 declared-v1, result v3 and bundle v2 add input-equivalence evidence. Legacy formats remain immutable and never gain new claims by loading or rerunning them. Create a new reviewed recipe to adopt the input contract; preserve old results. A new commit requires a new reviewed retained binding with unchanged frozen regression. Bundle checksums confer neither trusted-code status nor inherited execution approval.

## Legacy skill and removal

The older editable `skills/agent-fix-lab` wrapper/environment is distinct from the native bundled skill. Do not silently delete, replace or point it at a different data store. If the owner chooses removal, use the owned installer removal described in [hermes-integration.md](hermes-integration.md).

For native cleanup, run `hermes afterforge uninstall-runtime --confirm` before removing source, then `hermes plugins disable agent-fix-lab` and `hermes plugins remove agent-fix-lab`. Owned runtime/source removal preserves evidence and unrelated environments. Never modify another Hermes profile without explicit authorization.
