# Database Hub

> Supabase PostgreSQL 17. All writes go through `pipeline/src/db/writer.py`.

## Core Tables

### `signals`
Immutable daily signal rows per pair.
- PK: `(pair, date)`
- Columns: rate_diff, cot_percentile, realized_vol, spot, composite components

### `regime_calls`
**Immutable regime classifications.** This is the sacred ledger.
- PK: `(pair, date)`
- Columns: regime, confidence, signal_composite, predicted_direction, directional_bias, conviction
- Triggers: `trg_protect_immutable_calls` blocks UPDATE/DELETE

### `validation_log`
**Immutable T+5/T+20 outcomes.**
- Columns: correct_t5, brier_score_t5, log_return_t5_bps, actual_direction_t5
- Triggers: `trg_protect_immutable_validation` blocks UPDATE/DELETE on validated rows

### `validation_stats`
Aggregate statistics (not immutable — upserted on `as_of_date, pair`).
- Columns: win_rate, mean_brier, brier_skill, sharpe_like, calibration_json

### `historical_prices`
Backfilled spot prices from yfinance.
- PK: `(pair, date)`
- Used by: [[simulation_engine]], [[validation_engine]]

### `historical_yields`
Backfilled FRED yields.
- PK: `(series_id, date)`
- Series: DGS2, DGS10, IRLTLT01DEM156N, IRLTLT01JPM156N, INDIRLTLT01STM, T10YIE

## Constraints

| Constraint | Table | Purpose |
|------------|-------|---------|
| CHECK | `regime_calls` | `directional_bias IN ('LONG', 'SHORT', 'NEUTRAL')` |
| CHECK | `regime_calls` | `predicted_direction IN ('BULLISH', 'BEARISH', 'NEUTRAL')` |
| Trigger | `regime_calls` | Blocks UPDATE/DELETE (immutable ledger) |
| Trigger | `validation_log` | Blocks UPDATE/DELETE on validated rows |

## RLS Policies

| Table | Anon SELECT | Service Role |
|-------|-------------|--------------|
| `signals` | Yes | All |
| `regime_calls` | Yes | All |
| `validation_log` | Yes | All |
| `validation_stats` | Yes | All |
| `pipeline_errors` | No | All |

## Connections
- Written by: [[writer]] (the ONLY module allowed to write)
- Read by: [[Frontend]] (via Supabase client)
- Backfilled by: [[simulation_engine]], [[batch_validation_backfill]]
- Schema defined in: `sql/schema.sql`, `supabase/migrations/`
