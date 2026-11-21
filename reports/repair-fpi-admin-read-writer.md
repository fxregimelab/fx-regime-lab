# Saved administrative FPI writer and loader — leaf30.3

The central writer implementation is ready for parent verification. Its focused self-check passes 115 cases. Configured Ruff passes, and configured MyPy reports no issues in 229 source files. G1 is met; G2 remains pending and parent-owned. These results establish local fake-transport behavior, not real database integration, production origin, consumer acceptance or release readiness.

The work follows `docs/FPI_SAVED_READ_CONTRACT.md` and `docs/FPI_SAVED_READ_API.md` under the repair priority in `MASTERPLAN.md`. The base checkout was `codex/frontend`, HEAD `9fa150538d08ab5a2a6c587976552944f47a724d`, with prior uncommitted repair work preserved. The parent requested GPT-6-Astra/high for this boundary; the parent dispatch record owns verification of the actual route. This worker did not start or stop Docker, Hermes or PostgreSQL. Local fake-client checks require none of them. No credentials, provider endpoints, AI calls or production database calls were used. No commit, push or deployment was made.

`pipeline/src/db/writer.py` now exposes the three frozen public interfaces:

- `append_fpi_admin_read_policy(policy)` rebuilds the exact policy type and checks every document/derived field before acquiring the client. It submits one `append_fpi_admin_read_policy` RPC with only `p_policy_sha256` and `p_document_json`, then returns the pure validator's detached receipt.
- `capture_fpi_admin_read(request)` performs the same exact reconstruction for the request. It submits one `capture_fpi_admin_read` RPC with only `p_request_sha256` and `p_document_json`, then binds the returned identities and permanent trust fields through the pure receipt validator.
- `load_fpi_admin_read(read_id)` validates the local ID before client acquisition. It reads the nine-field contract projection from `fpi_admin_reads`, with `eq(read_id)` and `limit(2)` to reject non-singleton responses. It verifies canonical manifest/request documents, hashes, policy identity, status, decision ID and the returned UTC instant before dependency queries.

The loader uses **64 requested IDs per batch**. Each dependency query selects only the contract projection, uses an `in_` filter and sets `limit(batch_length + 1)`, at most 65 rows, to expose an extra returned row. The bound stays below the contract's maximum 256 and limits the digest list in a URL to roughly 4.3KB before the other query parameters. Every batch must return exactly its requested identity set. Missing or truncated pages fail with `READ_DEPENDENCY_MISSING`; duplicates, extra IDs and malformed projections fail with `READ_INTEGRITY_ERROR`. There is no retry, fallback, dependency upload or scope refresh.

Artifacts are fetched in separate PARSER and SELECTOR batches. Their retained identity stays `(kind, artifact_sha256)` even when the same body hash exists under both kinds. Rows are detached as exact primitive dictionaries before later query callbacks can modify earlier response objects. No current memberships, latest heads, policy aliases, approvals or provider data are queried.

Actual ASCII document lengths are checked before original decoding: captures and artifacts at most 7,000,000 bytes each, parses at most 4,000,000, and combined capture/parse/artifact text at most 64,000,000. Events are at most 400,000 bytes each and at most 16,000,000 combined. The frozen codec checks the 16,000,000-byte manifest bound, request/policy limits and all declared counts and set relations before dependency loading. Transport truncation cannot produce an accepted read. The loader invokes `verify_fpi_admin_read_originals` exactly once, retaining its original-proof checks. Failed saved reads fetch no dependencies and pass empty original tuples to that verifier.

Errors are fixed strings without raw document logging or displayed exception chains. Synchronous `concurrent.futures.CancelledError`, asynchronous cancellation, keyboard interruption, system exit and memory exhaustion propagate. COMPLETE and failure results retain `UNVERIFIED`, `eligible=false` and `feature=null`.

The fake client implements the real `table/select/eq/in_/limit/execute` sequence. It applies filters, selected columns and a configurable provider row cap before deliberate returned-row corruption. Tests do not replace the core consistency proof. Coverage includes:

- Exact RPC names/payloads, detached receipts, changed receipt fields and exact request retries.
- Every frozen input field, subclassed strings/objects, malformed local IDs and rejection before client acquisition.
- Minimal/empty, complete Monthly support, alternate parses, diagnostics and original qualification events.
- Every saved-row projection with wrong strings, booleans and nulls; missing/duplicate/extra rows and unknown returned fields across all five read tables.
- Same-length body corruption, changed record hashes, altered event text, removed support or absent heads, changed stored times and over-limit originals.
- Mutation of earlier response objects by subsequent callbacks, without changing the detached evidence under verification.
- A genuine 130-capture/130-parse/130-event fixture: each category uses batches `64,64,2`. Its 131 PARSER artifacts use `64,64,3`, followed by one SELECTOR query. The shared parser/selector hash appears in both kind-specific requests. A provider cap of 63 fails at the first dependency page without retry.
- Measured one capture validation per distinct capture, one record-parts validation per distinct parse, one artifact validation per retained artifact, one bulk reference build and one originals-verifier call on successful loads.

Four passes were completed. The implementation pass added the full boundary. Domain review checked permanent administrative authority, immutable replay and complete supporting memberships. Defect review added same-length corruption, real batching, cancellation and callback-mutation controls; it corrected fixture-only capture attribute assumptions and a test that incorrectly expected stored-time errors before the final pure verifier. The final pass checked SQL projection names and RPC parameters, exact-type reconstruction, count/size ordering and the final frozen inputs; it found no remaining source change to make.

GitNexus upstream impact was run for the new public APIs, private helpers and test symbols. They were absent from the shared index and returned `UNKNOWN`; this is missing graph coverage, not evidence of zero risk. The parent was notified. The shared index was not rebuilt. No commit was attempted, so commit-only change detection was not invoked.

Verification commands ran from `D:/Projects/fxregimelab/pipeline` unless stated otherwise:

| Check | Observed result |
|---|---|
| `python -m pytest -q tests/test_fpi_admin_read_writer.py` | 115 passed |
| `python -m ruff check src/db/writer.py tests/test_fpi_admin_read_writer.py` | All checks passed |
| `python -m mypy src/db/writer.py tests/test_fpi_admin_read_writer.py` | No issues in 2 source files |
| `python -m ruff check .` | All checks passed |
| `python -m mypy .` | No issues in 229 source files |
| G1: `node ../scripts/repair/verify-pytest.mjs tests/test_fpi_admin_read_writer.py` | Exit 0; `REPAIR_PYTEST_VERIFIED` matched |
| Gate lint, repository root | Passed; expected warning for manual, parent-owned G2 |

G1 was executed through the inspected unlazy checker with the repository root as its default CWD. Its evidence is recorded in `.unlazy/repair/gates/leaf-30.3.md`: definition SHA256 `0a451d03139fcda82104feb80eae4392be28af71755a22f1e6803102cdbbd965`; successful output SHA256 `1adc71d7561d1d69039311d16514202deb2a1a16aa50947daef164fa94a3578f`; 207 output bytes. Current leaf totals: **1 met, 1 unmet, 0 abandoned**.

Final SHA256 values, verified 29 September 2026:

| File | SHA256 |
|---|---|
| `pipeline/src/db/writer.py` | `2ff396cece9c299f19d279a0d2e63459e4d2d55a05ccc0b6f50158bf644f9391` |
| `pipeline/tests/test_fpi_admin_read_writer.py` | `ae5e2c89641b4a53e6be950da8c68a1efffadf5f209e1180214b81df962f8e9a` |
| Frozen `pipeline/src/research/fpi_saved_read.py` | `4bbdfc64b3f916418d4a3b22a7d6abe67b44daa4656ea691b2ad062bb3679f8b` |
| Frozen `supabase/migrations/20260928000014_fpi_admin_reads.sql` | `fd659bc33ea8f637f43a4904c9b2dfd4fb5f35659945b72e60168c0a413352fe` |

The writer and focused test files are frozen for parent re-verification. The parent still owns G2, real SQL-to-loader parity, independent changed-output controls, final timeout integration and the complete pipeline regression. FPI activation and release remain outside this leaf.
