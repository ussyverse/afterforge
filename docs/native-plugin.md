# Native Afterforge plugin — 0.5.1

The native adapter registers tools, slash/terminal aliases and one bundled skill around the standalone core. Registration imports only standard-library adapter code; application dependencies live in a separately managed environment. The package/import/plugin IDs are unchanged. Installation does not activate a reminder or grant evidence deployment authority.

## Supported installation locator

The public repository is https://github.com/ussyverse/afterforge. Use `release-metadata/stable.json` only after it names the desired version and links both successful exact-source CI workflows. It records source/distribution commits and SHA-256 values for all distribution files, including RELEASE.json. The supported pointer is `plugin-stable`; install the full distribution SHA from the locator, not either moving branch. The generated `plugin-release` branch is an unverified candidate until all required checks finish. No final 0.5.0 locator is certified by these docs.

```sh
hermes plugins install ussyverse/afterforge --ref FULL_DISTRIBUTION_COMMIT --enable
hermes afterforge setup
hermes afterforge doctor
export AFTERFORGE_SOURCE_ID=local-hermes
hermes afterforge scan
hermes afterforge serve
```

Read stock scanner findings at the normal confirmation prompt. Scanning remains enabled. The exact-warning gate retains the previously reviewed `context_exfil` privacy-document finding at its unchanged line/digest; new high/critical findings block. A dangerous verdict is never overridden. The privacy document is shipped intact, not removed or reworded to change a verdict. Scanner success is not proof that arbitrary sensitive content is absent.

`scripts/plugin_release.py` exports committed blobs, never dirty worktree files. All src/, hermes_plugin/ and skills/ files ship byte-for-byte, plus build metadata, uv.lock, legal notices and privacy/intervention documentation. The runtime README comes from packaging/plugin-readme.md. Development-only tests/fixtures/docs stay at the recorded source commit. No hidden application backend is fetched during setup. Declared Git dependencies retain full-SHA pins. RELEASE.json records source paths and hashes. Identical source/repository/parents reproduce the same distribution commit; a separate index preserves the caller's worktree and staging area.

## Inspected host matrix, not inferred support

| Host | Exact source | Source schema | 0.5.0 release status |
| --- | --- | --- | --- |
| Prior pinned stock Hermes, v0.20.4 (2026.8.18) | `277268d83ff2204de9646f0b1e376e73ac0a5d20` | 26 | Exact candidate CI lifecycle passed; see validation ledger |
| Stock Hermes v2026.9.11 | `939e45c91d751fadd94dcd1b873ac3cb44846213` | 30 | Exact candidate CI and local nonempty stock-schema lifecycle passed |

The newer annotated tag `2160b2d59c87316e82f749d77c1f25969bea1533` resolves to the second source SHA. Inspection found:

- `hermes_cli/plugins.py:638`: register_cli_command receives setup_fn and handler_fn and installs the handler through argparse defaults. `register_command` at line 652 supplies slash commands. These aliases must share one Runtime, not duplicate hooks/tools.
- `model_tools.py:643–683`: post_tool_call passes tool_name, args, result, call/session/turn/API IDs, duration_ms, status, error_type, error_message and middleware_trace. Host status is `ok`/`error`; `ok` is not proof of successful process exit. Retain only conservative sanitized metadata, never raw error messages/arguments/results.
- `hermes_cli/plugins.py:1890–1908`: pre_verify passes coding, attempt, final_response and changed_paths; it accepts continue/message (or block/reason), with first nonempty continuation winning. It is not an unconditional veto or process-verification oracle.
- `hermes_state_common.py:213,308–398`: schema 30 has parent_session_id, profile_name, cwd/Git metadata and archived session flags; messages retain role/content/tool IDs/timestamps/compacted state and add fields including active/effect_disposition. The importer accepts only 26/30 after required-column validation. The native harness inserts synthetic records into the actual stock schema, preserving its version and extra columns; unknown versions remain rejected.

Authoritative interfaces: [plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins), [hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks/), [session storage](https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage/). Official source and real manager execution take precedence over guessed September-era import paths. The prior host requires manifest_version 1 for Git installation even though its doctor accepts v2; retain the manifest compatibility choice and test both hosts rather than upgrading Hermes.

## Registration and command contracts

Stable tools: fixlab_status, fixlab_scan, fixlab_list_cases, fixlab_inspect_case, fixlab_review_case, fixlab_build_regression, fixlab_verify_regression, fixlab_report. Tool JSON `success` is operation-envelope success; inspect `data.status` separately for pass/fail/inconclusive/not-run. Native terminal operation failures and nonpassing verification exit nonzero with sanitized actionable diagnostics.

`/afterforge` and `/fixlab` share status, scan, failures, review and help. The review command lists the operator queue and supports accept/reject/retract with explicit rationale. `fixlab_build_regression` historically registers an existing test file; do not describe that registration as generated code. The guided browser and standalone draft commands produce a separate concrete artifact with source references, expected failure, frozen inputs and unknowns, followed by explicit review.

`hermes afterforge` and `hermes fixlab` share setup, doctor, scan, serve, export, demo, review, retained-plan, retained-check, current-check-plan, verify-current, policy and uninstall-runtime. Native retained-plan accepts recipe ID and target revision positionally; use the standalone command or guided browser for path-specific subject-data review. Bundled skill identity is `agent-fix-lab:regression-workflow`; the older editable skill is separate and not silently removed. See [legacy skill integration](hermes-integration.md).

## Runtime, source identity and capture

The active profile's documented plugin-data root owns `agent-fix-lab/data/lab.sqlite`, source-snapshots/, workspaces/, exports/, jobs/, runtimes/ and uv-cache/. Staged generations contain source, environment, requirements.lock and resolved-manifest.json. A schema-v2 runtime-install.json marker selects a generation only after locked sync and application doctor. Setup/update/removal share serialization; bounded private logs and cleanup prevent an ordinary failed upgrade from destroying the last usable generation. Never rename an installed venv: console-script shebangs bind its path. Hermes's environment is untouched.

Source namespaces require explicit profile/history mapping across native, CLI and browser paths. Set AFTERFORGE_SOURCE_ID for native/browser scan and launch Hermes with that value for session commands; use the same standalone `--source-id`. A database basename, copied path or profile display name is not a globally unique source identity. Reuse a mapping only for snapshots of the same logical store; independent copies do not implicitly become one source. Shared mapping and separate resumable correction cursors are implemented but final cross-surface acceptance remains open; see [workflow](workflow.md).

post_tool_call and on_session_end retain only bounded nonblocking metadata. Outcome retention has its own 32-session LRU and 64-event/session cap, independently of pending import hints; eviction/truncation and lock contention remain best-effort. Hooks perform no snapshots, process/model calls or transcript writes. Explicit scanning persists bounded cursors/hints and invokes read-only ingestion. Capture cannot certify complete verification.

## Upgrade and removal

A pinned `hermes plugins update agent-fix-lab` deliberately does not advance the pin. Inspect a new certified distribution, reinstall with `--force --ref NEW_DISTRIBUTION_SHA --enable` through the normal stock replacement/caution mechanism, then rerun setup. This does not override a dangerous scan verdict. Preserve evidence and old runtime during the upgrade; changed reminder implementation requires explicit reapproval.

Run `hermes afterforge uninstall-runtime --confirm` before `hermes plugins remove agent-fix-lab` if owned runtime cleanup is desired. `hermes plugins disable agent-fix-lab` stops registration for subsequent sessions; enable restores it without tool overrides. Source/runtime removal retains private evidence. Stop owned servers before teardown. Do not delete unrelated standalone environments or another profile's data.

Final acceptance requires real GitHub installation of the candidate SHA, unchanged stock scans/doctor, both host lifecycles, aliases, tools, hooks, skill, regression dispatch, interrupted upgrade/migration and teardown. The matrix is configured to fail closed; its presence is not evidence of a green run. See [validation](validation.md).