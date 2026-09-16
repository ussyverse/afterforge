# Jev / TypeSafe: optional shadow triage experiment

Status: implementation started; NO live API calls, accuracy, calibration, speed or cost measurements. Waiting for operator API access. Branch only; no native manifest/hook changes, no change to the certified catalog pin.

## Research and fit

Primary sources consulted:
- https://typesafe.ai/blog/introducing-system-one-models-and-jev (September 15, 2026)
- https://docs.typesafe.ai/introduction
- https://docs.typesafe.ai/api

Discovery used WebXNG/SearXNG, followed by direct official docs. Jev evaluates state against independent typed questions: Choice (label/probabilities/confidence), Noul (probability of a statement), Score (rubric score/distribution). It does not generate repair code or prose. Questions in one call do not consume each other's answers; any dependency must be composed in our code or a subsequent request.

Potential Afterforge benefits:
1. Identify likely verification gaps or explicit corrections missed by brittle textual rules.
2. Separate ordinary instructions from genuine corrective feedback, reducing review noise.
3. Surface uncertainty and missing evidence before spending effort on regression drafting.
4. Later: choose among existing candidate case IDs for duplicate review; never invent links.

Do NOT replace deterministic process exit evidence, test execution, human case acceptance or deployment approval. A type-correct classification can still be factually wrong. Vendor claims about calibration, cost and latency are hypotheses to evaluate on Afterforge, not established results. The model is not a substitute for our reviewed intervention loop.

## Implemented boundary

`python -m agent_fix_lab.jev summary.txt` previews the exact documented request and approval hash WITHOUT NETWORK. Input must be an operator-written summary, <=12000 UTF-8 bytes. The module does not read Hermes history, attach case files, import a database or run from hooks. Preview output contains the summary; treat terminal logs and redirected files as sensitive.

After reviewing the outgoing text, with explicit consent and credentials provided securely:

```sh
export TYPESAFE_API_KEY=...  # configure privately, not in git or shell history
python -m agent_fix_lab.jev summary.txt
python -m agent_fix_lab.jev summary.txt --send --approve-sha256 HASH_FROM_PREVIEW
```

The approval hash binds the model, summary and questions actually sent. It prevents accidental payload drift; it is not an authorization system against an agent/operator capable of generating hashes. No automatic redaction or privacy guarantee is asserted. Do not submit raw traces, credentials or personal messages. Confirm TypeSafe's retention/training terms before transmitting non-synthetic data.

The adapter posts only to https://api.typesafe.ai/v1/systemone with model jev-latest. No arbitrary base URL, redirects, proxies or automatic retries. A failed call exits nonzero and never applies a decision. Rate limiting requires an explicit later retry; this deliberately differs from the SDK's automatic-backoff policy to avoid unattended spending during initial access tests. Responses are bounded and validated for typed answers, finite probabilities, full distributions and chosen-label consistency. Returned/requested models and an input hash are retained in the emitted advisory record; input text/key are not copied to that record. jev-latest may move: record returned model and revalidate over time.

The first rubric asks three independent questions: failure kind, explicit evidence supporting completion, and explicit user correction. All output is shadow-only, no authority and always requires human review. The provisional 0.8 confidence review bucket is NOT a calibrated automation threshold. No cases, regressions, acceptance states, verification results or deployments are mutated. Uses Python standard library; no new dependency or manifest capability needed at this stage.

## Tests and access-day acceptance plan

`uv run pytest tests/test_jev.py -q`

Synthetic fixtures explicitly test contracts, not actual Jev behavior. Tests cover preview/no-network, payload-bound approval, missing key, valid transport shape, malformed distributions, NaN/booleans, incorrect winners and HTTP errors without retry. Current narrow tests do not prove malicious-text resistance.

When access arrives:
1. Send a consented synthetic smoke payload; verify exact live response schema and reported model. Never silently loosen validation to fit malformed replies.
2. Create human-labeled, redacted examples from real failures and benign counterexamples. Split by source/session to prevent train/evaluation leakage. Keep private fixtures out of the public repo.
3. Compare existing deterministic triage against Jev shadow suggestions. Measure per-class precision/recall, correction false-positive rate, abstention/coverage, and calibration (Brier score/reliability bins); report sample sizes and uncertainty.
4. Measure p50/p95 latency, reported usage and actual billing separately. Include network/rate-limit failures and model-version changes.
5. Test prompt-injection summaries, ambiguous completion claims, canceled tools, nonzero exits and new instructions that quote prior mistakes.
6. Only then propose optional case-store/UI integration with provenance, manual review, export consent and kill switch. No automatic acceptance/promotion. Any native plugin network integration requires new privacy/capability documentation and a separately reviewed release/catalog pin.
