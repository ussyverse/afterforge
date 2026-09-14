# Reviewed evidence and experimental reminder — 0.5.1

Afterforge's stable objective is deterministic reviewed regression retention. Intervention evidence, committed-check receipts and the optional native reminder have different authority. None establishes autonomous learning or measured model improvement.

## Committed checks

`afterforge --home LAB current-check-plan RECIPE_ID` returns the reviewed corrected-commit recipe and digest without execution. Inspect the code and inputs, then authorize with `verify-current RECIPE_ID --approve-digest DIGEST`. Native equivalents use `hermes afterforge` (legacy `hermes fixlab`). Tool JSON success means operation completion; inspect `data.status`. Native terminal operation errors/nonpassing verification exit nonzero.

The existing runner executes the corrected committed archive, not the baseline or live worktree. HEAD/reviewed assertion are observed at endpoints; changed evidence is inconclusive. This is not filesystem locking: transient changes, hidden-index flags, external services and the live environment are not certified. A later commit requires a new explicitly reviewed retained-check binding with unchanged frozen regression and an immutable receipt; never mutate the historical recipe or reuse its approval. Final guided later-commit/ignored-file integration remains a release gate. No receipt activates policy or proves efficacy. Trusted-code/not-an-OS-sandbox limits apply.

## Optional fixed reminder: one review, explicit activation, reversible state

The project-scoped one-shot pre_verify reminder is experimental and inert until activated. It does not execute tests or certify completion. Its built-in evaluation is `synthetic-hook-contract`, with `behavioral_efficacy=not-run`; no model-efficacy claim follows from reminder delivery.

```sh
hermes afterforge policy propose --scope ABSOLUTE_PROJECT
# Inspect message, scope, implementation fingerprint and candidate digest first.
hermes afterforge policy activate --scope ABSOLUTE_PROJECT --approve-digest DIGEST --generation 0
hermes afterforge policy status
hermes afterforge policy rollback --generation CURRENT_GENERATION
```

Use the actual expected generation from status; zero is only an initial-state example. An optional `--case-id INCIDENT_ID` links an existing immutable case digest. Supply the same case ID at activation; dropping/changing it changes the approval. No transcript text enters the reminder. Case linkage is provenance, not diagnosis, causal evidence or deployment approval.

Policy contract v2 binds the fixed message, scope, optional case linkage, native adapter Python bytes and registration entrypoint fingerprint. Old v1 approvals or changed implementation are inert and report `implementation_status=requires-reapproval`. Re-propose, inspect and approve the new digest explicitly; there is no silent transfer. Rollback cannot make a mismatched implementation effective.

Transitions check expected generations under a file lock and atomically replace private state while retaining prior records. Repeated rollback is idempotent rather than reactivation, and rollback remains available at the event cap. Activation state and rollback are inspectable; a GUI must expose this same review rather than introduce a second approval authority. Final integrated UI/migration validation is pending.

The hook reads current policy on invocation. It acts only for coding=true, attempt=0 and nonempty absolute changed paths wholly within the selected scope. Missing/relative/mixed paths, symlink escapes, a symlink-replaced scope or corrupt/incompatible state cause abstention. Host continuation caps still apply; this is not an unconditional completion veto. It may add a turn even when checks passed, but does not ask for reruns solely because of the reminder. No arbitrary prompt, memory, skill or permission changes occur. Model trials and cost/efficacy measurements remain unmeasured, not hidden behind code-test receipts.

## Structured verification shadow assessment

`afterforge verification-shadow --file evidence.json` evaluates strict verification-shadow-v1 input without opening the lab DB, executing commands or changing responses. Fields: schema_version, revision, draft_kind (success/blocker/continuation/unknown), obligations (id/scope), checks (unique sequence, obligation_id, scope, revision, status, optional purpose required/baseline/unrelated). Limits: 256 KiB, 64 obligations, 512 checks; unknown fields/coercions are rejected.

Only the latest required check at the exact declared revision/scope counts for each obligation. Unrelated successes cannot erase failure; baseline runs do not satisfy final verification; edits invalidate old revision evidence. Failed, missing and inconclusive checks stay distinct. Unresolved success drafts yield would-request-continuation; honest blocker/continuation drafts yield no-objection without claiming verification passed. Unknown drafts or absent obligations cause abstention. CLI exit zero means assessment completed, not tests passed; inspect verification_status and shadow_decision.

These are caller-declared identities, sequences and obligations, not authenticated terminal evidence or a semantic classifier. A digest is not an attestation. There is no automatic extraction or authoritative live capture adapter.

`verification-shadow --captured-bindings --file evidence.json` accepts an explicitly reviewed mapping of passive captured events to obligations. Input adds capture, bindings and reviewed=true; bindings carry sequence, tool_call_id, obligation_id, scope and revision. Missing/duplicate/inconsistent references are rejected. A binding_digest identifies the request. Otherwise passing overall verification is downgraded to inconclusive because capture is best-effort and may miss later results. No completeness override or positive certification exists. Independently bounded 32-session/64-event capture does not change that authority.

## Deterministic intervention evidence

Prepare an inert proposal with case_ids, surface, scope, hypothesis, rationale, candidate_text, base_revision, candidate_revision and suite. Surface labels code/tool-schema/skill/verification-policy/configuration/routing/memory describe proposals, not deployment adapters. Candidate text never executes or becomes model instructions.

Each suite entry references a distinct reviewed recipe at the proposal's exact revisions, role and expected baseline pass/fail; candidate must pass. Required roles: target, successful-control and negative-control. Target recipes belong to motivating cases and expect baseline fail; preservation controls pass before/after. Optional related/unrelated/held-out roles are caller declarations, not proof of independent samples.

```sh
afterforge --home LAB intervention-propose --file proposal.json
afterforge --home LAB intervention-list --limit 10
afterforge --home LAB intervention-show INTERVENTION_ID
afterforge --home LAB intervention-evaluate INTERVENTION_ID --candidate-digest DIGEST --reviewed
afterforge --home LAB intervention-review INTERVENTION_ID --evaluation-id EVALUATION_ID --candidate-digest DIGEST --decision accept-evidence --note 'Inspected the evidence'
```

A nonpassing evaluation exits 2. Evaluation uses the real Lab.run/pytest runner, not historical commands or candidate_text. Recipe/suite/candidate fingerprints, authorizations, fresh result IDs, interpreter/grader digests and review receipts are immutable. Changed proposals need new records. The `/interventions` page provides expert JSON proposal entry, receipt inspection, explicit evaluation and evidence review behind the existing loopback mutation protections; untrusted text is not HTML. Detail is bounded and older records remain stored.

Target success requires matched-failure comparison with compatible regression inputs, not arbitrary red/green exits. Controls must preserve pass. Results are `deterministic-recipe-suite`, `behavioral_trials=not-run`, `promotion_authorized=false`, authority local-caller-declared. Accept-evidence is not approve-deployment or authenticated human approval. Missing/stale/cancelled evidence never becomes a pass.

## Validation boundary

Synthetic tests cover lifecycle, digest/revision/assertion mismatch, legacy reapproval, symlink abstention, repeated rollback, controls, immutable conflicts, CLI/web mutation protection and malicious-looking text. Final 0.5.0 packaged browser and real-host migration must rerun these contracts; earlier milestone totals belong in CHANGELOG.md, not current certification.

Further efficacy research requires balanced controls, isolated repeated agent trials, calibrated grading and protected review. References: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents and https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks/#pre_verify . These are design requirements, not results established by this release.