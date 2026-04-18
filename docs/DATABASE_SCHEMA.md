# Database schema

Primary SQL source in repo: `sql/schema.sql`. **Reality:** none of the live tables include a `strategy_id` column today. Multi-strategy is a **forward** concept; see [[PROJECT_OVERVIEW]].

**Important mismatch with the Next.js type layer:** `web/lib/types/regime.ts` defines a `RegimeLabel` union (`NEUTRAL`, `TRENDING_LONG`, …). The pipeline persists **`regime_calls.regime` from composite label strings** such as `STRONG USD STRENGTH`, `MODERATE USD STRENGTH`, `NEUTRAL`, `VOL_EXPANDING` (IV override), and INR-specific labels from `inr_pipeline.py` (`STRONG DEPRECIATION PRESSURE`, etc.). UI code must treat `regime` as **string** from the database and not assume it matches the TypeScript union until a mapping layer exists.

## Live tables (in `sql/schema.sql`)

### `signals` (LIVE)

Daily wide-row per pair. **This is the live signal table name** (not `signal_values`). Upserted from Python (`core/signal_write.py` via merge step).

| Column | Type | Notes |
|--------|------|--------|
| `id` | SERIAL PK | |
| `date` | DATE | Part of unique key `(date, pair)` |
| `pair` | VARCHAR(10) | `EURUSD`, `USDJPY`, `USDINR` |
| `spot` | FLOAT | |
| `rate_diff_2y` | FLOAT | |
| `rate_diff_10y` | FLOAT | |
| `rate_diff_zscore` | FLOAT | |
| `cot_lev_money_net` | BIGINT | |
| `cot_asset_mgr_net` | BIGINT | |
| `cot_percentile` | FLOAT | |
| `realized_vol_5d` | FLOAT | |
| `realized_vol_20d` | FLOAT | |
| `implied_vol_30d` | FLOAT | |
| `vol_skew` | FLOAT | |
| `atm_vol` | FLOAT | |
| `risk_reversal_25d` | FLOAT | |
| `oi_delta` | INT | |
| `oi_price_alignment` | VARCHAR(10) | |
| `cross_asset_vix` | FLOAT | |
| `cross_asset_dxy` | FLOAT | |
| `cross_asset_oil` | FLOAT | |
| `created_at` | TIMESTAMPTZ | Default `now()` |

**RLS:** `SELECT` allowed for anon (`public_read_signals`).

**Upsert conflict target:** `(date, pair)` unique index `idx_signals_unique`.

### `regime_calls` (LIVE)

Written by `core/regime_persist.persist_regime_calls_and_brief` after the text brief is available (invoked from `morning_brief.py`).

| Column | Type | Notes |
|--------|------|--------|
| `id` | SERIAL PK | |
| `date` | DATE | With `pair` unique |
| `pair` | VARCHAR(10) | |
| `regime` | VARCHAR(30) | Composite label text, not the small `RegimeLabel` union |
| `confidence` | FLOAT | Derived from composite score magnitude (`_conf_from_score` in `regime_persist.py`, clamp `0..1`) |
| `signal_composite` | FLOAT | |
| `rate_signal` | VARCHAR(10) | `BULLISH` / `BEARISH` / `NEUTRAL` style strings |
| `cot_signal` | VARCHAR(10) | |
| `vol_signal` | VARCHAR(10) | |
| `rr_signal` | VARCHAR(10) | Not populated in `_regime_row` today (column exists) |
| `oi_signal` | VARCHAR(10) | Not populated in `_regime_row` today (column exists) |
| `primary_driver` | TEXT | |
| `created_at` | TIMESTAMPTZ | Default `now()` |

**RLS:** anon `SELECT` policy `public_read_regime`.

**Upsert conflict target:** `(date, pair)` unique index `idx_regime_unique`.

### `validation_log` (LIVE)

Written by `validation_regime.py` (next-trading-day validation).

| Column | Type | Notes |
|--------|------|--------|
| `id` | SERIAL PK | |
| `date` | DATE | |
| `pair` | VARCHAR(10) | |
| `predicted_direction` | VARCHAR(10) | |
| `predicted_regime` | VARCHAR(30) | |
| `confidence` | FLOAT | |
| `actual_direction` | VARCHAR(10) | |
| `actual_return_1d` | FLOAT | |
| `actual_return_5d` | FLOAT | |
| `correct_1d` | BOOLEAN | |
| `correct_5d` | BOOLEAN | |
| `notes` | TEXT | |
| `created_at` | TIMESTAMPTZ | Default `now()` |

**RLS:** anon `SELECT` policy `public_read_validation`.

**Upsert conflict target:** `(date, pair)` unique index `idx_validation_unique`.

### `brief_log` (LIVE)

Upserted in `regime_persist.py` with desk brief text and per-pair regime snapshot fields.

| Column | Type | Notes |
|--------|------|--------|
| `id` | SERIAL PK | |
| `date` | DATE | Unique per day |
| `brief_text` | TEXT | Cleaned brief, length capped in Python |
| `eurusd_regime` | VARCHAR(30) | |
| `usdjpy_regime` | VARCHAR(30) | |
| `usdinr_regime` | VARCHAR(30) | |
| `macro_context` | TEXT | First-line excerpt |
| `created_at` | TIMESTAMPTZ | Default `now()` |

**RLS:** anon `SELECT` policy `public_read_brief_log`.

**Upsert conflict target:** unique on `date` (`idx_brief_log_date`).

### `paper_positions` (LIVE schema, PLANNED pipeline use)

Defined in `sql/schema.sql` with full position lifecycle columns. **No Python references** found in repo grep at doc time: treat as **schema ready, application not wired**.

**RLS:** anon `SELECT` policy exists.

### `pipeline_errors` (LIVE)

| Column | Type | Notes |
|--------|------|--------|
| `id` | SERIAL PK | |
| `date` | DATE | Default `CURRENT_DATE` |
| `source` | VARCHAR(50) | |
| `pair` | VARCHAR(10) nullable | |
| `error_message` | TEXT | |
| `notes` | TEXT | |
| `timestamp` | TIMESTAMPTZ | Default `now()` |

**RLS enabled** but **no anon SELECT policy** in `sql/schema.sql` (internal operator visibility via service role).

## PLANNED tables (not in `sql/schema.sql`)

The following appear in product discussions but **do not exist** in the committed schema file:

- `strategies`
- `signal_definitions`
- `call_rationale` (append-only rationale ledger)
- `hypothesis_log`
- `methodology_versions`
- `divergence_log`

Treat any SQL snippets for these in archived docs under `_archive/v1/docs/` as **design drafts**, not production schema.

## strategy_id architecture

**PLANNED.** No `strategy_id` column exists on live tables today. The Next app uses string strategy id `fx-regime` in constants only.

## Immutability and timestamps (policy vs code)

- **`call_rationale`:** PLANNED table; append-only rule is a **design target**, not enforced in DB yet.
- **`validation_log.created_at`:** Database default `now()`. Python upserts should not fabricate historical timestamps.
- **General:** validation and regime persistence should not backdate `date` fields to pretend a run happened on an earlier calendar day.

## Index recommendations aligned to actual queries

Queries in `web/lib/supabase/queries.ts` and hooks:

- Latest row per pair ordered by `date` descending: composite index on `(pair, date DESC)` is ideal; repo has `(date, pair)` indexes. Postgres can still use `idx_*_date_pair` efficiently for `eq('pair')` + `order date desc`; verify `EXPLAIN` under load.

- `brief_log` latest by `date`: unique on `date` already supports “top 1 by date”.

## Related docs

- [[SIGNAL_DEFINITIONS]]
- [[PIPELINE_REFERENCE]]
- [[FRONTEND_ARCHITECTURE]]
