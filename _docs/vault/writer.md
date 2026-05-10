# writer

## Purpose
**ALL Supabase writes go through here.** The single point of persistence for the entire pipeline.

## File
`pipeline/src/db/writer.py` (~1276 lines)

## Key Functions

### `write_regime_call(call)`
Inserts a regime call into `regime_calls`. **Append-only.** Checks for existing row before insert to avoid immutable trigger errors.

### `write_signal_row(row)`
Upserts a signal row into `signals` on `(pair, date)`.

### `write_validation_row(row)`
Upserts a validation log entry. Guards against overwriting existing T+5 data.

### `write_validation_stats(row)`
Upserts aggregate stats into `validation_stats` on `(as_of_date, pair)`.

### `get_historical_prices(pair, limit)`
Returns price history oldest-first for time-series walks.

### `get_validation_log_for_stats(pair_filter, lookback_days)`
Fetches validation rows for aggregate statistics.

## Why Centralized Writes

1. **Audit trail:** Every write goes through one function. Debugging is trivial.
2. **RLS safety:** Service-role key is used here and only here. No accidental anon writes.
3. **Immutability:** The writer checks for existing rows before inserting regime_calls, preventing trigger errors.
4. **Schema evolution:** If the schema changes, only this file needs updating.

## Connections
- **Called by:** [[orchestrator]], [[validation_backfill]], [[batch_validation_backfill]], [[batch_validation_stats]], [[simulation_engine]]
- **Writes to:** [[Database]] (all tables)
- **Tests:** `tests/test_writer.py`

## Sacred Rule

> No module outside `db/writer.py` may call `supabase-py` directly.

This is a **locked decision**. If a new fetcher needs to write to the database, it calls `writer.write_*()`. No exceptions.
