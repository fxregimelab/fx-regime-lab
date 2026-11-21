# FPI storage request timeouts — leaf 29.2

Local self-verification passed on 28 September 2026 in the shared `codex/frontend` checkout at `9fa1505`. Parent acceptance remains pending. This packet changes three private storage entry points; it does not activate FPI or establish deployed connection settings.

Migration `20260928000013_fpi_storage_timeouts.sql` replaces `append_fpi_capture(text,text)`, `append_fpi_artifact(text,text)` and `append_fpi_parse_result(text,text,text)`. Each checks the inherited `pg_settings.statement_timeout` before decoding, hashing, acquiring evidence locks or writing. Values outside 1–30000 milliseconds are refused. Each function sets its local `lock_timeout` to 10 seconds. No function sets `statement_timeout`: the caller must arm the request timer before the top-level command arrives. This configuration guard cannot authenticate the timer state of a hostile nested caller.

The verifier compares each replacement with its original definition from migrations 10 and 11 after removing only the exact guard and local lock setting. The remaining source must match exactly. It also rejects any migration statement beyond those three definitions and the transaction boundary. Historical migrations, receipts, fixed search paths, security mode, permissions and stored evidence are preserved.

GitNexus upstream checks for all three SQL functions returned `Target not found` and `UNKNOWN`. This provides no caller or process coverage. Manual review traced the existing SQL storage bodies and their fixture inputs. The shared index was not rebuilt. The parse helper was read before import; it starts no database work at import time. The imported FPI codecs are pure. No legacy database verifier or central writer module is imported.

The parent confirmed PostgreSQL 17.11 readiness on the existing WSL socket, port 55437, with empty `listen_addresses` before the verifier ran. All checks used a uniquely named disposable database and explicitly synthetic evidence. The parent owns server shutdown. The verifier drops its database with `FORCE` in `finally` and exits persistent psql clients through `ROLLBACK` and `\q` when possible.

Seven scenario groups passed:

- The earlier definitions accepted insertion and exact retries at timeout 0 for all three RPCs. After replacement, those same request bytes were refused at 0 and 30001, while 30-second retries retained their receipts.
- Fresh valid requests were refused at both invalid settings with all four archive tables unchanged; 30-second insertion and exact retry then succeeded for each RPC. There were 12 unchanged-state timeout refusals across retained and fresh requests.
- Scratch triggers observed the 10-second lock setting inside actual writes. Persistent caller sessions retained their original 77-millisecond lock setting after both successful calls and caught guard refusals.
- All three RPCs waited on observed ungranted relation locks and were canceled by PostgreSQL with SQLSTATE `57014` and its statement-timeout diagnostic under an inherited 3000-millisecond timer. Process timeouts were only harness bounds. The archive remained unchanged, and insertion/retry succeeded after lock release.
- The parse cancellation blocked the membership table after inserting the result row. A scratch sequence advanced from an `AFTER INSERT` trigger, proving the result insertion was reached even though the transaction rolled back. No partial result or membership survived.
- Anonymous and authenticated roles could neither read the private tables nor execute the RPCs. All three application roles were denied direct table writes. Owner update, delete and truncate attempts hit immutable triggers; the public role had no RPC execution grant.
- Reapplication on populated storage preserved exact evidence, function ownership and grants, table grants, row security, policy definitions and immutable triggers. No other public function body or configuration changed.

Configured standalone Ruff and strict MyPy checks pass. Leaf G1 was executed and reverified through the Unlazy checker: output SHA-256 `7359636d904821b1d7de2aef7fc40ecd620913dcd0ac137a9d3def9160a42230`, 875 bytes, marker `FPI_STORAGE_TIMEOUTS_VERIFIED`. The leaf ledger has one met gate, one pending parent gate, and zero abandoned gates. The checker exits 1 because G2 remains pending; the G1 command exits 0.

Artifact SHA-256 values:

| File | SHA-256 |
| --- | --- |
| Migration 13 | `34f5faea73331cf90760b412620f13342b473e35983855ee0d8349300c998267` |
| Storage timeout verifier | `a4bf56826291f184e8d4e74f3fbd06d8be77183f19045e06f2ff0d45971713d0` |
| Unchanged migration 10 | `6f5052635b24fd1b8f11d279b8c2706c274fd7161787a2b7745dcbf560978d12` |
| Unchanged migration 11 | `0a3e6fa6af5ef498a85e9b1f9baa9e2998cd116ad0477c81d2d89690fef6a675` |

Parent testing can set `MIGRATION_SQL` in memory. To exercise the behavioral oracle beyond source-preservation checks, replace `GUARD` with a syntactically matching false condition and update the module's `GUARD` constant to the same text. The actual timeout-refusal checks must then fail. G2, full repair acceptance, deployed request setup and all release actions remain outside this leaf's self-verification.
