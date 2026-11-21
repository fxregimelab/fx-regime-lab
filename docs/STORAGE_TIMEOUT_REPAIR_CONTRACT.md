# Remaining storage request timeout repair

Packet31 addresses the remaining local O02/L04 write-entry boundaries identified after packet29. PostgreSQL function-local statement_timeout does not arm the outer request timer. The accepted repair requires a bounded inherited timer and verifies actual server cancellation. Deployed PostgREST connection setup remains separate evidence; a client HTTP timeout does not establish database cancellation.

Add forward migration `supabase/migrations/20260928000015_storage_request_timeouts.sql`. Replace exactly these current public definitions:

| Function | Authoritative existing definition |
|---|---|
| append_validation_evaluation(jsonb) | migration20260927000006_validation_price_evidence.sql |
| append_regime_publication(jsonb,jsonb,jsonb,integer) | migration20260927000004_atomic_publication.sql |
| append_price_observations(jsonb) | migration20260927000007_price_observations.sql |
| append_quote_capture(text,text) | migration20260927000008_quote_capture_storage.sql |
| append_quote_snapshot(text,text) | migration20260927000008_quote_capture_storage.sql |
| append_quote_acquisition_event(text,text) | migration20260927000009_quote_acquisition_events.sql |

Preserve signatures, argument defaults, security modes, fixed search paths, grants, validation, receipt meaning and body semantics. Do not edit historical migrations or the internal append_validation_evaluation_v1 helper. Add function-local lock_timeout=10s and require inherited pg_settings.statement_timeout in1..30000ms at the beginning of each body, before decoding, hashing, queries, locks or writes. Do not set statement_timeout inside a function. Removing only these two additions from each replacement must reproduce its current definition exactly. No function renames, wrappers, schema/data rewrites or broader hardening are part of this leaf.

The guard is a configuration check, not proof of a hostile nested caller's timer state. A correctly configured top-level call retains existing insert, idempotent retry, version-dispatch and conflict behavior. Invalid timer0 or30001 must fail without changes for both fresh and retry requests. Preserve append-only originals, rollback and application role boundaries. Reapplication must preserve populated evidence, function configuration, grants and constraints.

Own `scripts/repair/verify-storage-request-timeouts-db.py` and `reports/repair-storage-request-timeouts.md`. The verifier must be import-safe with a parent-overridable MIGRATION_SQL, use a unique disposable database on the parent-confirmed socket-only server, and apply the needed authoritative prerequisites. Reuse inspected pure builders/fixtures without importing scripts that execute database work at import. Treat existing fixture and verifier files as read-only. Expose bounded, readable results and measured scenario counts; never print bodies, credentials or raw private SQL errors.

Required evidence for every entry point: baseline valid timeout0 succeeds before migration; inherited0/30001 refuse unchanged state afterward; inherited30000 permits valid insert and retry; exact scoped10s lock timeout restores caller settings; real PostgreSQL timeout cancellation while blocked on an observed row/table/advisory lock leaves no new or partial evidence; the same request succeeds after release; immutable/role controls and populated reapplication pass. Use actual server SQLSTATE57014 or equivalent precise cancellation evidence, not a subprocess timeout. Where a transaction inserts into multiple tables, prove rollback after a write was attempted using a scratch trigger/sequence witness. Preserve both supported validation contract versions and publication's versioned/superseding identity behavior in focused positive controls.

The parent will independently rerun the gate, inspect definition equality, challenge a removed guard and integrate later with the deployed request configuration. Source bodies, semantics and unrelated source files are outside this leaf's ownership. Configured standalone Ruff/MyPy and git diff checks are required. GitNexus upstream impact before replacing each symbol; report UNKNOWN honestly, warn on HIGH/CRITICAL, and do not rebuild the shared index. Parent owns runtime startup/shutdown; worker must not stop the server used by other leaves. No credentials, provider/AI requests, production writes, notifications, commit, push or deployment.
