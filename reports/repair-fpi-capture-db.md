# Private FPI capture database storage — leaf 22.2

The forward migration adds one private, append-only table for complete NSDL FPI HTTP response bytes. It keeps the submitted JSON text exactly, stores a parsed JSONB copy for inspection, and verifies both the document SHA-256 and the decoded response-body SHA-256 before insertion. It does not parse HTML, qualify an observation, assign source release time, or activate an FPI feature.

## Dependency audit

Before the schema was written, searches across `pipeline/src`, `web/src`, existing migrations and `docs/DB_STATUS.md` found no `fpi_captures` or `append_fpi_capture` consumer. The existing `signals.fpi_flow` column is a legacy signal value, not a raw-capture storage dependency. The new writer calls only `append_fpi_capture`; the table has no path into signals, historical prices, regime calls, validation or public readers.

GitNexus found no indexed symbol for the new RPC, helpers or verifier entry points. It reported zero callers and `UNKNOWN` risk, which is expected for new database objects and does not mean schema work has no risk. Supabase exposes the `public` schema, so the migration uses explicit table/function revocations and RLS rather than relying on naming or convention for privacy.

The final repository-wide `detect-changes` scan reported `critical` because the shared checkout already contained 93 modified files and 606 changed indexed symbols across the broader repair. The three owned files are new and untracked, so that scan did not attribute an indexed process to them. This global result is not evidence that leaf 22.2 changed those existing symbols.

## Stored contract

`fpi_captures` stores the capture identity, authoritative `document_json`, parsed `document`, fixed source URL, request and retrieval times, raw-body identity, decoded size, HTTP status and database-assigned `stored_at`. The two required indexes cover source/retrieval lookup and raw-byte identity lookup.

The security-definer RPC validates the 7,000,000-byte document limit before parsing, recursive duplicate JSON keys, the exact field set and primitive types, the two production HTTPS URLs, strict UTC timestamp spelling and time order, integer lexical forms and bounds, canonical padded Base64, the 5,000,000-byte decoded limit, decoded size, raw hash and exact document hash. Integer checks use the original JSON lexemes because JSONB would normalize values such as `2e2` and `200.0` to an integer-looking value. All caught failures return one fixed message and do not echo submitted JSON or decoded bytes.

Exact retries keep the original `stored_at`. Concurrent identical calls return one insertion and one retry with the same receipt. A matching identity with different retained text rejects. UPDATE, DELETE and TRUNCATE triggers refuse owner mutations. RLS and grants give `service_role` read access and the exact RPC, while direct writes, helper execution and anonymous/authenticated access remain denied.

## Verification

The final commands from the repository root were:

```powershell
python scripts/repair/verify-fpi-capture-db.py
python -m ruff check scripts/repair/verify-fpi-capture-db.py
git diff --check -- supabase/migrations/20260927000010_fpi_capture_storage.sql scripts/repair/verify-fpi-capture-db.py reports/repair-fpi-capture-db.md
```

The isolated database run used PostgreSQL 17.11 over the parent's Unix socket at port 55437. It exited zero and emitted `REPAIR_FPI_CAPTURE_DB_VERIFIED`. Scoped Ruff and the diff whitespace check passed. The verifier dropped its unique scratch database in `finally`; a follow-up query found zero `fxfpi_%` databases.

The verifier proved:

- The actual Python `build_fpi_capture` and central `archive_fpi_capture` path wrote through the service-role RPC, retained exact JSON and original NUL/invalid-UTF-8 bytes, and returned a UTC receipt even when the caller session used `Asia/Kolkata` and `SQL, DMY` formatting.
- Exact retry identity and `stored_at`, simultaneous retry behavior, and distinct capture identity for the same bytes retrieved at a later time.
- Empty error-response evidence and the exact 5,000,000-byte body boundary; 5,000,001-byte bodies and documents above 7,000,000 bytes rejected.
- Malformed and duplicate JSON, unexpected/missing fields, boolean/string/float/exponent integer substitutions, URL variants, impossible/non-UTC/future/reversed timestamps, bad hashes, size mismatches, Base64 whitespace/padding errors and nonzero padding bits all rejected without changing a complete-row archive digest or exposing sentinel payloads.
- An injected retained-text conflict rejected without replacing the row.
- Broad pre-existing default grants did not escape the explicit revocations. `service_role` could read and execute only the entry point; anonymous and authenticated roles remained blind even after temporary accidental SELECT grants; helper execution and all application-role direct mutations were denied. Owner UPDATE, DELETE and TRUNCATE attempts hit the immutable triggers.
- Empty and populated migration reapplication preserved every complete capture row, sampled unrelated role permissions, and synthetic price, call, signal, rationale, validation and evaluation sentinels.

The first database run exposed a missing service-role RLS read policy: the table grant existed, but RLS correctly returned no rows. The migration was corrected with a narrow `service_role` SELECT policy, and the complete gate was rerun from a fresh scratch database.

## Limits

The preservation fixture is deliberately bounded and synthetic; it does not recreate the full production migration history. No production database, credentials or provider endpoint was used, and nothing was deployed. The test proves storage consistency and privacy for the current working-tree builder/writer interface. It does not authenticate NSDL, prove source publication or first-seen time, qualify any parsed observation, establish a revision occurrence, or make FPI eligible for forecasting.
