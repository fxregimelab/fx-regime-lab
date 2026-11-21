# Quote attempt ledger — packet 16

The local database self-check passed on 27 September 2026. The migration preserves durable starts, acknowledged pages and terminal events, including attempts that receive no response. This is private retrieval evidence; it does not qualify a price or permit evaluation.

The worker changed only the migration, verifier and this report. The checkout base was `9fa150538d08ab5a2a6c587976552944f47a724d`; the work remains uncommitted. Independent parent verification and the leaf's manual review gate remain pending at this handoff.

## What changed

`supabase/migrations/20260927000009_quote_acquisition_events.sql` adds one append-only table and one service-role RPC. It stores the exact unsigned UTF-8 text, its fingerprint and a parsed document. A transaction advisory lock serializes each attempt. An identical retry returns `inserted=false`, including after completion; competing content for the same sequence is rejected. No event can follow a terminal event.

The RPC validates exact keys, types, UUID spelling, timestamps, locked pair/instrument/day identity, phase-specific fields, limits and runtime provenance. Runtime manifest JSON must be canonical and identify the exact five source files and two dependency versions. Its exact bytes must match the implementation fingerprint. Numeric fields reject booleans, fractional JSON numbers and exponent spelling.

A page must reference an existing capture with the expected index and identity. Its request must occur at or after the preceding event; its receipt must occur at or before its own page event. Stored response sizes must fit both the individual page cap and the accumulated byte cap. A terminal snapshot must already exist and match the attempt's ordered page list, identity, source fingerprint, client version and time. Completion requires complete acquisition; failed attempts can retain diagnostic snapshots.

The table has RLS, service-role SELECT and RPC-only writes. Anonymous and authenticated roles cannot read it or execute the RPC. Private storage helpers remain private. Owner UPDATE, DELETE and TRUNCATE operations are refused. Reapplication replaces only this migration's function, triggers, policy and grants; earlier records and unrelated grants remain intact.

## Observed checks

Command: `python scripts/repair/verify-quote-acquisition-db.py`

Result: exit 0, `REPAIR_QUOTE_ACQUISITION_DB_VERIFIED`, PostgreSQL `17.11 (Ubuntu 17.11-1.pgdg24.04+2)`. The final run rejected **174** malformed or inconsistent direct SQL cases, with the event table unchanged after each rejection.

| Group | Evidence |
|---|---|
| G1 — Python bridge | Actual event builder, capture constructor, snapshot constructor and central writers call PostgreSQL as service_role. Stored text and documents round-trip exactly. All three pairs and zero-response failures persist. Exact retries remain stable after terminal completion. |
| G2 — schema and provenance | Missing/extra/duplicate keys, hashes, scalar types, integer spelling, timestamps, limits, oversized envelopes and malformed/noncanonical runtime manifests reject. Noncanonical outer JSON text still retains its exact original bytes. SQL errors omit the sensitive test sentinel. |
| G3 — lineage | Wrong predecessors, missing captures, wrong indexes, changed identity/limits/provenance, receipt ordering, pre-attempt and pre-acknowledgement requests, page/byte caps and invalid terminal transitions reject. Wrong snapshot order, membership, source, version, time and incomplete acquisition reject; a diagnostic failed snapshot persists. |
| G4 — concurrent writes | Two overlapping exact terminal writes produce one insert and one retry. Two differing terminal writes at the same sequence produce one winner and one rejection. The transaction retains its lock long enough to exercise contention. |
| G5 — privacy and immutability | Real roles exercise read/write/COPY/RPC/helper denial. RLS still hides rows when SELECT is temporarily granted. Owner UPDATE/DELETE/TRUNCATE fail. The RPC is SECURITY DEFINER with a fixed search path and no PUBLIC execution grant. |
| G6 — rollback and reapplication | An injected AFTER INSERT failure rolls back the new event. Fresh and populated migration reapplication preserve exact events, captures and snapshots. Original call, signal, rationale, price, validation and evaluation sentinels and unrelated table grants remain unchanged. |

The same run also executes the real `acquire_quotes` function with synthetic injected transports for two-page success and zero-response failure. Database queries inside the transport prove the start or prior page event is durable before each request. All responses close. Snapshot membership matches acknowledged events; no credential or opaque cursor appears in event storage. This uses actual central persistence functions and PostgreSQL, with no provider request.

`python -m ruff check scripts/repair/verify-quote-acquisition-db.py` passed. Parsing the verifier with Python's `ast.parse` passed. The verifier creates a unique `fxattempt_` database and drops it in `finally`; it neither starts nor stops the parent-owned socket runtime. Binary subprocess pipes preserve UTF-8 text and newlines on Windows.

## Review and limits

The four leaf passes covered full implementation, contract parity, adversarial defects and final cleanup. Review added lexical integer tests and canonical manifest checks, then the parent's request-order and byte-budget amendments. A test initially used the canonical serializer for `0.0`, which normalized it to `0`; the negative test now sends original JSON number spelling. The amended complete run passed after that correction.

GitNexus reported the new RPC and new verifier entrypoint as unindexed, with risk UNKNOWN and no indexed callers. The dependency review covered the frozen acquisition/storage contracts, the complete prior storage migration and its verifier. No existing function, trigger or grant definition was edited outside the new migration's scope.

These checks prove behavior in an isolated local PostgreSQL database. They do not prove deployment, a scheduled run, provider behavior, observation history or forecast accuracy. SQL validates stored bytes and relationships, not that the recorded source code actually executed. The runtime fingerprint identifies observed disk files and installed versions; it is not an attestation of in-memory execution. SQL also relies on packet 15 for valid capture/snapshot storage and does not recompute quote arithmetic.

The acquisition deadline bounds network work and iteration. Synchronous database archive operations use their client timeouts and are not cancelled midway to claim a hard end-to-end deadline. A database failure can leave an attempt unfinished when even a terminal event cannot be saved. The parent owns broader transport tests, the full pipeline suite and release acceptance.

## Source fingerprints at handoff

SHA-256 values below were read from disk after the amended passing run. Shared transport development was still active; the parent must reverify the final integrated source state.

| File | SHA-256 |
|---|---|
| `supabase/migrations/20260927000009_quote_acquisition_events.sql` | `e0e91690c9eef626b30f09b498fb6479c4b76b0e44a7cf043f1edb2853cacc4c` |
| `scripts/repair/verify-quote-acquisition-db.py` | `613d285fcc3e89666944ec54d15ef890232434946889e5de0ac6f6d93935d33d` |
| `scripts/repair/verify-quote-storage-db.py` (verifier utility dependency) | `23acf6e1cc3e3eae17deff03736bca64a910d58fb51422851db58babb87b8cf5` |
| `pipeline/src/research/quote_attempt.py` | `f9f8a0248d3ed00e3e84a6c0d7b1206c9e22dca2b2dc835a14926ff567cf20d7` |
| `pipeline/src/research/quote_acquisition.py` | `e991de9ae99c19d51b817face31c94fecb84b2a0b851b2a7755e4ee2a01b28f4` |
| `pipeline/src/research/quote_capture.py` | `fd1007f4f15bbfa07d2de30df6ae59462c1d38a599224a3b0b0bdb25884dddbe` |
| `pipeline/src/research/quote_reference.py` | `3529aac69e7cb0af68ed6a0884dc440a348cdf4bc259d1238dbcf190213844f0` |
| `pipeline/src/db/writer.py` | `9cc02b385adc0193c46cd9c79e39b92772f3c8ef4d5d048748e880b14913d942` |

## Independent parent acceptance

The parent reviewed the final integrated source and independently re-executed the leaf gate. The final PostgreSQL bridge and all six groups passed with 174 rejection cases. The final transport gate passed 39 tests; the full pipeline gate passed with 1003 tests collected, and full Ruff/MyPy195 passed. PostgreSQL was stopped after zero scratch databases and other client sessions were confirmed. Source-only worker checks were not treated as full integration acceptance. No production/research acceptance is implied.

Final integrated acquisition source SHA-256: `a94813e6e6ea80f974ec4b046ac393a0a2cb4538430e0203856543e548b707c2`.
