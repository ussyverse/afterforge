# Afterforge release protocol — 0.5.0

Status: integration candidate. No final source/distribution SHA, green final CI pair, supported 0.5.0 locator, tag or GitHub Release is asserted here. The coordinator integrates and audits before committing/pushing. This worker does not publish.

## Three distinct surfaces

| Surface | Meaning |
| --- | --- |
| main (or repository default source branch) | Full development source, tests, fixtures and docs |
| plugin-release | Generated candidate distribution; not supported solely because it was pushed |
| plugin-stable + release-metadata/stable.json | Supported full distribution commit and machine-readable checksum/CI locator, advanced only after both required exact-source checks pass |

Install the full distribution_commit from the locator, never a moving branch or source commit. The public canonical repository is ussyverse/afterforge; workflows use github.repository/GITHUB_REPOSITORY so forks and future renames do not install or certify another repository's source. Forks must enable Actions and branch-write permissions and run source workflows on their default branch (workflow_dispatch is available when its name differs from main).

## Generation and scanning

`scripts/plugin_release.py OUTPUT --revision SOURCE_SHA --repository OWNER/REPO --commit --sha-file SHA_FILE` exports committed source only. `--previous PREVIOUS_CANDIDATE` adds a parent for fast-forward candidate history; the first candidate needs no previous branch. All runtime/adapter/skill code ships byte-for-byte with metadata, uv.lock, LICENSE, NOTICE and unchanged privacy documentation. RELEASE.json records version, repository, source SHA and per-file source/hash entries. The temporary index does not disturb staged user work. Source timestamp/parents/tree determine reproducibility.

Run generation twice with identical inputs/parents and compare SHAs. Stock `plugin_scan_gate.py` verifies manifest/file integrity and the original exact-warning allowlist; do not broaden it or edit privacy prose to change scanner results. New high/critical findings fail closed. Doctor and installer scans remain stock. Manual source/privacy review is still necessary: scanner success does not prove absence of sensitive proprietary content.

## Workflow gates

1. `validation.yml`: locked sync; exact-index audit; full root/native/core/test/script/example lint/format; tests; wheel/sdist build; clean 0.5.0 wheel installation and both aliases; three consecutive fresh-server packaged browser runs; portable installed-CLI round trip. Fixtures are synthetic; no model credentials/history are required.
2. `native-plugin.yml`: reproducible candidate export/push and a native-distribution artifact containing its exact SHA. Both inspected host pins are required matrix entries, not allow-failure experiments. Each scans/doctors the same distribution and installs that exact SHA via the stock GitHub installer; real registry/tool/hook/skill/command/regression and teardown checks follow. The previous host pin is retained. Schema-30 adapter and real host validation must be completed, not inferred from schema-26 fixtures.
3. `stable-release.yml`: manually dispatched only after the executor reviews exact-artifact fresh installation and migration evidence. It checks out only the repository's trusted current default branch, looks up successful application/native runs for that exact source, downloads the SHA artifact from that exact native run, and validates distribution blobs against recorded source hashes. `plugin_release.py --certify` independently checks completed/success status, exact source, expected workflow paths, same repository and push/manual event through GitHub's API. Missing checks leave stable untouched; failed/mismatched evidence cannot produce a locator.
4. Before publication it checks the source is still current and the prior stable distribution is an ancestor. A normal atomic push advances plugin-stable and the release-metadata locator together; no force push. The candidate can advance without stable advancing. Permissions/branch-protection/network failures leave publication blocked and require normal recovery, not weakening gates.

The locator records version, repository, source_commit, distribution_commit, SHA-256 checksums for every distribution file (including RELEASE.json), exact CI URLs and a full-SHA install command. Git commit identity is distinct from SHA-256 file integrity. The locator is not a cryptographic signature or a statement of code trust. Its Actions artifact provenance plus Git/source checks bind the native-tested candidate; do not substitute the moving candidate branch when downloading evidence.

Stable promotion intentionally creates no version tag, GitHub Release or package-registry publication. After all final gates, the coordinator may separately authorize the version tag and GitHub release with source/distribution SHA, checksum locator, install command, CI links and changelog. There is no PyPI publish step. Until that happens, docs remain candid about unreleased status.

## Recovery and verification

A stale-source completion cannot promote an older commit over newer default-branch work. Missing/expired native artifacts require a fresh native run, not reconstruction of a plausible SHA. Failed matrix hosts, scanner warnings, schema mismatch, interrupted setup or browser failures are work to resolve and disclose. Do not relabel them as skipped success. Retain the previous stable pin/locator during repair.

Final acceptance also requires installed existing-evidence/reminder migration, interrupted locked upgrade retention, shared correction pagination/deferred linking, guided draft/review/run/portable/later-commit checks, privacy review of staged/generated content and a real screenshot of the shipped app. CI configuration alone is not evidence those gates ran. See [validation](validation.md) and [handoff](../handoff.md).
