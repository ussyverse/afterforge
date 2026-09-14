# Bounded status evidence: request-boundary revision and remaining-budget results

## Decision

**Insufficient demonstrated benefit. Do not activate or proceed to a scoped trial.**

Request-time measurement now works through the actual configured Codex client
boundary and was proven offline before inference. The unchanged procedure then
completed the 22 previously unexecuted attempts with verified delivery. However,
baseline and candidate were equally correct, acquired the same required substantive
evidence, and met the same content/uncertainty/next-step rubric. There is no
demonstrated accuracy, retrieval, or strict-content benefit in this sample.

Candidate tool-returned context was much smaller. That positive cost dimension
is retained, not discarded. It was accompanied by more retrieval operations, more
elapsed time, more total input including cache, and four failed frozen cost gates.
Smaller tool returns alone do not meet the predeclared paired-usefulness rule.

This conclusion is about this default-off procedure and these coordinator-authored
synthetic scenarios, not global model ability, durable learning, or the efficacy of
the shipped native `pre_verify` hook.

## Provenance and unchanged boundaries

The source parent is `b110285311a4c7851d4186acd6ff8378d872b448` on
`experiment/bounded-status-evidence-v1`. The
[original stopped study](bounded-status-findings.md) remains unchanged: two
completed delivery-unverified attempts, 22 not run under its v1 protocol. Those
two answers were neither retrospectively attested nor pooled into these results.

The new [v2 evaluation protocol](experiments/status-evidence-v2-protocol.json) is an
explicitly linked **instrumentation revision**, not a new behavioral procedure or
independent holdout. Its SHA-256 is
`d4f90a973f2c0e45ed39ec6f6a3d726d434a598dfc5f1885b2becc11f50e5d7a`.

The v1 procedure wording, behavioral scope, launcher, and approval lifecycle are
unchanged. Procedure SHA-256:
`7aecb292216df87c0ac41419af5a0c5dbd6f3f6ac00473e82908fe8e8a2a73bc`.

The revision inherited exactly the prior schedule suffix, questions, fixture
bytes, per-case expected content, grading rules, time/turn caps, search budgets,
cost thresholds, and stop conditions. It used 22 fresh isolated execution homes,
not the old prepared homes. There were no inference retries, replacements, prompt
changes, Astra comparisons, or post-result threshold changes.

Eleven paired scenarios remained: two each valid completion, wrong environment,
missing result, later rollback and unrelated task, but only one wrong-version
scenario. Nine pairs ask project-status questions. Five pairs require explicit
uncertainty and a missing-record next step. The inherited rubric still refers to
the original six uncertainty cases; its case-level applicability now covers five
because the first wrong-version pair belongs to the stopped study.

The same coordinator authored the original synthetic fixtures and reviewed the new
natural answers and tool traces without blinding. These are not independent
historical samples or production validation. One baseline/candidate pair per
scenario is not a variance estimate, and provider-internal reasoning is not
independently attested. Requested/recorded model: `gpt-5.6-luna`, `openai-codex`, low
reasoning. The inspected host HEAD, actual source-manifest hash, SDK source-manifest
hash, observer/runner identities and offline proof were frozen before inference.
The host source identity and installed SDK sources were verified unchanged afterward.

## Delivery is measured separately from behavior

[Observer implementation and offline proof](request-boundary-observation.md)
describe the actual CLI → preload → ephemeral assembly → Codex transformation →
OpenAI SDK serialization → HTTPX client boundary. The observer inspects the complete
approved rendered body/version/digest in the final `instructions` field, before
first task tool execution. It excludes auxiliary/title/scanner activity using task
session/context and exact final query/model identity. It never reconstructs a
request from persisted storage or equates a loaded-skill flag with delivery.

| First task-request outcome | Baseline | Candidate |
| --- | ---: | ---: |
| Verified absent | 11 | 0 |
| Verified present | 0 | 11 |
| Mismatch | 0 | 0 |
| Unknown | 0 | 0 |

All 22 attempts exited successfully, preserved fixtures/scope and matched the
request/submission/session/model/host/approved-body evidence. No integrity stop
occurred; zero attempts remain not run in **v2**. First-tool ordering was verified
for all 20 tool-using attempts; the two rewrite attempts correctly used no tools.
Auxiliary events are explicitly non-attesting, not baseline absence evidence.

Seven offline real-CLI/local-stub cases passed before inference: enabled, baseline,
disabled, removed, changed-body, marker-only and missing observer. Guidance was
absent from persisted base storage but present in the outgoing candidate request.
Observer and stub saw identical request hashes. Tampered/missing delivery could
not execute the first tool. No provider credentials or network inference were used
for these tests. The old stored-prompt boolean helper now raises a retirement error,
even for a missing baseline prompt.

The observer retains only private hashes, statuses, lengths and correlation/order
metadata, not observed prompts, headers, credentials or raw requests. This verifies
**instructions submitted through the client request boundary**, not attention,
compliance, provider acceptance, or correctness of a generated answer.

## Behavioral results

| Frozen dimension | Baseline | Candidate |
| --- | ---: | ---: |
| Main task accuracy | 11/11 | 11/11 |
| Project-status accuracy (subset) | 9/9 | 9/9 |
| Required substantive evidence acquired | 10/10 applicable | 10/10 applicable |
| Answers with unsupported material/minor claims | 0/11 | 0/11 |
| Precise uncertainty | 5/5 applicable | 5/5 applicable |
| Specific missing-record next step | 5/5 applicable | 5/5 applicable |
| Scope preserved | 11/11 | 11/11 |
| Strict content pass, cost assessed separately | 11/11 | 11/11 |

The unrelated rewrite needs no evidence; the other unrelated control requires a
local config value. Retrieval credit requires actual substantive result text.
The audit checked all non-heading lines of relevant outcome/coverage/reversal
records in retained tool returns, not merely filenames, path visits or answer
correctness. Broad baseline searches sometimes returned sufficient full snippets
without a separate receipt-file read; those count as substantive acquisition.

Both arms kept wrong-version/environment and missing-execution outcomes unknown,
identified the specific missing target record, respected the requested time boundary
for rollbacks, and avoided converting scheduling approval into release approval or
“rollback not performed” into “rollback unnecessary.” Additional candidate wording
was not credited as a strict-content improvement when baseline already met the
frozen rubric. Unrelated controls performed the same zero and one operations.

## Cost: retain both the reduction and the failures

Every individual `search_files`/`read_file` call counts, including members of a
batch. No terminal calls or hidden multi-read commands occurred. Tool-returned
context includes JSON envelopes and path text, not just document prose; its UTF-8
byte counts equal character counts in this retained sample.

| Aggregate across 11 attempts per arm | Baseline | Candidate | Candidate / baseline |
| --- | ---: | ---: | ---: |
| Individual retrieval operations | 61 | 84 | 1.377 |
| Tool-result characters / UTF-8 bytes | 442,953 | 57,484 | 0.130 |
| Elapsed seconds, including CLI/launcher | 184.317 | 286.284 | 1.553 |
| Noncached input tokens, host-normalized | 174,747 | 132,804 | 0.760 |
| Cache-read input tokens | 143,872 | 255,488 | 1.776 |
| Total input including cache | 318,619 | 388,292 | 1.219 |
| Output tokens | 5,790 | 8,775 | 1.516 |
| Reasoning tokens, reported separately | 399 | 1,227 | 3.075 |
| First-request instruction characters | 98,115 | 156,661 | 1.597 |
| Injected approved-body characters | 0 | 50,353 | N/A |

There were no cache-write tokens. Hermes normalizes `input_tokens` to noncached
input; labeling that field alone as total model context would be misleading.
Reasoning tokens are not added again to output-token totals. Instruction characters
are first-request measurements, while token totals accumulate across task-session
calls. Token/cache differences are not dollar billing evidence. Elapsed time includes
startup and observer overhead in both arms and is not a controlled latency benchmark.

Failed frozen gates:

- Aggregate operations: 1.377 exceeds the 1.25 maximum.
- Candidate per-case operations: `version-b` used 11, exceeding the 10 maximum
  (baseline used 2). The costly answer was retained and did not stop the queue.
- Missing/rollback paired delta: `rollback-b` used 10 versus 7, a +3 increase
  exceeding the +2 maximum.
- Aggregate elapsed time: 1.553 exceeds the 1.5 maximum.

Passed cost gates: aggregate tool context, every candidate's 20,000-character
per-case ceiling, no individual unrelated-archive reads, and unrelated-task search
and operation preservation. The candidate still omitted the 20-result limit on
three initial searches in one missing-result case, leaving the tool's default 50;
actual returned context remains counted. A candidate also read an unnecessary
settings file during a status case. These residual procedure-adherence costs are
preserved rather than hidden by the large context reduction.

## Verification and withdrawal

Local validation passed: 305 tests, no skips, lint, formatting, source/wheel build,
and both real-host delivery probes. The CI delivery job includes the full offline
request-boundary test and pins the observed HTTPX/OpenAI versions alongside the
Hermes commit. Exact-commit workflow status is separate engineering evidence, not
a behavioral effectiveness score.

Frozen protocol/order/fixture/question/implementation checks passed. Private grades
bind the exact reviewed result and trace hashes. Original study artifacts, original
findings/reminder, procedure wording, native plugin and release metadata were checked
unchanged. All experimental skills were removed from the 22 new homes after the
evaluation, with private evidence and credentials verified intact. Nothing was
enabled in the live profile or promoted to main/stable.

Retain the measurement repair and negative evaluation as evidence. The predeclared
rule requires a paired retrieval or strict-content gain in addition to passing
cost/safety gates. Neither requirement is satisfied here. The final recommendation
is **insufficient demonstrated benefit**, not another prompt-tuning cycle or trial.
