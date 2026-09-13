# Agent Fix Lab — native Hermes distribution

Local-first regression workbench that turns Hermes failures and corrections into reproducible, evidence-backed test cases.

This generated release contains the complete application source and web assets, the thin native adapter, the bundled workflow skill, pinned direct dependencies and lockfile, and legal and security documentation. No application backend is downloaded separately. Explicit setup builds the application from this tree and installs its declared dependencies into an isolated environment. The three Git dependencies are pinned by full commit ID in pyproject.toml. Review them as part of installation trust.

RELEASE.json identifies the exact development-source commit and SHA-256 hashes of every shipped file. The full development repository, tests, fixtures, build workflows and contributor documentation remain at https://github.com/ussyverse/agent-fix-lab . They are not runtime inputs. This repository is private; GitHub access is required.

## Install

Use an immutable release commit, not the development main commit:

```
hermes plugins install ussyverse/agent-fix-lab --ref RELEASE_COMMIT_SHA --enable
hermes fixlab setup
hermes fixlab doctor
```

Keep stock Hermes security scanning enabled. A CAUTION verdict requires operator review and confirmation; a DANGEROUS verdict blocks installation. No scanner patch or configuration exception is required by this distribution. Enabling a plugin executes trusted local Python with your user permissions.

Tools: fixlab_status, fixlab_scan, fixlab_list_cases, fixlab_inspect_case, fixlab_review_case, fixlab_build_regression, fixlab_verify_regression, fixlab_report.

In-session: /fixlab status, scan, failures, review, help. Bundled skill: agent-fix-lab:regression-workflow.

Terminal: hermes fixlab setup, doctor, scan, serve, export CASE_ID, uninstall-runtime --confirm. Serve stays loopback-only. The standalone agent-fix-lab CLI is also installed inside the managed environment.

## Review and privacy

Standalone 0.2.0/native 0.3.0 includes immutable intervention proposals, deterministic recipe-suite evaluation and evidence review. Use the managed standalone CLI's intervention-propose/list/show/evaluate/review commands or visit /interventions on the local web service. Read docs/interventions.md for input contracts and limitations. No activation or deployment approval is implemented; accepting evidence does not change Hermes behavior.

Read docs/privacy.md before importing history, executing a recipe or exporting evidence. Source logs and runtime state remain in the active profile's private plugin-data directory, never in this code tree. Hooks retain bounded identifiers and process metadata, not raw tool arguments or results. Scanning is explicit and uses the existing read-only importer. Inferred corrections remain proposals; no automatic prompt, memory, policy or skill modification occurs.

Regression execution requires an explicitly reviewed recipe. Imported or historical commands are not execution authorization. Reviewed pytest code runs with your permissions: this is NOT an operating-system sandbox. Use a separate VM or OS account for hostile code.

## Update and remove

Install a newly reviewed release SHA through the same pinned command, with the installer's replacement option if necessary, then rerun setup. A source fingerprint detects an outdated environment. Pinned source is not silently advanced by an ordinary update.

Run hermes fixlab uninstall-runtime --confirm before removing plugin code to remove only its owned environment. Evidence is retained. Use hermes plugins disable agent-fix-lab to disable registration and hermes plugins remove agent-fix-lab to remove source. Existing standalone installations and the older editable skill are retained, not migrated or deleted automatically.
