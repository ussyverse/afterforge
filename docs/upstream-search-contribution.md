# Current-upstream search contribution

The [original pinned reproduction](history-discovery-tool-repair.md) and its patch/probe remain unchanged. This is a separate current-upstream verification, not a replacement of that evidence.

## Source and contribution

Upstream HEAD checked before repair and again before publication: `5eb99eb2844b22ebb723711b8e6a0bbb80bb5f04`. Search now lives in `tools/file_operations_search.py`. Contribution instructions, area instructions, and existing issues/PRs were inspected.

Draft PR: https://github.com/NousResearch/hermes-agent/pull/110715

Focused fork commit: https://github.com/mojomast/hermes-agent/commit/a52c3943e4e4ae2b3202ba6849e0390f5ba5b06a

Branch: `mojomast:fix/search-pattern-argument-boundary`. Only the search implementation and `tests/tools/test_search_pattern_arguments.py` are changed.

Existing open contributions #93846, #85798 and #50357 overlap. In particular #93846 repairs the current module's main rg and common grep builders, but its inspected diff omits zero-match probe construction. The draft explicitly requests consolidation and preserves acknowledgement of earlier contributors; it does not claim first discovery or supersede their authorship.

The three argument builders now use `-e PATTERN -- PATH`: main rg, common grep (including pruned find/grep), and zero-match probes. Shell quoting alone did not protect executable option parsing. Regex semantics are preserved.

## Executed evidence

The failure was reproduced before implementation edits. An untouched worktree at the pinned upstream base also ran the identical final regression file. Private receipts retain source/test hashes, exit codes and complete output, including the earlier runs before dependency locking.

With locked dev dependencies and upstream's canonical hermetic per-file runner:

- Baseline: 94 failed, 31 passed, exit 1.
- Repaired new matrix: 125 passed.
- Repaired matrix plus 12 existing related files: 362 passed, zero failed, six Windows-only skips, exit 0.
- Ruff and whitespace checks passed.

Tests use synthetic temporary files, real LocalEnvironment execution and the registered search tool dispatcher, with isolated homes and stripped credentials. Spies confirm transport selection without supplying fake search output. Coverage includes option-like literals, CSS alternation and ordinary regexes, successful controls, file globs, content/count/files_only output, no-match controls, invalid regex rejection, and case/hidden/literal zero-match probes.

Exercised: Linux x86_64, Python 3.11.15, ripgrep 14.1.1, GNU grep 3.11; native rg, shell rg, forced grep fallback, and find-pruned grep with a synthetic excluded directory. Not exercised: actual Windows/macOS, macOS TCC, BSD grep, remote/container transports or the entire upstream suite. OS-mocked tests passing on Linux do not establish native OS coverage.

Known separate limitation: pruned find/grep already folds invalid-regex errors into an empty result. This patch does not fix that error-propagation contract. Invalid-regex rejection is verified on rg and ordinary grep, not asserted for the pruned lane.

CI status at initial publication: the draft was verified open at the exact commit, but GitHub returned no checks or workflow runs. No upstream CI success is claimed. Check https://github.com/NousResearch/hermes-agent/pull/110715/checks for subsequent results. Original Afterforge proof CI remains https://github.com/ussyverse/afterforge/actions/runs/34819727470 and is not current-upstream CI.

## Later reviewed installation and rollback

No rollout has occurred. Live profiles, installed Hermes, stable release, original reproduction and inactive bounded-status procedure remain unchanged.

1. Obtain maintainer review/consolidation and green required CI for the final accepted SHA. If another PR lands first, fetch current upstream and rerun the regression; do not install a duplicate patch. Recheck this plan against the accepted source layout.
2. Build a separate checkout/release directory at that exact reviewed SHA, with its own locked environment (`uv sync --locked --extra dev`). Never apply the old `file_operations.py` patch to the refactored module. Run `bash scripts/run_tests.sh tests/tools/test_search_pattern_arguments.py` plus the related search tests using an isolated HOME/HERMES_HOME and no provider credentials.
3. Before any production switch, record the existing launcher/service target and exact installed SHA; retain that release directory and environment. Securely back up the affected profile configuration and database through the supported backup mechanism. Do not publish these backups or credentials.
4. With explicit rollout approval, point only a canary launcher/service at the reviewed new release. Do not mutate the old release in place. Run synthetic option-like, normal-regex, invalid-regex and no-match smoke checks through its actual registered tool; require correct content, counts and file identities. Broader deployment waits for canary acceptance.
5. On regression, stop the canary/new service, restore the recorded launcher/service target to the retained old release and restart it. Verify its recorded SHA, service readiness and ordinary-search control. This patch changes no data schema; restore profile backups only if separately needed, not by overwriting new user data automatically. Preserve failed canary evidence privately and keep the new release inactive.

No further discovery, inference study or prompt tuning is authorized by this contribution.
