# Database Status — FX Regime Lab

> **Living document.** Update this file immediately after any migration, schema change, or pipeline type change.  
> **Last updated:** 2026-05-21  
> **Project ref:** `weaaacohvzzgkgxzpaee.supabase.co`

---

## 1. Executive Summary

The Supabase schema has been cleaned of all stale columns and tables that were never written by the current 3-pair pipeline. All 37 `signals` columns written by `pipeline/src/db/writer.py` are present and accounted for. The TypeScript types in `web/src/lib/supabase/database.types.ts` are synced with the live schema.

**Total tables:** 30 active tables  
**Total migrations applied:** 49 (all local ↔ remote synced)  
**Known issues:**
- `pair_profiles` exists in `database.types.ts` but is never referenced in any code (ghost type; table may not exist in remote)
- `historical_yields` has no migration; table is auto-created by Supabase on first upsert from `fred_historical.py`

---

## 2. Migration History (Current State)

All migrations are synced between local (`supabase/migrations/`) and remote (`supabase_migrations.schema_migrations`).

| # | Timestamp | Name | Status | Notes |
|---|-----------|------|--------|-------|
| 1 | 20260401000001 | initial_schema | ✅ | regime_calls, signals, validation_log, brief, macro_events, ai_usage_log |
| 2 | 20260401000002 | rls_policies | ✅ | RLS enablement |
| 3 | 20260401000003 | indexes | ✅ | Initial indexes |
| 4 | 20260404154618 | remote_schema | ✅ | Empty (placeholder) |
| 5 | 20260426000001 | phase3_new_tables | ✅ | brief, macro_events, ai_usage_log (re-created with RLS) |
| 6 | 20260427205525 | remote_alignment | ✅ | Empty (placeholder) |
| 7 | 20260428000001 | hardening | ✅ | brief_log, validation_log RLS, protect_immutable_calls function |
| 8 | 20260428000002 | add_cross_asset_us10y | ✅ | signals.cross_asset_us10y |
| 9 | 20260428000003 | historical_data | ✅ | historical_prices, research_analogs |
| 10 | 20260428000004 | desk_cards_and_security | ✅ | desk_open_cards |
| 11 | 20260428000005 | event_risk_schema | ✅ | historical_macro_surprises |
| 12 | 20260428000006 | event_risk_matrices | ✅ | event_risk_matrices |
| 13 | 20260428000007 | strategy_ledger | ✅ | strategy_ledger |
| 14 | 20260428000008 | analog_rpc | ✅ | match_historical_analogs RPC |
| 15 | 20260428000009 | add_commodity_signals | ✅ | signals.cross_asset_gold/copper/stoxx |
| 16 | 20260428000010 | structural_instability | ✅ | signals.structural_instability |
| 17 | 20260428000011 | add_ranking_to_desk | ✅ | desk_open_cards.global_rank, apex_score |
| 18 | 20260428000012 | universe_table | ✅ | universe |
| 19 | 20260428000013 | desk_regime_age_chart_thin | ✅ | desk_open_cards.regime_age |
| 20 | 20260428000014 | macro_aliases | ✅ | event_aliases |
| 21 | 20260428000015 | event_risk_exhaustion_bands | ✅ | exhaustion bands on event_risk_matrices |
| 22 | 20260428000016 | systemic_synthesis | ✅ | brief_log.dollar_dominance, idiosyncratic_outlier, sentiment_json |
| 23 | 20260428000017 | terminal_launch_blockers | ✅ | signals.breakeven_inflation_10y, rate_diff_10y_real, rate_z_tactical, rate_z_structural |
| 24 | 20260428000018 | research_memos | ✅ | research_memos |
| 25 | 20260428000019 | webhook_subscriptions | ✅ | Created (later dropped) |
| 26 | 20260428000020 | ledger_mae | ✅ | strategy_ledger.max_pain_bps |
| 27 | 20260428114056 | remote_history_alignment | ✅ | Empty (placeholder) |
| 28 | 20260504000000 | pillar2_volume_rvol | ✅ | signals.volume_rvol, universe.volume_ticker |
| 29 | 20260504000001 | pillar3_mean_reversion | ✅ | event_risk_matrices.mean_reversion_prob |
| 30 | 20260504000003 | phase3_audit_fixes | ✅ | Various fixes |
| 31 | 20260504000004 | ai_rpc | ✅ | increment_ai_usage RPC |
| 32 | 20260505000000 | round1_foundation_audit | ✅ | signals.cot_net_pos, risk_reversal_25d, rate_diff_mom (later dropped), realized_vol_21 (later dropped) |
| 33 | 20260505000001 | round3_validation_engine | ✅ | validation_log T+5/T+20 columns |
| 34 | 20260505000002 | validation_stats | ✅ | validation_stats table |
| 35 | 20260505000003 | layer3_execution_schema | ✅ | signals.realized_vol_rank, skew_alignment; regime_calls.entry_timing, position_size, stop_level |
| 36 | 20260508000001 | p0_validation_immutability | ✅ | audit_log, immutability triggers, validation_log enrichment |
| 37 | 20260508000002 | p1_audit_trail | ✅ | regime_calls.correlation_id, write_hash |
| 38 | 20260508000003 | p1_data_lineage | ✅ | historical_prices.source, fetch_timestamp |
| 39 | 20260509000001 | p1_audit_trail | ✅ | Additional audit columns |
| 40 | 20260509000002 | p1_audit_trail_fix | ✅ | pipeline_errors schema fix |
| 41 | 20260515000001 | v2_fpi_flow | ✅ | signals.fpi_flow |
| 42 | 20260515000002 | cleanup_bad_may15_data | ✅ | Data cleanup |
| 43 | 20260516000001 | cleanup_bad_may12_data | ✅ | Data cleanup + unique constraints |
| 44 | 20260518000001 | drop_webhook_subscriptions | ✅ | Drops webhook_subscriptions table |
| 45 | 20260518000002 | desk_open_cards_anon_read | ✅ | RLS policy fix |
| 46 | 20260518000003 | stream_a_signal_depth | ✅ | Adds ecb_balance_sheet, bund_btp_spread, boj_policy_rate, india_vix, inr_forward_premium |
| 47 | 20260520000001 | cleanup_stale_columns | ✅ | Drops 18 stale columns (6 from signals, 12 from validation_log) |
| 48 | 20260520000002 | pipeline_runs | ✅ | pipeline_runs table |
| 49 | 20260521000001 | drop_validation_log_notes | ✅ | Drops validation_log.notes |
| 41 | 20260515000001 | v2_fpi_flow | ✅ | signals.fpi_flow |
| 42 | 20260515000002 | cleanup_bad_may15_data | ✅ | Data cleanup |
| 43 | 20260516000001 | cleanup_bad_may12_data | ✅ | Data cleanup + unique constraints |
| 44 | 20260518000001 | drop_webhook_subscriptions | ✅ | **Fixed:** Drops webhook_subscriptions table |
| 45 | 20260518000002 | desk_open_cards_anon_read | ✅ | RLS policy fix |
| 46 | 20260518000003 | stream_a_signal_depth | ✅ | **Adds ecb_balance_sheet, bund_btp_spread, boj_policy_rate, india_vix, inr_forward_premium** |
| 47 | 20260520000001 | cleanup_stale_columns | ✅ | **Drops 18 stale columns (6 from signals, 12 from validation_log)** |
| 48 | 20260520000002 | pipeline_runs | ✅ | pipeline_runs table (renamed from duplicate timestamp) |
| 49 | 20260521000001 | drop_validation_log_notes | ✅ | **Drops validation_log.notes** |

---

## 3. Active Tables

### 3.1 Core Pipeline Tables

#### `regime_calls` — Immutable Ledger
**Purpose:** Daily regime classification per pair. **DO NOT MODIFY EXISTING ROWS.**

| Column | Type | Writable By | Notes |
|--------|------|-------------|-------|
| id | int (PK) | Auto | Serial primary key |
| pair | text | Pipeline | 3-pair lock: EURUSD, USDJPY, USDINR |
| date | date | Pipeline | Call date |
| regime | text | Pipeline | Layer 1 output (e.g., "Carry Collapse") |
| confidence | float | Pipeline | Calibrated confidence [0, 1] |
| signal_composite | float | Pipeline | Weighted composite score |
| rate_signal | text | Pipeline | BULLISH / BEARISH / NEUTRAL |
| primary_driver | text | Pipeline | e.g., "rate", "cot", "vol" |
| entry_timing | text | Pipeline | ENTER / WAIT (Layer 3) |
| position_size | text | Pipeline | FULL / HALF (Layer 3) |
| stop_level | float | Pipeline | Stop price (Layer 3) |
| data_quality_score | float | Pipeline | 0.0–1.0 freshness metric |
| stress_level | text | Pipeline | GREEN / AMBER / RED |
| predicted_direction | text | Pipeline | BULLISH / BEARISH / NEUTRAL (Layer 2) |
| directional_bias | text | Pipeline | LONG / SHORT / NEUTRAL (Layer 2) |
| conviction | int | Pipeline | 1–5 (Layer 2) |
| cot_signal | text | Pipeline | BULLISH / BEARISH / NEUTRAL |
| vol_signal | text | Pipeline | BULLISH / BEARISH / NEUTRAL / VOL_EXPANDING |
| oi_signal | text | Pipeline | BULLISH / BEARISH / NEUTRAL |
| rr_signal | text | Pipeline | BULLISH / BEARISH / NEUTRAL |
| special_signal_value | float | Pipeline | Normalized [-1, 1] |
| special_signal_label | text | Pipeline | e.g., "frag_risk", "macro_special" |
| model_version | text | Pipeline | e.g., "2.1-m3" |
| write_hash | text | Pipeline | SHA-256 for tamper detection |
| correlation_id | text | Pipeline | Trace ID |
| created_at | timestamptz | Auto | — |

**Constraints:**
- UNIQUE (pair, date)
- CHECK (confidence >= 0 AND confidence <= 1)
- Immutable trigger: blocks UPDATE/DELETE

---

#### `signals` — Daily Signal Snapshot
**Purpose:** Raw signal inputs per pair per day.

| Column | Type | Writable By | Pair-Specific | Notes |
|--------|------|-------------|---------------|-------|
| id | int (PK) | Auto | — | — |
| pair | text | Pipeline | — | 3-pair lock |
| date | date | Pipeline | — | — |
| rate_diff_2y | float | Pipeline | All | US 2Y yield |
| rate_diff_10y | float | Pipeline | All | US 10Y – quote 10Y |
| rate_diff_10y_real | float | Pipeline | All | Real yield spread |
| rate_z_tactical | float | Pipeline | All | MAD Z-score tactical |
| rate_z_structural | float | Pipeline | All | MAD Z-score structural |
| cot_percentile | float | Pipeline | EURUSD, USDJPY | USDINR uses fallback |
| cot_net_pos | int | Pipeline | EURUSD, USDJPY | Net positioning |
| cot_asset_mgr_net | int | Pipeline | EURUSD, USDJPY | AM net |
| cot_lev_money_net | int | Pipeline | EURUSD, USDJPY | LM net |
| realized_vol_20d | float | Pipeline | All | 20-day annualized RV |
| realized_vol_5d | float | Pipeline | All | 5-day annualized RV |
| implied_vol_30d | float | Pipeline | All | 30-day implied vol |
| spot | float | Pipeline | All | FX spot close |
| day_change | float | Pipeline | All | Spot change |
| day_change_pct | float | Pipeline | All | Spot change % |
| cross_asset_vix | float | Pipeline | All | VIX level |
| cross_asset_dxy | float | Pipeline | All | DXY index |
| cross_asset_oil | float | Pipeline | All | Oil price |
| cross_asset_us10y | float | Pipeline | All | US 10Y yield |
| cross_asset_gold | float | Pipeline | All | Gold price |
| cross_asset_copper | float | Pipeline | All | Copper price |
| cross_asset_stoxx | float | Pipeline | All | STOXX index |
| oi_delta | int | Pipeline | All | Open interest change |
| volume_rvol | float | Pipeline | All | Relative volume |
| structural_instability | bool | Pipeline | All | Boolean flag |
| breakeven_inflation_10y | float | Pipeline | All | T10YIE |
| realized_vol_rank | float | Pipeline | All | Vol percentile rank |
| skew_alignment | int | Pipeline | All | Skew alignment score |
| risk_reversal_25d | float | Pipeline | All | 25D RR in bps |
| fpi_flow | float | Pipeline | USDINR only | NSDL FPI flow |
| ecb_balance_sheet | float | Pipeline | EURUSD only | ECB total assets (bn EUR) |
| bund_btp_spread | float | Pipeline | EURUSD only | 10Y Bund – 10Y BTP (pp) |
| boj_policy_rate | float | Pipeline | USDJPY only | BoJ policy rate (%) |
| india_vix | float | Pipeline | USDINR only | India VIX level |
| inr_forward_premium | float | Pipeline | USDINR only | 1M forward premium (%) |
| created_at | timestamptz | Auto | — | — |

**Constraints:** UNIQUE (pair, date)

**Key rule:** `oi_delta` and `volume_rvol` are present for all pairs but OI weight in composite is 0.05 (heavily discounted).

---

#### `validation_log` — Outcome Scoring
**Purpose:** T+5 / T+20 directional accuracy scoring. **Append-only.**

| Column | Type | Writable By | Notes |
|--------|------|-------------|-------|
| id | int (PK) | Auto | — |
| date | date | Pipeline | Call date (legacy) |
| call_date | date | Pipeline | Call date (canonical) |
| pair | text | Pipeline | — |
| call | text | Pipeline | BULLISH / BEARISH / NEUTRAL |
| outcome | text | Pipeline | correct / incorrect (legacy) |
| return_pct | float | Pipeline | Legacy return field |
| actual_direction_t5 | text | Pipeline | UP / DOWN / NEUTRAL |
| actual_direction_t20 | text | Pipeline | UP / DOWN / NEUTRAL |
| log_return_t5_bps | float | Pipeline | T+5 log return in bps |
| log_return_t20_bps | float | Pipeline | T+20 log return in bps |
| correct_t5 | bool | Pipeline | Directional match |
| correct_t20 | bool | Pipeline | Directional match |
| correct_5d | bool | Pipeline | Legacy alias |
| correct_20d | bool | Pipeline | Legacy alias |
| brier_score_t5 | float | Pipeline | T+5 Brier score |
| brier_score_t20 | float | Pipeline | T+20 Brier score |
| brier_5d | float | Pipeline | Legacy alias |
| brier_20d | float | Pipeline | Legacy alias |
| actual_return_5d | float | Pipeline | T+5 return |
| actual_return_20d | float | Pipeline | T+20 return |
| log_return_net_bps_t5 | float | Pipeline | T+5 log return after round-trip cost |
| log_return_net_bps_t20 | float | Pipeline | T+20 log return after round-trip cost |
| correct_net_t5 | bool | Pipeline | Net-correctness flag after costs (T+5) |
| correct_net_t20 | bool | Pipeline | Net-correctness flag after costs (T+20) |
| cost_bps_t5 | float | Pipeline | Round-trip transaction cost in bps (T+5) |
| cost_bps_t20 | float | Pipeline | Round-trip transaction cost in bps (T+20) |
| call_id | int | Pipeline | FK → regime_calls.id |
| is_superseded | bool | Pipeline | Flag for revised calls |
| confidence | float | Pipeline | Call confidence at time |
| created_at | timestamptz | Auto | — |

**Constraints:**
- UNIQUE (call_date, pair) WHERE call_date IS NOT NULL
- UNIQUE (call_id) WHERE call_id IS NOT NULL
- Conditional immutability trigger: blocks UPDATE/DELETE on rows with brier_score_t5

---

### 3.2 Supporting Tables

| Table | Purpose | Key Columns | Writable By |
|-------|---------|-------------|-------------|
| `brief` | Per-pair AI narrative | pair, date, analysis, regime, confidence | Pipeline AI |
| `brief_log` | Daily systemic synthesis | date, brief_text, dollar_dominance, sentiment_json | Pipeline AI |
| `historical_prices` | OHLCV | pair, date, open, high, low, close, volume, source | Pipeline |
| `historical_yields` | Yield time series | series_id, date, value | Pipeline |
| `historical_cot` | COT positioning history | pair, date, net_long, asset_mgr_net, lev_money_net | Pipeline |
| `historical_cross_asset` | Cross-asset history | date, vix, dxy, oil, gold, copper, stoxx | Pipeline |
| `historical_implied_vol` | Implied vol history | date, euv, jxv | Pipeline |
| `historical_macro_surprises` | Macro release surprises | event_name, date, actual, consensus, surprise_bps | Pipeline |
| `macro_events` | Economic calendar | date, event, impact, pairs, ai_brief | Pipeline |
| `event_aliases` | Event name canonicalization | canonical_name, alias_name | Manual |
| `event_risk_matrices` | MIE / tail-risk per event | date, pair, event_name, asymmetry_ratio, exhaustion bands | Pipeline |
| `desk_open_cards` | Layer-3 execution HUD | pair, date, structural_regime, dominance_array, apex_score | Pipeline |
| `strategy_ledger` | Alpha edge tracking | date, pair, regime, primary_driver, direction, t1_hit…t5_hit | Pipeline |
| `research_analogs` | Historical analog matches | pair, as_of_date, match_date, match_score, forward_30d_return | Pipeline |
| `research_memos` | Memo archive | date, title, raw_content, ai_thesis_summary | Pipeline AI |
| `universe` | Instrument registry | pair, class, spot_ticker, yield_base, yield_quote, cot_ticker | Manual |
| `health_checks` | Pipeline health telemetry | pipeline_date, data_quality_score, sources_used, sources_failed | Pipeline |
| `pipeline_runs` | Execution metadata | date, status, dqs_score, pairs_processed, errors | Pipeline |
| `pipeline_errors` | Structured exceptions | step, error_type, message, traceback, correlation_id | Pipeline |
| `ai_usage_log` | AI request metering | date, request_count, purpose, model | Pipeline |
| `audit_log` | Immutable audit trail | operation, table_name, row_id, old_value, new_value | Auto (trigger) |
| `pair_profiles` | Per-pair weight config | pair, rate_weight, cot_weight, vol_weight, oi_weight, special_weight | Manual |
| `validation_stats` | Aggregated accuracy stats | pair, as_of_date, t5_total_calls, t5_win_rate, t5_net_win_rate, t5_mean_brier, t5_rolling_90d_accuracy, t20_total_calls, t20_win_rate, t20_net_win_rate, t20_rolling_90d_accuracy… | Pipeline |

---

## 4. What Was Removed (Cleanup History)

### 4.1 Dropped from `signals` (2026-05-20)

| Column | Reason |
|--------|--------|
| `atm_vol` | Never written by pipeline |
| `oi_price_alignment` | Never written by pipeline |
| `rate_diff_zscore` | Never written by pipeline |
| `vol_skew` | Never written by pipeline |
| `rate_diff_mom` | Added by migration but never populated by writer |
| `realized_vol_21` | Added by migration but never populated by writer |

### 4.2 Dropped from `validation_log` (2026-05-20)

| Column | Reason |
|--------|--------|
| `validation_date` | Early iteration, never populated |
| `is_correct` | Early iteration, never populated |
| `pnl_bps` | Early iteration, never populated |
| `actual_return_1d` | Early iteration, never populated |
| `alpha_return_1d` | Early iteration, never populated |
| `correct_1d` | Early iteration, never populated |
| `dxy_return_1d` | Early iteration, never populated |
| `max_intraday_adverse_bps` | Early iteration, never populated |
| `predicted_direction` | Replaced by `call` (same semantic) |
| `predicted_regime` | Ghost column, always null; refactored to join `regime_calls` |
| `regime_at_call` | Early iteration, never populated |
| `vol_regime_at_call` | Early iteration, never populated |
| `notes` | Never populated (2026-05-21) |

### 4.3 Dropped Tables from `database.types.ts` (2026-05-21)

These tables may still exist in the remote DB but are **not referenced anywhere** in the app code. They were removed from TypeScript types to reduce noise:

- `macro_releases`
- `model_predictions`
- `paper_bets`
- `paper_positions`
- `performance_summary`
- `polymarket_markets`

### 4.4 Fixed Migration Issues

| Issue | Fix |
|-------|-----|
| Duplicate timestamp `20260516000001` | Renamed `pipeline_runs.sql` → `20260520000002_pipeline_runs.sql` |
| `DROP POLICY IF EXISTS` on missing table | Reordered to `DROP TABLE IF EXISTS` first |

---

## 5. Pipeline ↔ DB Alignment

### 5.1 `SignalRow` (37 fields) ↔ `signals` (39 columns)

All 37 `SignalRow` fields are written by `write_signal_row()`. The DB has 2 extra auto-generated columns (`id`, `created_at`). **Perfect alignment.**

### 5.2 `RegimeCall` (22 fields) ↔ `regime_calls` (26 columns)

All `RegimeCall` fields map to DB columns. The DB has 4 extra columns:
- `id` (auto-generated)
- `created_at` (auto-generated)
- `correlation_id` (added by `write_regime_call`)
- `write_hash` (added by `write_regime_call`)

**Alignment: all 22 dataclass fields present in DB.**

### 5.3 `ValidationLogRow` (TypeScript) ↔ `validation_log` (24 columns)

The TypeScript type now matches the cleaned schema. `call` was manually added to the type (was missing despite existing in schema since initial migration).

---

## 6. Pair-Specific Data Rules

These rules are **enforced by convention**, not by DB constraints. The pipeline writes NULL for pair-irrelevant columns.

| Column | EURUSD | USDJPY | USDINR | Rationale |
|--------|--------|--------|--------|-----------|
| `ecb_balance_sheet` | ✅ | ❌ | ❌ | ECB is EUR-specific |
| `bund_btp_spread` | ✅ | ❌ | ❌ | Bund-BTP = EUR fragmentation |
| `boj_policy_rate` | ❌ | ✅ | ❌ | BoJ is JPY-specific |
| `india_vix` | ❌ | ❌ | ✅ | India-specific stress |
| `inr_forward_premium` | ❌ | ❌ | ✅ | INR forward market |
| `fpi_flow` | ❌ | ❌ | ✅ | NSDL FPI is INR-specific |
| `cot_percentile` | ✅ | ✅ | ⚠️ | USDINR uses `net_long` fallback (no liquid futures) |
| `cot_net_pos` | ✅ | ✅ | ⚠️ | Same as above |
| `cot_asset_mgr_net` | ✅ | ✅ | ⚠️ | Same as above |
| `cot_lev_money_net` | ✅ | ✅ | ⚠️ | Same as above |

> ⚠️ **USDINR COT:** Uses `net_long` as fallback because no liquid COT futures exist for INR. Smart spread logic falls back to net_long when AM/LM data is unavailable.

---

## 7. Change Protocol

**Before adding any new column or table:**

1. Read this file (`docs/DB_STATUS.md`)
2. Add the column to `pipeline/src/types.py` dataclass
3. Add the column to `pipeline/src/db/writer.py` payload
4. Create a migration in `supabase/migrations/`
5. Update `web/src/lib/supabase/database.types.ts`
6. Update `web/src/lib/supabase/queries.ts` if exposed to UI
7. Update this file (`docs/DB_STATUS.md`)
8. Run: `pytest`, `ruff check .`, `npx tsc --noEmit`

**Before dropping any column:**

1. Verify zero references in `pipeline/src/`, `web/src/`, and `docs/`
2. Verify the column is never populated (check `information_schema` + data samples)
3. Create a migration with `DROP COLUMN IF EXISTS`
4. Update `database.types.ts`
5. Update this file

---

## 8. Verification Commands

```bash
# Run all checks
cd pipeline && pytest                # 234 tests
cd pipeline && ruff check .          # lint
cd web && npx tsc --noEmit           # TypeScript

# Check migration sync
supabase migration list --linked

# Check schema alignment (run from authenticated env)
psql -h db.weaaacohvzzgkgxzpaee.supabase.co -U postgres -d postgres \
  -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'signals' ORDER BY column_name;"
```

---

*This document is maintained by the FX Regime Lab agent system. Any agent modifying the database must update this file and reference it in commit messages.*
