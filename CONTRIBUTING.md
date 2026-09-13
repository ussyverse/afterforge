# Contributing

Read AGENTS.md, SPEC.md and docs/privacy.md. Discuss changes to evidence/runner/export contracts before implementing incompatible formats. Use an isolated environment, not Hermes's runtime.

```sh
uv sync --locked
uv run ruff check src tests scripts examples
uv run ruff format --check src tests scripts examples
uv run pytest -q
uv build
```

For browser and portable-bundle checks, follow .github/workflows/validation.yml. `scripts/browser_fixture.py NEW_DIRECTORY` builds synthetic cases and reviewed-code fixtures; it never reads personal logs. Browser tests start a fresh loopback server per iteration and assert product completion states, rejection behavior, text rendering and reversed-response safety. Do not hide races with arbitrary sleeps.

Use synthetic canaries and minimal reviewed reproductions for public tests. Document whether examples are synthetic, derived or real. Never copy historical prompts, credentials, raw tool output, local manifests or personal paths into Git. Keep debugging evidence in a private directory outside the checkout.

Before committing: inspect `git diff --cached`, run `uv run python scripts/audit_index.py`, preserve existing commits and push normally. A passing test is not enough if expected assertions changed or private evidence was exposed. Update CHANGELOG.md and relevant docs with measured results and limitations. Do not claim independently validated learning or generalization from process-derived labels.

Dependency updates must be pinned and revalidated as described in docs/sources.md. No personal logs, model APIs or repository secrets are permitted as CI prerequisites.
