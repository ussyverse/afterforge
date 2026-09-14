# Guided regression workflow — 0.5.0 candidate

The shared services and `/guided` screen provide the implemented workflow below. Three consecutive packaged guided flows now include correction review, draft authorization, red/green, later-commit retention and error recovery. Separate expert/intervention browser and portable installed-CLI checks passed. Exact candidate CI/native evidence and the remaining original-fixture migration baseline blocker are recorded in [validation](validation.md).

## 1. Select an explicit source and scan bounded pages

Set `AFTERFORGE_SOURCE_ID` to a private stable identifier for one logical profile/history store before launching native Hermes or the browser server. Standalone `import-hermes --source PATH --source-id SAME_ID` uses the same mapping. Reuse an identity across that store's snapshots, not across independent copies merely called state.db. HERMES_HOME is already resolved; do not append profiles/default. Missing mapping is an actionable error, not permission to infer identity from a basename.

Native `hermes afterforge scan`, `/afterforge scan` and the guided scan action delegate to shared bounded ingestion. Tool import and correction discovery retain independent cursors: tool message ID and correction timestamp/message-ID pair. A bounded tool page arriving later can link a deferred correction without rescanning or inventing a candidate. Repeat pages/reviews must remain idempotent. `correction-scan --after TIMESTAMP --after-id ID` resumes its own stream; inspect returned next_cursor. Dry run does not approve or persist corrections.

Unknown source schemas fail closed. Both pinned native host lifecycles populate and import their actual stock schemas (26 and 30); the current-host nonempty import also passed locally. Merely changing the allowed integer is not validation.

## 2. Inspect and review a correction

The guided queue exposes pending/accepted/rejected state, details and review controls. Session aliases `/afterforge review` and `/fixlab review` show the bounded queue; `review page OFFSET`, `review accept/reject ID NOTE` and `review retract ID REVIEW_ID NOTE` provide explicit review actions. The terminal queue is `hermes afterforge review --offset 0 --limit 10`.

Standalone review is explicit:

```sh
afterforge corrections --status pending
afterforge review-correction CANDIDATE_ID --decision accepted --reviewer operator --note 'Inspected the source facts and remaining unknowns'
afterforge review-correction CANDIDATE_ID --decision rejected --reviewer operator --note 'Evidence does not support this pairing'
afterforge review-correction CANDIDATE_ID --decision retracted --retracts REVIEW_ID --reviewer operator --note 'Retract this review without erasing history'
```

Agents must declare `--reviewer agent`, never impersonate operator/human-declared authority. A surface that does not expose reviewer kind must not be used to manufacture a human review; final native reviewer-kind acceptance is a release gate. Roles, chronology and review flags are observations/declarations, not authenticated human identity or causal ground truth. Annotation of expected behavior is separate from candidate review and code authorization.

## 3. Create a concrete draft or register an existing file

`afterforge demo` creates a labeled synthetic case, miniature faulty/corrected Git subject and an **unapproved** draft. It does not read personal history or call inference. Use a private `--home`, then serve and open `/guided` to inspect it.

For your own deterministic callable, the guided form requests repository, exact faulty/corrected revisions, Python module/function, expected behavior, intended failure and explicit JSON examples (`args` plus `expected`). The equivalent `afterforge draft-regression --file REQUEST.json` accepts those named fields plus case_id and derived/synthetic provenance. It generates a real pytest assertion and separately frozen examples.json; the returned draft includes source_refs, assertion, input declaration, unknowns and draft_digest. It is a reduction, not historical reconstruction. No transcript command becomes executable code.

By contrast, `recipe --file RECIPE.json --reviewed` and legacy fixlab_build_regression register an existing inspected pytest file. They do not generate a draft; name that operation honestly.

## 4. Authorize and run

Inspect both committed implementations, the exact generated assertion, frozen example bytes, intended failure and dependency completeness. A draft starts with input_contract unknown and execution_authorized false. Only after inspection:

```sh
afterforge authorize-draft DRAFT_ID --approve-digest DRAFT_DIGEST --reviewed --declared-inputs
afterforge run RETURNED_RECIPE_ID
afterforge compare RETURNED_RECIPE_ID
```

The GUI offers the same separate code-review and deterministic-input declarations. The new reviewed recipe is immutable and distinct from its draft. Changed assertion/digest/input cannot inherit approval. Recipe v2 declared-v1 excludes ambient inputs/hidden side effects; unsupported equivalence stays inconclusive. Result v3 checks collected identities and typed/frozen input identity, not just count or custom IDs. Inspect both real results and matched intended failure. See [recipes](recipes-and-bundles.md).

## 5. Retain at a new reviewed commit

```sh
afterforge retained-plan RECIPE_ID --target-revision NEW_COMMIT
# Inspect the returned plan, exact target and unchanged regression first:
afterforge retained-check PLAN_ID --approve-digest PLAN_DIGEST --reviewed
```

Intentional subject-data/config changes can be declared with `--reviewed-data-changes` JSON mapping safe paths to specific rationales; this cannot authorize changing regression input to hide a failure. Native plan syntax uses positional target: `hermes afterforge retained-plan RECIPE_ID NEW_COMMIT`; native retained-check uses the same plan/digest/review arguments.

The plan preserves the original recipe/digest, creates a new explicit target recipe and retains a new committed-archive receipt. Ignored files and live edits are not executed or certified. This differs from the stricter legacy current-check-plan/verify-current path, which requires a clean checkout at its already reviewed corrected commit. Neither route certifies the live environment, external services or model efficacy.

## 6. Export a reviewed reduction, not private history

Use bundle-export with approved selected files and separately sanitized descriptions, bundle-validate, then a fresh-home bundle-import and local review before execution. Bundle v2 carries frozen inputs and checksums; legacy v1 gains no new authority. Review every file before sharing—checksums and pattern scans cannot establish trusted code or absence of arbitrary proprietary content. No raw conversation is included.

The optional fixed reminder is a separate explicit experimental review/activation/rollback flow, not an automatic consequence of retaining a regression or accepting evidence. Read [interventions](interventions.md), [privacy](privacy.md), and the honest [validation ledger](validation.md).
