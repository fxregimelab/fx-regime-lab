# Atomic publication writer — local repair

The central writer now submits the call, its complete signal snapshot and its rationale in one database operation. Both the legacy daily path and the staged production adapter use this boundary. A failed receipt or database error propagates before publication notices. There is no fallback to a call-only insert.

The writer checks the locked pair, matching call/signal date, explicit source/model/strategy, published direction, predecessor identity shape and finite JSON before database access. Mutable notes are detached. The database owns the durable ID and semantic conflict decision. Core persistence preserves the caller's provenance instead of forcibly relabeling historical work as live. Rationale records the actual published confidence and quality score; confidence is described as heuristic.

Historical bulk publication preflights the entire batch, requires backtest provenance, and appends through the same boundary. A database failure may leave an already committed prefix; exact retries are resumable through database identity checks. It never deletes original calls or disables protections. Forced date purging and call-only publication reject before I/O. Retrospective rationale can insert a missing row or accept identical existing content, but cannot overwrite an explanation.

## Checks

The parent independently reran the declared writer/daily-contract gate: 44 tests passed. It covers invalid inputs and receipts, detached full snapshots, one RPC, propagated failures, bulk preflight and retry, retired writes, immutable rationale and correct core provenance. Scoped tests use mocks; database atomicity is established separately by `repair-atomic-publication-db.md` and its real PostgreSQL verifier. Staged integration has its own independently rerun gate and report. Source search found no remaining production caller of the retired call-only writer.

The full pipeline Ruff and MyPy checks passed, with 172 source files checked by MyPy. Whole-suite acceptance is recorded in the current repair checkpoint after execution.

## Review boundaries

Publication identity now includes source, strategy and model. Existing current-call readers that filter only pair/date need explicit live/version selection before release. Original legacy calls without bound evidence remain legacy; the new boundary cannot manufacture their original inputs. Existing model names must be revised for changed inference before release. Direct signal observations for withheld stress calls remain a current projection, not a published call's authoritative evidence.

The migration has not been deployed. This packet does not establish complete historical migration safety, point-in-time source availability, forecasting skill, notification deduplication or production acceptance. Keep L01/L02 and the wider repair goal open until their full integration and release evidence is accepted.
