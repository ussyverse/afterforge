# Native Hermes plugin — 0.2.0

The native plugin is a thin adapter around the unchanged standalone architecture. The immutable standalone green baseline is 53c451334593943fc55e1a991b6620b477bec923. All native application dependencies load only in the explicitly installed managed backend, not during registration.

## Distribution, not a scanner patch

Development remains on main. A reproducible runtime distribution is published on plugin-release. Install an exact release SHA from a successful native-plugin Actions run; do not use a development commit or the bare default-branch installation command.

```sh
hermes plugins install ussyverse/agent-fix-lab --ref FULL_RELEASE_COMMIT_SHA --enable
hermes fixlab setup
hermes fixlab doctor
```

The repository remains private; users need authenticated GitHub access. No public visibility change was made. The stock installer accepts a full commit with --ref and resolves plugin.yaml at the cloned root. Its `plugins pack` feature is a set of pinned plugins, not a source archive packager. No unverified subdirectory syntax is used.

scripts/plugin_release.py reads committed Git blobs, never uncommitted files. Every src/, hermes_plugin/ and skills/ file ships unchanged, including the entire standalone core, JSON bridge and web assets. Build metadata, uv.lock, LICENSE, NOTICE and docs/privacy.md also ship unchanged. A runtime README is supplied from packaging/plugin-readme.md. Tests, fixtures, contributor docs and CI scripts remain in the development source; they are not needed at runtime. No executable code is omitted to change a scan verdict, and setup does not fetch a hidden application backend. Normal declared dependencies include three full-SHA Git dependencies visible in pyproject.toml. Initial dependency installation requires network; inspect these dependencies as part of trust review.

RELEASE.json records the full source SHA and per-file source paths and SHA-256 values. A release commit has the source commit and previous release as parents, retaining auditable history and allowing a normal fast-forward release branch. Identical inputs/parents reproduce the same release SHA. A separate temporary Git index protects the working tree and existing staged changes. Source security tests are retained and run before publication.

The untouched stock scanner reports CAUTION for the release, not DANGEROUS. Its one high finding matches "Output and context" in the unchanged privacy document; medium findings identify legitimate process execution. Review the warning at the normal installer prompt. CI uses the stock installer's --force caution confirmation only after scripts/plugin_scan_gate.py checks the complete release manifest and matches that warning to an exact previously reviewed file digest. New high/critical findings stop publication. Scanning is never disabled; --force still cannot override DANGEROUS. No Hermes scanner changes are used or proposed for distribution. The previously explored isolated scanner patch is abandoned.

## Host compatibility

Tested stock host: Hermes Agent v0.20.4 (2026.8.18), source 277268d83ff2204de9646f0b1e376e73ac0a5d20. Python 3.11.16 locally; CI installs the same public Hermes revision in an isolated environment. Production imports no manager, tool registry or model-tools internals. The lazy storage import uses the documented plugins.plugin_storage.plugin_data_dir API. Test-host manager/registry imports follow that host's own compatibility fixtures. No September-migration import path is guessed.

The runtime doctor accepts manifest v2 but that version's Git installer rejects it, so the distribution uses manifest_version: 1 with additive metadata. No privileged capabilities or host-environment Python dependencies are requested. `hermes plugins compat` is not available on this host; real doctor and actual manager lifecycle checks are used instead. Re-enabling may display the host's optional tool-override prompt: decline it; this plugin does not need tool overrides.

## Tools and commands

Eight bounded JSON tools: fixlab_status, fixlab_scan, fixlab_list_cases, fixlab_inspect_case, fixlab_review_case, fixlab_build_regression, fixlab_verify_regression, fixlab_report. All accept additive host keyword context and return structured errors rather than propagating ordinary exceptions. List pages contain at most 25 cases. Oversized evidence stays private and returns an explicit limit error. Process outcomes retain fail/pass/inconclusive/not-run.

In-session CLI/gateway command: /fixlab status, scan, failures, review, help. Review/help provide guidance; case-specific mutation uses structured tools. Bundled read-only skill: agent-fix-lab:regression-workflow. Existing ordinary editable skills are retained; migration is an operator decision, not an automatic write.

Terminal commands: hermes fixlab setup; doctor; scan; serve [--port PORT]; export CASE_ID; uninstall-runtime --confirm. Export uses the core's privacy-minimized summary. Executable bundles remain available through the standalone CLI. The web service retains loopback binding, Host/Origin checks and mutation authorization.

## Runtime, data and capture

The documented profile plugin-data root contains agent-fix-lab/data/lab.sqlite, source-snapshots/, workspaces/, exports/, jobs/ and runtime/. Source history and derived evidence never enter the Git code tree. Explicit setup installs the complete included application into its own environment and writes a version/source marker and private log. Missing/outdated environments provide a setup instruction. The fingerprint includes Python code, assets, build metadata and lockfile. Hermes's environment is not modified.

post_tool_call and on_session_end only update bounded nonblocking in-memory metadata. They retain identifiers and conservative process status, not raw arguments, results or error messages. Hooks perform no snapshots, subprocess/Git/model calls or disk writes. Explicit scan persists small hints/cursors with ctx.state and invokes the existing read-only WAL-consistent importer. Hints are best-effort, capped at 32 sessions; global import cursors and source deduplication are authoritative after process exit or contention.

Inferred corrections remain proposals. Historical commands are not recipes. Regression execution requires an inspected, explicitly reviewed recipe. No automatic changes to prompts, memories, policies or skills occur. Reviewed Python runs with user permissions, NOT in an OS sandbox. Use separate OS/container isolation for hostile code.

## Update and removal

Pinned `hermes plugins update agent-fix-lab` deliberately exits 1 and leaves the pin unchanged. To upgrade, inspect a new release and use `hermes plugins install ussyverse/agent-fix-lab --force --ref NEW_RELEASE_SHA --enable`, then rerun setup. Source replacement preserves plugin-data. The --force flag here is the stock replacement/caution mechanism, not a dangerous-verdict exception.

`hermes plugins disable agent-fix-lab` stops registration on the next session. `hermes plugins enable agent-fix-lab` re-enables it without needing tool-override permission. `hermes fixlab uninstall-runtime --confirm` removes only the owned environment and marker, retaining evidence. Run it before `hermes plugins remove agent-fix-lab` if environment cleanup is desired; code removal also retains plugin-data. The older standalone environment and private dataset are not touched.

## Validation

The first generated release, 4c219d2689e2fe663e16c7ae42b9fa3953de61bb, was installed from GitHub into isolated profiles on unmodified Hermes. Explicit setup and actual registry dispatch passed: all eight tools, both hooks, bundled skill discovery, four slash subcommands, one failed incident, four total cases including two inconclusive cases, repeat-import zero additions, and reviewed faulty-fail/corrected-pass comparison. Runtime removal, disable/enable and code removal preserved the evidence database. The synthetic fixture includes malformed output; the harness was corrected to assert its preservation, not drop it.

.github/workflows/native-plugin.yml now reproduces release generation twice, scans with the stock host, publishes the candidate branch, installs that exact GitHub SHA into a clean home, and verifies native lifecycle and teardown. A pushed candidate is not a certified release until its run succeeds. The ordinary validation workflow retains all standalone tests, builds, three fresh-server browser workflows and bundle checks. Read the final Actions result before selecting a release SHA.
