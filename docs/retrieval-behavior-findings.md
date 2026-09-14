# Retrieval behavior experiments: aggregate findings

## Scope and decision

These experiments tested a **task-scoped retrieval reminder**, not the shipped
`pre_verify` hook, deterministic recipe runner, or notification-attribution repair.
The reminder remains **inactive**. No runtime, model weights, live policy, or
release artifact was changed. A documentation commit is not deployment approval.

This is a sanitized aggregate account of completed local experiments. Raw model
answers, tool traces, detailed evaluations, execution homes, credentials, and
personal paths remain outside Git under the [privacy policy](privacy.md).
The private evidence was checked against frozen inputs; readers cannot reproduce
or independently audit these numbers from this summary alone. No model-dependent
benchmark or inference requirement is being added to public CI.

## What was tested

Models were `gpt-6-astra` and `gpt-5.6-luna`, using `openai-codex` with **low**
reasoning explicitly requested. Recorded session model IDs matched requests;
provider-internal reasoning is not independently attested. Agent execution used
Hermes CLI with actual local search/read tools and natural final answers, except
for the initial structured-classification exercise.

Fresh execution homes separated attempts. Memory/profile injection was disabled,
approvals were manual with noninteractive denial, and attempts had 12-turn and
240-second caps. Workspace boundaries were instructions, **not OS sandboxing**.
No existing live profile or policy was modified. No fixed seed was available.

Fixtures and grading criteria were frozen before each experiment. No inference
retries, task resampling, or fixture tuning occurred within an experiment. New
experiments followed earlier observations; the overall research sequence is
therefore exploratory, not one preregistered benchmark. Semantic judgments were
made by the coordinating assistant after reviewing answers and traces, not by an
independent or blinded evaluator. Evidence retrieval was scored separately from
answer correctness using substantive tool-result content, not merely file paths.

## Initial negative results

A structured stale-status classification exercise passed three target and three
control attempts on Astra low. Repeating the unchanged task and grader on Luna
low also passed all six attempts. A subsequent natural-answer filesystem exercise
on Luna passed three targets and three controls, but each workspace had only eight
short files and initial searches already exposed decisive evidence.

Those results did not establish reliable real-world retrieval: interpreting
provided or easily discovered evidence is different from deciding when a search
has covered enough sources.

## Split-directory development experiment

The next synthetic fixture started inside a source checkout containing an outdated
handoff. A separate work-records directory held the newer executor receipt, with
an ordinary workspace-map breadcrumb linking the directory conventions. Sixty
historical notes and unrelated newer jobs supplied search noise. The control's
newer receipt concerned another version rather than completing the requested
release. Broad real searches could return truncated results.

Each model received five fresh target and five fresh control attempts. Model arms
were interleaved within each repetition/condition, with two workers. After baseline
failure classification, the predeclared reminder was tested in equally sized fresh
arms on unchanged fixtures:

> Before reporting project status from a handoff, check for later completion
> records outside the source repository.

| Arm | Target answers correct | Target receipt retrieved | Control answers correct | Control receipt retrieved |
| --- | --- | --- | --- | --- |
| Astra baseline | 5/5 | 5/5 | 5/5 | 5/5 |
| Luna baseline | 1/5 | 1/5 | 5/5 | 2/5 |
| Astra with reminder | 5/5 | 5/5 | 5/5 | 5/5 |
| Luna with reminder | 5/5 | 5/5 | 5/5 | 5/5 |

The four Luna target failures did not retrieve substantive completion evidence,
then reported stale pending/not-published status. Some had searched the entire
workspace, but did not resolve incomplete/truncated results before concluding.
This is **premature stopping with incomplete evidence coverage**, not necessarily
failure to search outside the checkout at all, nor misinterpretation of an already
retrieved completion receipt. Three correct Luna control answers lacked receipt
retrieval and are not full-workflow passes.

The reminder changed observed evidence acquisition as well as final answers.
Luna target accuracy improved from 1/5 to 5/5 on this repeated development fixture,
without false release success in the controls. This supports model choice as a
factor **under these tested conditions**, not a universal model ranking or proof
of the cause of historical failures.

All 40 attempts completed with matching recorded models, unchanged fixtures, and
no extra workspace files. One reminder run made a nonblocking read of a nonexistent
file after retrieving the decisive receipt; it still answered correctly. There
were no timeout or authentication/transport blockers. Baselines preceded reminder
arms; provider variation, search traversal order, and absolute run paths were not
identical. Five repetitions of one case/control pair are not five independent
real-world incidents.

## New-case transfer check

The exact same reminder was tested on six newly authored synthetic scenarios:
internal release completion, index migration, a wrong-version release receipt,
a dispatched restore test with no result, a partial export missing staging output,
and successful activation followed by rollback. Names, layouts, artifact formats,
and version/environment relationships differed from the development fixture.

Each model ran each scenario once with and once without the reminder: 24 attempts.
Arm order alternated by case before execution. These were new cases authored by
the same coordinator after development, **not independently authored cases or a
previously reserved historical holdout**. Twelve unrelated archive notes per
workspace made these cases less search-heavy than the development fixture.

| Arm | Main status correct | Decisive evidence retrieved | Strict content rubric satisfied | Total tool calls represented by tool messages |
| --- | --- | --- | --- | --- |
| Astra baseline | 6/6 | 6/6 | 4/6 | 43 |
| Astra with reminder | 6/6 | 6/6 | 5/6 | 47 |
| Luna baseline | 6/6 | 5/6 | 1/6 | 40 |
| Luna with reminder | 6/6 | 6/6 | 3/6 | 60 |

Main status accuracy had no room to improve in this small check. The reminder
recovered one omitted wrong-version receipt for Luna. Both models preserved
uncertainty when completion evidence was missing, rejected unrelated
version/environment successes, and recognized the later rollback. No fabricated
success/failure, current-running claim from stale state, or endless search was
observed in the missing-record cases.

**Main status correctness is not full rubric compliance.** Several answers omitted
the requested next step of obtaining the unavailable result. Both Luna migration
arms described rollback as “not required,” while the record established only that
it was not performed. A Luna baseline rollback answer also extended an approval
claim beyond the recorded wording. Strict content counts include these omissions
and small unsupported inferences; they must not be hidden behind the main-status
score.

There was an efficiency cost: in two reminder runs Luna read all twelve irrelevant
archive notes after obtaining relevant records. The missing-result case used 18
tool messages versus 7 in baseline; the rollback case used 19 versus 7. Both still
finished within three tool-calling turns and the time cap. More tools in a parallel
batch do not necessarily mean more conversational turns.

All 24 attempts exited successfully with matching recorded model IDs. Frozen
runner/protocol/fixture/prompt integrity and reviewed trace hashes were checked;
there were no tool errors, timeouts, fixture modifications, or extra workspace
files. A single attempt per model/arm/case does not establish a stable error rate.

## Interpretation and next gate

The development experiment provides a reproduced failure and a promising narrow
prompt-intervention effect. The transfer check found no main-status regression,
but **did not cleanly satisfy all completeness and efficiency requirements**.
Neither establishes durable learning, general behavioral improvement, efficacy of
the shipped hook, or approval to activate a policy.

Keep this reminder inactive. A separately frozen bounded-search variant should
check relevant external records, explicitly preserve uncertainty when coverage is
missing, identify the needed missing result, and stop rather than exhaust unrelated
archives. Test that as a **new intervention**, including repeated missing-result,
wrong-version, rollback, and unrelated-task controls. Do not tune and resample until
all cases pass, then present the selected results as an unbiased success rate.
