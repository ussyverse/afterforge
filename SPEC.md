# Afterforge specification — 0.5.1

Turn agent mistakes into lasting regression checks.

## Product contract

A local, single-user Linux/Python 3.11+ workbench for reviewed pytest regression retention. Import bounded Hermes observations without writing to its database; distinguish process facts from symptoms and unknowns; review inferred corrections; inspect a draft or register an existing assertion; explicitly authorize frozen inputs and committed source; run both variants; retain immutable receipts and portable reviewed reductions. Historical success is not fresh verification. This is not autonomous learning.

The standalone entry point is `afterforge --home HOME COMMAND`. `agent-fix-lab` remains an alias. Native entry points are `/afterforge` and `hermes afterforge`; `/fixlab` and `hermes fixlab` remain aliases. Package/import/plugin/tool/data identities are preserved for the migration release. Each command's `--help` and the installed native help are authoritative for available operations. See [migration](docs/migration.md).

## Evidence and execution invariants

- Source documents are immutable. The v4 history parser scopes call identity by explicit source and lineage, not a globally reused call ID. Compaction observations remain traceable; conflicting or missing-call observations cannot silently merge unrelated incidents.
- Legacy records remain readable. Reconciliation links only an exactly retained source observation under explicit review; it does not transfer annotation, split, correction or recurrence authority. Missing original evidence stays unknown.
- Inferred correction candidates are pending hypotheses. Reviewer kind is declared, not authenticated; an agent review is not a human review. Reviews/retractions append records instead of rewriting evidence.
- Historical commands never execute. Draft creation, existing-file registration, execution authorization, comparison and retained-check authorization are separate operations.
- Recipe v2 `declared-v1` is an explicit review of deterministic regression inputs, not automatic dependency discovery. Frozen UTF-8 fixtures are separate from subject code. Intentional subject data changes require path-specific review and cannot excuse changed regression inputs.
- Result v3 comparisons require compatible recipe/runtime/assertion identity, collected test identities and frozen/typed parameter-input identity, plus the intended faulty assertion failure and corrected pass. Same test count/hash alone is insufficient; custom IDs cannot conceal different values.
- Missing equivalence evidence, skips, zero tests, collection/setup errors, timeouts, truncation and incompatible evidence cannot verify a fix. Old recipes/results do not acquire new equivalence authority on load or rerun.
- A later-commit retained check requires a new explicitly reviewed binding/receipt; it must preserve the historical recipe and frozen regression. Execution certifies the committed archive only, not live edits or the surrounding environment.
- Portable bundle v2 transfers selected reviewed code and frozen inputs, not transcripts or execution authority. Imports require fresh local review and execution. Legacy v1 stays readable without new claims.
- Passive capture is bounded independently to 32 sessions and 64 outcomes/session, best-effort and nonauthoritative. Missing host process evidence is inconclusive. Tool-envelope success is separate from `data.status`; native command errors/nonpassing verification must exit nonzero.

## Runtime and release invariants

Managed setup uses the committed uv lock, transitive hashed export and resolved manifest in a private staged generation. Setup/update/removal are serialized; readiness is published atomically only after doctor. Failed upgrades retain the previously usable runtime. No application dependencies are installed into Hermes's environment.

Candidate distribution and supported release are separate. The supported pointer/locator may advance only after both application CI and the complete native host matrix succeed for the exact final source and generated distribution. Locator records version, source SHA, distribution SHA, file checksums and CI links. No release SHA is verified by this document. [Release protocol](docs/release.md) and [validation gates](docs/validation.md) define the evidence required.

## Optional experiment and exclusions

The fixed project-scoped verification reminder is opt-in and experimental. Approval binds message, scope, implementation digest and optional case provenance; state transitions use generations and conflict-safe rollback. Changed implementation requires reapproval, with symlink abstention. Synthetic hook receipts are not evidence of model efficacy. No arbitrary prompt, memory, skill or permission mutation is permitted.

Not an OS sandbox, multi-user service, semantic truth oracle, authenticated-human identity provider, historical model replay engine, or arbitrary dependency installer. The importer accepts only verified schema versions 26 and 30 with required-column checks and rejects unknown future versions. Both pinned stock-host CI lifecycles populate their actual native schemas rather than replace them with a reduced schema-26 fixture. Migration baseline certification and supported publication remain gated as recorded in the handoff.