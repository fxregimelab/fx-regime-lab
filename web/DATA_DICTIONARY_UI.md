# FX Regime Lab — Comprehensive Data Dictionary & UI API Specification

> Generated: 2026-05-07  
> Scope: Database → Frontend data flow for UI builders  
> Sources: `database.types.ts`, `pipeline/src/types.py`, `pipeline/src/db/writer.py`, live Supabase queries, `sql/schema.sql`, `web/src/lib/queries.ts`

---

## 1. Executive Summary

The FX Regime Lab UI is a Next.js 15+ (App Router) application using **TanStack Query** for server-state management and **Supabase** (PostgreSQL) as its single source of truth. All public tables have `SELECT` RLS policies for the `anon` key; mutations are blocked. The pipeline (Python) writes via `SUPABASE_SERVICE_ROLE_KEY`.

**Data freshness:** Pipeline runs daily (Prefect Cloud). Latest data date in production: **2026-05-01**.

**Key architectural principle:** The frontend does **not** compute regimes or signals. It reads pre-computed, immutable rows from the database and applies lightweight client-side transformations (pivoting, slicing, formatting).

---

## 2. Database Schema — Complete Table Reference

### 2.1 Table Inventory

| Table | Rows (prod) | Writable by | UI Reads | Purpose |
|-------|-------------|-------------|----------|---------|
| `signals` | 4,957 | Pipeline | Yes | Raw + computed signal metrics per pair per day |
| `regime_calls` | 66 | Pipeline | Yes | Layer 1–3 regime classification output |
| `desk_open_cards` | 10 | Pipeline | Yes | Cross-sectional desk snapshot (dominance, Markov, telemetry) |
| `validation_log` | 56 | Pipeline | Yes | Out-of-sample accuracy tracking (T+1, T+5, T+20) |
| `brief_log` | 19 | Pipeline | Yes | Unified daily systemic brief + sentiment JSON |
| `macro_events` | 23 | Pipeline | Yes | Forward calendar (next 14 days) |
| `strategy_ledger` | 9 | Pipeline | Yes | Forward-walking alpha ledger (directional calls only) |
| `research_memos` | 0 | Pipeline | Yes | Weekly Substack memo archive (thesis bullets) |
| `event_risk_matrices` | 0 | Pipeline | Yes | Pre-computed event risk for Convexity Radar |
| `historical_prices` | 5,040 | Pipeline | Yes | OHLCV deep history (2Y daily, Friday-only older) |
| `research_analogs` | 12 | Pipeline | Yes | Postgres-matched historical analogs |
| `brief` | 5 | Pipeline | Yes | Per-pair AI analysis (legacy; still used by `usePairBrief`) |
| `universe` | 7 | Pipeline | Yes | Pair registry (replaces static JSON) |
| `health_checks` | 0 | Pipeline | No (internal) | Pipeline run metadata |
| `validation_stats` | — | Pipeline | Yes | Aggregate win-rate / Brier stats |
| `ai_usage_log` | — | Pipeline | No (internal) | AI request counting |
| `webhook_subscriptions` | — | User (anon insert) | No | Encrypted webhook URLs |
| `historical_macro_surprises` | — | Pipeline | Yes | Consensus vs actual macro releases |
| `event_aliases` | — | Pipeline | Yes | Canonical ↔ alias name mapping |

---

## 3. Per-Table Data Shapes

### 3.1 `signals` — The Signal Master Table

**Unique key:** `(pair, date)`  
**Sample date:** `2026-05-01`  
**Row count:** ~5K (multi-pair history)

| Column | Type | Nullable | Source / Meaning |
|--------|------|----------|------------------|
| `id` | `number` (auto-inc) | No | Surrogate PK |
| `date` | `string` (ISO date) | No | Observation date (NY close) |
| `pair` | `string` | No | `EURUSD`, `USDJPY`, `USDINR` |
| `spot` | `number` | Yes | FX spot close |
| `day_change` | `number` | Yes | Absolute day change |
| `day_change_pct` | `number` | Yes | Percent day change |
| `rate_diff_2y` | `number` | Yes | 2Y yield spread (base – quote) |
| `rate_diff_10y` | `number` | Yes | 10Y yield spread |
| `rate_diff_zscore` | `number` | Yes | Z-score of rate differential |
| `rate_diff_mom` | `number` | Yes | 4-week momentum of `rate_diff_2y` *(not in TS types)* |
| `rate_diff_10y_real` | `number` | Yes | Nominal 10Y spread minus breakeven inflation |
| `rate_z_tactical` | `number` | Yes | MAD Z on carry, 252-day window |
| `rate_z_structural` | `number` | Yes | MAD Z on carry, 2520-day window |
| `cot_lev_money_net` | `number` | Yes | Leveraged money net positioning |
| `cot_asset_mgr_net` | `number` | Yes | Asset manager net positioning |
| `cot_percentile` | `number` | Yes | Net positioning vs 3-year rolling percentile |
| `cot_net_pos` | `number` | Yes | Non-commercial net positioning *(not in TS types)* |
| `realized_vol_5d` | `number` | Yes | 5-day annualized realized vol |
| `realized_vol_20d` | `number` | Yes | 20-day annualized realized vol |
| `realized_vol_21` | `number` | Yes | 21-day realized vol *(not in TS types)* |
| `realized_vol_rank` | `number` | Yes | Empirical CDF rank of 21d vol vs 3-year history |
| `implied_vol_30d` | `number` | Yes | 30-day ATM implied vol |
| `vol_skew` | `number` | Yes | Vol skew metric |
| `atm_vol` | `number` | Yes | ATM volatility |
| `risk_reversal_25d` | `number` | Yes | 25-delta risk reversal (Put vs Call premium) |
| `oi_delta` | `number` | Yes | Open interest delta |
| `oi_price_alignment` | `string` | Yes | Text classification of OI vs price alignment |
| `cross_asset_vix` | `number` | Yes | VIX index value |
| `cross_asset_dxy` | `number` | Yes | DXY index value |
| `cross_asset_oil` | `number` | Yes | Oil price proxy |
| `cross_asset_us10y` | `number` | Yes | US 10Y yield |
| `cross_asset_gold` | `number` | Yes | Gold price proxy |
| `cross_asset_copper` | `number` | Yes | Copper price proxy |
| `cross_asset_stoxx` | `number` | Yes | EU equity index proxy |
| `structural_instability` | `boolean` | Yes | Rate carry scale: 1y MAD vs 5y MAD flag |
| `breakeven_inflation_10y` | `number` | Yes | FRED T10YIE |
| `volume_rvol` | `number` | Yes | Relative volume proxy (futures) *(not in TS types)* |
| `skew_alignment` | `number` | Yes | Alignment between bias and 25d RR: `-1, 0, 1` |
| `created_at` | `string` (timestamptz) | No | Write timestamp |

**Frontend projection (`LatestSignalRow`):**
```ts
Pick<SignalRow,
  'pair' | 'date' | 'spot' | 'rate_diff_2y' | 'rate_diff_10y' | 'rate_diff_zscore'
  | 'cot_percentile' | 'realized_vol_20d' | 'realized_vol_5d' | 'implied_vol_30d'
  | 'cross_asset_vix' | 'cross_asset_dxy' | 'cross_asset_oil' | 'cross_asset_us10y'
  | 'cross_asset_gold' | 'cross_asset_copper' | 'cross_asset_stoxx'
  | 'day_change_pct' | 'cot_lev_money_net' | 'oi_delta' | 'created_at'>
```

---

### 3.2 `regime_calls` — Layer 1–3 Output

**Unique key:** `(pair, date)`  
**Row count:** 66

| Column | Type | Nullable | Meaning |
|--------|------|----------|---------|
| `id` | `number` | No | Surrogate PK |
| `date` | `string` | No | Call date |
| `pair` | `string` | No | FX pair |
| `regime` | `string` | No | Layer 1 regime label (e.g. `USD_WEAKNESS_MODERATE`) |
| `confidence` | `number` | No | 0.0–1.0 confidence score |
| `signal_composite` | `number` | No | Blended composite signal (-2 to +2) |
| `rate_signal` | `string` | Yes | `BULLISH` / `BEARISH` / `NEUTRAL` |
| `cot_signal` | `string` | Yes | COT-based signal |
| `vol_signal` | `string` | Yes | Volatility-based signal |
| `rr_signal` | `string` | Yes | Risk-reversal signal |
| `oi_signal` | `string` | Yes | Open-interest signal |
| `primary_driver` | `string` | Yes | Human-readable driver description |
| `special_signal_value` | `number` | Yes | Special/auxiliary signal value |
| `special_signal_label` | `string` | Yes | Label for special signal |
| `model_version` | `string` | Yes | Model version string (e.g. `1.0-universal`) |
| `data_quality_score` | `number` | Yes | Data completeness score |
| `stress_level` | `string` | Yes | Stress classification |
| `predicted_direction` | `string` | Yes | Directional bias *(not in TS types)* |
| `directional_bias` | `string` | Yes | `Long` / `Short` / `Neutral` *(not in TS types)* |
| `conviction` | `number` | Yes | 1–5 conviction score *(not in TS types)* |
| `entry_timing` | `string` | Yes | `ENTER` or `WAIT` *(not in TS types)* |
| `position_size` | `string` | Yes | `FULL` or `HALF` *(not in TS types)* |
| `stop_level` | `number` | Yes | Calculated stop-loss level *(not in TS types)* |
| `created_at` | `string` | No | Write timestamp |

**Frontend projection (`LatestRegimeCallRow`):**
```ts
Pick<RegimeCallRow,
  'pair' | 'date' | 'regime' | 'confidence' | 'signal_composite'
  | 'rate_signal' | 'cot_signal' | 'vol_signal' | 'rr_signal' | 'oi_signal'
  | 'primary_driver' | 'created_at'>
```

---

### 3.3 `desk_open_cards` — Cross-Sectional Desk Snapshot

**Unique key:** `(pair, date)`  
**Row count:** 10 (latest snapshot: 2026-05-01)

| Column | Type | Nullable | Meaning |
|--------|------|----------|---------|
| `date` | `string` | No | Snapshot date |
| `pair` | `string` | No | FX pair |
| `structural_regime` | `string` | No | Layer 1 regime label |
| `dominance_array` | `Json` | Yes | Array of `{ rank, signal_family, signal_strength, beta, dominance_score }` |
| `pain_index` | `number` | Yes | 0–100 divergence pressure index |
| `markov_probabilities` | `Json` | Yes | `{ continuation_probability, transitions: {regime: pct}, weighted_sample_size }` |
| `ai_brief` | `string` | Yes | JSON string with `bias_summary`, `catalyst_driver`, `squeeze_risk` |
| `telemetry_audit` | `Json` | Yes | `{ cot_is_stale, cot_age_days, parameter_instability, underwater_triggered, Systemic_Cluster, ... }` |
| `invalidation_triggered` | `boolean` | Yes | Overnight invalidation flag |
| `telemetry_status` | `string` | Yes | `ONLINE` / `OFFLINE` |
| `global_rank` | `number` | Yes | Cross-sectional apex rank (1 = best) |
| `apex_score` | `number` | Yes | 0–1 composite attractiveness score |
| `regime_age` | `number` | Yes | Consecutive days in current regime |

**Frontend transformation:** `mapDeskRow()` in `queries.ts` casts JSON fields and derives `parameter_instability` from `telemetry_audit.parameter_instability`.

---

### 3.4 `validation_log` — Out-of-Sample Accuracy

**Unique key:** `(call_date, pair)` (new); legacy `(date, pair)`  
**Row count:** 56

| Column | Type | Nullable | Meaning |
|--------|------|----------|---------|
| `id` | `number` | No | Surrogate PK |
| `date` | `string` | No | Call date (legacy) |
| `pair` | `string` | No | FX pair |
| `predicted_direction` | `string` | Yes | `BULLISH` / `BEARISH` / `NEUTRAL` |
| `predicted_regime` | `string` | Yes | Predicted regime label |
| `confidence` | `number` | Yes | Confidence at call time |
| `actual_direction` | `string` | Yes | Actual observed direction |
| `actual_return_1d` | `number` | Yes | T+1 log return |
| `actual_return_5d` | `number` | Yes | T+5 log return |
| `correct_1d` | `boolean` | Yes | T+1 directional accuracy |
| `correct_5d` | `boolean` | Yes | T+5 directional accuracy |
| `dxy_return_1d` | `number` | Yes | DXY return T+1 |
| `alpha_return_1d` | `number` | Yes | Alpha return T+1 |
| `max_intraday_adverse_bps` | `number` | Yes | Max adverse excursion in bps |
| `vol_regime_at_call` | `string` | Yes | Vol regime when call was made |
| `regime_at_call` | `string` | Yes | Regime label at call time |
| `notes` | `string` | Yes | Free-text notes |
| `call_id` | `number` | Yes | FK to `regime_calls.id` *(not in TS types)* |
| `validation_date` | `string` | Yes | T+5/T+20 observation date *(not in TS types)* |
| `is_correct` | `boolean` | Yes | Directional bias matched *(not in TS types)* |
| `pnl_bps` | `number` | Yes | Price movement in bps *(not in TS types)* |
| `actual_direction_t5` | `string` | Yes | T+5 direction *(not in TS types)* |
| `actual_direction_t20` | `string` | Yes | T+20 direction *(not in TS types)* |
| `log_return_t5_bps` | `number` | Yes | T+5 log return in bps *(not in TS types)* |
| `log_return_t20_bps` | `number` | Yes | T+20 log return in bps *(not in TS types)* |
| `correct_t5` | `boolean` | Yes | T+5 correct *(not in TS types)* |
| `correct_t20` | `boolean` | Yes | T+20 correct *(not in TS types)* |
| `brier_score_t5` | `number` | Yes | T+5 Brier score *(not in TS types)* |
| `brier_score_t20` | `number` | Yes | T+20 Brier score *(not in TS types)* |
| `is_superseded` | `boolean` | Yes | Superseded flag *(not in TS types)* |
| `created_at` | `string` | No | Write timestamp |

---

### 3.5 `brief_log` — Daily Systemic Brief

**Unique key:** `(date)`  
**Row count:** 19

| Column | Type | Nullable | Meaning |
|--------|------|----------|---------|
| `id` | `number` | No | Surrogate PK |
| `date` | `string` | No | Brief date |
| `brief_text` | `string` | Yes | Full AI-generated daily summary |
| `eurusd_regime` | `string` | Yes | Cached regime label |
| `usdjpy_regime` | `string` | Yes | Cached regime label |
| `usdinr_regime` | `string` | Yes | Cached regime label |
| `pair_regimes` | `Json` | Yes | Structured pair→regime map |
| `macro_context` | `string` | Yes | Macro narrative summary |
| `dollar_dominance` | `number` | Yes | 0–100 USD thematic alignment |
| `idiosyncratic_outlier` | `string` | Yes | Pair most idiosyncratic vs FX basket |
| `sentiment_json` | `Json` | Yes | `{ polymarket_top3, dual_correlation: {20d, 60d} }` |
| `created_at` | `string` | No | Write timestamp |

---

### 3.6 `macro_events` — Forward Calendar

**Unique key:** `(date, event)`  
**Row count:** 23

| Column | Type | Nullable | Meaning |
|--------|------|----------|---------|
| `id` | `string` (UUID) | No | Surrogate PK |
| `date` | `string` | No | Event date |
| `event` | `string` | No | Event name (e.g. `ECB Rate Decision`) |
| `impact` | `string` | No | `HIGH`, `MEDIUM`, `LOW` |
| `pairs` | `string[]` | No | Affected pairs |
| `category` | `string` | Yes | Region/category tag |
| `ai_brief` | `string` | Yes | AI-generated event brief |
| `created_at` | `string` | No | Write timestamp |

---

### 3.7 `strategy_ledger` — Forward-Walking Alpha Ledger

**Unique key:** `(date, pair, regime, primary_driver)`  
**Row count:** 9

| Column | Type | Nullable | Meaning |
|--------|------|----------|---------|
| `id` | `string` (UUID) | No | Surrogate PK |
| `date` | `string` | No | Entry date |
| `pair` | `string` | No | FX pair |
| `regime` | `string` | No | Regime at entry |
| `primary_driver` | `string` | No | Driver at entry |
| `direction` | `string` | No | `LONG`, `SHORT`, `NEUTRAL` |
| `entry_close` | `number` | Yes | Entry spot close |
| `confidence` | `number` | Yes | Confidence at entry |
| `t1_close` | `number` | Yes | T+1 close (for MTM) |
| `t3_close` | `number` | Yes | T+3 close |
| `t5_close` | `number` | Yes | T+5 close |
| `t1_hit` | `number` | Yes | `1` = hit, `0` = miss, `null` = pending |
| `t3_hit` | `number` | Yes | Same |
| `t5_hit` | `number` | Yes | Same |
| `brier_score_t5` | `number` | Yes | T+5 Brier score |
| `max_pain_bps` | `number` | Yes | Max adverse excursion in bps |

**Frontend filter:** `useStrategyLedger` excludes `direction = 'NEUTRAL'`.

---

### 3.8 `research_memos` — Weekly Memo Archive

**Unique key:** `(link_url)`  
**Row count:** 0 (empty in production)

| Column | Type | Nullable | Meaning |
|--------|------|----------|---------|
| `id` | `string` (UUID) | No | Surrogate PK |
| `date` | `string` | No | Memo date |
| `title` | `string` | No | Memo title |
| `raw_content` | `string` | No | Full text body |
| `ai_thesis_summary` | `Json` | No | Array of thesis bullet strings |
| `link_url` | `string` | No | Substack / source URL |
| `created_at` | `string` | No | Write timestamp |

**Note:** Daily desk briefs must **not** load `raw_content`. Use `ai_thesis_summary` only.

---

### 3.9 `event_risk_matrices` — Convexity Radar Data

**Unique key:** `(date, pair, event_name)`  
**Row count:** 0 (empty in production)

| Column | Type | Nullable | Meaning |
|--------|------|----------|---------|
| `id` | `string` (UUID) | No | Surrogate PK |
| `date` | `string` | No | Event date |
| `pair` | `string` | No | FX pair |
| `event_name` | `string` | No | Canonical event name |
| `active_regime` | `string` | No | Regime active at event time |
| `sample_size` | `number` | No | Historical sample count |
| `median_mie_multiplier` | `number` | Yes | Median MIE multiplier |
| `beat_median_return` | `number` | Yes | Median T+1 return for BEAT surprise |
| `miss_median_return` | `number` | Yes | Median T+1 return for MISS surprise |
| `inline_median_return` | `number` | Yes | Median T+1 return for IN-LINE surprise |
| `asymmetry_ratio` | `number` | Yes | Beat vs Miss asymmetry ratio |
| `asymmetry_direction` | `string` | Yes | Direction of asymmetry |
| `t1_exhaustion_p2_5` | `number` | Yes | T+1 return 2.5th percentile |
| `t1_exhaustion_p16` | `number` | Yes | T+1 return 16th percentile |
| `t1_exhaustion_p84` | `number` | Yes | T+1 return 84th percentile |
| `t1_exhaustion_p97_5` | `number` | Yes | T+1 return 97.5th percentile |
| `t1_tail_risk_p95` | `number` | Yes | T+1 return 95th percentile |
| `t1_tail_risk_p05` | `number` | Yes | T+1 return 5th percentile |
| `ai_context` | `string` | Yes | AI-generated event context |
| `mean_reversion_prob` | `number` | Yes | Probability price reverts to 20% of daily range by T+0 close |
| `created_at` | `string` | Yes | Write timestamp |

---

## 4. Python Pipeline Types (`pipeline/src/types.py`)

These dataclasses define what the pipeline computes before writing to the DB.

### `SignalRow` (dataclass)
```python
pair: str
date: date
rate_diff_2y: float | None
rate_diff_10y: float | None
cot_percentile: float | None
realized_vol_20d: float | None
realized_vol_5d: float | None
implied_vol_30d: float | None
spot: float | None
day_change: float | None
day_change_pct: float | None
cross_asset_vix: float | None
cross_asset_dxy: float | None
cross_asset_oil: float | None
cross_asset_us10y: float | None
cross_asset_gold: float | None
cross_asset_copper: float | None
cross_asset_stoxx: float | None
oi_delta: int | None
volume_rvol: float | None = None
structural_instability: bool = False
breakeven_inflation_10y: float | None = None
rate_diff_10y_real: float | None = None
rate_z_tactical: float | None = None
rate_z_structural: float | None = None
realized_vol_rank: float | None = None
skew_alignment: int | None = None
```

### `RegimeCall` (dataclass)
```python
pair: str
date: date
regime: str
confidence: float
signal_composite: float
rate_signal: str
primary_driver: str | None = None
entry_timing: Layer3EntryTiming | None = None   # "ENTER" | "WAIT"
position_size: Layer3PositionSize | None = None # "FULL" | "HALF"
stop_level: float | None = None
data_quality_score: float | None = None
stress_level: str | None = None
```

### `DeskOpenCardRow` (dataclass)
```python
date: date
pair: str
structural_regime: str
dominance_array: list[dict[str, Any]]
pain_index: float | None
markov_probabilities: dict[str, Any]
ai_brief: str
telemetry_audit: dict[str, Any]
invalidation_triggered: bool = False
telemetry_status: str = "ONLINE"
global_rank: int | None = None
apex_score: float | None = None
regime_age: int | None = None
```

### `StrategyLedgerRow` (dataclass)
```python
date: date
pair: str
regime: str
primary_driver: str
direction: str
entry_close: float | None = None
confidence: float | None = None
t1_close: float | None = None
t3_close: float | None = None
t5_close: float | None = None
t1_hit: int | None = None
t3_hit: int | None = None
t5_hit: int | None = None
brier_score_t5: float | None = None
```

---

## 5. Writer Logic (`pipeline/src/db/writer.py`)

All writes go through `writer.py`. Key functions:

| Function | Target Table | Upsert Key | Notes |
|----------|--------------|------------|-------|
| `write_signal_row(row: SignalRow)` | `signals` | `(pair, date)` | Excludes `cot_lev_money_net`, `cot_asset_mgr_net`, `vol_skew`, `atm_vol`, `risk_reversal_25d` from payload (those are fetched but not written by this function — they may come from other writers or be in DB from earlier migrations) |
| `write_regime_call(call: RegimeCall)` | `regime_calls` | `(pair, date)` | Uses `dataclasses.asdict()` then isoformats date |
| `write_desk_open_card(card: DeskOpenCardRow)` | `desk_open_cards` | `(pair, date)` | JSON fields serialized as-is |
| `write_brief_log(...)` | `brief_log` | `(date)` | Single row per day |
| `write_validation_row(row)` | `validation_log` | `(pair,call_date)` or `(pair,date)` | Legacy fallback |
| `write_ledger_entry(row)` | `strategy_ledger` | `(date,pair,regime,primary_driver)` | Forward-walk tracking |
| `write_macro_events(events)` | `macro_events` | `(date,event)` | Calendar ingestion |
| `write_research_memo(...)` | `research_memos` | `(link_url)` | Weekly memo ingest |
| `write_event_risk_matrices(rows)` | `event_risk_matrices` | `(date,pair,event_name)` | Pre-computed risk |
| `write_historical_prices(rows)` | `historical_prices` | `(pair,date)` | OHLCV batch |
| `write_research_analogs(rows)` | `research_analogs` | `(pair,as_of_date,rank)` | Postgres RPC fallback |
| `write_validation_stats(row)` | `validation_stats` | `(as_of_date,pair)` | Aggregate stats |
| `write_brief(...)` | `brief` | `(pair,date)` | Per-pair AI analysis |

---

## 6. Frontend Hooks — Complete API Specification

All hooks live in **`web/src/lib/queries.ts`** (primary) and **`web/src/lib/supabase/queries.ts`** (legacy support).

### 6.1 Universe & Discovery

```ts
export function useUniverse()
// Returns: string[] (FX pairs from `universe` table filtered against canonical list)
// Query: SELECT pair FROM universe WHERE class = 'FX' ORDER BY pair ASC
// Stale time: 60 min
```

### 6.2 Latest Snapshot Hooks (Gateway / Mosaic)

These fetch the **latest calendar date present in the DB** (not `today()`), then take the contiguous block for that date.

```ts
export function useLatestRegimeCalls()
// Returns: Record<string, LatestRegimeCallRow>
// Query: SELECT (projection) FROM regime_calls
//         WHERE pair IN (universe)
//         ORDER BY date DESC LIMIT 64
// Transform: sliceLatestCalendarDate() → first row per pair

export function useLatestSignals()
// Returns: Record<string, LatestSignalRow>
// Query: SELECT (projection) FROM signals
//         WHERE pair IN (universe)
//         ORDER BY date DESC LIMIT 64
// Transform: sliceLatestCalendarDate() → first row per pair

export function useLatestDeskOpenCardsSnapshot()
// Returns: { asOfDate: string | null; cards: DeskOpenCardSnapshotRow[]; rankJumpByPair: Record<string, number> }
// Step 1: SELECT date FROM desk_open_cards ORDER BY date DESC LIMIT 1
// Step 2: SELECT * FROM desk_open_cards WHERE date = latest AND pair IN (universe)
// Step 3: SELECT pair, global_rank FROM desk_open_cards WHERE date = prevDay
// Transform: mapDeskRow() on each; compute rankJumpByPair = prev - curr (if positive)
```

### 6.3 Historical / Time-Series Hooks

```ts
export function useRegimeHistory30D(pair: string)
// Returns: { date, regime, confidence }[]
// Query: SELECT date, regime, confidence FROM regime_calls
//         WHERE pair = ? AND date >= (today - 30d) ORDER BY date ASC

export function useRegimeHistory(pair: string)
// Returns: { date, regime, confidence }[]
// Query: SELECT date, regime, confidence FROM regime_calls
//         WHERE pair = ? ORDER BY date DESC LIMIT 90

export function useSignalHistory(pair: string, limit = 14)
// Returns: SignalRow[] (oldest → newest)
// Query: SELECT * FROM signals WHERE pair = ? ORDER BY date DESC LIMIT ?
// Transform: .slice().reverse()

export function useHistoricalData(pair: string, enabled = false)
// Returns: { date, pair, open, high, low, close, volume }[]
// Query: RPC historical_prices_for_max_chart(p_pair, p_cutoff = 2Y ago)
// Stale time: Infinity
```

### 6.4 Desk Card & Telemetry

```ts
export function useDeskOpenCard(pair: string)
// Returns: DeskOpenCardSnapshotRow | null
// Query: SELECT * FROM desk_open_cards WHERE pair = ? ORDER BY date DESC LIMIT 1
// Transform: mapDeskRow() + casts JSON fields to typed objects
// Stale time: Infinity

export function useTelemetryStatus(pair: string)
// Returns: { invalidation_triggered: boolean; telemetry_status: string }
// Query: SELECT invalidation_triggered, telemetry_status FROM desk_open_cards
//         WHERE pair = ? ORDER BY date DESC LIMIT 1
// Refetch interval: 60 sec
```

### 6.5 Brief & Systemic

```ts
export function useLatestBrief()
// Returns: BriefLogRow | null
// Query: SELECT * FROM brief_log ORDER BY date DESC LIMIT 1

export function useBriefLogDominanceSeries(limit = 5)
// Returns: { date, dollar_dominance }[] (oldest → newest)
// Query: SELECT date, dollar_dominance FROM brief_log ORDER BY date DESC LIMIT ?
// Transform: reverse()
// Stale time: 5 min

export function usePairBrief(pair: string)
// Returns: Pick<BriefRow, 'analysis' | 'date' | 'regime' | 'confidence' | 'composite' | 'primary_driver'> | null
// Query: SELECT analysis, date, regime, confidence, composite, primary_driver FROM brief
//         WHERE pair = ? ORDER BY date DESC LIMIT 1
```

### 6.6 Macro & Events

```ts
export function useUpcomingMacroEvents()
// Returns: MacroEventRow[]
// Query: SELECT * FROM macro_events
//         WHERE date BETWEEN today AND today+14d
//           AND impact IN ('HIGH', 'MEDIUM')
//         ORDER BY date ASC

export function useEventRiskMatrices(pair: string)
// Returns: EventRiskMatrixRow[]
// Query: SELECT * FROM event_risk_matrices
//         WHERE pair = ? AND date BETWEEN today AND today+14d
//         ORDER BY date ASC
// Stale time: Infinity
```

### 6.7 Validation & Performance

```ts
export function useValidationLog(limit = 30)
// Returns: ValidationLogRow[]
// Query: SELECT * FROM validation_log ORDER BY date DESC LIMIT ?

export function useEquityCurve()
// Returns: { date, pair, actual_return_1d }[]
// Query: SELECT date, pair, actual_return_1d FROM validation_log
//         WHERE pair IN (universe) ORDER BY date ASC

export function useVerified90dEdge()
// Returns: { hitRatePct: number | null; trials: number }
// Logic: Paginated scan of strategy_ledger (1000/page)
//         WHERE date >= today-90d AND direction != 'NEUTRAL'
//         Counts t1_hit + t3_hit trials/hits
// Stale time: 60 min
```

### 6.8 Strategy Ledger

```ts
export function useStrategyLedger(pair: string)
// Returns: Row[] (projection)
// Query: SELECT id, date, pair, regime, primary_driver, direction,
//          entry_close, confidence, t1_close, t3_close, t5_close,
//          t1_hit, t3_hit, t5_hit, brier_score_t5, max_pain_bps
//        FROM strategy_ledger
//        WHERE pair = ? AND direction != 'NEUTRAL'
//        ORDER BY date DESC LIMIT 1000
```

### 6.9 Correlation & Analogs

```ts
export function useFxCorrelationMatrix()
// Returns: FxCorrelationJson
// Query: RPC get_fx_correlation_matrix()
// Stale time: 5 min

export function useLatestResearchAnalogs(pair: string)
// Returns: { as_of_date, pair, rank, match_date, match_score,
//            forward_30d_return, regime_stability, context_label }[]
// Query: SELECT (projection) FROM research_analogs
//         WHERE pair = ? ORDER BY as_of_date DESC, rank ASC LIMIT 3
```

### 6.10 Research Memos

```ts
export function useResearchMemosList()
// Returns: ResearchMemoListItem[]
// Query: SELECT id, date, title, link_url, ai_thesis_summary FROM research_memos
//         ORDER BY date DESC
// Stale time: 5 min

export function useResearchMemoReader(id: string | null)
// Returns: Pick<ResearchMemoRow, 'id' | 'date' | 'title' | 'raw_content' | 'link_url'> | null
// Query: SELECT id, date, title, raw_content, link_url FROM research_memos
//         WHERE id = ? LIMIT 1
```

### 6.11 Cross-Asset Pulse

```ts
export function useCrossAssetPulse()
// Returns: { vix: { value, change }, dxy: { value, change },
//            oil: { value, change }, us10y: { value, change }, date }
// Query: SELECT date, cross_asset_vix, cross_asset_dxy,
//          cross_asset_oil, cross_asset_us10y
//        FROM signals WHERE pair = 'EURUSD' ORDER BY date DESC LIMIT 2
// Transform: Computes delta(latest, prev) for each asset
```

---

## 7. Key Data Transformations (Frontend)

### 7.1 `sliceLatestCalendarDate<T>(rows)`
Takes rows ordered `date DESC`. Returns contiguous rows for the newest date only. Used by `useLatestRegimeCalls`, `useLatestSignals`, `useLatestDeskOpenCardsSnapshot`.

### 7.2 `mapDeskRow(row: DeskOpenCardRow): DeskOpenCardSnapshotRow`
```ts
{
  ...row,
  dominance_array: row.dominance_array as DominanceItem[],
  markov_probabilities: row.markov_probabilities as MarkovPayload,
  telemetry_audit: row.telemetry_audit as TelemetryAuditPayload,
  parameter_instability: Boolean(audit?.parameter_instability),
}
```

### 7.3 `pivotRegimeHeatmapRows(rows, pairLabels)`
Pivots flat `{ date, pair, regime }[]` into:
```ts
{ dates: string[]; regimes: Record<string, string[]> }
```
Regimes default to `'NEUTRAL'` when missing for a date.

### 7.4 `parseDeskAiBriefRows(raw: string)`
Parses `ai_brief` JSON. Supports:
- **New format:** `{ bias_summary, catalyst_driver, squeeze_risk }`
- **Legacy format:** `{ regime_state, key_divergence, swing_factor }`
- **Fallback:** Raw text truncated to 320 chars

Returns: `{ label: string; value: string }[]`

### 7.5 `getGlobalHitRate(days)`
Client-side paginated aggregation over `strategy_ledger`:
- Filters `direction != 'NEUTRAL'` and `date >= today - days`
- Counts `t1_hit` and `t3_hit` as separate trials
- Returns `hitRatePct = (hits / trials) * 100`

---

## 8. RPC Functions Available to Frontend

| Function | Args | Returns | Grants |
|----------|------|---------|--------|
| `get_fx_correlation_matrix` | `Record<string, never>` | `Json` (half-matrix) | `anon` |
| `historical_prices_for_max_chart` | `p_pair: string, p_cutoff: string` | `historical_prices` rows | `anon` |
| `match_historical_analogs` | `target_pair, as_of_date, current_trend, current_comp, limit_rows` | analog rows | `anon` |
| `calculate_dual_correlation` | `p_pair: string, p_lookback: int` | `float` | `anon` |
| `increment_ai_usage` | `p_date, p_purpose, p_model` | `boolean` | `service_role` |

---

## 9. RLS & Security Summary

- **All public tables:** `anon` can `SELECT`. `INSERT/UPDATE/DELETE` blocked via explicit policies.
- **Internal tables (`ai_usage_log`, `pipeline_errors`):** No `anon` access. Service role only.
- **`webhook_subscriptions`:** `anon` can `INSERT` only (write-only ingress).

---

## 10. Data Gaps & Type Mismatches (Actionable)

| Issue | Impact | Recommended Fix |
|-------|--------|-----------------|
| `database.types.ts` missing `signals` columns: `rate_diff_mom`, `cot_net_pos`, `realized_vol_21`, `volume_rvol`, `structural_instability`, `breakeven_inflation_10y`, `rate_diff_10y_real`, `rate_z_tactical`, `rate_z_structural`, `realized_vol_rank`, `skew_alignment` | TypeScript will error if these fields are selected | Regenerate Supabase types (`supabase gen types typescript`) |
| `database.types.ts` missing `regime_calls` columns: `predicted_direction`, `directional_bias`, `conviction`, `entry_timing`, `position_size`, `stop_level` | Same as above | Regenerate Supabase types |
| `database.types.ts` missing `validation_log` columns: `call_id`, `validation_date`, `is_correct`, `pnl_bps`, `actual_direction_t5`, `actual_direction_t20`, `log_return_t5_bps`, `log_return_t20_bps`, `correct_t5`, `correct_t20`, `brier_score_t5`, `brier_score_t20`, `is_superseded` | Same as above | Regenerate Supabase types |
| `event_risk_matrices` is empty in production | Convexity Radar page shows no data | Pipeline not yet writing to this table |
| `research_memos` is empty in production | Memos page shows empty list | Substack ingestion not yet running |
| `signals.id`, `regime_calls.id`, `validation_log.id` are typed as `number` in TS but are `UUID` in schema | Minor; Postgres auto-casts in JS | Regenerate Supabase types |

---

## 11. Component → Data Mapping

| Component / Page | Primary Hooks | Tables |
|------------------|---------------|--------|
| `FxRegimePairSelectionPage` (Mosaic) | `useLatestRegimeCalls`, `useLatestSignals`, `useLatestDeskOpenCardsSnapshot`, `useFxCorrelationMatrix` | `regime_calls`, `signals`, `desk_open_cards` |
| `DeskCard` | `useDeskOpenCard` | `desk_open_cards` |
| `AlphaLedger` | `useStrategyLedger` | `strategy_ledger` |
| `MacroDriftEngine` | `useLatestBrief`, `useBriefLogDominanceSeries` | `brief_log` |
| `CorrelationMatrix` | `useFxCorrelationMatrix` | RPC |
| `PerformanceLedgerPage` | `useValidationLog`, `useEquityCurve`, `useVerified90dEdge` | `validation_log`, `strategy_ledger` |
| `ConvexityRadarPage` | `useEventRiskMatrices`, `useUpcomingMacroEvents` | `event_risk_matrices`, `macro_events` |
| `MemoSidebar` | `useResearchMemosList`, `useResearchMemoReader` | `research_memos` |
| `GlobalMacroPulse` | `useCrossAssetPulse` | `signals` |

---

*End of Data Dictionary*
