# Public publication readers — leaf 10.2

## Result

Public call readers now select only `live` / `v2` publications for EURUSD, USDJPY and USDINR, with a UTC-today cutoff. Each pair uses its own bounded query ordered by date descending and durable call ID descending. This prevents a heavily revised pair from hiding another pair.

Public history applies the same provenance, pair and cutoff rules. It reads in pages before choosing the greatest call ID for each date and before applying the requested session limit. Returned rows retain both durable call ID and model version. The pair history UI displays the model version, including an explicit unlabeled state for legacy records.

Signal rendering is bound to the already selected call set. `getLatestSignals` queries only `live_publication_signals` for those exact call IDs. It does not query or fall back to the mutable `signals` projection. The reader verifies call ID, pair and date across the selected call, public view row and embedded payload. Missing evidence stays absent; inconsistent or malformed identity raises an error. Evidence payloads do not invent a database timestamp: `created_at` is `null` because the stored Python `SignalRow` snapshot has no such field.

The home, desk overview and pair routes select calls first and pass that same set into the signal reader. The desk layout no longer makes an unused independent signal query. Owned pages and each desk signal card show `INPUTS UNAVAILABLE` when a selected legacy call has no immutable signal evidence. Signal-card exports include the durable call ID, honest model version and immutable view provenance. Their regime streak counts observed publication sessions, including the current session, rather than claiming calendar days.

The generated database type now contains only the public view's four columns: `call_id`, `pair`, `date` and `signal_payload`. No rationale, execution advice, hash or correlation metadata is exposed by this type.

## Evidence

- `node --test --test-reporter=tap tests/publication-queries.test.mjs`: 8 passed, 0 failed.
- `node --test --test-reporter=tap tests/validation-queries.test.mjs`: 10 passed, 0 failed. This confirms the existing complete validation reader behavior remains intact.
- `npx tsc --noEmit`: passed.
- Scoped `npx biome check` across the seven owned TypeScript/TSX files and the new query test: passed after formatting.
- `git diff --check` on owned implementation files: passed.

The publication query suite covers future rows, backtests, missing provenance, other strategies, an unsupported pair, multiple models on one date, more than 1,000 revisions, history pagination before deduplication, exact signal call IDs, a newer unrelated snapshot, missing evidence, identity mismatch and query failures. It also checks that owned routes cannot call the signal reader without their selected call set.

GitNexus reported CRITICAL impact for the three reader functions, owned route entry points and `SignalCard`. Its trace mixed same-named TypeScript and Python symbols, but it correctly identified broad public UI impact. The implementation therefore keeps existing public return shapes except for the required durable call ID, history model label and nullable evidence timestamp. The repository-wide change scan is also CRITICAL because the shared worktree contains 60 files and 408 changed symbols from the wider repair; this leaf did not modify files outside its nine-file ledger.

## Remaining boundaries

The parent owns the SQL view, PostgreSQL role/immutability checks, full frontend build and complete pipeline regression. No database, credential, network, AI, production, runtime, commit, push or deployment action was performed here.

The compact desk history remains a sparkline and streak summary rather than a row-by-row ledger. It now labels the current model and the history as revised publication history; the pair page provides each session's model/version label.
