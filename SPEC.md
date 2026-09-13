# Agent Fix Lab specification — 0.1

Local-first regression workbench that turns Hermes failures and corrections into reproducible, evidence-backed test cases.

## Acceptance contract

A single-user Linux/Python 3.11+ installation imports bounded Hermes schema-26 observations without writing to Hermes. An operator can inspect facts and unknowns, annotate expected behavior, review a conservative correction candidate, select compatible configuration evidence, run a reviewed pytest assertion against two committed implementations, inspect both subprocess results, and export either a summary or reviewed portable bundle.

The CLI contract is `agent-fix-lab --home HOME COMMAND`; `--help` on each command is authoritative. Commands: doctor, import-hermes, list, show, annotate, baseline, recipe, run, compare, report, export, serve, correction-scan, corrections, review-correction, bundle-export, bundle-validate, bundle-import.

## Invariants

- Source documents are immutable. Re-import does not create recurrence or overwrite annotations.
- Exit status is independent of symptom recognition. Missing process evidence is inconclusive.
- Pending correction candidates are not user-authored ground truth. Review records declare their authority.
- Compaction/delegation and exact duplicates retain source identity; import does not certify independent incidents.
- Only explicitly reviewed pytest recipes execute. No shell-command or transcript-execution endpoint exists.
- Same assertion bytes, interpreter/dependencies and test count are required across two distinct revisions. Faulty assertion failures must match the intended reason.
- Collection errors, skips, zero tests, timeouts, truncation and incompatibility cannot verify a fix.
- Portable imports never inherit execution authorization or fresh-result authority from a bundle.
- No automatic policy, prompt, memory or permission mutation.

## Delivery gates

Unit/adapter/integration/privacy tests, three fresh-server browser runs, wheel/sdist build, clean-wheel CLI/web checks, portable red/green round trip, reversible installed Hermes skill, exact-index audit, clean-checkout verification, private remote push and green Actions. See validation.md for measured results, not implied certification.

## Scoped exclusions

Not a model reasoning replay engine, OS sandbox, multi-user service, semantic truth oracle, authenticated-human identity provider or arbitrary dependency installer. Legacy Hermes logs and schemas other than 26 require a future explicit adapter. Historical source reconstruction is unavailable for the three included reductions.
