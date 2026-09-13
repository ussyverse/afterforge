# Native Hermes plugin — 0.2.0 (installation validation blocked)

The standalone application, CLI, web UI and regression core remain unchanged in architecture. The immutable pre-plugin green baseline is 53c451334593943fc55e1a991b6620b477bec923. Native registration is a dependency-free adapter; application dependencies load only in a managed subprocess after explicit setup.

## Current delivery boundary

Native plugin doctor passes real runtime discovery, parsing, namespaced import and registration (eight tools, two hooks). The local suite passes 86 tests: the original 68 plus 18 adapter tests. Git installation is NOT yet certified. The installer blocks this repository with a DANGEROUS security verdict. Managed setup and the actual registry-dispatch lifecycle therefore remain unverified. Do not bypass scanning or infer successful installation from doctor/unit tests.

Tested host: Hermes Agent v0.20.4 (2026.8.18), Python 3.11.16 locally; installed source 277268d83ff2204de9646f0b1e376e73ac0a5d20. CI independently installs that exact public Hermes revision in an isolated environment. Host test-only imports follow that revision's own compatibility fixtures; production code imports no manager, tool registry, model-tools or other internal modules. Its only lazy Hermes import is the documented plugins.plugin_storage.plugin_data_dir API, as shown in both installed and fetched current plugin guides. No unverified September-migration path is guessed.

The runtime parser/doctor accepts manifest v2 but the Git installer explicitly rejects it (supports at most v1). This adapter uses manifest_version: 1 with additive license/homepage/tags/config metadata. No privileged capabilities or host Python dependencies are requested. `hermes plugins compat .` is unavailable on this host (argparse invalid-choice exit 2). Real doctor and host lifecycle tests are the available compatibility checks, not a fabricated compat success.

## Installation after security review

Authenticate GitHub access to the private repository. These are intended supported commands; the current installer security block must first receive an operator-reviewed resolution:

```sh
hermes plugins install ussyverse/agent-fix-lab --enable
hermes plugins install ussyverse/agent-fix-lab --ref FULL_40_CHARACTER_COMMIT_SHA --enable
hermes fixlab setup
hermes fixlab doctor
hermes plugins list
hermes plugins capabilities agent-fix-lab
```

Desktop link, where the desktop client supports it: hermes://plugin/install?repo=ussyverse/agent-fix-lab&enable=1 . This is not a promise that the installed CLI owns a desktop URL handler or that the link bypasses install validation.

Enabling a plugin executes trusted local Python with the user's permissions. Inspect the source first. Regression recipes remain trusted pytest code, NOT an operating-system sandbox.

## Commands and tools

Tools: fixlab_status checks setup/version and legacy-skill migration; fixlab_scan imports at most the configured page size; fixlab_list_cases accepts query/status/offset/limit (at most 25); fixlab_inspect_case separates observations, unknowns and interpretations; fixlab_review_case records an agent-proposed annotation or declared agent review of a pending candidate; fixlab_build_regression associates an existing inspected recipe file and requires reviewed=true; fixlab_verify_regression executes only an existing reviewed recipe; fixlab_report returns the existing privacy-minimized summary. No automatic regression reduction or arbitrary shell execution is exposed. Oversized responses fail explicitly and direct the operator to the standalone CLI.

In-session command, registered for CLI and gateway dispatch: `/fixlab status`, `/fixlab scan`, `/fixlab failures`, `/fixlab review`, `/fixlab help`. Review/help provide workflow guidance; case-specific mutation uses the structured tools.

Terminal commands: `hermes fixlab setup`, `doctor`, `scan`, `serve [--port PORT]`, `export CASE_ID`, `uninstall-runtime --confirm`. Export is the core's safe summary; executable bundles remain available through the standalone bundle CLI. Serving stays loopback-only by the existing CLI contract.

Bundled read-only skill: agent-fix-lab:regression-workflow, registered using ctx.register_skill. It is not copied into the editable skills directory. The existing ordinary agent-fix-lab skill is detected and retained. Use the native skill after successful native installation; remove the old owned wrapper only if you intentionally choose to migrate, following docs/hermes-integration.md. Existing standalone data is neither moved nor deleted automatically.

## Storage, updates and removal

The documented profile plugin-data root contains agent-fix-lab/data/lab.sqlite (the existing Store filename is preserved), source-snapshots/, workspaces/, exports/, jobs/ and runtime/. Setup logs and a version/source fingerprint marker stay there, never in the Git installation. The managed environment installs the existing package from the checked-out plugin source; Hermes's environment is not modified. Runtime checks detect missing/outdated markers and backend failures and suggest setup. Setup source/dependency installation needs network and uv; ordinary analysis uses local services.

`hermes plugins disable agent-fix-lab` stops future registration after reload. `hermes plugins enable agent-fix-lab` enables it. For an unpinned install, `hermes plugins update agent-fix-lab` updates source; rerun setup if its fingerprint changed. Pinned updates use the install command with a new immutable SHA and the installer's normal replacement flow. `hermes plugins remove agent-fix-lab` removes code, not plugin-data. `hermes fixlab uninstall-runtime --confirm` removes only the owned environment and marker, retaining evidence. Remove it before removing plugin code if desired. These lifecycle commands still require full verification once the security block is resolved.

## Passive capture and privacy

post_tool_call and on_session_end accept additive keyword payloads. Hooks only update a nonblocking in-memory map bounded to 32 sessions. They retain identifiers, a tool name, conservative process status, generic error class, capture time and pending/eligible flags. Raw arguments/results and error messages are never retained. Large/non-JSON results remain inconclusive. Hooks perform no snapshots, subprocess/Git/model calls or disk writes and isolate errors.

Scan persists small queued hints/cursors/job status through ctx.state, then invokes the existing read-only WAL-consistent importer in the managed backend. The global import cursor and idempotent source identity are authoritative. Volatile hints can be dropped under contention, capacity pressure or process exit before a scan; later bounded global scans recover persisted history. This is best-effort metadata capture, not a durable event journal. No inferred correction changes prompts, memories, policies or skills.

## Blocker and reproducible test path

The v1 pinned attempt at 167f3cc743104fa7daa7f3583640812e9c6f1984 failed with: `Blocked: Security scan blocked plugin install: Blocked (dangerous verdict, 76 findings). --force does not override a dangerous verdict.` Findings included the existing synthetic credential canary, contributing instructions and privacy documentation. They were preserved rather than disguised. The scan was not disabled and no alternate installation path was used.

scripts/plugin_lifecycle.py is a pending real-host harness, not proof of successful dispatch. It requires an explicit isolated-home marker, synthetic fixtures, successful Git installation and managed setup, then checks all tools, hooks, slash dispatch, bundled skills, one failed incident, repeat-import zero additions and red/green execution. .github/workflows/native-plugin.yml deliberately preserves the required installation gate; it must not be made green by skipping security or lifecycle checks. The ordinary validation workflow continues to exercise packaging, browser, bundle and standalone regression behavior.
