# Atomic publication contract — repair candidate

Original calls and evaluations are immutable. A changed historical calculation is a new version, never a rewrite of an original call. Three pairs only: EURUSD, USDJPY, USDINR. No migration may disable protections or delete existing observations.

## Boundary

The only new publication entry is writer.publish_regime_call(call, signal_row, *, rationale=None, correlation_id=None, supersedes_call_id=None). It invokes public.append_regime_publication(p_call jsonb, p_signal jsonb, p_rationale jsonb, p_supersedes_call_id integer default null) and returns the durable call ID. The writer serializes complete dataclass snapshots with finite JSON values; pair/date identities and nonempty model/strategy/source provenance must agree. Calls may be live or backtest. Core rationale generation precedes this call; neither core nor staged publication performs separate writes. A staged adapter uses the same core persistence function as legacy. No API fallback may silently return an unrelated existing row.

## Identity and history

Publication identity is (pair, date, data_source, strategy_version, model_version). A repeated identical semantic payload returns the same ID. Different call, signal or rationale content at that identity raises a conflict requiring an explicit new model version. An existing legacy call without publication evidence cannot be silently adopted. A supplied predecessor must exist and share pair/date; originals stay present and unchanged. The optional link does not fabricate original signal provenance.

The database stores publication_evidence keyed uniquely by call_id, containing immutable call_payload, signal_payload, rationale_payload, SHA256 payload_hash and optional supersedes_call_id. Correlation IDs and client write hashes are operational metadata, excluded from the semantic fingerprint. The server computes the hash and supplies call_id/date/pair to rationale storage. Unknown internal id/timestamp overrides are rejected or removed before insertion. No caller-supplied SQL names are interpolated.

The previous pair/date unique constraint on regime_calls becomes provenance-aware uniqueness. Existing rows must survive byte-for-byte. Migration failure on duplicate identities is preferable to silently discarding a row. Preserve historical title-case directional_bias values while accepting the uppercase spelling produced by the current engine; replace only that named legacy constraint. Protect calls, evidence and rationale against UPDATE/DELETE. Restrict publication RPC execution to service_role; anon/authenticated must not insert calls or evidence. Use a fixed search_path and fully qualified tables.

## Signal projection

publication_evidence is the authoritative signal snapshot for a new call. The existing signals table is a current projection for existing readers. Only live publications update that projection; backtest replays do not. A signal_projection_history table plus UPDATE/DELETE trigger preserves every replaced/deleted prior projection without asserting that it was the original input for a legacy call. This history is append-only. A new call, immutable evidence, rationale and any live projection change either all commit or all roll back.

## Historical paths

Bulk replay validates the entire input batch before writing, requires data_source=backtest and explicit nonempty model/strategy versions, then appends each publication through the central boundary. A partially completed batch is resumable by deterministic identity; it never deletes a pair or disables triggers. Forced date purge is retired for protected originals. Synthetic risk reversal cannot justify revising published predictions; retire its write mode and keep any inspection read-only. Batch statistics must use the canonical cohort aggregator rather than deleting snapshots or bypassing triggers. Retrospective rationale insertion must never overwrite an existing rationale.

## Acceptance

Test exact repeats and conflicting repeats, mixed live/backtest same-date calls, independent versions, mismatched identity, invalid provenance, predecessor checks, lossless signal notes, one-RPC writer delegation and failures before notification. Real local PostgreSQL must verify all-or-nothing rollback after insertion, concurrent repeats/conflicts, immutable original rows/evidence/rationale, signal history, unchanged live projection for replay, migration reapplication and role permissions. Use a task-local scratch database only. Full historical migration rehearsal and production release remain separate gates.

Before release, current-call readers must select explicit live provenance and a deterministic version policy, and signal explanations must be bound to the selected call's evidence. Validation still traverses every eligible historical call by durable ID. Pair/date alone is no longer a unique publication key. Current prior-regime queries also need an as-of cutoff so replay or future calls cannot affect an earlier decision. These reader repairs are a dependent packet, not implied by atomic storage tests.
