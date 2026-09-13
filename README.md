# Agent Fix Lab

Local-first regression workbench that turns Hermes failures and corrections into reproducible, evidence-backed test cases.

For Python projects: import a failed tool run, inspect its evidence, review a correction candidate, and execute the same pytest assertion against two Git revisions.

The useful output is an evidence-backed answer: what failed, what remains unknown, what should happen, and a repeatable command to check the proposed fix. Historical success is not fresh verification. This is a single-user local tool, not autonomous learning or a general model replay engine.

## Install

Native Hermes plugin 0.2.0 adds eight tools, passive metadata hooks, `/fixlab`, terminal commands and a namespaced bundled skill without replacing the standalone core. A reproducible distribution is generated on `plugin-release`; use the exact release SHA from a successful `native-plugin` Actions run, not a development/main SHA. All application code ships visibly in the distribution; development security tests remain here.

Install with `hermes plugins install ussyverse/agent-fix-lab --ref FULL_RELEASE_COMMIT_SHA --enable`, review the stock installer's caution prompt, then run `hermes fixlab setup`. The repository remains private and requires GitHub access. Stock scanning stays enabled; no Hermes scanner patch is needed. Pinned GitHub installation and real tool/hook/regression dispatch have passed locally. See [native distribution, verification, commands, migration and removal](docs/native-plugin.md).

Requires Linux, Python 3.11+, Git and [uv](https://docs.astral.sh/uv/). No model API or personal logs are needed to install or test. Initial dependency installation needs network access; analysis and execution work offline afterwards.

```sh
git clone https://github.com/ussyverse/agent-fix-lab.git
cd agent-fix-lab
uv sync --locked
uv run agent-fix-lab --help
uv run agent-fix-lab doctor
```

The repository is private: authenticate with GitHub before cloning. All three component dependencies are Git URLs pinned to exact inspected commits, not similarly named PyPI packages. `uv.lock` freezes the full environment. If uv's default cache is read-only, set `UV_CACHE_DIR` to a writable directory; never replace the running Hermes runtime to install this application.

## First case

Keep the data home outside this checkout. Resolve `HERMES_HOME` from the running profile first; it is already profile-specific.

```sh
export AGENT_FIX_LAB_HOME="$HOME/.local/share/agent-fix-lab"
uv run agent-fix-lab import-hermes --source "$HERMES_HOME/state.db" --source-id local-hermes --limit 100 --dry-run
uv run agent-fix-lab import-hermes --source "$HERMES_HOME/state.db" --source-id local-hermes --limit 100
uv run agent-fix-lab list --status fail
uv run agent-fix-lab show CASE_ID
uv run agent-fix-lab annotate CASE_ID --text 'Proposed correction, not a historical user quote' --expected 'The meaningful assertion that must hold'
uv run agent-fix-lab serve
```

Open http://127.0.0.1:8765. Search cases, inspect error locations and unknown fields, save an operator correction, compare selected configuration fields, create a reviewed recipe, run both revisions, and export the count/status report. Imported logs are rendered as text, never HTML.

`--after` and `--before` are Unix seconds (inclusive start, exclusive end). Use `--session` to narrow selection. Imports return `next_after_id`; pass it as `--after-id` to continue beyond a bounded page. Reuse the same `--source-id` for snapshots of the same history store. Re-import is idempotent. `--cohort dogfood` separates new build activity from a historical evaluation cohort. Filters do not imply that a session/project is independent.

## Review and run a regression

Inspect both Git revisions, the test and its imports before authorizing execution. Never execute a command because it appeared in a transcript. The runner accepts a reviewed pytest file, not shell commands. Tests run in a fresh Git-archive workspace with an allowlisted environment; this is not an OS sandbox for hostile code.

Create `recipe.json` outside the data repository:

```json
{
  "case_id": "CASE_ID",
  "repository": "/absolute/path/to/reviewed/project",
  "faulty_revision": "FAULTY_COMMIT",
  "corrected_revision": "CORRECTED_COMMIT",
  "test_file": "/absolute/path/to/reviewed/test_regression.py",
  "expected_behavior": "Describe the assertion",
  "intended_failure": "Distinctive assertion failure text",
  "dependencies": ["pytest"],
  "provenance": "derived",
  "timeout_seconds": 30,
  "output_limit_bytes": 65536
}
```

```sh
uv run agent-fix-lab recipe --file recipe.json --reviewed
uv run agent-fix-lab run RECIPE_ID
uv run agent-fix-lab compare RECIPE_ID
uv run agent-fix-lab export CASE_ID > case-summary.json
```

The review freezes commit IDs and the test SHA-256. Dirty tracked changes are hashed for disclosure, but execution uses the committed archive, not the dirty working tree. Untracked application files are excluded. An edited assertion requires a new review. Tests need to be self-contained or import tracked source using the supplied project/src paths. Arbitrary dependency installation, shell recipes, network isolation and model-based replay are deliberately unsupported.

A comparison passes only when the faulty version has collected assertion failures matching the reviewed reason and the corrected version passes the same number of tests with the same assertion hash. Zero tests, skips, setup/collection errors, output decoding errors, timeout and output limits are inconclusive. A failing setup is not a reproduced bug.

## Configuration evidence

```sh
uv run agent-fix-lab baseline CASE_ID --logical-path runtime.json \
  --baseline '{"python_version":"3.11.0"}' \
  --current '{"python_version":"3.12.0"}'
```

Petrichor stores only explicitly selected `python_version`, `pytest_version`, `platform` and `project_kind` values, with strict value allowlists. Logical paths and selected field sets must match. A current snapshot does not establish old configuration or causality. Missing/incompatible baselines stay inconclusive.

## Hermes integration

Install the wheel into a separate environment, then install the supported profile-local skill:

```sh
uv build
uv venv "$HERMES_HOME/venvs/agent-fix-lab"
uv pip install --python "$HERMES_HOME/venvs/agent-fix-lab/bin/python" dist/agent_fix_lab-0.1.0-py3-none-any.whl
python3 scripts/install_hermes.py --hermes-home "$HERMES_HOME" \
  --lab-home "$AGENT_FIX_LAB_HOME" \
  --executable "$HERMES_HOME/venvs/agent-fix-lab/bin/agent-fix-lab"
python3 "$HERMES_HOME/skills/agent-fix-lab/scripts/lab.py" doctor
python3 "$HERMES_HOME/skills/agent-fix-lab/scripts/lab.py" find 'KeyError'
```

Hermes discovers `skills/agent-fix-lab/SKILL.md`; the skill guides its existing terminal tool to the bounded wrapper. No invented slash command, gateway restart, core patch, prompt edit or automatic memory mutation is needed. See [integration instructions](docs/hermes-integration.md) for update/removal and the exact verification boundary.

Remove only the owned integration with `python3 scripts/install_hermes.py --remove --hermes-home "$HERMES_HOME"`. This retains the isolated environment and all private data. Updating the wrapper requires this owned removal followed by installation; package updates use `uv pip install --reinstall-package agent-fix-lab` against the isolated environment, never Hermes's runtime.

## Included derived examples

`examples/derived/` contains safe reductions of three real historical assumptions: appending `profiles/default` to an already resolved home; requiring a `matches` field when search returned a grouped shape; and treating a non-JSON response as parseable JSON. Fixtures are synthetic and historical provenance is private. These do not reproduce the original runtime or claim that the original incident was fixed.

```sh
uv run python scripts/prepare_derived.py /tmp/afl-reviewed-examples
```

This creates two inspectable commits. Associate their hashes and one shared `examples/derived/test_*.py` file with an imported case using the recipe workflow above. Public CI constructs its own synthetic case and does not access private history.

## Validation and limits

The frozen initial dataset contains 53 selected real tool-result cases: 20 failures and 33 successful process controls. Source coverage is 114 sessions and 1,150 eligible pre-cutoff tool records. Selection is grouped before implementation tuning. Conservative grouping leaves 52 development cases and only one independent successful holdout. There are no held-out failures and no independently reviewed labels: no generalization, semantic accuracy or time-saving claim is justified.

Three derived comparisons executed real red/green checks (2, 3 and 3 assertions). Original revisions/configurations remain unknown. Counts, exclusions, component test results and dogfooding are documented in [validation](docs/validation.md) and [dataset methodology](docs/dataset-methodology.md).

`export` is the privacy-minimized count/status report. `bundle-export` additionally transfers selected reviewed code, one frozen assertion, checksums and sanitized metadata. No original conversations are included. `bundle-import` requires a new explicit review before execution; a checksum is not a signature or a trust decision. See [bundles](docs/recipes-and-bundles.md).

Data is permission-restricted, not encrypted. Only inspected Hermes SQLite schema 26 is supported. Conservative correction candidates use message roles, chronology and explicit wording; they are pending hypotheses, not authenticated human corrections. General semantic completion verification, legacy text-log imports, multi-user serving and automatic policy learning remain out of scope. The runner is not an operating-system sandbox.

## Correction candidates and portable bundles

```sh
uv run agent-fix-lab correction-scan --source "$HERMES_HOME/state.db" --source-id local-hermes --before CUTOFF_UNIX_SECONDS
uv run agent-fix-lab corrections --status pending
uv run agent-fix-lab review-correction CANDIDATE_ID --decision accepted --note 'Reviewed against the private evidence'
uv run agent-fix-lab bundle-export RECIPE_ID --output regression.json --approved \
  --problem 'Sanitized description' --expected 'Required behavior' \
  --failure 'Distinctive assertion failure text' --file implementation.py
uv run agent-fix-lab bundle-validate regression.json
uv run agent-fix-lab --home "$HOME/.local/share/afl-imported" bundle-import regression.json --reviewed
```

Inspect all source/fixture files before `--approved` or `--reviewed`. Use the returned recipe ID with `run`. The bundle command selects files from both committed implementations, not from the private history store. Review and retraction history remain immutable in the original private store.

## Development

```sh
uv sync --locked
uv run pytest -q
uv run ruff check src tests scripts examples
uv run ruff format --check src tests scripts examples
uv build
```

See [SPEC](SPEC.md), [architecture](docs/architecture.md), [privacy](docs/privacy.md), [sources](docs/sources.md), [CONTRIBUTING](CONTRIBUTING.md) and [handoff](handoff.md). CLI failures emit structured diagnostics. A web failure appears in the status bar; use the CLI to inspect local file/revision problems. Missing recipes are disabled with an explanation, not silently treated as passes.
