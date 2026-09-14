# Contributing to Afterforge

Read SPEC.md, docs/privacy.md, docs/migration.md and the repository maintainer instructions before changing immutable evidence, execution or export. AGENTS.md records the explicitly authorized public-visibility requirement; preserve its other instructions. Public source is not permission to publish private data.

Use Linux/Python 3.11+ and `uv sync --locked` in an isolated environment, never Hermes's runtime. Preserve package/plugin IDs, old aliases, component pins and immutable legacy contracts for 0.5.0. No dependency upgrades merely for branding, no force push, no PyPI publication.

Run:

```sh
uv run ruff check __init__.py hermes_plugin src tests scripts examples packaging
uv run ruff format --check __init__.py hermes_plugin src tests scripts examples packaging
uv run pytest -q tests packaging
uv build
```

Follow .github/workflows/validation.yml for clean-wheel aliases/assets, three fresh packaged browser servers and portable execution. An existing Chromium can be selected via AFL_CHROMIUM; installation is unnecessary when a suitable cached executable is available. Keep executable paths private. Browser tests must observe actual health/completion states, not hide races with sleeps.

Public fixtures must be labeled synthetic and require no personal logs, model API or repository credentials. Historical reductions must disclose unknown original revisions. New equivalence claims require versioned input contracts and rejection tests, not weaker assertions. New native host support requires inspected loader/hook/schema source plus real stock manager tests on exact pins.

Before a coordinator-authorized commit: inspect `git diff --cached`, run `uv run python scripts/audit_index.py`, review generated release blobs and stock scan output, and retain meaningful privacy prose. An empty index audit does not audit unstaged edits; scanner/regex success is not proof of absence of arbitrary sensitive content. Raw history, credentials, personal paths and detailed reports remain outside Git.

Record actual command results and remaining gates in docs/validation.md and handoff.md. Move historical milestones to CHANGELOG.md rather than appending contradictory current-state paragraphs. Do not claim CI, a screenshot, installed migration, model efficacy or a verified release SHA without corresponding real evidence. Component attribution/license boundaries remain in NOTICE and docs/sources.md.
