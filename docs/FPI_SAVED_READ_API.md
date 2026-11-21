# Saved-read implementation interfaces

Packet30 supplements docs/FPI_SAVED_READ_CONTRACT.md with exact Python and SQL ownership interfaces. The canonical documents and acceptance scenarios there remain authoritative. No activation or consumer feature follows from this packet.

## Pure module

New pipeline/src/research/fpi_saved_read.py exposes frozen document value objects:

- FpiAdminReadPolicy(document_json: str), with computed init=False policy_sha256.
- FpiAdminReadRequest(document_json: str), with computed init=False request_sha256, read_id and decision_id.
- FpiAdminReadManifest(document_json: str), with computed init=False read_sha256, read_id, request_sha256, decision_id, read_at and status (all exact strings).

Each constructor verifies bounded canonical text, exact schema and all internally decidable consistency rules before computing fields. No cached mutable decoded object is exposed. These are validated document assertions, not database-origin or execution attestations. Public boundaries rebuild and compare exact derived primitive fields to reject forged frozen objects. No edits to older codecs or identity meanings.

Public functions:

```python
validate_fpi_admin_policy_receipt(value: Any, policy: FpiAdminReadPolicy) -> dict[str, Any]
validate_fpi_admin_read_receipt(value: Any, request: FpiAdminReadRequest) -> dict[str, Any]
verify_fpi_admin_read_originals(
    manifest: FpiAdminReadManifest, *,
    capture_rows: tuple[dict[str, Any], ...],
    parse_rows: tuple[dict[str, Any], ...],
    artifact_rows: tuple[dict[str, Any], ...],
    event_rows: tuple[dict[str, Any], ...],
) -> FpiAdminReadManifest
```

Receipt validators return detached exact dictionaries. Originals verification takes exact tuples and exact dict rows, snapshots exact primitive values before validating anything, rejects unexpected/duplicate/missing rows and returns a rebuilt manifest after proof. It performs no I/O. Rows are minimal immutable storage projections with exact keys:

- capture: capture_sha256, document_json, stored_at;
- parse: parse_id, record_sha256, document_json, stored_at;
- artifact: kind, artifact_sha256, document_json, stored_at;
- event: event_id, event_document_json.

Original documents remain byte-exact. Database stored_at strings use the existing finite UTC receipt grammar (zero to six fractional digits with Z or +00:00); compare parsed instants to canonical manifest times, without changing original documents. Reject non-UTC offsets, nonfinite/invalid dates, subclasses and extra fields. New manifest times themselves keep the strict canonical rule. Failure manifests accept only empty original-row tuples and return no usable data. COMPLETE requires the exact retained sets, per-document/aggregate budgets, one artifact validation per unique artifact, one bulk build_fpi_read_references call and exact rebuilt reference comparison, stored-time matches and original event-document equality. Pure manifest validation rebuilds the compact qualification view once; originals verification must not duplicate raw capture validation per parse. Preserve all full supporting memberships, and recompute all compact identities that can be decided from the references; unknown source/value/record content remains an explicit original-verification duty.

No broad exception swallowing: malformed input raises bounded ValueError without private input/exception chaining; cancellation and system exceptions propagate. No parser HTML execution, artifacts execution, database/network, selection or normalization.

## Central writer and loader

Only pipeline/src/db/writer.py will add:

```python
append_fpi_admin_read_policy(policy: FpiAdminReadPolicy) -> dict[str, Any]
capture_fpi_admin_read(request: FpiAdminReadRequest) -> dict[str, Any]
load_fpi_admin_read(read_id: str) -> FpiAdminReadManifest
```

The first two operations rebuild inputs before client acquisition, submit exactly one matching RPC from the main contract, and validate exact receipts through the pure functions. No automatic dependency upload, identity replacement or retry re-read. The loader reads one fpi_admin_reads row with exactly read_id,decision_id,request_sha256,request_document_json,policy_sha256,read_sha256,manifest_document_json,read_at,status and verifies all projections. For COMPLETE it fetches only the four original projections above in requested-ID batches of at most256, with exact identity-set matching. Artifacts use (kind,artifact_sha256) identity; batch by kind so equal hashes under different kinds never collapse. On failure manifests it performs no dependency queries. It calls the pure verifier once and never queries today's membership universe, heads, policy aliases or providers. Boundary errors are static RuntimeError without exception chains/raw logs; malformed local inputs fail before I/O. System/cancellation exceptions propagate. Tests use fake clients and preserve real call structure and pagination limitations.

## SQL and verification ownership

Migration14: supabase/migrations/20260928000014_fpi_admin_reads.sql implements both tables, indexes, helpers and RPCs in the full contract, including all retained outcomes and deterministic staged resource guards. Do not simplify to caller-supplied manifests, multi-statement evidence reads, accepted-only rows, truncation or timestamp-based visibility. Helpers must not create separate evidence snapshots. Existing rows/functions stay unchanged. New clock helper and scratch barrier seams are private. Read Commited only; inherited request timer and local lock timeout as packet29. All downstream audit and RLS/grant/immutability rules from the contract apply before edits. Python codec and SQL schema can be implemented independently against these frozen documents and golden vectors; actual cross-language integration follows their independent acceptance.

SQL worker owns scripts/repair/verify-fpi-admin-read-db.py, a real scratch database verifier covering the SQL scope, concurrency, retry, overflow, clock, permissions and reapplication portions of SR01-SR26. Python tests own codec/receipt/original-consistency portions; later writer tests own transport/missing-page behavior. SQL self-verification must not import the in-flight new Python module; use inspected existing original builders and independent canonical expectations. Integration must subsequently exercise actual new Python/writer loading against the saved SQL output. Parent owns runtime startup/health/shutdown and deliberate wrong-scope/receipt/reference controls.

The full work is complete only after SQL, pure validation and actual central loader agree on complete retained reads. A passing leaf alone does not close SR01-SR26 or the broader repair goal.
