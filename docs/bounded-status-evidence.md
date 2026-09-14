# Experimental bounded status-evidence procedure v1

This is a **default-off, explicitly preloaded skill**, separate from the original
one-sentence reminder and the existing native `pre_verify` policy. It is research
on a scoped retrieval workflow, not durable learning or a stable-release change.

The procedure lives in `src/agent_fix_lab/status_evidence_skill.md`. The executable
launcher is `python -m agent_fix_lab.status_evidence`. Installing Afterforge does
not install or enable this skill in any Hermes profile. It is not registered with
the native plugin or the existing policy lifecycle.

## Why this delivery mechanism

The [Hermes hook documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks/)
describes `pre_verify` as a bounded edited-code verification gate. The current
Afterforge directive also requires a coding task with changed paths. That is not
a suitable before-first-retrieval delivery point for a read-only status question.
No efficacy claim for that hook follows from these experiments.

The [Hermes skill documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/)
and `hermes chat --help` describe skills and explicit `--skills` preloading. The
inspected host's CLI joins preload completion before constructing its agent and
snapshots the resulting system prompt. The launcher uses that actual mechanism,
not a substitute prefix on the user question. `scripts/status_skill_probe.py`
exercises the real loader and CLI assembly without inference, including the host's
own disabled-skill setting. **The attempted evaluation observer was insufficient:**
it looked for the rendered body in the retained session system prompt, but this
host keeps CLI skill guidance in `ephemeral_system_prompt`, appended only at
API-call time and omitted from the stored base prompt. The study stopped after
two attempts under its frozen delivery gate. Loader/CLI assembly success is not
request-time attestation. See the [stopped-cycle findings](bounded-status-findings.md).
Do not interpret the missing stored body as proof the model did not receive it.
Neither null storage nor a missing marker proves baseline non-delivery. The
low-level `delivery_evidence` helper is not an authoritative certification API;
it requires an actual effective prompt, which this observer did not retain.

## Scope and evidence contracts

Before retrieval, the skill asks the agent to identify the project, version/job,
environment, and requested time; unspecified values remain unknown. It follows
README/handoff/workspace-map pointers to substantive external records within the
approved workspace, checks relevant reversals up to the time boundary, and does
not interpret incomplete search coverage as absence.

The procedure budgets eight individual search/read operations, with at most two
additional operations for a specific coverage gap or contradiction. Each call in
a batch counts; terminal bulk reads are not a workaround. Initial reads are
limited to 100 lines, searches to 20 results with one context line. On unresolved
coverage it stops, distinguishes established facts from unknown outcomes, and
recommends obtaining the specific missing job/result/environment evidence. It
must not exhaust unrelated archives. These are **behavioral soft limits**, not
hard tool interception. The launcher separately enforces 12 turns and a
240-second child-process cap.

Dispatch is not completion. Rollback not performed is not rollback unnecessary.
Approval, version, environment, and chronology claims must stay within the viewed
evidence. Unrelated rewriting, formatting, or local-value questions should not
trigger extra status retrieval. Task classification is an instruction followed by
the model, not an authenticated intent classifier.

## Explicit isolated-home lifecycle

Use an installed experimental build or `uv run python` from this feature checkout.
The following placeholders are operator-chosen canonical absolute directories;
do not substitute a live Hermes home. The home must not exist yet. Its parent
must exist, and it must be disjoint from the workspace. The project is an existing
subdirectory of the workspace (or the workspace itself).

```sh
python -m agent_fix_lab.status_evidence init \
  --home /tmp/status-trial-home \
  --workspace /tmp/status-trial-workspace \
  --project /tmp/status-trial-workspace/checkout
python -m agent_fix_lab.status_evidence inspect --home /tmp/status-trial-home
```

Initialization creates a new owner-only home, a disabled manifest, a private
append-only lifecycle ledger, and conservative single-query configuration. It
refuses existing homes rather than modifying another profile. It does **not** copy
credentials; configure supported Hermes authentication separately in this isolated
home if a user-reviewed trial is authorized. Never put credentials in this repo.

Review the skill text and the manifest's project/workspace/version/hash. Enabling
requires its exact `approval_digest`, binding those values and the rendered body:

```sh
python -m agent_fix_lab.status_evidence enable \
  --home /tmp/status-trial-home --approve-digest REVIEWED_DIGEST
python -m agent_fix_lab.status_evidence run \
  --home /tmp/status-trial-home --query-file /tmp/status-question.txt
python -m agent_fix_lab.status_evidence disable --home /tmp/status-trial-home
python -m agent_fix_lab.status_evidence remove --home /tmp/status-trial-home
```

The run command uses Luna low, `openai-codex`, `terminal,file`, a fresh single-query
session, and the approved project cwd. It does not accept resume or arbitrary
model/tool flags. When enabled it adds `--skills afterforge-status-evidence-v1`.
When disabled or removed it omits the flag and refuses a stray discoverable skill.
Removal is terminal for this manifest; use a new home for a new installation.
An interrupted process does not silently promote a policy.

Disable/removal withdraw only the unchanged owned skill file; they preserve
credentials, session evidence, unrelated files, and historical approvals. Changed
or symlinked skill files and unowned children cause refusal rather than deletion.
A changed procedure/scope cannot use an old approval. A lock serializes launches
and lifecycle operations; disabling waits for the bounded in-flight run and does
not erase an already-started session's prompt. Do not bypass the launcher with
an ordinary interactive session in an enabled experimental home: the skill is
then discoverable for the lifetime of that enabled home. This is why trial homes
are dedicated and temporary, not live profiles.

The scope is a launch/cwd check plus model instructions, **not an OS sandbox**.
Same-user processes, credentials, and host code are trusted. The implementation is
not a hostile-filesystem/race security boundary. These limits must not be confused
with enforcement of arbitrary read-only or network restrictions.

## Frozen evaluation and checks

[The frozen protocol](experiments/status-evidence-v1-protocol.json) defines the
new intervention identity, randomized 24-attempt Luna schedule, six scenario
categories, authorship/grading limitations, budgets, stop conditions, and decision
gates. Prior reports and the original reminder remain unchanged. Raw fixtures,
answers, session prompts, and trace-level grades are retained privately; public
findings contain sanitized aggregate and category/case-label costs only.

`tests/test_status_evidence.py` covers default-off behavior, exact approval,
scoping, symlinks, changed procedure/content, withdrawal with evidence retention,
call/context accounting, and exact-body delivery checks. These deterministic
contracts are not substitutes for behavioral results. The real-host probe is also
run in application CI against a pinned Hermes checkout without credentials or
model calls; it does not run native candidate publication or stable promotion.
