# Afterforge 0.5.0 validation ledger

Status: **integration candidate; final release gates open**. Current implementation is being integrated by multiple workers. Intermediate local tests do not certify the final source, a generated distribution, installed migration or GitHub CI. No final verified SHA, screenshot or successful final CI pair is invented here.

## Evidence currently available

- Coordinator reported 195 tests passing at an intermediate identity/input/runtime state. That is supplied intermediate evidence, not this worker's final rerun or a release total.
- Documentation/release worker ran `uv run pytest -q tests/test_plugin_release.py packaging`: **18 passed**. These are real local tests of committed-source reproducibility, fork metadata, exact-distribution binding, complete runtime projection, tampering rejection, fail-closed CI logic and documentation links. The CI responses in rejection tests are explicitly synthetic mocks, not actual GitHub results.
- Latest worker local snapshot: **231 passed, 2 deprecation warnings, no skips** with AFL_CHROMIUM set to the available cached executable and AFL_BROWSER_PYTHON set to the clean installed 0.5.0 wheel environment. This includes three consecutive fresh packaged guided servers exercising synthetic demo, authorization, red/green comparison and retained execution at the corrected commit. It does not cover every final portable/later-commit/reminder browser requirement or certify final committed source. An earlier concurrent integration run had a stale branding assertion in tests/test_web.py; it passed after the owning worker's changes, without edits to that file by this worker.
- Full root/native/core/test/script/example/packaging Ruff check and formatting passed (63 files). Wheel and sdist built; both installed CLI aliases worked. Installed-wheel demo generated an unapproved synthetic draft, exact-digest authorization succeeded, and real execution returned faulty=fail, corrected=pass, comparison=pass with two collected assertions and matching input identity.
- actionlint v1.7.7 validated all three workflow files. A temporary index containing the assigned current docs/release changes passed the repository audit: 91 text files, zero excluded artifacts or sensitive-pattern matches. The real index was not changed; this is not the coordinator's final integrated/staged audit.
- docs/privacy.md retained SHA-256 `bde77e91c873461941ef72b603edba6e195eff3977ecab33e8cf5906d5f83c15`; the stock scanner warning allowlist was not broadened. This digest preservation is not a final stock scan of the changed distribution.
- Current official host source was inspected at `939e45c91d751fadd94dcd1b873ac3cb44846213`: loader/slash/terminal registration, post_tool_call structured status/error payload, pre_verify continuation and schema **30**. The prior exact pin `277268d83ff2204de9646f0b1e376e73ac0a5d20` is retained. Inspection is not compatibility certification; see [native-plugin.md](native-plugin.md).
- Earlier dataset/component/browser/install/CI results are historical, retained in CHANGELOG.md and dataset-methodology.md rather than presented as new 0.5.0 results.

## Final release gates

| Gate | Required evidence | Current status |
| --- | --- | --- |
| Full quality/build | Root/native/core/test/script/example/packaging Ruff + formatting; full tests; 0.5.0 wheel/sdist | Local snapshot passed as above; final exact-source CI pending |
| A: history identity | Unrelated reused call IDs separated; lineage/compaction retained; absent/conflicting/repeated observations; explicit legacy reconciliation | Implementation/tests present; final integrated acceptance pending |
| B: input equivalence | Identical external pytest with CASES=[-1]/[1], custom IDs, frozen input/fixture changes; explicit data review; legacy immutable authority | Implementation/tests present; final guided/portable acceptance pending |
| C: capture bounds | Independent 32-session/64-event outcomes, LRU, pending cleanup, races, best-effort truncation | Implementation/tests present; real-host acceptance pending |
| D: native status | Actual registered terminal errors/nonpassing verification nonzero; JSON success separate from data.status | Implementation/tests present; both host dispatch gates pending |
| Shared workflow/scale | Native/browser/CLI explicit source mapping; independent same-time correction cursor; deferred linking; idempotent review; SQL-bounded pages/details | Guided worker integration pending |
| Packaged browser | Three consecutive fresh wheel servers: draft, review, authorize, red/green, portable import, later commit, errors/reminder controls if exposed | Three installed guided runs passed for demo/authorization/comparison/corrected-commit retention; broader final path and real screenshot pending |
| Installed migration | Old aliases/evidence retained, no duplicate hooks; prior approval inert after fingerprint change; owned removal | Final distribution migration pending |
| Locked runtime | Transitive hashed export/resolved manifest, doctor-before-readiness, interrupted upgrade old-runtime retention, serialized teardown | Unit implementation present; final installed interruption/upgrade pending |
| Stock host matrix | Exact GitHub distribution install, unchanged scanner/doctor/manager/tools/hooks/skill, old pin + inspected v2026.9.11 source/schema | Both final matrix runs pending; schema 30 must not be blindly allowed |
| Privacy | Exact staged diff/index, generated distribution and reachable history review; no private paths/raw data | Final coordinator audit pending; scanner alone is insufficient |
| CI certification | Both application and complete native matrix green for exact final source and native-tested distribution artifact | Not run for final source |
| Publication | Stable checksum/CI locator, supported pointer, then coordinator-approved tag/GitHub Release | Not published; no PyPI step |

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

The validation workflow separately runs the three guided browser tests with an explicit installed-wheel interpreter and a real Chromium path, so their environment-dependent skips cannot masquerade as that gate. The older expert browser smoke is retained. Final full portable/later-commit/reminder/error paths must still be exercised by the coordinator, not inferred from narrower passing tests. Read actual completion states/health checks, not arbitrary delays. Keep screenshots limited to synthetic data from the shipped app.

The application is not an OS sandbox, full capture attestation or model-efficacy evaluator. Historical process-derived labels, weak holdout and synthetic reductions cannot support semantic/generalization claims. Final release certification uses [release.md](release.md), not a remembered green candidate.