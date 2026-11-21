# Private price observation archive

Repair leaf 12.4, 27 September 2026. Local verification passed: `python scripts/repair/verify-price-observation-db.py` exited 0 and printed `PRICE_OBSERVATION_DB_VERIFIED`, including the actual preparation and Python writer integration. The parent still owns independent acceptance.

Migration `20260927000007_price_observations.sql` adds a private, append-only record of provider observations. It does not certify final closes, reconstruct historical retrieval times, or write `historical_prices`.

The service RPC accepts the exact fields in `docs/PRICE_OBSERVATION_CONTRACT.md`, including explicit nulls for unknown session and window facts. It validates the entire batch before allocating IDs. A payload hash uses migration 004's numeric canonicalization, so numeric spellings such as `0` and `0.0` produce the same identity. Later retrievals, changed prices and changed metadata create separate rows. Original JSON is retained without stripping metadata or normalizing away the provider's timestamp text.

The RPC returns IDs in input order and separate inserted/existing counts, including repeated IDs within a batch. Sorted transaction locks and a unique hash constraint handle simultaneous retries and reversed overlapping batches. Any later storage failure rolls back the complete batch.

Both table privileges and row-level security restrict reading to the service role. Only that role may execute the append RPC; no application role may directly insert, update, delete, truncate or allocate sequence IDs. Triggers also reject owner-level update/delete/truncate. Functions have fixed search paths and helper execution is revoked from application roles.

The database checks cover:

- Exact fields, three permitted pairs/providers, strict date labels, nonblank instruments, finite positive OHLC with exact numeric ordering, and finite nonnegative volume.
- Required retrieval time, aware timestamp offsets, future retrieval/provider timestamp rejection, provider time at or before retrieval, paired and ordered windows, and retrieval at or after window start. A future end is retained as an open observation, never promoted to a completed close.
- The frozen provider metadata key list with scalar values only; unknown keys, nested objects and arrays are rejected.
- Empty batches, the inclusive 5,000-row limit, repeated payloads and numeric-equivalent nested metadata.
- Original rows surviving later retrievals and corrections; validation before sequence allocation; injected mid-batch failure rollback.
- Simultaneous duplicate requests and reversed overlapping batches; private role access; RLS protection even after an accidental read grant; immutable triggers and fixed search paths.

## Verification boundary

`python scripts/repair/verify-price-observation-db.py` uses a random scratch database on the task's PostgreSQL 17 Unix socket at port 55437. It applies the publication fixture and migration 004, then migration 007. It exercises actual SQL, not a mocked database. The integration check passes actual `SpotBar` objects through `prepare_price_observations`, then the actual Python writer. The writer transport alone is redirected into the local SQL RPC. It compares stored metadata, requires one RPC per call, forbids a table-write fallback and checks retry IDs. Cleanup drops only its own uniquely named database.

The final run passed all eight check groups after the provider-time/retrieval guard was added. Verified SHA-256 hashes:

- Migration 007: `ed8e8c3ce82dd7e84a7306223993caffc6b707570cffc6b63864635fc10525b4`.
- Verifier: `e77b4ad62aece53958ef31580dee81acc9ef11f913c949cb4fcdfcd05856c0a8`.

No production connection, provider call, credentials, `.env`, startup change, ledger rewrite, migration deployment or commit was used. This leaf creates new SQL and verifier symbols only; it does not edit indexed application symbols or older migrations. The parent owns the downstream writer and caller integration.

Provider daily boundaries, completion policies, historical vintages and raw full-response retention remain separate evidence gaps described in `reports/repair-price-provider-research.md`. These observations cannot automatically become validation endpoints. Passing this database verifier would prove archive behavior on local fixtures; it would not prove deployment compatibility or final market-close acquisition.
