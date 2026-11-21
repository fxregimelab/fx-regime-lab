# Private FPI capture storage

This is the durable input layer for the replacement FPI pipeline. It preserves complete HTTP response bytes before parsing. It does not establish observation first-seen times, acceptance, release times or feature eligibility. Raw reports stay private; no source tables are committed or exposed publicly.

## Capture identity

`build_fpi_capture(*, body: bytes, source_url: str, requested_at: datetime, retrieved_at: datetime, http_status: int) -> FpiCapture` is pure. `FpiCapture` is a frozen dataclass with `capture_sha256` and `document_json` strings. The authoritative document is Python JSON with sorted keys, compact separators and ensure_ascii=True. Its exact ASCII bytes are hashed with SHA-256.

The document has exactly these fields:

- `version`: `fpi-http-capture-v1`.
- `source_url`: exactly the NSDL Latest.aspx or Monthly.aspx HTTPS URL accepted by the parser, with no query, fragment, user information or alternate host.
- `requested_at`, `retrieved_at`: aware input datetimes normalized to UTC, serialized by `datetime.isoformat()`. Request start cannot follow retrieval completion. Timestamps must fit years 1 through 9999, including UTC conversion.
- `http_status`: an integer from 100 through 599; booleans are invalid.
- `body_base64`: canonical standard padded Base64 of the exact bytes, including invalid UTF-8 and NUL. Empty bodies are allowed as failure evidence; the maximum is 5,000,000 bytes, matching the parser's input bound.
- `body_size`: exact byte count, integer, never boolean.
- `raw_sha256`: lowercase hex SHA-256 of the exact decoded bytes.

Every HTTP outcome can be archived, including an error page or malformed report. There is no implicit parser invocation. A complete empty body is distinct from a request that never produced a complete body; attempt, timeout and truncated-body records belong to the acquisition layer. Do not invent a capture for a no-response failure. Request headers, cookies, credentials and response headers are outside this envelope. It is for these fixed public report endpoints only.

`validate_fpi_capture(capture) -> None` verifies the exact dataclass type, bounded canonical text, exact field set/types, canonical Base64 and timestamps, byte count, both hashes and temporal order by reconstruction. A changed status, timestamp or source is a different capture even when raw bytes match. Exact retry retains the original identity; re-downloading the same bytes at a different time is a new capture.

## Central writer and database

`archive_fpi_capture(capture: FpiCapture) -> dict[str, Any]` lives only in `pipeline/src/db/writer.py`. Validate before creating a client. Send exactly one RPC: `append_fpi_capture(p_capture_sha256 text, p_document_json text)`. Do not write other tables. Sanitize provider/client errors to a fixed message without source body, credentials or exception chaining.

The receipt has exactly `capture_sha256`, `inserted` (JSON boolean), and `stored_at` (finite UTC timestamp string). The hash must equal the requested identity; stored_at cannot precede retrieved_at. Accept PostgreSQL's UTC `+00:00` or `Z` timestamp spelling with zero to six fractional digits. Reject other types, extra fields, timezone offsets, impossible dates and excess precision. Return a detached receipt.

Forward migration `20260927000010_fpi_capture_storage.sql` creates private `fpi_captures`: capture_sha256 primary key, authoritative document_json TEXT, parsed document JSONB, source_url TEXT, requested_at and retrieved_at TIMESTAMPTZ, raw_sha256 TEXT, body_size INTEGER, http_status INTEGER, stored_at TIMESTAMPTZ assigned by the database. Index source_url/retrieved_at and raw_sha256. Do not parse Base64 bytes as text or HTML in SQL.

The RPC verifies the exact text hash, unique JSON keys, exact field set, primitive types, URL allowlist, timestamp grammar/order, integer bounds, canonical Base64, decoded size and raw hash. Bound document UTF-8 bytes to 7,000,000 before parsing. SQL verifies envelope consistency but need not reproduce Python key ordering; it retains submitted text exactly. Require retrieved_at no later than database clock_timestamp(). Stored time is assigned only after validation and while inserting; it is immutable on retry. Hash collision or retained-text mismatch rejects. Concurrent identical calls produce exactly one row and identical stored_at receipts. Unrelated captured responses can coexist.

All table UPDATE/DELETE/TRUNCATE operations fail through triggers, including owner operations. Enable RLS and revoke PUBLIC, anon and authenticated table/function rights. service_role has SELECT and execution of the exact RPC, with no direct INSERT/UPDATE/DELETE/TRUNCATE. SECURITY DEFINER entry point has a fixed pg_catalog/public search_path. Helpers have no public or application execution grants. Reapplication is idempotent and must preserve records and unrelated table/role permissions. Diagnostics must not reveal captured bytes or submitted JSON, even on malformed direct SQL inputs.

## Timing and next layers

`stored_at` records execution inside a transaction. It is **not** a commit timestamp, an observed read-visibility timestamp, a source release time or a substitute for qualified available_at. Acquisition timestamps are caller assertions until a bounded runner binds them to transport and attempt evidence. Older private research captures can be imported only when the required envelope metadata exists; never invent a request start to fit this schema. Import cannot prove historical availability.

Observation identity, capture membership, acceptance/withdrawal and decision-time selection need separate append-only records. In particular A → B → A is a new occurrence of a previously seen value: immutable first-seen identity must not suppress that reversion. Preserve capture occurrence and visibility evidence separately before integrating the current pure selector. Neither this archive nor a successful parse activates FPI.

## Verification

Pure tests prove exact byte preservation, mutation/type/size rejection before I/O, retry identity and strict receipt validation. An isolated PostgreSQL verifier exercises the actual Python builder and central writer through service-role RPCs: fresh/reapplied migration, exact round-trip, malformed direct SQL, concurrent retries, permissions, RLS, mutation refusal and unrelated-table preservation. Use authored synthetic bytes in committed tests. Parent owns the existing task-local socket-only PostgreSQL lifecycle; no production credentials or provider requests are needed.
