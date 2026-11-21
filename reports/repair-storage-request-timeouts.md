# Storage request timeout repair — packet31

Local verification passed on PostgreSQL 17.11. Migration15 replaces exactly six current entry points: validation evaluation, regime publication, price observations, quote capture, quote snapshot and quote acquisition events. Each replacement adds an inherited statement_timeout check for 1–30000ms at the start of its body and a function-local lock_timeout of 10s. No function sets statement_timeout.

Removing those two additions reproduces each authoritative definition exactly. Validation comes from migration06, including its v1 dispatcher; the internal v1 helper is unchanged. Signatures, defaults, security modes, fixed search paths, receipts and original body semantics are preserved.

## Evidence

The import-safe verifier uses a unique disposable database on the parent-owned WSL socket server. It strips the fixture's role bootstrap and requires the three existing application roles. It does not start or stop a runtime, alter shared roles, contact providers, read credentials or write to production. Final cleanup left zero databases with this verifier's prefix.

| Check | Observed result |
|---|---|
| Original valid calls with inherited timeout 0 | All six entry points, including both validation versions, insert and retry before migration |
| Refusals with timeout 0 and 30001 | 28 fresh/retry requests rejected with SQLSTATE 22023; complete evidence snapshots unchanged |
| Valid insertion and exact retry | 21 pairs across baseline, bounded requests and post-cancellation recovery; receipt identities and stored rows preserved |
| Actual cancellation and rollback | Seven observed ungranted advisory locks; PostgreSQL returned SQLSTATE 57014 under a 3s inherited request timer |
| Attempted writes | All seven scratch AFTER INSERT triggers advanced a nontransactional sequence; complete evidence snapshots matched after cancellation |
| Caller settings | 14 success/refusal paths observed 10s inside writes and restored 77ms outside; all seven cancellations also restored 77ms and retained the inherited 3s timer |
| Roles and immutable evidence | 143 permission/immutability probes passed, including direct INSERT/UPDATE/DELETE/TRUNCATE denial, denied anon/authenticated RPC execution and private v1 helper access |
| Version behavior | Both validation versions preserve T+5 when T+20 completes, retain one superseded revision and reject changes to completed horizons; publication version identity, explicit predecessor, exact retry and conflicting predecessor refusal pass |
| Populated reapplication | Both repeat applications preserve evidence, function ownership/ACL/security, table grants, RLS, triggers and constraints |

Cancellation reaches the first insert in publication and snapshot storage before their later table writes. Validation cancellation occurs while appending T+20 after T+5 exists, proving rollback of the prior revision's superseded flag as well as the new insert. The price batch contains two rows, so cancellation after its first insert cannot leave a partial batch. Each identical canceled request inserts successfully and retries without further changes after the holder releases its lock.

leaf-31.1:G1 passed with automatic evidence: output SHA-256 371b7e7bf7eef8d59e37ef8c3e90c322f7ef77fb86e7f5cf1008ed36276face1, 1654 bytes. The ledger currently has **1 met, 1 unmet, 0 abandoned**; parent-owned G2 remains pending. The checker exits 1 because G2 is pending, while G1's verifier exited 0 and matched its success token.

Configured standalone Ruff and MyPy pass. Importing the verifier with subprocess execution blocked succeeds; six individual guard-removal mutations fail the source equality check. The parent's actual database guard-removal challenge remains separate. Git diff whitespace checks and an explicit check of the new untracked files pass.

Four passes completed: implementation; exact-body and database semantics review; correctness review with added UPDATE permission/immutability probes and import-safety checks; formatting and final gate verification. Full pipeline/frontend suites were not rerun because those sources are unchanged by this leaf.

## Source and handoff

Base checkout: codex/frontend, 9fa150538d08ab5a2a6c587976552944f47a724d, with existing dirty repair work preserved. GitNexus upstream impact ran for all six symbols; each returned target-not-found and UNKNOWN. The reported zero count is unavailable graph coverage, not evidence of no callers. The shared index was not rebuilt.

| File | SHA-256 |
|---|---|
| supabase/migrations/20260928000015_storage_request_timeouts.sql | bca11ef02f257ec651b587269924c9b1253d6c518ad6510808e06d5f321b0f87 |
| scripts/repair/verify-storage-request-timeouts-db.py | 32cbc79c47d9640e3b4bd9d9a60a6037c7e7cc4c631149a9ab46d9a79cad4123 |
| Authoritative migration04 | bc21d91174aa66fc4dff73787e76eb42b6300aa9134ddf6fe943f9b496e75e9c |
| Authoritative migration06 | ee371e61c379a6d804477da6723f1811dbc023495994ea65c2f04d3b7a488725 |
| Authoritative migration07 | ed8e8c3ce82dd7e84a7306223993caffc6b707570cffc6b63864635fc10525b4 |
| Authoritative migration08 | 22b2c15cef17e9d22e4dc1844c8ab5b256ba47a6ba9f49b59b7eb78d3922d02b |
| Authoritative migration09 | e0e91690c9eef626b30f09b498fb6479c4b76b0e44a7cf043f1edb2853cacc4c |

Run python scripts/repair/verify-storage-request-timeouts-db.py from the repository root. For the gate, use the same root as --cwd and --timeout 600. Parent verification can override MIGRATION_SQL in memory. Suppressing only verify_source lets a deliberate removed-guard mutation reach the database refusal checks.

This establishes local PostgreSQL behavior with the timer armed before each request. It does not prove deployed PostgREST connection/request configuration or that a hostile nested caller has armed the outer timer merely by changing a setting. Deployment, production acceptance and the full historical migration chain remain outside this leaf. No commit, push or deployment occurred; parent owns the running server and G2.
