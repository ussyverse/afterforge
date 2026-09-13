# Reviewed recipes and portable bundles

A recipe is a constrained pytest check, not a shell command. Required fields are shown in README.md. `recipe --file FILE --reviewed` freezes both full Git commits and one test SHA-256. Only the runner's installed pytest dependency is supported. Fixtures must be tracked inspected files in the source repository; external fixture references are rejected. A changed assertion requires a new review and cannot silently replace an existing recipe.

Run with `run RECIPE_ID`; inspect with `compare RECIPE_ID`. A comparison pass requires the faulty implementation to fail assertions for the intended reason and the corrected implementation to pass identical assertion bytes, runtime fields and test count. Dirty tracked diff identity is recorded for disclosure but committed archives are executed. Zero tests/skips/errors/timeouts/truncated or undecodable evidence are inconclusive.

## Bundle format v1

A UTF-8 JSON file, at most 2 MiB: format `agent-fix-lab.regression.v1`, schema_version 1, stable hashed case ID, sanitized problem/expectations/failure reason, two selected source projections with commit IDs, one shared assertion, pytest-only command/dependency declaration, limits, allowlisted configuration fields, original historical revision marked unknown, real-result status summary, explicit derived/synthetic provenance, redaction manifest, README and SHA-256 checksums. A canonical full-manifest digest covers metadata and file digests.

Select only inspected files using repeated `--file logical/name.py`. Supported regular text source/fixtures end in .py, .json or .txt. Links, absolute/traversal/dot paths, arbitrary commands, unknown fields/versions, excessive sizes and invalid checksums are rejected. These conservative constraints intentionally exclude many general-purpose projects.

```sh
agent-fix-lab bundle-export RECIPE_ID --output regression.json --approved --problem 'Sanitized reduction' --expected 'Behavior to assert' --failure 'Distinctive assertion text' --file implementation.py
agent-fix-lab bundle-validate regression.json
agent-fix-lab --home NEW_PRIVATE_HOME bundle-import regression.json
```

Import without `--reviewed` is inspect-only; `run` rejects its recipe. To authorize, inspect the entire bundle first and import into the intended fresh home with `--reviewed`. Re-import is idempotent and deliberately does not escalate prior review authority. To review a previously unreviewed import, inspect the returned local recipe via case detail and use `recipe --file FILE --reviewed` to create a new reviewed local record.

Import generates new local Git commits for the selected source projections, stores original supplied commit IDs separately, and resets execution to not-run. It does not claim these generated commits are historical originals. Both variants use the same bundled assertion. Imported configuration is informational, never evidence of the old runtime. Checksums are integrity checks, not code authentication.

## Repeatable demonstration

CI uses `scripts/browser_fixture.py` to create synthetic source/history and `scripts/bundle_smoke.py` to export, validate, import into a new data home and run through the wheel-installed CLI. The real-history-derived grouped-search reduction also completed this round trip with faulty=fail and corrected=pass. Detailed paths/results remain private. No original conversations are needed to execute an exported reduction.
