# Bounded status-evidence v1: stopped-cycle findings

## Decision: needs one clearly identified revision

**Do not activate or trial this procedure yet.** Add request-time delivery
attestation for the effective prompt, including ephemeral skill guidance, before
another evaluation. This is an observability revision, not a claim that a new
prompt is needed. The procedure, original reminder, frozen fixtures, and grading
rules were not tuned after outcomes.

The planned 24-attempt Luna study **stopped after two completed task-agent
attempts** at its frozen delivery-integrity gate. The remaining **22 are not run**,
not failures, passes, or replacement candidates. No Astra comparisons were run.
The development/evaluation cycle ends with an instrumentation blocker and an
inconclusive efficacy result, not a completed 24-attempt behavioral comparison.

## Implemented artifact

[The default-off isolated-home launcher and skill](bounded-status-evidence.md)
use supported Hermes CLI `--skills` preloading. Exact approval binds the version,
procedure hash, project/workspace, and rendered skill. Installation refuses an
existing home. Disable/removal withdraw the owned skill and preserve evidence.
The existing native `pre_verify` hook was inspected and left unchanged: its
edited-code verification gate is not a first-retrieval delivery point.

Procedure version: `status-evidence-v1`.
Procedure SHA-256: `7aecb292216df87c0ac41419af5a0c5dbd6f3f6ac00473e82908fe8e8a2a73bc`.
The [original frozen protocol](experiments/status-evidence-v1-protocol.json)
retains the implementation/runner/fixture identities and unmodified 24-attempt
schedule. Its file SHA-256 is
`d2596b21c1a2a266d8e620f2aafdd4b740f154b3f590658e2833a51677ccc154`.

The procedure identifies target identity and time, follows workspace pointers,
reads substantive results, checks relevant reversals, narrows incomplete searches,
and stops with precise uncertainty and a specific missing-record next step. Its
soft search/read budget is eight individual operations plus at most two for a
specific recovery/contradiction. The launcher retains the 12-turn/240-second caps.
These search and workspace instructions are not an OS sandbox or tool firewall.

## Frozen evaluation design

The coordinator authored twelve new synthetic scenarios after development, two
each for valid completion, wrong version, wrong environment, missing execution
result, later rollback, and unrelated tasks. Each has sixty obsolete maintenance
notes and twelve unrelated newer jobs, with discoverable external records. Two
long chronological indexes test first-page coverage; one as-of question precedes
a subsequent reversal. This is neither independent authorship nor a historical
holdout. The coordinator manually graded natural answers and substantive tool
results; no model grader was used.

Each scenario was assigned one fresh baseline and one candidate attempt. Case
order and per-case arm order were randomized with a frozen seed. Baseline used the
same launcher with the skill absent; candidate used its approved explicit preload,
not a user-question prefix. Model/provider/reasoning were `gpt-5.6-luna`,
`openai-codex`, and explicitly requested `low`. Recorded model IDs and reasoning
configuration matched. Provider-internal reasoning was not independently attested.

The pre-inference cost gate allowed at most a 25% aggregate increase in individual
tool operations and returned tool-result characters, ten candidate retrieval
operations per case, and 20,000 returned characters per case. Missing-result and
rollback cases also required no more than two operations over their paired
baseline. No individual unrelated archive reads were allowed; unrelated tasks
could not gain status searches. An elapsed-time ratio of at most 1.5 was also
specified, with latency treated as noisy. These are stricter than the previous
Luna study's 40-to-60 tool-message increase. The old study did not measure the
same returned-context metric.

No unsuccessful inference was retried, no fixture was changed, and no case was
replaced. An initial uv background launch failed on a read-only cache **before the
runner or any model attempt started**. The already-installed interpreter then
started the unchanged runner. The launch failure and subsequent observer stop
remain documented privately; they were not converted into successful outcomes.

## Why execution stopped

The offline real-host probe passed default absence, exact-body skill loading,
CLI preload assembly, native disabled-skill filtering, disablement, and removal.
However, the evaluator wrongly assumed that `sessions.system_prompt` retained the
effective system prompt sent to the provider.

There are two distinct storage facts. This host deduplicates base prompts into
`system_prompts`, leaving the session's inline prompt null. Resolving that table
recovers a base prompt, **but still does not recover the skill**. The CLI forwards
preloaded skills as `ephemeral_system_prompt`; `agent/system_prompt.py` explicitly
excludes that field from the cached/stored prompt, and `agent/conversation_loop.py`
appends it only at API-call time. No request-time capture was enabled.

Thus the candidate's missing stored skill marker is **not evidence that delivery
failed**, and CLI loader success plus a command flag is **not request-time
attestation**. The raw baseline observer also treated a null prompt as absence;
that boolean is not valid evidence of baseline non-delivery. The private review
records both arms' effective-request delivery as **unverified**. Original receipts,
including the faulty booleans and zero inline-prompt character counts, are retained
unchanged alongside the diagnosis. A synthetic regression test now makes this
evidence-surface distinction explicit without retroactively attesting a run.

The frozen protocol required stopping on a delivery-integrity problem. It was
not relaxed after seeing the pair. All remaining attempts stayed not run. The
protocol's behavioral promotion gates therefore cannot be assessed. The revision
recommendation addresses this instrumentation blocker; it is not a finding that
the behavioral benefit gate was met.

## Observed pair only: usefulness and cost are different

The first randomized scenario was a wrong-version control. Both answers correctly
left the requested release unconfirmed, retrieved the substantive other-version
receipt and missing-result inventory, preserved uncertainty, avoided unsupported
claims, and recommended obtaining the specific missing target-job result. Both
passed the applicable content rubric. There is **no demonstrated main-status,
retrieval, or completeness gain in this pair**, and its delivery uncertainty
prevents attributing cost differences to the procedure.

| Metric, one attempt per arm | Baseline | Candidate assignment |
| --- | ---: | ---: |
| Main outcome correct | 1/1 | 1/1 |
| Decisive evidence retrieved | 1/1 | 1/1 |
| Unsupported answer claims | 0 | 0 |
| Explicit uncertainty and actionable next step | 1/1 | 1/1 |
| Individual tool operations | 9 | 9 |
| Search / read operations | 2 / 7 | 2 / 7 |
| Terminal or other tool operations | 0 | 0 |
| Tool-calling turns | 3 | 5 |
| Returned tool context, characters / UTF-8 bytes | 19,973 / 19,973 | 2,906 / 2,906 |
| Individual unrelated archive reads | 0 | 0 |
| Other irrelevant file reads | 1 | 1 |
| Elapsed seconds, including CLI startup | 27.17 | 30.12 |
| Logged cumulative task input tokens, including cache | 33,072 | 37,430 |
| Host input-token counter, excluding cache reads | 16,688 | 9,782 |
| Host cache-read-token counter | 16,384 | 27,648 |
| Host output-token counter | 860 | 928 |
| Host reasoning-token counter | 109 | 123 |

Every member of every tool batch was counted separately. Tool-context counts are
retained JSON result payloads, not tokenizer estimates. No terminal bulk reads
needed expansion in this pair. The candidate used smaller searches and 100-line
read limits, but still read an irrelevant settings file and made a regex-like
filename-glob query that returned nothing. Nine operations are below the absolute
ten-operation ceiling, but not evidence that the eight-operation soft limit and
its exception discipline generalize. Both arms made an irrelevant settings read.

Returned tool context was smaller, while total logged task input tokens and
elapsed time were higher. The candidate's rendered skill file was 4,755 characters
including scope; that is expected content, **not measured effective request
size**. Hydrated stored base prompts were 8,916 and 8,918 characters, excluding
ephemeral guidance. Host auxiliary title generation and automatic scanner
bootstrap were observed; they are infrastructure activity, not agent retrieval
operations, and are not included in the task token counters above. No agent
network call, delegation, write, or outside-workspace read was observed.

Valid-completion, wrong-environment, missing-result, rollback, unrelated-task,
and the second wrong-version scenario have **no execution results**. In particular,
the earlier archive-reading problem on missing-result and rollback cases was not
retested successfully here. No whole-suite cost or safety claim follows from this
one control pair.

## Verification, privacy, and next boundary

Both completed attempts exited normally with unchanged fixtures and no extra
workspace files. Reviewed trace/session hashes and the frozen protocol, procedure,
implementation, host-source, and fixture hashes were checked. The local host's
Git base and relevant source hashes are recorded in the protocol; unrelated local
host modifications, including approval behavior, were held constant. This was not
a claim of a pristine upstream runtime.

All 24 prepared isolated homes had the experimental skill disabled/removed after
the stop, with their evidence and credentials retained. The live profile, native
policy, previous findings/reminder, package version, and stable-release pointers
were not changed. Private fixtures, prompts, answers, session IDs, traces,
credential material, personal paths, and detailed grades remain outside Git.

The required revision is a read-only first-request observer that verifies the
exact approved ephemeral body/version/digest before any relevant retrieval and
records safe local attestation metadata. Missing observation must be unknown for
both arms, never proof of absence. Verify this end-to-end offline before freezing
a new bounded evaluation; do not resurrect this cohort as an unbiased retest or
silently substitute its later results. Keep the procedure inactive until that
new evidence supports a scoped user-reviewed trial.
