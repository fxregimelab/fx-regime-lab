# Quote storage writer — packet 15

The central database writer now has separate entrypoints for response captures and acquisition snapshots. Both validate before acquiring the database client, send exact canonical unsigned JSON text and its SHA-256 fingerprint, and require a complete matching receipt. Captures keep their existing identity; snapshots bind the actual pure constructor output and the caller's implementation/client labels. Those labels are provenance assertions, not proof that a particular implementation executed.

Each call uses one RPC and has no table-write fallback. Snapshot writing does not upload missing pages: acquisition must preserve each response first, then append its terminal snapshot. A failed snapshot therefore cannot be mistaken for successful archival, and it does not authorize erasing already captured pages. Actual database atomicity, privileges and retry behavior are checked by the separate PostgreSQL verifier.

Snapshot input rejects an empty or excessive page collection, malformed pages, invalid provenance labels and mixed pair/window identity before I/O. Duplicate or failed pages can still produce an explicit incomplete diagnostic snapshot. Its quote prices remain null and validation eligibility remains false. Repeating the same inputs and as-of time retains the snapshot fingerprint; changing as-of creates a new snapshot while preserving the source input fingerprint.

Storage bounds are explicit: 32 MiB for a serialized capture, 1 MiB for a serialized snapshot and at most 10,000 ordered page occurrences. The test suite exercises a real Unicode response under the 16 MiB raw-body limit whose escaped representation exceeds the storage limit; the writer rejects it before opening a client instead of truncating it.

## Verification

The 35 writer tests pass. They cover exact capture reconstruction, fingerprint equality, constructor-to-writer equivalence, detached inputs, three-pair identity, stable retries, revised as-of identity, incomplete duplicate snapshots, invalid receipts, pre-I/O rejection and failure propagation without fallback. Scoped Ruff and strict MyPy pass. Integrated capture/constructor/writer checks pass 148 tests after the text-storage amendment. Parent independently reverified the actual PostgreSQL writer bridge, retries, concurrency, rollback, permissions and lineage. The full pipeline gate passes with 889 tests collected; full Ruff and MyPy (191 source files) pass. Six root completion requirements remain open.

GitNexus reports the new writer functions as unindexed with UNKNOWN risk. The inspected consumers are the new tests and local PostgreSQL verifier; existing publication/validation callers are unchanged. No market acquisition, production database write, acceptance event or price promotion has occurred. The storage contract is [recorded separately](../docs/QUOTE_STORAGE_CONTRACT.md).
