# Afterforge 0.5.0 validation ledger

Status: **release candidate; existing-fixture migration certification blocked**. One exclusive executor owns the integrated release. The original migration database differed from its privately recorded checksum before any upgrade write; its policy checksum matched. That fixture and baseline are preserved, not silently replaced. Supported promotion/tag/release remain withheld pending reconciliation of this external baseline evidence.

## Evidence currently available

- Source `72db27e5a887379fcb4562d48f0c1cd610df9942`: [application CI 34796312216](https://github.com/ussyverse/afterforge/actions/runs/34796312216) and [native CI 34796312234](https://github.com/ussyverse/afterforge/actions/runs/34796312234) both completed successfully. Native distribution artifact: `2a20ceef8efef39bc5ebe084983260aa662884d0`. These links certify that candidate, not an untested follow-up commit or supported release.
- Local full suite: **232 passed, 2 dependency deprecation warnings, no skips**, including packaging/test_release_gate.py. Full Ruff check/format passed over 85 Python files. CI API rejection fixtures are labeled synthetic mocks, not substituted for the real Actions results above.
- Three fresh installed-wheel guided flows cover synthetic scan, correction rationale rejection/recovery, operator acceptance, linked-case draft creation, frozen-input authorization, red/green, corrected-target retention, undeclared later-data rejection, explicit later-commit review, and archived execution despite failing live edits. Real screenshots are retained privately because the displayed fixture paths are local.
- Three separate fresh packaged expert/intervention browser flows passed with zero console errors and zero failed workflow requests; security rejections were verified separately. A portable installed-CLI round trip returned faulty=fail, corrected=pass, comparison=pass. No inference was used.
- Wheel/sdist builds and the exact staged privacy audit passed: 101 text files, zero excluded artifacts or sensitive-pattern matches. docs/privacy.md retains SHA-256 `bde77e91c873461941ef72b603edba6e195eff3977ecab33e8cf5906d5f83c15`. The current stock scanner verified all 41 candidate files with CAUTION, only the original reviewed high finding, no widened allowlist.
- Both exact stock pins passed native GitHub CI: `277268d83ff2204de9646f0b1e376e73ac0a5d20` (schema 26) and `939e45c91d751fadd94dcd1b873ac3cb44846213` (schema 30). The lifecycle preserves each actual stock schema and inserts synthetic rows instead of copying a reduced database over it.
- The exact candidate artifact was also installed from GitHub into a fresh isolated current-host profile locally. Managed setup/doctor/old alias, nonempty schema-30 import, 8 tools, hooks, bundled skill, red/green, reminder activation and rollback passed. Real stock setup interrupted while waiting for its installation lock preserved the old marker/runtime; retry published a ready new generation. Unit tests separately exercise interruption immediately before and after atomic publication with real uv installs.
- Earlier dataset/component/browser/install/CI results are historical, retained in CHANGELOG.md and dataset-methodology.md rather than presented as new 0.5.0 results.

## Final release gates

| Gate | Required evidence | Current status |
| --- | --- | --- |
| Quality/contracts | Full lint/format/tests/build; history identity, equivalence, capture bounds, native status, shared pagination | Passed for recorded candidate; repeat after changes |
| Packaged workflows | Three fresh guided and expert/intervention flows, portable round trip, later commit/error recovery, real screenshot | Passed as above; screenshots private |
| Installed migration | Exact original baseline, old IDs/bytes/aliases, reminder reapproval, rollback/removal retention | BLOCKED: reconcile pre-upgrade baseline discrepancy before modifying the original fixture |
| Locked runtime | Hashed lock/manifest, doctor readiness, interruption and serialized cleanup | Real uv tests and installed interruption/retry passed |
| Stock host matrix | Exact GitHub artifact, stock scans/doctor/tools/hooks/skill, both native schemas | Both pins passed for recorded candidate |
| Privacy | Exact index and generated projection audit plus manual review | Candidate audits passed; repeat for final follow-up |
| CI/publication | Both exact-source CI runs, exact artifact installation, then supported locator/tag/release | Candidate CI/install passed; stable intentionally withheld for migration gate |

## Reproduction commands

```sh
uv sync --locked
uv run ruff check __init__.py hermes_plugin src tests scripts examples packaging
uv run ruff format --check __init__.py hermes_plugin src tests scripts examples packaging
uv run pytest -q tests packaging
uv build
uv venv "$WHEEL_ENV"
uv pip install --python "$WHEEL_ENV/bin/python" dist/agent_fix_lab-0.5.0-py3-none-any.whl
"$WHEEL_ENV/bin/afterforge" --help
"$WHEEL_ENV/bin/agent-fix-lab" --help
uv run python scripts/browser_fixture.py "$SYNTHETIC_FIXTURE"
uv run python scripts/browser_smoke.py --python "$WHEEL_ENV/bin/python" --home "$SYNTHETIC_FIXTURE/lab" --recipe-file "$SYNTHETIC_FIXTURE/recipe.json" --query Unfamiliar --repeat 3 --interventions
uv run python scripts/bundle_smoke.py --python "$WHEEL_ENV/bin/python" --home "$SYNTHETIC_FIXTURE/lab" --recipe-file "$SYNTHETIC_FIXTURE/recipe.json" --output-directory "$NEW_ROUNDTRIP" --file implementation.py
uv run python scripts/audit_index.py
```

Set variables to private paths outside the checkout and use a new synthetic fixture directory. `AFL_CHROMIUM` selects an available cached browser executable; no installation is needed when that executable is already available. CI installs browser OS dependencies on its fresh runner. Use a writable UV_CACHE_DIR if the default is read-only; the worker's initial default-cache command failed with read-only filesystem and was rerun successfully with an isolated writable cache. No dependency version was changed to work around it.

The validation workflow separately runs the three guided browser tests with an explicit installed-wheel interpreter and a real Chromium path, so their environment-dependent skips cannot masquerade as that gate. The expert/intervention browser smoke and portable round trip remain separate required checks. Read actual completion states/health checks, not arbitrary delays. Keep screenshots limited to synthetic data from the shipped app.

The application is not an OS sandbox, full capture attestation or model-efficacy evaluator. Historical process-derived labels, weak holdout and synthetic reductions cannot support semantic/generalization claims. Final release certification uses [release.md](release.md), not a remembered green candidate.