# FPI capture constructor and central writer

## Result

Leaf 22.1 now has a private, byte-exact HTTP capture envelope and one central writer entry point. The implementation accepts only the two frozen NSDL report URLs. It preserves arbitrary response bytes as standard padded Base64, binds the full canonical document to a SHA-256 identity, and validates every claim again before database access.

`archive_fpi_capture` sends one `append_fpi_capture` RPC with only the capture identity and authoritative JSON text. It accepts a new-row or exact-retry receipt, checks the returned identity and UTC storage time, returns a detached dictionary, and replaces client or provider errors with a fixed message.

This layer does not parse the report, establish first-seen time, prove source release time, select an observation, or activate FPI in the signal pipeline.

## Four-pass review

1. **Contract trace:** checked the frozen field set, exact URL allowlist, UTC normalization, temporal order, HTTP status type and range, 5,000,000-byte body limit, canonical Base64, byte count, raw hash, document hash and 7,000,000-byte document limit. Empty and invalid UTF-8 bodies remain valid capture evidence.
2. **Adversarial validation:** tests reject altered hashes and fields, duplicate or extra JSON keys, noncanonical text and Base64, booleans, floats, exponent-form numbers, invalid and overflowing timestamps, query or fragment URLs, oversized bodies, oversized documents and deeply malformed JSON.
3. **Writer boundary:** tests prove validation happens before client creation, exactly one RPC is used, no table fallback occurs, `inserted=false` retries are accepted, receipts are detached, malformed or early timestamps are rejected, and provider details are not exposed through exceptions.
4. **Integration and scope:** the existing quote-storage writer suite still passes. Ruff, strict MyPy, Python compilation and the focused repair gate pass. The GitNexus CLI reports an index for HEAD `9fa1505`, but that index does not cover the shared dirty worktree or these untracked new APIs. The new symbols therefore return `UNKNOWN`; this is not evidence of zero downstream risk. The MCP path was also unavailable because storage version 42 does not match runtime version 40. Direct source inspection and focused tests provide the change coverage for this leaf. The shared writer's pre-existing changes were retained.

## Verification

- `node ../scripts/repair/verify-pytest.mjs tests/test_fpi_capture.py` — 47 passed; `REPAIR_PYTEST_VERIFIED`
- `python -m pytest -q tests/test_quote_storage_writer.py` — 35 passed
- `python -m ruff check src/research/fpi_capture.py src/db/writer.py tests/test_fpi_capture.py` — passed
- `python -m mypy src/research/fpi_capture.py src/db/writer.py tests/test_fpi_capture.py` — passed with no issues
- `python -m compileall -q src/research/fpi_capture.py tests/test_fpi_capture.py` — passed

The pytest autouse network guard was active. No provider request, credential, production database, Docker or Hermes runtime was used.

## Remaining acceptance boundary

The separate SQL migration and isolated PostgreSQL verifier own database-side hashing, permissions, RLS, immutable retry behavior and concurrent receipt checks. This leaf does not claim those database properties. It also does not prove historical availability or make any captured response feature-eligible.
