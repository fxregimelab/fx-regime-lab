# Private quote storage — packet 15.1

The forward migration adds private, append-only capture records, snapshot records and ordered snapshot membership. Application writes enter through the two central-writer RPCs. The migration does not write to historical prices, calls, validation records or evaluations.

Each stored fingerprint is checked against SHA-256 of the exact UTF-8 unsigned JSON text. That original text is retained beside an inspectable JSONB document. Source bodies stay strings inside the document; SQL uses JSON rather than JSONB to inspect them, so a source number such as `1e1000000` is retained without PostgreSQL numeric overflow.

The migration verifies the page and snapshot field sets, fixed identifiers, pair/instrument/window identity, timestamp types and ordering, request/header allowlists, cursor evidence, issue ordering, body hashes and snapshot input hashes. Snapshots require every referenced capture to exist. Ordinal membership preserves repeated hashes in incomplete diagnostic snapshots. One transaction inserts a snapshot and all its membership; retries return the same fingerprint.

All three tables have RLS enabled. Service role can read and call the exact two RPCs; anonymous and authenticated roles cannot read or call them. Direct service-role writes are denied. Triggers reject UPDATE, DELETE and TRUNCATE even for ordinary owner operations. Helpers have no application execution grant and every function fixes its search path to `pg_catalog, public`.

Storage verifies internal consistency. It does not authenticate the provider, certify the caller's implementation label, independently recompute midpoint arithmetic, or establish price eligibility. All references remain provisional and validation-ineligible. There is no promotion path into historical prices.

## Verification

Run from the repository root:

```powershell
python scripts/repair/verify-quote-storage-db.py
python -m ruff check scripts/repair/verify-quote-storage-db.py
```

The verifier creates and drops a uniquely named isolated database on the parent's existing PostgreSQL 17.11 Unix-socket runtime. It does not start or stop the runtime, read credentials, load `.env`, contact a provider, send notifications or modify a production database.

The final complete database run passed and emitted `REPAIR_QUOTE_STORAGE_DB_VERIFIED`. Scoped Ruff also passed. The isolated test database was dropped in the verifier's cleanup block; the parent's PostgreSQL runtime remains running for its other checks.

Expanded tests found a PostgreSQL JSON limitation: extracting an unrelated field can still decode exceptional NUL or lone-surrogate source strings and keys. The parent amended capture sanitation to retain visible escapes and the explicit `text_storage_escaped` issue. Such evidence remains incomplete. Original response byte hashes and sizes are preserved; exceptional source strings are sanitized, not claimed to be lossless originals. The final real-database run verifies the amended value, key and malformed-body cases.

The exact-text test also exposed Windows newline conversion in the verifier's initial text-mode subprocess pipes. SQL correctly rejected the changed fingerprint. Binary UTF-8 pipes now preserve the submitted text, and the final run verifies a non-ASCII, multiline document byte for byte. No hash check was weakened.

The verifier checks:

- Actual Python capture, exact Decimal midpoint construction and central-writer serialization into the real service-role RPCs, followed by exact text/document/ordered-lineage reconstruction.
- Strict direct-SQL malformed shapes, types, timestamps, request metadata, headers, issue lists, fingerprints, cursor evidence, missing pages and inconsistent identities. Every rejection is checked against archive state and source-error disclosure.
- Exact retries and simultaneous retries for both RPCs, with one insert per fingerprint.
- Injected failure on the second membership insert, leaving neither a partial snapshot nor any partial membership.
- All three locked pairs; empty, incomplete, intraday, duplicated-page, invalid-UTF-8/JSON, crossed-price and extreme-exponent evidence; the 10,000-page membership boundary; exact non-ASCII UTF-8 hashing.
- Broad pre-existing default grants, private helper execution, RLS after accidental read grants, denied direct INSERT/COPY/UPDATE/DELETE/TRUNCATE, and owner mutation refusal.
- Fresh migration, empty and populated reapplication, and unchanged price/call/signal/rationale/validation/evaluation sentinels. These are bounded synthetic preservation fixtures, not a claim to recreate the full production migration history.

GitNexus impact checks found no indexed symbols for the new RPCs and verifier entry point: zero known callers, risk reported as UNKNOWN. This is new private storage, not a claim that database changes carry no risk. No commit or deployment was made.

Parent acceptance: the full actual PostgreSQL gate was independently rerun and passed. All packet-15 leaf gates are accepted. The parent confirmed zero quote scratch databases and zero other client connections, then stopped the task-local PostgreSQL instance and verified no server running.
