# Request-boundary observation v2 (experimental, default-off)

This is an instrumentation revision of the unchanged
[bounded status-evidence v1 procedure](bounded-status-evidence.md), not a new
behavioral prompt or a native `pre_verify` policy. It does not change the live
profile, main branch, stable release, or the old stopped study.

## What is observed

`scripts/status_request_entry.py` starts the actual Hermes CLI in an initialized,
new isolated home. The normal skill preload, agent construction, ephemeral prompt
assembly, Codex provider transformation, and OpenAI SDK serialization all run.
Only this child process is instrumented; no host source is patched on disk.

The observer inspects the already-buffered serialized request at
`httpx.Client._send_single_request`, after HTTPX request hooks and before transport,
for the configured `chatgpt.com/backend-api/codex/responses` path. It validates the
complete `Content-Length`-matched JSON payload, model and exact task-query identity,
and the `instructions` field. It does not reconstruct an expected outgoing request
from a stored prompt or infer delivery from the skill flag/name.

Root-task Codex execution is identified by the actual agent session and a runtime
context variable. Exact user-query hashing in the final payload is an additional
check. Auxiliary title generation, scanner/bootstrap traffic, and other requests
cannot satisfy task delivery. Unexpected task provider paths block rather than
silently applying this Codex-specific observer to another transport.

For the candidate, the complete approved rendered body (including workspace scope)
must occur exactly once, with its v1 version marker, in `instructions`. The observer
checks the approved body's digest before execution and records the body and full
request hashes, not their contents. For baseline, absence is accepted only from a
complete, successfully observed task request. Missing, null, empty, partial,
malformed, or failed observation is never verified absence. Ambiguous secondary
instruction fields are unknown rather than silently ignored.

The explicit outcomes are `verified-present`, `verified-absent`, `mismatch`, and
`unknown`. Mismatch or unknown blocks the isolated child before sending the first
request. A missing observer is independently caught before processing a task
response or executing its first tool. Transport failure downgrades delivery to
unknown and blocks continued execution. A request/submission hash comparison checks
that observation did not mutate the request. A separate first-tool gate orders the
observation before execution, including concurrent and sequential tool dispatch.
For tasks needing no tools, request evidence still applies.

This verifies **instructions submitted through the client request boundary**. It
does not prove model attention/compliance, semantic correctness, server acceptance,
authenticated human approval, or durable learning. HTTPX's internal method and the
host's Codex dispatch functions are explicitly pinned research interfaces, not a
promise of compatibility with arbitrary host versions/providers. Same-user code is
trusted; this is not an OS sandbox.

## Retention and the retired helper

The observer writes owner-only JSONL metadata: attempt label, local request ID,
session hash, model, host-manifest identity, procedure version/hash, approved-body
hash, request/instruction hashes and lengths, outcomes, and monotonic ordering.
It does not retain observed prompts, headers, credentials, or raw requests.
The normal private task traces/answers remain separate from that observer metadata.
Approved procedure text and synthetic query fixtures are private evaluation inputs,
not captured wire requests.

The old `status_evidence_metrics.delivery_evidence` function now raises a clear
retirement error for every input, including null baseline prompts. It no longer
returns its misleading boolean. The new dependency-free assessor exposes explicit
outcomes; callers must supply a real complete observed request, and the entry
script provides the provenance and pre-tool enforcement. Old v1 receipts retain
their original faulty values, with the prior diagnosis alongside them. No old run
is retroactively attested.

## Offline proof, before behavioral inference

`scripts/status_request_probe.py` exercises the real CLI-to-request path with a
local HTTPX `MockTransport`. Only authentication resolution and transport are
substituted with explicitly synthetic test values; no provider credentials or
network inference are used. Socket connection attempts are denied in the probe.
The stub sees the final SDK request in memory and returns a minimal valid Codex SSE
tool call, followed by a minimal final response. The tool actually reads a labeled
synthetic local fixture, after the observer gate.

Cases cover enabled, baseline, disabled, removed, changed-body, marker-only, and
missing-observer delivery. Enabled guidance must appear in the outgoing request
while remaining absent from the persisted base prompt. Baseline/disable/removal
must verify absence; changed/marker-only cases mismatch; missing observation is
unknown and cannot execute the tool. The tests compare observer/transport/submission
hashes and verify that an explicit auxiliary request does not become task evidence.
Raw request bodies are inspected only in memory, not emitted by the probe.

The `status-skill-delivery` CI job runs both the original loader/lifecycle probe
and this full request-boundary probe on the pinned clean Hermes checkout, without
model credentials or inference. Unit tests additionally cover partial/null/malformed
observations, incorrect models/queries, duplicate/changed bodies, secondary
instruction fields, non-mutation and metadata-only output.

## Explicit launch surface

The unchanged `status_evidence` lifecycle remains the delivery authority: initialize
a new home, review/approve its exact scoped procedure, enable only that home, and
withdraw/remove the skill after the run. The observed execution uses the existing
`se.command`/`se.run` flags and time/turn limits with a small executable shim that
forwards them to `status_request_entry.py`. There is no global auto-installation,
background hook registration, or modification of the procedure wording.

The entry accepts `--host-root`, `--observation-config`, then `--` and normal Hermes
CLI arguments. A private observation config identifies the attempt, host manifest,
procedure version/source hash, approved-body file/hash, evidence-file destination,
expected enabled state, model, and query hash. Use only canonical dedicated trial
paths. The offline probe demonstrates configuration without real credentials;
`--offline` and `--missing-observer` are test controls, never valid behavioral runs.
The evidence file must not already exist, preventing silent overwrite of a prior
observation. Credentials are never part of this config or public repository.

## Linked evaluation, not a replacement for the stopped study

[Protocol v2](experiments/status-evidence-v2-protocol.json) carries forward only the
22 never-executed v1 attempts: 11 paired scenarios, two each valid completion,
wrong environment, missing execution result, later rollback, and unrelated task,
but only one wrong-version scenario. Fixtures/questions, relative arm order,
grading rules, search-cost thresholds, time/turn caps and stop conditions are
inherited unchanged. There are no Astra comparisons, retries, replacement cases,
or prompt tuning. Fresh homes and independent receipts distinguish this study.

The same coordinator authored the original synthetic cases and grades the new
answers/traces. This is an instrumentation revision with inherited authorship and
small-sample limitations, not an independent historical holdout. The two original
delivery-unverified attempts stay in the stopped study and are not pooled with
verified results. See the [v2 findings](request-boundary-findings.md) for the actual
completed outcomes and recommendation.
