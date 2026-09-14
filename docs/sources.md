# Afterforge sources and reuse

All component repositories were cloned and inspected outside the application Git tree. Exact revisions:

| Source | Revision | Decision |
| --- | --- | --- |
| [brainstorm](https://github.com/ussyverse/brainstorm) | 46f4c8b9fbaa39340402c19f3eb748d2f8d3e171 | Research only; README, AGENTS, compounded ideas, source-checked combinations and relevant repository index entries. Afterforge (formerly Agent Fix Lab) is the selected product regardless of the general audiovisual ranking. |
| [triageussy](https://github.com/ussyverse/triageussy) | 36a391039b286a5571c91574267efe644d8ec1fe | Runtime dependency through explicit symptom adapter; 160 upstream tests passed locally. |
| [petrichorussy](https://github.com/ussyverse/petrichorussy) | 76b19e47e1aa1800e16b02aa73a8462bacddcad6 | Runtime dependency for hashes/diffs and selected configuration history; 140 upstream tests passed. |
| [correction-aware-learning](https://github.com/mojomast/hermes-correction-aware-learning) | 84c8c8c7e27c820cbc1aa0a5fcf99f891f503f48 | Runtime structural evidence/retraction/shadow report adapter; 76 upstream tests passed. Architecture/privacy contracts inspected. |
| [Hermes fork](https://github.com/mojomast/hermes-agent) | cd941c46745e09d475d75d7ac88d41bc5364a0ed | Storage/extensions/routing reference, not a runtime dependency. Deterministic routing evaluation is not model reasoning replay. |
| [Hermes upstream](https://github.com/NousResearch/hermes-agent) | 643b3f450df1c6c884b2de8d0832d0af9b6ed272 | Source/extension reference; actual installed schema/code was checked separately. |
| [clanker03](https://github.com/mojomast/clanker03) | e9f8608828c31077980f9e86224799c60c8f73e4 | AgentReplay reference only, no dependency. Store concerns around createHash/zlib and promisified stream construction were inspected; no functioning replay certification is claimed. |

Installed Hermes source at discovery: 277268d83ff2204de9646f0b1e376e73ac0a5d20, detached checkout; schema 26. Directory/release naming was not used as revision evidence. Official storage docs: https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage/ . The profile-local skills loader was exercised against the installed implementation, not only the reference checkout.

Dependencies use exact Git URLs in pyproject.toml and uv.lock, avoiding similarly named registry packages. No upstream implementation is vendored or rewritten. Triage and Petrichor declare MIT in package metadata but contain no root LICENSE file at these revisions; correction-aware-learning includes its MIT license. See NOTICE.

0.5.0 does not upgrade any component pin for the rename. The prior component test totals above are historical evidence, not newly rerun totals for this release. The current inspected official Hermes release v2026.9.11 resolves to `939e45c91d751fadd94dcd1b873ac3cb44846213`, schema 30; loader/hook/schema source observations and pending host tests are in [native-plugin.md](native-plugin.md). Keep the old exact host pin. Authoritative plugin API documentation: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins .

Update strategy: inspect upstream interface/privacy changes, choose an exact commit, run that component's tests and our adapter/regression/privacy tests, update both pins and lock, rebuild the wheel and rerun clean installation/browser checks. Never silently track HEAD or upgrade Hermes to accommodate this application. Initial installation requires network/Git; core analysis and trusted regression execution are local afterwards.
