# Quote attempt schema and central writer — packet 16

The new helper builds detached, hash-bound events for started, saved-page and finished states. It rejects unknown fields, noncanonical identities/timestamps, invalid limits, malformed source manifests and impossible local phase combinations before database access. The database adds predecessor, concurrent-write and capture/snapshot lineage checks.

The runtime manifest fingerprints five fixed repository files and the observed Python/aiohttp versions. Missing source files fail; no fallback fingerprint is invented. It describes disk artifacts and dependency labels, not an attestation of in-memory execution or provider authenticity.

The central writer sends one exact canonical unsigned document to the private RPC. It checks the event identity, attempt ID, integer sequence and boolean inserted receipt. Exact duplicate receipts are valid at this layer; the HTTP runner separately refuses to restart an existing attempt. Database failures raise a generic error without exposing the original exception chain. No fallback table write exists.

## Evidence

The initial parent suite passed 75 focused tests. The independently executed leaf command also passed these tests together with the 35 existing quote-storage writer tests. Scoped Ruff and MyPy passed. These checks cover exact serialized bytes/hash, altered-but-rehashed fields, limits, phases, dependency/source changes, missing files, receipt corruption, privacy and caller mutation.

Parent independently reverified the final 110-test helper/storage-writer gate and the 39-test transport gate. The actual PostgreSQL event/writer bridge and full synthetic acquire_quotes-to-writers-to-SQL integration passed, including 174 rejection cases. Full pipeline gate passes with 1003 tests collected; full Ruff/MyPy195 pass. The packet is accepted locally; the wider repair goal remains active.

## Limits

Local validation cannot prove predecessor durability or snapshot membership; those are SQL responsibilities. All results remain private provisional evidence. No market request, qualified price, point-in-time research result, release or live reliability window is established by these tests.
