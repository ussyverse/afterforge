# Afterforge

**Turn agent mistakes into lasting regression checks.**

Afterforge is a local-first workbench for Python projects: inspect a failed agent tool run, review the correction, freeze a meaningful pytest regression, and retain evidence from real executions against committed code. A passing old run is not verification of today's code. Unknowns, failed checks and unreviewed proposals stay visible.

Version **0.5.0** provides a bounded deterministic regression-retention workflow. Packaged browser, portable bundle, both pinned stock-host CI and existing-fixture migration gates have passed for the recorded candidate. Real packaged-browser screenshots are retained privately, not replaced by mock images. The [stable locator](https://raw.githubusercontent.com/ussyverse/afterforge/release-metadata/stable.json) identifies the supported version and exact source/distribution checksums and CI; an unlisted candidate is not certified merely by its version. See [validation](docs/validation.md).

This is bounded, reviewed regression retention—not autonomous learning, a model replay engine or an OS sandbox. An optional fixed verification reminder is [experimental and opt-in](docs/interventions.md); code receipts do not measure model efficacy.

## Install into Hermes

Requires Linux, Git, Python 3.11+ and [uv](https://docs.astral.sh/uv/). The public repository is [ussyverse/afterforge](https://github.com/ussyverse/afterforge), renamed in place without changing repository identity or visibility. No GitHub credentials are needed merely to read the public source. Dependency installation needs network initially; normal local analysis does not need model API keys or personal logs.

Once a supported 0.5.0 release is certified, its stable locator will be at:

`https://raw.githubusercontent.com/ussyverse/afterforge/release-metadata/stable.json`

The locator must name version 0.5.0, the full source and distribution commits, SHA-256 file checksums, and successful application/native CI links for that exact source. An absent locator or one for an older version is **not** a verified 0.5.0 installation. `plugin-release` is only a candidate branch. Do not install a moving branch or development SHA as a supported release.

After inspecting the locator, distribution and stock scanner warnings, substitute its full `distribution_commit`:

```sh
hermes plugins install ussyverse/afterforge --ref FULL_DISTRIBUTION_COMMIT --enable
hermes afterforge setup
hermes afterforge doctor
export AFTERFORGE_SOURCE_ID=local-hermes
hermes afterforge scan
hermes afterforge serve
```

Use `/afterforge status`, `/afterforge scan` and `/afterforge review` in a Hermes session. Launch Hermes with the same explicit AFTERFORGE_SOURCE_ID used by the browser/native scans and standalone `--source-id`; choose a different value for an independent store. See the guided queue/draft/retained-check [workflow](docs/workflow.md). `hermes fixlab`, `/fixlab` and the standalone `agent-fix-lab` command remain aliases for this migration release. The plugin ID remains `agent-fix-lab`: do not install a second plugin under the new brand.

Setup uses the committed uv lock and a private staged environment, records transitive hashes/resolved packages, and switches readiness only after doctor. It never installs dependencies into Hermes's environment. Failed upgrades retain the last working runtime. See [native installation/host matrix](docs/native-plugin.md), [release protocol](docs/release.md) and [migration](docs/migration.md).

## Five-minute synthetic demo from source

This development demo does not install into Hermes, read personal history, call a model or claim reconstruction of a real incident. The first dependency download may take longer than five minutes.

```sh
git clone https://github.com/ussyverse/afterforge.git
cd afterforge
uv sync --locked
uv run afterforge --help
DEMO_ROOT=$(mktemp -d)
uv run afterforge --home "$DEMO_ROOT/lab" demo
uv run afterforge --home "$DEMO_ROOT/lab" serve
```

Open http://127.0.0.1:8765/guided and select the synthetic case. Inspect the generated draft, both miniature source revisions, assertion, frozen examples and unknowns. Declare code review and deterministic input completeness only after inspection; authorize the exact draft, then run faulty/corrected archives. The source workbench remains at `/` for expert JSON/configuration evidence. Three consecutive fresh packaged guided servers exercised scan, correction review, draft authorization, red/green, retained checks and a later reviewed commit despite failing live edits. Separate packaged expert/intervention workflows and a portable installed-CLI round trip also passed; see the validation ledger.

In a second shell, using the same `DEMO_ROOT`, review and execute the fixture:

```sh
# Substitute the demo's draft ID and digest only after inspecting it:
uv run afterforge --home "$DEMO_ROOT/lab" authorize-draft DRAFT_ID --approve-digest DRAFT_DIGEST --reviewed --declared-inputs
# Substitute the returned reviewed recipe ID, not the case or draft ID:
uv run afterforge --home "$DEMO_ROOT/lab" run RECIPE_ID
uv run afterforge --home "$DEMO_ROOT/lab" compare RECIPE_ID
```

Expected acceptance is faulty assertion failure for the reviewed reason, corrected pass, and compatible regression inputs—not just two exit codes. The commands produce actual local receipts. See [recipes and portable bundles](docs/recipes-and-bundles.md) for input declarations, limits and fresh-import review.

## Use your own evidence

Keep the data home outside the checkout. `HERMES_HOME` is already the active profile's resolved home: do not append `profiles/default`. Choose an explicit stable private source ID for that history store; reuse it across its snapshots, not across independent stores merely named `state.db`.

```sh
export AGENT_FIX_LAB_HOME="$HOME/.local/share/agent-fix-lab"
uv run afterforge import-hermes --source "$HERMES_HOME/state.db" --source-id local-hermes --limit 100 --dry-run
uv run afterforge import-hermes --source "$HERMES_HOME/state.db" --source-id local-hermes --limit 100
uv run afterforge list --status fail
uv run afterforge show CASE_ID
uv run afterforge annotate CASE_ID --text 'Proposed correction, not a historical quote' --expected 'The assertion that must hold'
```

Imports are bounded and resumable with the returned `next_after_id` passed as `--after-id`. `--after` is inclusive Unix seconds; `--before` is exclusive. `--cohort dogfood` separates build activity from a frozen historical cohort. Import is WAL-consistent and read-only; unsupported source schemas are rejected, not migrated. The newer inspected host has schema 30, not 26; final support requires its adapter and real-host gates.

Correction discovery and review are distinct from annotation. Use `correction-scan --help`, `corrections --status pending` and `review-correction --help`; declare agent reviews as `--reviewer agent`, never as a human review. Role/chronology are observations, not authenticated user intent. Native/browser/CLI profile-source mapping and resumable correction linking are being integrated and must pass the shared-workflow gate before release.

## Freeze, verify, retain

Recipe v2 `declared-v1` review binds deterministic regression input dependencies. Freeze external UTF-8 fixture bytes separately from subject revisions; typed pytest parameter values and collection identities must agree. Same test count or custom test IDs cannot conceal changed values. Intentional subject-data changes need path-specific rationale; they must not change the regression itself. Unsupported ambient inputs mean equivalence is inconclusive. Legacy recipes and results remain immutable and do not gain new claims on rerun.

Tests execute from committed archives, not live worktree edits. Review the code and use separate OS/container isolation for hostile code. No transcript command is replayed. Portable bundle v2 contains only explicitly selected reviewed source, assertions, frozen inputs, sanitized metadata and checksums; it is not a transcript export or a code signature.

For a later commit, use `afterforge retained-plan RECIPE_ID --target-revision NEW_COMMIT`, inspect the returned plan and unchanged regression, then `afterforge retained-check PLAN_ID --approve-digest PLAN_DIGEST --reviewed`. This creates a new binding and receipt; do not edit the historical recipe or reuse its approval. Ignored/live files are not executed or certified. The legacy `current-check-plan` / `verify-current` path requires a clean checkout at its already reviewed corrected commit. Final later-commit browser/native acceptance remains open. A receipt never certifies external services, model learning or reminder efficacy.

## Remove or upgrade

Inspect a newly certified full distribution SHA and reinstall with the stock installer's replacement option, then rerun setup. A pinned `hermes plugins update agent-fix-lab` must not silently advance the pin. Inspect changed reminder implementation and reapprove explicitly; old approvals do not migrate automatically.

```sh
hermes afterforge uninstall-runtime --confirm
hermes plugins disable agent-fix-lab
hermes plugins remove agent-fix-lab
```

Run runtime removal before removing source if environment cleanup is desired. Evidence in profile-local plugin-data is retained. The older standalone skill/environment is not deleted or automatically merged; [legacy skill instructions](docs/hermes-integration.md) explain owned removal.

## Privacy, evidence and development

Data is permission-restricted, not encrypted. Never publish private histories, session IDs, local paths, credentials or raw outputs. The loopback web service has mutation tokens, origin/host checks and text-only history rendering; it is not a multi-user hosted service. Read [privacy](docs/privacy.md) before import, execution or export. The stock scanner and its exact-warning gate remain enabled and unchanged in scope.

The historical evaluation cohort and its weak holdout are documented in [dataset methodology](docs/dataset-methodology.md); they are not a new 0.5.0 benchmark. The three included history-derived examples are synthetic reductions, not recovered historical source or proof of repair of original incidents. Component pins remain unchanged; see [sources and attribution](docs/sources.md).

```sh
uv run ruff check __init__.py hermes_plugin src tests scripts examples
uv run ruff format --check __init__.py hermes_plugin src tests scripts examples
uv run pytest -q
uv build
```

See [SPEC](SPEC.md), [architecture](docs/architecture.md), [data model](docs/data-model.md), [contributing](docs/contributing.md), [CHANGELOG](CHANGELOG.md) and the current [handoff](handoff.md). Unfinished release gates are explicit; an intermediate test total or candidate branch is not final certification.