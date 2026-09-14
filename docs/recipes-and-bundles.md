# Reviewed recipes, retained checks and portable bundles

Afterforge 0.5.0 uses recipe v2, result v3 and bundle v2. Legacy immutable records remain readable without acquiring new equivalence or approval claims.

## Review before execution

A recipe registers an inspected pytest file, not a shell command. An existing-file registration is not generated regression code. A draft must be a concrete artifact with source references, expected failure, fixture/input declarations and unknowns; neither a draft nor an inferred correction is execution authorization. The guided draft path is under integration; the explicit JSON recipe interface remains available.

Example input to `afterforge recipe --file recipe.json --reviewed` (replace symbolic values with inspected local paths/commits):

```json
{
  "schema_version": 2,
  "case_id": "CASE_ID",
  "repository": "/absolute/path/to/reviewed/project",
  "faulty_revision": "FAULTY_COMMIT",
  "corrected_revision": "CORRECTED_COMMIT",
  "test_file": "/absolute/path/to/reviewed/test_regression.py",
  "expected_behavior": "The meaningful assertion that must hold",
  "intended_failure": "Distinctive assertion failure text",
  "input_contract": "declared-v1",
  "frozen_inputs": [],
  "reviewed_data_changes": {},
  "dependencies": ["pytest"],
  "provenance": "derived",
  "timeout_seconds": 30,
  "output_limit_bytes": 65536
}
```

Do not copy `declared-v1` blindly. It declares that inspection established deterministic reviewed code, supported typed pytest parameters and frozen inputs, with no ambient file/network/clock/random/environment inputs, hidden mutable globals or fixture side effects. If that cannot be established, use unknown and accept an inconclusive equivalence result. This is local-caller review, not automatic dependency discovery or authenticated human approval.

Each frozen input is `{logical_path, content, sha256}` with reviewed UTF-8 content and its actual SHA-256. Up to 50 files, 256 KiB content per file and 1 MiB total are bounded by validation. Safe relative paths are required; no traversal, dot paths or duplicates. They are materialized separately and accessed through `AFTERFORGE_FROZEN_INPUTS`, not overlaid onto the subject. Legacy external `fixture_inputs` references remain unsupported. Path-specific nonempty `reviewed_data_changes` rationales may authorize intentional changes to subject data, never changing the regression's inputs to hide failure.

The review resolves full Git commits and freezes assertion bytes. Source fixtures must be inspected. Only the installed pytest dependency is supported; no arbitrary installer or transcript replay endpoint exists.

```sh
afterforge recipe --file recipe.json --reviewed
afterforge run RECIPE_ID
afterforge compare RECIPE_ID
```

## Meaning of a comparison

Tests execute in temporary committed Git archives, not the working tree. Dirty-diff identity is disclosure, not certification of live edits. Assertion bytes, compatible recipe/runtime digests, collected test identities and frozen/typed parameter-input identities must agree. A faulty collected assertion must fail for the reviewed reason and corrected assertions must pass. Same count/hash alone is not enough; CASES=[-1] versus CASES=[1] cannot look equivalent merely because both collect one test with the same custom ID.

Zero tests, skips, setup/collection errors, timeouts, output limits/decoding errors, unsupported inputs or absent equivalence evidence cannot verify a fix. Changing assertion/input/revision approval requires a new immutable review. Legacy recipes/results are not upgraded by reloading or rerunning them.

This is trusted local Python execution, NOT an OS sandbox. Code can access user files/network and evade process-group cleanup. Use a separate VM/container/account for hostile code.

## Retain against a later commit

`afterforge current-check-plan RECIPE_ID` exposes the reviewed corrected-commit recipe digest; `verify-current RECIPE_ID --approve-digest DIGEST` authorizes its committed archive. Native aliases accept the same operations. Inspect the plan before approval. A new commit requires a new reviewed binding/recipe and immutable receipt with unchanged frozen regression—not modification of the historical recipe or reuse of its old digest. Final guided later-commit integration and ignored-file practicality are acceptance gates. A retained check does not certify live edits, transient endpoint changes, external services or model behavior.

## Bundle v2

The UTF-8 JSON envelope is bounded to 2 MiB. Format and schema version must agree. v2 carries selected source variants, a shared assertion, frozen inputs/input contract, reviewed subject-data rationale, sanitized problem/expectations/failure, pytest-only dependency/limits, allowlisted configuration, provenance/unknown historical revisions, checksums and a redaction manifest. `agent-fix-lab.regression.v1` remains readable but does not gain v2 input authority.

Select only inspected regular text `.py`, `.json` or `.txt` files with repeated `--file`; links, unsafe paths, arbitrary commands, unknown fields/versions, excessive sizes and checksum mismatches are rejected. These constraints intentionally exclude many general projects.

```sh
afterforge bundle-export RECIPE_ID --output regression.json --approved --problem 'Sanitized reduction' --expected 'Behavior to assert' --failure 'Distinctive assertion text' --file implementation.py
afterforge bundle-validate regression.json
afterforge --home NEW_PRIVATE_HOME bundle-import regression.json
```

Import without `--reviewed` is inspect-only. Inspect all selected code/inputs before importing into the intended fresh home with `--reviewed`. Reimport is idempotent and does not escalate earlier review authority. New local source-projection commits do not masquerade as historical originals; execution starts not-run and needs fresh local results. Checksums detect changes, not trusted code or maliciously re-signed content. Review every bundle before sharing: regex cannot identify arbitrary proprietary strings. No raw history, session/message IDs, annotations or original prompts are exported.

The CI browser fixture and bundle smoke script use labeled synthetic data and an installed wheel. Historical reduction results are documented separately; final 0.5.0 round-trip evidence remains a [validation gate](validation.md).