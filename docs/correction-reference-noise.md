# Correction discovery v4: bounded queue-noise repair

This is a source-branch repair, not a stable release or a live Hermes intervention.

Two synthetic regressions failed on the baseline: a complete reference-only
compaction envelope was selected as a correction, and a repeated observation
created another pending item across scan pages. Both now pass.

Discovery v4 omits only one complete, line-delimited reference-shaped span within
its inspection bound. Original message content is retained whenever a candidate
is created; speech before and after the span is still examined. Nested, partial,
oversized, inline or otherwise unsupported envelopes remain visible. Text shape
is not authenticated origin. This deliberately does not suppress every real-world
compaction summary, nor every next-phase request containing correction words.

New repeated observations with exactly equal source, session, timestamp and full
bounded content reuse the existing queue item. Different sources, sessions,
timestamps or content remain separate. Same-text events sharing all those fields
cannot be distinguished from replay without stronger host provenance. Existing
candidates and review records are never deleted, relabeled or merged retroactively.
Legacy parser versions remain readable; unknown future versions are rejected.

The shared pagination fixture now gives its five intended distinct corrections
separate text while retaining identical timestamps. Its five-item pagination and
operator-review assertions are unchanged. Exact duplicates have dedicated tests.

## Verification

Baseline focused regressions: two failed, four passed after correcting the fixture
cursor to skip its unrelated initial user message.

Final application and packaging suite with Chromium enabled: 274 passed, no skips,
two dependency deprecation warnings. Lint and format checks passed for root plugin,
native adapter, application, tests, scripts, examples and packaging. Wheel and
source distribution builds passed. No package release is implied by build success.

A supplementary private-window scan completed, but the source had accumulated
additional replay rows since the earlier scan, so it is not a frozen before/after
benchmark. Exact-repeat suppression fired; reference-span suppression did not.
This supports the bounded duplicate path, not broad real-history compaction recall.
Private histories and raw scan output are not included in this repository.

## Partial-closeout and stale-validation findings

These behavioral opportunities remain hypotheses, not measured improvements.
A separate candidate procedure should track each requested deliverable, its exact
source/artifact identity, last applicable verification, pending checks and concrete
blockers. Source changes invalidate affected checks. Honest partial progress is not
false success, but an agent should not end an authorized task merely because one
component passed. Stop/changed-scope instructions and real authorization boundaries
must override persistence.

Before any activation, compare a frozen baseline and candidate in isolated Hermes
homes on multi-stage completion, post-test edits, genuine blockers, revoked scope,
and already-completed tasks. Score actual artifact/check identity, premature stops,
unauthorized continuation, repeated work and tool cost. Keep failed/inconclusive
outcomes. Existing negative bounded-status studies remain closed and inactive.
This patch does not install a reminder or claim to improve Hermes task completion.
