# Architecture

The package is a local application, independent of Hermes runtime imports. `cli.py` and `web.py` call a shared `Lab` service. Browser assets are installed inside the wheel; neither a frontend build server nor an external CDN is required. SQLite stores versioned JSON documents atomically. Network/model access is unnecessary after dependencies are installed.

## Explicit boundaries

`history.py` opens the source with SQLite URI mode=ro and query_only, uses SQLite backup into a private temporary database, and validates schema 26. Bounded rows, outputs and surrounding messages become immutable `Run` and `Case` documents. Same-source IDs and payload digests preserve provenance. Parser revisions do not silently rewrite facts.

`adapters.py` calls the pinned Triage `extract_errors` API for symptoms, while retaining exit codes separately. Its Petrichor adapter hashes and stores only selected allowlisted configuration JSON under normalized logical paths. Its correction-aware-learning adapter writes constrained evidence/relation records and exposes count-only recurrence, shadow-only. Raw case text remains in our private store, never the structural learning store.

`corrections.py` scans bounded user-role messages in the same read-only schema. Explicit lexical correction markers require a nearby imported failure or completion-like assistant claim. Candidates retain source/message IDs, role observations, limited private text, selection reason and uncertainty. Reviews and retractions are append-only; candidate detection never grants human-authenticated authority.

`runner.py` resolves committed revisions, freezes one test hash, archives tracked source into temporary workspaces, controls environment, disables plugin autoload/user pytest configuration, and executes pytest directly without a shell. JUnit plus return code/output determine outcomes. Same-process-runtime configuration, assertion identity and test counts are checked before comparison. It is not an OS sandbox.

`bundles.py` projects only explicitly approved source files and separately supplied sanitized metadata. No raw history is copied. Validation checks schema, paths, field allowlists and checksums. Import creates new local source-projection commits and a not-run recipe; explicit local review is mandatory for execution.

## Web consistency and security

Request generations guard list and detail responses. Old responses cannot replace newer selections. Mutations are single-flight; the main interface is inert while they run. `data-state`, `data-completed`, `data-case-id` and discarded-response state let browser tests observe actual completion. No sleeps substitute for product state.

The CLI binds 127.0.0.1. Host/Origin/Fetch-Site checks, per-launch mutation tokens, bounded bodies, no CORS, restrictive CSP and text-only rendering defend browser-origin attacks. This is a single-user local service, not authenticated multi-user hosting.

## Source interfaces not reused

Hermes task-router evaluation checks deterministic routing, not general reasoning replay. AgentReplay is reference-only, not a dependency. No Hermes core patches, prompt modifications or automatic learning activation are made.
