# Validation record

## Measured development and continuation results

The first continuation code commit with bundles/security, d495b5a, passed 64 local tests. GitHub validation run https://github.com/ussyverse/agent-fix-lab/actions/runs/34781817583 completed successfully for that commit. Final-tree results are recorded below after the final validation pass.

Versions used: uv 0.11.2; isolated Python 3.11.15; FastAPI 0.141.1, Pydantic 2.13.5, Uvicorn 0.52.4, pytest 9.1.1, Ruff 0.16.7, Playwright 1.62.0. Full transitive pins are in uv.lock. Two Starlette/httpx/AnyIO deprecation warnings are present; they are not test failures. Upstream component suites: Triage 160, Petrichor 140, correction-aware-learning 76, all passed at the exact revisions in sources.md.

## Commands (private paths represented by shell variables)

```sh
uv sync --locked
uv run ruff check src tests scripts examples
uv run ruff format --check src tests scripts examples
uv run pytest -q
uv build
uv venv "$WHEEL_ENV"
uv pip install --python "$WHEEL_ENV/bin/python" dist/agent_fix_lab-0.1.0-py3-none-any.whl
"$WHEEL_ENV/bin/agent-fix-lab" --help
uv run python scripts/browser_smoke.py --python "$WHEEL_ENV/bin/python" --home "$PRIVATE_LAB" --recipe-file "$PRIVATE_REVIEWED_RECIPE" --repeat 3
uv run python scripts/bundle_smoke.py --python "$WHEEL_ENV/bin/python" --home "$PRIVATE_LAB" --recipe-file "$PRIVATE_REVIEWED_RECIPE" --output-directory "$PRIVATE_NEW_ROUNDTRIP" --file regression_subject.py
uv run python scripts/audit_index.py
```

For an existing system Chromium, set AFL_CHROMIUM to its executable; otherwise `uv run playwright install chromium`. CI installs browser OS dependencies and uses synthetic fixtures. Set WHEEL_ENV/PRIVATE_LAB and other variables outside the repository; never commit their local values.

The wheel browser workflow passed three consecutive fresh-server real-case runs, then three more with explicit reversed-response and synthetic XSS probes. Every run saved annotation/configuration, reviewed a recipe, executed faulty/corrected processes, displayed a passing comparison, rejected unreviewed creation and tokenless execution, and reported zero console errors and zero failed workflow requests. Intentional rejected probes are counted separately. Readiness uses a health check and UI completion attributes; no arbitrary browser sleeps.

The actual grouped-search reduced regression exported selected reviewed code, validated checksums, imported into a new private data home through the wheel CLI, and returned faulty=fail/corrected=pass/comparison=pass. Provenance remains derived; original historical revisions are unknown.

## Coverage and interpretation

Tests cover immutable identities, version rejection, malformed/partial records, WAL backup, bounded imports, duplicate/compacted observations, delegation, cohorts, annotations/candidates/retractions, selected configuration, direct adapter contracts, reviewed recipes, assertion changes/weakening, collection/empty/skip/timeouts, revision/argument rejection, environment/workspace separation, archive traversal/links, output limits, safe summaries, bundle checksums/unsafe paths, CSRF/body/CSP checks and installer ownership/removal. Browser tests cover actual wheel assets and asynchronous stale responses.

Five dogfood tests initially failed and passed after fixes to wrapped results, actual delegation markers, pagination, compacted provenance and retraction restoration. The browser failures came from both stale test assumptions and an application overwrite race. A missing favicon also generated a console 404 and was fixed with an explicit response.

Frozen real dataset: 53 cases, 20 failures/33 controls; 52 development and one held-out control, no held-out failures. 53/53 agreement is with process-derived labels, not independent semantic accuracy/generalization. Three synthetic reductions derived from real history achieved meaningful red/green checks. Two conservative correction candidates remain pending. See dataset-methodology.md for grouping audit and exclusions.

## Final gate

Completed against code commit c1d980dd517da58b7806c83bff7d1b5b42a12dde: 68 local tests passed; a fresh authenticated GitHub clone independently passed all 68 tests, Ruff checking/formatting, wheel and sdist builds, isolated-wheel installation, three consecutive fresh-server browser workflows and a synthetic portable bundle round trip through the installed CLI. All browser runs reported zero console errors and failed workflow requests, two expected security rejections and comparison=pass. The installed Hermes skill loader again returned success=true and readiness_status=available. The installed wrapper doctor reached the real package and profile. Installation/removal/ownership checks are included in the suite.

The exact-index audit covered 52 text files with zero excluded artifacts or sensitive-pattern matches. All four existing committed trees also passed. Private history and detailed evidence stayed outside Git. The clean-clone commands follow the sequence above with synthetic fixtures created by scripts/browser_fixture.py and query Unfamiliar. Actual source data was not copied into the clean checkout. Final documentation-only commits do not change the validated implementation; their required Actions run is checked separately before delivery.
