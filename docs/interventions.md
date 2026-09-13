# Reviewed interventions — evidence milestone

Standalone 0.2.0 / native plugin 0.3.0. This is the implemented proposal and deterministic evaluation milestone, not automatic policy learning or deployment. No new behavior-changing hooks, memory writes, profile changes or promotion endpoints exist. The existing eight native tools and two passive hooks are unchanged.

## Working workflow

Create the motivating cases and existing reviewed recipes with the current CLI/web workflow. Prepare an intervention JSON object containing case_ids, surface, scope, hypothesis, rationale, candidate_text, base_revision, candidate_revision and suite. Supported surface labels: code, tool-schema, skill, verification-policy, configuration, routing, memory. Labels describe proposals; they are not implemented deployment adapters. The text is inert and no model inference is performed to generate or evaluate it.

Each suite entry names a recipe_id, role and baseline (pass or fail); candidate must be pass. A target, successful-control and negative-control are required. Related, unrelated and held-out roles are optional. Every recipe must be explicitly reviewed, refer to the proposal's exact baseline/candidate Git revisions, and have a distinct ID. Target recipes must belong to a motivating case and expect baseline fail. Preservation controls expect pass before and after. Role assignment is a caller assertion, not proof of independent samples or held-out isolation.

```sh
agent-fix-lab --home PRIVATE_HOME intervention-propose --file proposal.json
agent-fix-lab --home PRIVATE_HOME intervention-list --limit 10
agent-fix-lab --home PRIVATE_HOME intervention-show INTERVENTION_ID
agent-fix-lab --home PRIVATE_HOME intervention-evaluate INTERVENTION_ID --candidate-digest EXACT_DIGEST --reviewed
agent-fix-lab --home PRIVATE_HOME intervention-review INTERVENTION_ID --evaluation-id EVALUATION_ID --candidate-digest EXACT_DIGEST --decision accept-evidence --note 'Inspected the evidence'
```

A nonpassing evaluation exits 2. Evaluation invokes the existing Lab.run/pytest runner, not candidate_text or commands extracted from history. Recipe fingerprints, candidate/suite digests, evaluation authorizations, fresh result IDs, interpreter version, grader source digest and review receipts are preserved in the existing immutable Store. No DB schema migration is required. Changing a proposal means creating another immutable record; an old digest cannot authorize evaluation/review of the new record.

The web interface at /interventions provides proposal JSON entry, candidate/receipt inspection, explicit evaluation authorization and evidence review. It uses the existing loopback Host/Origin checks, per-launch mutation token, request size bound and restrictive CSP. Candidate and receipt content is rendered as text, not HTML. The homepage links to it. Listing is paginated; detail returns at most the latest 20 evaluation and review receipts (older records remain in Store).

## Meaning of a result

Target success requires the core's matched-failure comparison, not merely arbitrary red/green exit codes. Successful and negative controls must retain passing results in both variants. Unknown/missing/stale/cancelled evidence is not treated as success. Evaluation failures remain distinct from inconclusive results. The regression recipe's expected failure text still applies; an unexpected failure remains inconclusive rather than silently being attributed to the intervention.

Results are labeled deterministic-recipe-suite and behavioral_trials=not-run. Passing verifies the frozen recipe suite against those code revisions, not that the proposal text explains the causal fix, that a skill/memory change works, or that Hermes has learned. Accept-evidence does not mean approve-deployment. All receipts retain promotion_authorized=false and authority=local-caller-declared. The local CLI/web review is not cryptographic human authentication and agents with equivalent local privileges may invoke it. No inference of human approval is made.

The motivating correction, hypothesis and candidate text can contain untrusted content. They never become executable instructions or permission to modify the host. Execution remains trusted local pytest, NOT an OS sandbox. Candidate generators cannot obtain promotion by supplying extra JSON fields; contracts reject unknown fields.

## Implemented tests and next acceptance boundary

Tests execute real target and control recipes, cover changed assertions, failed controls, digest mismatch, immutable-record conflicts, missing/duplicate controls, unreviewed recipes, revision mismatch, unknown approval fields, cross-candidate receipt reuse, CLI access, and web mutation protection. Packaged browser smoke tests exercise proposal creation, execution, evidence review and text-only rendering of malicious-looking candidate content.

The next milestone remains the structured verification-obligation/shadow-policy engine, followed by real isolated Hermes inference trials. Only after that should target-specific, operator-approved activation and conflict-safe rollback be implemented. The documented pre_verify hook is bounded and coding-only; do not advertise it as an unconditional completion veto. Existing Hermes built-in verification behavior must be tested before introducing overlapping policy.

Research/design context: Anthropic's agent eval guidance (https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) and Hermes's documented hook contract (https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks/#pre_verify). Balanced controls, isolated repeated agent trials, grader calibration and protected review are requirements for the later behavioral milestone, not results established by this release.
