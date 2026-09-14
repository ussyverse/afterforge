# Historical discovery: a current search-tool defect

## Decision and scope

The bounded-status intervention is **closed: insufficient demonstrated benefit**.
It remains inactive. Its procedure, original reminder, stopped study, completed
continuation, review decisions and evidence are preserved. The 24 original and
22 continuation evaluation homes have disabled/removed manifests and no procedure
skill file. No additional behavioral attempts or prompt tuning were performed.
See the unchanged [continuation findings](request-boundary-findings.md).

This follow-on selects a concrete, currently reproducible Hermes search-tool
argument-boundary defect. A five-line repair is supplied as a patch and verified
against an isolated copy of the current implementation. **It is not installed
in the live host**, an active profile, main, or a stable release.

## Discovery coverage

The existing private 30/90-day expansion was already complete. Rather than
re-importing it, this cycle reused its snapshots, canonical source identities,
`hermes.sqlite.v4` observation identity, dependency-group split and repaired
notification filter. Snapshots were opened with SQLite `mode=ro&immutable=1`;
nonempty WAL files would have stopped the reader. Source bytes were hashed before
and after. No live histories, credentials or held-out message bodies were read.

The frozen cutoff is **2026-09-14 02:19:41 UTC**. The 30-day window begins
2026-08-15; the 90-day window begins 2026-06-16 at the same time of day. These
are rolling windows, not a claim of continuous archival coverage or coverage
through the time this report was published.

| Measurement | Cumulative 30 days | Cumulative 90 days |
|---|---:|---:|
| Retained all-role rows in the windows, including held-out metadata counts | 53,496 | 330,397 |
| Development tool rows scanned | 29,147 | 153,602 |
| Deduplicated development tool observations | 28,282 | 152,560 |
| Development user rows passed through the existing notification filter | 1,774 | 8,843 |
| Oversized tool rows limited to the 65,536-character prefix | 36 | 1,213 |
| Recognized whole notifications excluded from correction speech | 244 | 244 |
| Uncertain notification attribution, retained as uncertain | 324 | 1,689 |
| Remaining marker hits, **not confirmed corrections or behavioral failures** | 178 | 2,284 |

For transparency, the incremental older-than-seven-day 30-day scan read 11,795
tool and 870 user rows; the additional 30-to-90-day scan read 124,455 tool and
7,069 user rows. The existing recent seven-day slice was re-audited, not treated
as new independent evidence. No historical tool commands were replayed.

Fourteen inventoried history entries reduce, under the existing alias/empty-source
handling, to twelve nonempty canonical sources. The private mapping is unchanged.
Public labels below do not disclose home paths, account names or session IDs.
"Recorded days" counts rolling 24-hour bins containing at least one retained
message; an empty bin can mean inactivity or unavailable history, not necessarily
an ingestion failure.

| Source | First retained date | Last retained date | Recorded days within 30 / 90 | All-role rows within 30 / 90 |
|---|---|---|---|---|
| S01 | 2026-09-07 | 2026-09-12 | 5 / 5 | 16,778 / 16,778 |
| S02 | 2026-08-19 | 2026-08-20 | 1 / 1 | 16 / 16 |
| S03 | 2026-08-20 | 2026-08-20 | 1 / 1 | 8 / 8 |
| S04 | 2026-08-20 | 2026-08-25 | 3 / 3 | 55 / 55 |
| S05 | 2026-08-19 | 2026-08-25 | 4 / 4 | 151 / 151 |
| S06 | 2026-08-19 | 2026-09-07 | 8 / 8 | 4,553 / 4,553 |
| S07 | 2026-09-07 | 2026-09-08 | 1 / 1 | 222 / 222 |
| S08 | 2026-08-19 | 2026-08-25 | 6 / 6 | 627 / 627 |
| S09 | 2026-08-19 | 2026-08-20 | 2 / 2 | 483 / 483 |
| S10 | 2026-08-20 | 2026-09-07 | 8 / 8 | 5,740 / 5,740 |
| S11 | 2026-09-08 | 2026-09-14 | 6 / 6 | 8,590 / 8,590 |
| S12 | 2026-04-01 | 2026-09-12 | 16 / 76 | 16,273 / 293,174 |

Only S12 supplies history older than 30 days. Its pre-90-day bodies were not read.
S11 retains 78 rows after the fixed cutoff; their bodies were excluded. There
were no null message timestamps in these source metadata inventories. S04 has
no development tool rows, so its retained rows are not tool-discovery coverage.
The global preserved metadata split has 2,727 development and 594 held-out
linked-session groups; those totals include retained metadata outside the two
windows and are not the number of reviewed independent trials.

Other gaps: nonstandard/uninventoried histories, deleted records, missing tool
names in older imported records, capped outputs, unrecognized notification
formats and unresolved cross-session relationships. Reading a bounded prefix
never proves that a failure or correction was absent from the omitted suffix.
This is deterministic diagnostic discovery plus targeted coordinator
review, not exhaustive semantic grading of every interaction.

## Ranked shortlist, at most five groups

Priority is qualitative: a presently reproduced, narrow and independently
checkable defect outranks a larger but heterogeneous historical bucket. Counts
are deduplicated diagnostic observations, **not adjudicated agent-failure rates**.
Sessions are also grouped by parent/delegation lineage and by the preserved
broader dependency links. Even different linked groups are not guaranteed
statistically independent.

| Priority / family | Observations / sessions / lineages / linked groups | Impact and current relevance | Attribution, action and reproducibility |
|---|---|---|---|
| 1. Leading-hyphen search patterns interpreted as options | 4 / 4 / 4 / 4 | Valid searches fail; two recent-seven-day and two additional-30-day observations. Current implementation affected. | **Confirmed tool defect.** All four complete error records were linked to their actual search arguments. Reproduced through the current tool before repair design. Fix the command argument boundary; selected. |
| 2. Invalid regex inputs | 8 / 6 / 6 / 6 | Repeated search interruptions, all within 30 days; generally recoverable. | Input-contract diagnostic, not proof the engine is defective. Current invalid-regex control correctly rejects `(`. Caller intent/behavior is not fully adjudicated; validate or escape the intended input rather than suppress errors. Not selected for a prompt intervention. |
| 3. Patch target mismatch | 61 / 51 / 45 / 45 | Blocks edits; eight observations in the additional-30-day slice and 53 older. | Safeguard/caller/state diagnostic. Eight explicitly name the patch tool; 53 lack tool-name attribution. Re-reading current content is a plausible action, but no single current implementation fault was established or repaired here. |
| 4. Missing paths | 234 / 189 / 132 / 122 | Frequently blocks work, but strongly archive-weighted and heterogeneous. | Path/environment/caller diagnostic, not one proven tool defect. Only 57 have an explicit search/terminal name; 177 lack it. Establish the expected cwd and file existence before deciding whether an adapter or caller failed. Current causal reproduction not established. |
| 5. Transport unavailable | 29 / 22 / 18 / 11 | Can make tools unusable; dependent sessions substantially inflate raw frequency. | Infrastructure/transport diagnostic, not an answer-quality failure. Eight explicitly name terminal/process; 21 lack a tool name. Isolate a transport contract and health outcome before repair. No production service was changed or probed to reproduce it in this cycle. |

Permission/environment and argument-contract diagnostic buckets remain private
and unranked; neither was promoted into another repair. The shortlist does not
turn tool errors, expected safeguards, intentional negative tests or correction
marker hits into established agent behavior failures. The selected four events
are valid regex inputs rejected by the tool's option parser, not examples of an
agent refusing to follow guidance.

## Baseline before repair

The current Hermes source identity is
`277268d83ff2204de9646f0b1e376e73ac0a5d20`; the affected tracked file had no local
diff. Its SHA-256 is
`f78960962d844315019e4f835f5116f6bbdaa41ff30d8b1e52901f521bbfb0b1`.

A newly authored, private synthetic text file contained `--example-option`.
The actual current `search_files` tool returned:

```text
Search failed: rg: unrecognized flag --example-option
```

Before changing the implementation, the executable minimal regression then
failed against a byte-identical isolated source copy, while four control tests
passed. The failure was the wrong search result, not a missing dependency,
provider error, timeout or test collection problem. No historical command or
private project content was needed to reproduce it.

## Targeted repair and verification

[The patch](../patches/hermes-search-option-boundary.patch) changes five lines
in `tools/file_operations.py`: the ripgrep and grep builders, plus the three
existing zero-match probe commands. Each now passes the regex as `-e PATTERN`
and places `--` before the path. Shell quoting alone did not stop option parsing.
Regex semantics, glob filtering, safety checks and output modes are unchanged.
The repaired source SHA-256 is
`510bb9133dee820ec31d9f159652afddc9dd87ba606668e6e1b59b5bb87c6b83`.

The [regression runner](../scripts/search_option_regression.py) exercises the
actual source module with real Linux bash, ripgrep 14.1.1 and grep. Its local
shell object implements the existing terminal backend's `execute` contract;
search results are not mocked. The wrapper check uses the actual
`file_tools.search_tool`, with only its file-operations factory directed to the
isolated implementation and synthetic local environment.

Final result: **one expected baseline failure plus four passing controls;
all ten repaired tests pass, no skips**. Coverage includes:

- the minimal literal CLI-option search;
- ordinary regex behavior, no-match and invalid-regex controls;
- successful glob, count and files-only controls;
- a separate CSS-variable alternation case, with exact expected lines and all
  three output modes;
- a recognized option, `--version`, required to be searched as data;
- the real grep fallback;
- case-insensitive, hidden-file and fixed-string zero-match probes;
- the actual tool wrapper's serialized match and line number.

The separate cases were authored before the five-line repair. They are synthetic
checks of different manifestations, not independent historical holdouts or a
behavioral efficacy study. Two initial wrapper-test errors assumed the wrong
output representation/line key. Those harness failures were retained privately;
the final assertions use the implementation's documented `matches[].line`
representation. The minimal regression, controls and repair were unchanged.

The [proof driver](../scripts/search_option_probe.py) refuses a source-hash
mismatch, creates a new private directory, copies rather than modifies the host,
checks and applies the public patch there, requires the exact expected red result,
and then requires all ten green tests. It clears inherited credentials from the
child environment and uses isolated homes. It emits receipts and logs locally.
The existing pinned-host CI job also runs this same red/green proof.

```sh
python scripts/search_option_probe.py \
  --host-python /path/to/hermes/python \
  --host-root /path/to/hermes/source \
  --output /new/private/search-option-proof
```

This command never installs the patch into the supplied host. The checked
source file must match the documented baseline. Future or different versions
require a fresh baseline rather than an assertion that this defect still exists.

Final local product validation also passed: 305 tests with no skips, the index
privacy audit, lint, formatting and package build. The ten real-tool checks above
are separate from that product test count. Existing dependency deprecation
warnings did not fail the suite. Exact-commit CI is a separate publication gate,
not a substitute for the historical or current-source evidence.

No prompt delivery is involved, so no request-boundary prompt attestation or
model inference is needed. Windows, remote/container terminal backends and
provider behavior were not tested. This establishes a narrow deterministic tool
repair, not general agent improvement, durable learning or a production rollout.

Aggregate counts, source/patch hashes, preserved-artifact hashes and exact test
names are in [the public evidence record](experiments/history-search-option-evidence.json).
Private snapshots, linked event/call records, correction candidates, scripts,
closure receipts and all test outcomes remain outside public Git.
