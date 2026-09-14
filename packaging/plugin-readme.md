# Afterforge 0.5.0 — native Hermes distribution

Turn agent mistakes into lasting regression checks.

This generated tree contains the complete application, web assets, thin native adapter, bundled workflow skill, legal/security documentation and committed dependency lock. The public development repository is https://github.com/ussyverse/afterforge. Package/import/plugin/tool/data identities remain `agent-fix-lab`, `agent_fix_lab` and `fixlab_*` for compatibility; the product name is Afterforge.

RELEASE.json records the exact source commit, version, repository and per-file SHA-256 hashes. A generated candidate is not a supported release. Consult `https://raw.githubusercontent.com/ussyverse/afterforge/release-metadata/stable.json` for the certified version, source/distribution commits, checksums and successful application/native CI links. On forks substitute the fork's repository. If the locator is missing or names another version, this tree is not thereby certified. Install the locator's full distribution commit, not a development SHA or moving candidate branch.

```sh
hermes plugins install ussyverse/afterforge --ref FULL_DISTRIBUTION_COMMIT --enable
hermes afterforge setup
hermes afterforge doctor
export AFTERFORGE_SOURCE_ID=local-hermes
hermes afterforge scan
hermes afterforge serve
```

Stock scanning remains enabled: review caution findings; dangerous findings block. No scanner patch or widened warning exception is part of installation. Enabling this plugin executes trusted local Python with your OS-user permissions.

Choose an explicit private source identity for this logical profile store. Launch Hermes with AFTERFORGE_SOURCE_ID for session commands and use the same standalone --source-id. Do not reuse it for independent histories just because their database filenames match. Open `/guided` on the loopback server for the guided case screen; a synthetic demo needs no private history or inference.

Setup uses uv's committed lock in a private staged generation, exports transitive hashed requirements, records resolved package versions and publishes readiness only after doctor. Failed upgrades retain the previously usable runtime. Hermes's environment is never modified and no hidden application backend is downloaded. Inspect the three full-SHA Git dependencies declared in pyproject.toml. Initial dependency installation needs network.

## Commands and evidence

Standalone: `afterforge` and legacy `agent-fix-lab`. Native: `hermes afterforge` and legacy `hermes fixlab`. Session commands: `/afterforge` and legacy `/fixlab`. Consult installed help for current review/draft/retained-check operations. Bundled skill remains `agent-fix-lab:regression-workflow`; do not install a duplicate under the new brand.

Stable tools: fixlab_status, fixlab_scan, fixlab_list_cases, fixlab_inspect_case, fixlab_review_case, fixlab_build_regression, fixlab_verify_regression, fixlab_report. Existing-file registration is not draft generation. Model-tool envelope success is distinct from verification `data.status`; missing/inconclusive results cannot certify a fix.

Read docs/privacy.md before importing history, authorizing code or exporting selected evidence. Historical commands never execute automatically. Recipe v2 declared-v1 binds reviewed deterministic inputs; result v3 checks collection/typed-input identity as well as assertion/runtime identity. Legacy evidence remains immutable. Bundle v2 requires new local review and execution after import. Checksums are not code signatures. The committed archive is tested, not live edits or model behavior.

Source logs and evidence remain in the active profile's private plugin-data, not this code tree. Hooks retain bounded identifiers/process metadata, not raw arguments/results. Inferred corrections are pending hypotheses and agent reviewers are not authenticated humans. No arbitrary prompt, memory or skill mutation occurs.

The optional fixed project-scoped reminder is experimental, inactive until digest-bound explicit approval. Implementation changes require reapproval; generation-safe rollback preserves prior evidence. Deterministic intervention receipts and reminder delivery do not establish behavioral efficacy. Read docs/interventions.md.

Reviewed pytest runs with user permissions, NOT in an operating-system sandbox. Use separate VM/container/account isolation for hostile code. The browser is loopback-only, not a multi-user hosted service.

## Upgrade and removal

Inspect a newly certified full SHA and reinstall with the stock replacement option, then rerun setup. A pinned ordinary update does not silently advance. Keep the plugin ID `agent-fix-lab`; evidence directories and environment fallback names are unchanged.

Run `hermes afterforge uninstall-runtime --confirm` before removing source if runtime cleanup is desired. Then `hermes plugins disable agent-fix-lab` and `hermes plugins remove agent-fix-lab`. Owned environment removal preserves evidence. Older standalone installations and editable skills are retained rather than silently merged/deleted.

The final 0.5.0 installed host/migration/browser/CI gates must be read at the recorded source's docs/validation.md. The current inspected host is v2026.9.11 at schema 30; the prior schema-26 host pin is retained. Inspection alone is not support certification.