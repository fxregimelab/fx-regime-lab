# FPI parse database evidence

27 September 2026. Leaf 24.2 retains private implementation artifacts and complete parsed report results. It preserves the existing parse, value, membership and content identities. It does not qualify those records or establish what an earlier decision saw.

The leaf owns only migration `20260927000011_fpi_parse_storage.sql`, `scripts/repair/verify-fpi-parse-db.py`, and this report. No production credentials, providers, AI calls, deployed database or public research records were used. The parent started and checked the existing socket-only PostgreSQL 17 runtime; this leaf did not start or stop it.

## Storage and checks

The migration adds three append-only tables: implementation artifacts, complete parse results, and dated memberships. The parse references an existing capture and a retained artifact declared as `PARSER`. A retained `SELECTOR` with the same hash alone cannot satisfy that dependency. Successful results retain every dated INR document and its independent USD source document. Failed results retain one bounded failure code and no members.

The SQL entry points independently verify exact canonical JSON, duplicate keys before JSONB conversion, permitted fields and primitive types, exact bytes and hashes, the existing pure identities, dates, recording time, decimal formats and reconciliation bounds. SQL rejects zero-microsecond `.000000` recording times because Python's canonical `isoformat()` omits that fraction. All errors from storage entry points use a bounded message that excludes submitted bodies.

The verifier uses the real Python artifact/parse codecs and central writer. Only the transport is replaced: the writer's actual RPC parameters go through UTF-8 binary pipes to service-role PostgreSQL calls. Scratch database names start with `fxfpiparse_` and contain a fresh UUID. Cleanup runs in `finally` and never shares the capture verifier's database name.

Checks cover:

- Exact binary artifact retention, both artifact kinds, complete INR/USD readback, unchanged pure identities and stable retry times under non-UTC database session settings.
- Malformed direct SQL, unknown or missing structure, duplicate keys/dates, primitive-type substitutions, bad dates, future recording times, canonical formatting, body-size exponent/decimal lexemes, malformed Base64, document/body limits and forged hashes.
- Numeric defects after recomputing every affected hash. Fresh absent parse identities prevent an existing-row conflict from masking a numeric failure. Separate positive and negative controls test the immediate inside/outside boundaries for gross-minus-sales, INR route/subtotal/total, and USD route/subtotal/total reconciliation.
- Missing capture, missing parser, SELECTOR-only dependency refusal, failed non-200 capture preservation, and a deliberately injected second-member insert failure. The latter checks rollback after insertion has begun, including the parent result row.
- Simultaneous exact retries and competing valid recordings under one parse identity. One retained result survives with a complete membership list and stable original storage time; conflicting text cannot replace it.
- A real paused central-writer transaction. An explicit session returns its RPC receipt and a readiness marker before commit. A separate service-role connection sees zero results and zero memberships. After an explicit commit marker, that connection sees one result and both memberships. Queue waits are bounded; visibility does not rely on guessed sleep timing.
- Five-million-byte artifact acceptance, oversized-body rejection and a complete 31-member parse.
- Table grants, PUBLIC revocation, RLS, private helper permissions, fixed search paths, and UPDATE/DELETE/TRUNCATE protection even for the table owner. Owner TRUNCATE uses CASCADE to reach the immutability trigger rather than stopping at the foreign-key restriction.
- Fresh, empty and populated migration reapplication. Exact retained rows, existing capture helper permissions, original call/signal/rationale rows and permissions, and an unrelated table permission remain unchanged.

## Four review passes

1. Implemented complete schema, independent validation, transactional insertion and a real writer-to-SQL verifier.
2. Compared the identity and numeric rules against the existing observation, parser and selection modules. Added fresh rehashed positive/negative numeric controls to avoid conflict masking.
3. Exercised actual PostgreSQL. Corrected the verifier's owner TRUNCATE assertion to reach the trigger, and corrected the SQL/Python zero-microsecond timestamp mismatch. Added explicit preservation checks for existing grants and rows.
4. Re-read the final SQL and verifier for canonicalization, dependency, privacy, retry, rollback, cleanup and evidence claims. Scoped Ruff and the final complete executable run passed.

## Verification status

`python scripts/repair/verify-fpi-parse-db.py` exited zero with `REPAIR_FPI_PARSE_DB_VERIFIED` after all nine reported check groups. This final run includes the timestamp, 31-member, oversized-body and broader privilege-preservation checks. `python -m ruff check scripts/repair/verify-fpi-parse-db.py` passed. Parent independent acceptance remains separate.

Tested SHA-256 fingerprints:

- Migration: `0a3e6fa6af5ef498a85e9b1f9baa9e2998cd116ad0477c81d2d89690fef6a675`.
- Verifier: `3ecf08ae90825b9085071f857d7d44881eea99ace7b88ef201e9b5124cff0bf8`.

## Limits

This is an isolated capture-plus-parse migration test using authored synthetic records. It is not a full historical migration-chain rehearsal or a production rollout. The parent owns original-report round-trip evidence and independent negative controls. GitNexus MCP could not read the existing index because its runtime uses storage version 40 and the index uses version 42. The working CLI reported the newly introduced targets absent from the index, with risk `UNKNOWN`; no existing indexed functions were changed and the index was not rebuilt.

`stored_at` is assigned within the transaction. It is not a commit timestamp. The observed visibility test proves atomic publication of this result and its members only. Artifact retention does not prove bundle completeness, trusted execution or source authenticity. Durable qualification transitions, exact committed decision-read snapshots, reverse-commit reconstruction and consumer parity remain work for the next layer. FPI activation is outside this leaf.
