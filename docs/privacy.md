# Privacy and threat model

Protect: private conversation/tool content, credentials and personal paths; integrity of original evidence; the running Hermes installation; operator review and process-verification boundaries.

Trust model: a single local user explicitly approves source/test code. Historical messages, annotations and imported bundles are untrusted data. Message role is not authenticated human identity. Review flags are operator assertions, not cryptographic attestations. Other processes running as the same OS user are outside the local web security boundary.

## Data handling

Data lives outside the checkout. Application/private roots use mode 0700 and SQLite/evidence files are permission-restricted; this is not encryption or secure deletion. Read-only SQLite source plus backup prevents accidental migrations and preserves WAL consistency. Output and context are bounded. No source conversations, manifests or private report files are required by CI.

Triage symptoms do not replace process status. Petrichor receives only allowlisted version/platform/project-kind fields and normalized logical paths, never arbitrary configuration text. Correction-aware-learning receives structural evidence and relations, not transcripts; recurrence output is count-only and learning stays shadow-only. The private application store separately retains selected case and correction content.

`export` is count/status-only. Portable export requires explicit review, separately supplied sanitized descriptions and selected source/fixture files. Raw outputs, session/message IDs, annotations and original prompts are not copied. Path/secret-like pattern checks and privacy canary tests add safeguards. Arbitrary proprietary strings cannot be reliably identified by regex: inspect every bundle before sharing. Checksums detect accidental tampering, not maliciously re-signed manifests or trustworthy code.

## Execution

No command is executed merely because it appears in history. No shell recipes or unrestricted command endpoints exist. Recipes freeze committed revisions and assertion hashes, archive into a temporary workspace, disable pytest plugin autoload, control the environment and clean up subprocess groups on timeout. Output limits are checked and captured output/report reads are bounded. Temporary output may consume disk before the runner observes it; OS-level resource quotas are not provided.

This is NOT an operating-system sandbox. Reviewed Python can access the filesystem/network as the user and can escape a process group. Do not import with `--reviewed` or execute code that has not been inspected. Use a separate container/VM/OS account for hostile code; this product does not configure that isolation.

## Web

Loopback bind by default; no public hosting support. Host/Origin/Fetch-Site guards, per-launch mutation tokens, bounded streamed request bodies, restrictive CSP and no CORS protect browser-origin mutation. Historical text uses textContent, not HTML. No model/API keys are sent to the browser. Same-user malware and deliberate insecure reverse proxies are not prevented.

## Repository audit

.gitignore excludes databases, WAL/journals, raw logs, environments, private directories and test artifacts. `scripts/audit_index.py` scans exact staged blobs, rejecting excluded paths, unreviewed binary content, personal-path and credential-like patterns. Always inspect the staged diff too; neither ignore patterns nor secret scanning alone proves absence of private data. Only synthetic fixtures and aggregate historical findings belong in Git.
