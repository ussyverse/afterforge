# Private dataset methodology

The original snapshot, discovery script, source revisions, selected rows and versioned manifest are outside Git in a permission-restricted private directory. They were preserved during continuation. SQLite backup accounts for live WAL state; copying only the main file is never the ingestion strategy.

Cutoff: 1789329060 Unix seconds. Discovery covered 114 sessions and 1,150 eligible pre-cutoff JSON tool records with integer exit codes, explicit errors or success=false. Non-JSON tool records and non-tool candidate selection were excluded from this initial process-label cohort. Current build activity is imported separately as dogfood (100 additional records in the recorded checkpoint).

53 selected real observations: 20 failures and 33 successful process controls. The selection script takes up to 20 temporally spaced records per status/group. The original manifest description erroneously said three recent records; a private companion grouping audit records this erratum without rewriting the original manifest.

## Labels and split

Labels are agent-produced interpretations of observed process facts, not independent human semantic judgments. 53/53 matched those process-derived labels (20/20 failures, 33/33 controls; zero observed classification disagreements). This is a contract/coverage check, not generalization performance. Nearby success does not prove recovery.

Groups were formed before tuning using ancestry, project metadata where available and exact tool-output duplication. Compaction/delegation descendants stay together. The frozen split has 52 development cases and one held-out successful control, with no held-out failures. Any held-out control inspection is disclosed here; it cannot support a failure-detection accuracy claim.

Continuation audit: 105 ancestry components, largest four sessions; exact payload matching joined 54 previously separate components, including 16 matches shorter than 200 characters. Zero sessions had Git project metadata. Generic duplicate outputs can overmerge unrelated work. Conversely, absent project metadata cannot certify that those sessions are independent. The actual delegation key is `_delegate_from`, now supported by the importer. The private grouping audit preserves the original split and records these limitations. We did not weaken lineage or relabel tuned examples to fabricate holdout failures.

## Correction candidates

A separate conservative scan of the frozen source inspected 289 user-role messages. Two candidates were selected and remain pending; 17 correction-marker messages lacked enough nearby imported failure/claim evidence. Role and chronology are observed; intent, causality and identity are not authenticated. Cross-session causal pairing and authenticated-human attribution are explicitly unsupported. Candidates preserve bounded private excerpts and source IDs, distinct from proposed labels and fresh results.

## Regression provenance

Three regressions reduce real historical assumptions: resolved profile home, grouped search-result shape and non-JSON response handling. Their code and fixtures are synthetic reductions. Real historical observations remain separately preserved; original source revisions/configuration could not be reconstructed. Fresh faulty/corrected processes passed red/green checks with 2, 3 and 3 shared assertions respectively. These results validate the reductions, not repair of the original incidents or a new model/prompt.

Public tests, browser fixtures and CI are synthetic and require no private history or API credentials. Browser XSS/race probes inject test-only responses without changing historical records. Public exports omit conversation content and provenance IDs; detailed reports remain private.
