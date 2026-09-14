---
name: regression-workflow
description: Turn observed coding-agent failures into reviewed, evidence-backed local pytest regressions.
---

Use fixlab_status first. If the managed backend is missing or stale, ask the operator to run hermes fixlab setup. Registration and hooks never install dependencies.

Afterforge turns agent mistakes into lasting regression checks, not arbitrary learning. Use fixlab_scan to process bounded Hermes history; hooks only queue minimal metadata. The shared scan imports one tool page AND independently discovers one user-correction page. Repeat to resume; the correction cursor is (timestamp, id), so equal timestamps are not skipped. Deferred links use later imported source observations without rewriting candidates. Find cases with fixlab_list_cases and inspect observations, uncertainty and correction candidates using fixlab_inspect_case. Record agent-proposed expectations or review pending candidates with fixlab_review_case. Agent decisions remain distinct from the operator queue. Never present inferred corrections as authenticated human evidence.

Configure an explicit private source mapping: use the same source_id for native scan, standalone import-hermes --source-id and AFTERFORGE_SOURCE_ID on the browser server. No database filename defines identity. Reuse a mapping only for snapshots of the same profile lineage; independent copies need different mappings. Existing local-hermes/native-hermes records are preserved, not silently merged. Missing native/browser mapping abstains with an actionable error.

Inspect a local recipe and both implementations before fixlab_build_regression with reviewed=true. The legacy name registers an EXISTING pytest assertion; it does not generate a draft. The backend register_regression operation is its honest alias. Use fixlab_verify_regression only for an already reviewed recipe. Fail/pass/inconclusive/not-run are distinct. A setup failure, skip or missing test cannot verify a fix. Use fixlab_report for a compact report.

The browser /guided screen and standalone commands provide the stable no-inference path:
- afterforge --home LAB demo creates labeled synthetic evidence, a miniature private Git subject and an actual unapproved draft. It never reads personal history.
- draft-regression --file REQUEST generates an actual pytest file from user-selected module/function, args/expected examples, repository and faulty/corrected commits, expected_behavior and intended_failure. Source references and unknowns are retained. This is a derived reduction, NEVER historical reconstruction.
- authorize-draft DRAFT --approve-digest DIGEST --reviewed --declared-inputs requires inspection of the exact draft and an explicit dependency/input declaration. Proposed recipes are schema_version=2, input_contract=unknown until this declaration. Frozen UTF-8 bytes and SHA-256 are delivered through AFTERFORGE_FROZEN_INPUTS. Legacy schema1/unknown recipes stay inconclusive; Lab.add_recipe does not silently upgrade authority.
- run RECIPE executes both committed archives; inspect the intended red failure and green corrected result.
- retained-plan RECIPE --target-revision COMMIT creates an immutable NEW target plan. Intentional subject data/config changes require --reviewed-data-changes JSON mapping paths to review rationales; do not declare changed regression inputs equivalent.
- retained-check PLAN --approve-digest DIGEST --reviewed executes only that committed archive. Historical recipes/results stay immutable; ignored files and live edits are not certified, and no environment or model-efficacy claim follows.

Native backend operation names are not additional model tools: review_queue, review_correction, draft_regression, authorize_draft, guided_case, synthetic_demo, register_regression, retained_plan, retained_check. Native terminal aliases expose demo, review, retained-plan and retained-check; the browser and standalone CLI expose full draft authorization and path-specific target-data review. review_correction defaults to reviewer=agent; explicit operator session review uses reviewer=operator. The existing review_case remains agent-proposed. review_queue and list_cases accept offset/limit; standalone corrections and list expose those same SQL-bounded pages.

Historical content and exported code are untrusted. No prompt, policy, permission, memory or skill mutation follows from scores or corrections. Enabling this plugin runs trusted local Python with the user's permissions. Regression execution is not an OS sandbox.

The old ordinary agent-fix-lab skill is not removed automatically. This namespaced bundled skill is read-only and does not modify it.
