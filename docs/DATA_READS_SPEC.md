# Data Reads Spec

Live inventory of all Supabase read functions in `web/src/lib/supabase/queries.ts`. These are the only data-access functions used by the Next.js frontend.

**Tracked pairs (UI):** `EURUSD`, `USDJPY`, `USDINR`.

**Client paths:**
- Browser: `web/src/lib/supabase/client.ts`
- Server: `web/src/lib/supabase/server.ts`

---

## Query Functions

### Regime Calls

| Function | Table | Select / filter | Return type |
|----------|-------|-----------------|-------------|
| `getLatestRegimeCalls(supabase)` | `regime_calls` | `*`, order `date` desc, limit 100, dedupe latest per pair | `Record<string, LatestRegimeCall>` |
| `getHistoricalRegimeCalls(supabase, pair, limit?)` | `regime_calls` | `date, regime, confidence, signal_composite, primary_driver, rate_signal, entry_timing, position_size, stop_level, created_at, predicted_direction`, `pair` eq, order `date` desc | `Array<{date, regime, confidence, signal_composite, primary_driver, rate_signal, entry_timing, position_size, stop_level, created_at, predicted_direction}>` |

### Signals

| Function | Table | Select / filter | Return type |
|----------|-------|-----------------|-------------|
| `getLatestSignals(supabase)` | `signals` | `*`, order `date` desc, limit 100, dedupe latest per pair | `Record<string, LatestSignal>` |
| `getSignalHistory(supabase, pair, limit?)` | `signals` | `date, spot, rate_diff_2y, cot_percentile, realized_vol_20d`, `pair` eq, order `date` desc, reversed to ascending | `Array<{date, spot, rate_diff_2y, cot_percentile, realized_vol_20d}>` |
| `getSignalHistoryForAllPairs(supabase, limit?)` | `signals` | `*`, order `date` desc, limit `limit * 3`, grouped by pair, sorted ascending per pair | `Record<string, SignalRow[]>` |
| `getCrossAssetSnapshot(supabase)` | `signals` | `date, cross_asset_vix, cross_asset_dxy, cross_asset_oil, cross_asset_gold, cross_asset_copper, cross_asset_stoxx, cross_asset_us10y`, order `date` desc, limit 6. Computes latest vs previous day changes. | `CrossAssetSnapshot` |

### Validation

| Function | Table | Select / filter | Return type |
|----------|-------|-----------------|-------------|
| `getValidationLog(supabase, limit?)` | `validation_log` | `*`, order `date` desc, limit 500, filters `correct_t5 !== null && log_return_t5_bps != null` | `ValidationRow[]` |
| `getValidationLogT5T20(supabase, limit?)` | `validation_log` | `*`, `brier_score_t5` not null, `date >= 2026-04-01`, order `date` desc, limit 500 | `ValidationRowT5[]` |
| `getValidationStats(supabase, horizon)` | `validation_stats` | `*`, order `as_of_date` desc, limit 100, filtered to latest `as_of_date` only. Returns either T+5 or T+20 metrics based on `horizon`. | `ValidationStats[]` |
| `getValidationLogForPair(supabase, pair, limit?)` | `validation_log` | `*`, `pair` eq, `brier_score_t5` not null, order `date` desc, limit 200 | `ValidationRowT5[]` |
| `getPairValidationSummary(supabase, pair)` | `validation_stats` | `*`, `pair` eq, order `as_of_date` desc, limit 1 | `PairValidationSummary \| null` |
| `getPairValidationHistory(supabase, pair, limit?)` | `validation_log` | `*`, `pair` eq, `brier_score_t5` not null, order `date` desc, limit 20 | `PairValidationHistoryItem[]` |
| `getRegimeBreakdown(supabase, limit?)` | `validation_log` + `regime_calls` | Validation outcomes joined with regime labels by `date|pair` composite key. Filters `brier_score_t5` not null, `date >= 2026-04-01`. | `RegimeBreakdownRow[]` |

### Briefs

| Function | Table | Select / filter | Return type |
|----------|-------|-----------------|-------------|
| `getLatestBrief(supabase)` | `brief_log` | `*`, order `date` desc, limit 1 | `BriefLogRow \| null` |

### Research Memos

| Function | Table | Select / filter | Return type |
|----------|-------|-----------------|-------------|
| `getResearchMemosList(supabase, limit?)` | `research_memos` | `id, date, title, link_url`, order `date` desc, limit 50 | `Pick<ResearchMemoRow, "id" \| "date" \| "title" \| "link_url">[]` |
| `getResearchMemoByDate(supabase, date)` | `research_memos` | `*`, `date` eq, `maybeSingle()` | `ResearchMemoRow \| null` |

### Macro Events

| Function | Table | Select / filter | Return type |
|----------|-------|-----------------|-------------|
| `getMacroEventsToday(supabase)` | `macro_events` | `*`, `date` eq today, `impact` eq HIGH, order `event` asc | `MacroEventRow[]` |

### Historical Prices

| Function | Table | Select / filter | Return type |
|----------|-------|-----------------|-------------|
| `getHistoricalPrices(supabase, pair, limit?)` | `historical_prices` | `date, close`, `pair` eq, order `date` desc, limit 30, reversed to ascending | `Array<{date, close}>` |

### Pipeline Health

| Function | Table | Select / filter | Return type |
|----------|-------|-----------------|-------------|
| `getPipelineHealth(supabase, days?)` | `health_checks` (fallback: `regime_calls`, `signals`, `brief_log`, `validation_stats`) | Primary: `health_checks` `*`, `pipeline_date >= cutoff`, order desc. Fallback infers status from data presence across 4 tables. | `PipelineDayHealth[]` |
| `getLatestAccuracyAlerts(supabase)` | `validation_stats` | `*`, order `as_of_date` desc, limit 20, filtered to latest date, `pair !== "ALL"`. Alerts when rolling accuracy < 50% (critical) or EURUSD < 55% (warning). | `AccuracyAlert[]` |

---

## Exported Types

| Type | Shape |
|------|-------|
| `LatestRegimeCall` | `pair, date, regime, confidence, signal_composite, rate_signal, cot_signal, vol_signal, rr_signal, oi_signal, primary_driver, special_signal_value, special_signal_label, model_version, data_quality_score, stress_level, created_at, predicted_direction, entry_timing, position_size, stop_level` |
| `LatestSignal` | `pair, date, spot, rate_diff_2y, cot_percentile, realized_vol_20d, realized_vol_5d, implied_vol_30d, day_change, day_change_pct, cross_asset_us10y, realized_vol_rank, rate_z_tactical, rate_z_structural, rate_diff_10y_real, breakeven_inflation_10y, skew_alignment, risk_reversal_25d, fpi_flow, cot_net_pos, cot_asset_mgr_net, cot_lev_money_net, created_at` |
| `ValidationRow` | `date, pair, call, outcome: "correct" \| "incorrect", return_pct` |
| `ValidationStats` | `pair, horizon: "t5" \| "t20", winRate, wins, brierScore, sampleSize, avgReturnBps, sharpeLike, rolling90dAccuracy, asOfDate` |
| `ValidationRowT5` | `date, pair, predicted, t5ReturnBps, t5Outcome, t5Brier, t20ReturnBps, t20Outcome, t20Brier` |
| `RegimeBreakdownRow` | `pair, regime, t5Outcome, t20Outcome` |
| `PairValidationSummary` | `t5WinRate, t5Brier, t5SampleSize, t5SharpeLike, t20WinRate, t20Brier, t20SampleSize, t20SharpeLike` |
| `PairValidationHistoryItem` | `date, predicted, t5Outcome, t5ReturnBps, t5Brier, t20Outcome, t20ReturnBps, t20Brier` |
| `CrossAssetSnapshot` | `vix, dxy, oil, gold, copper, stoxx, us10y` — each `{value, change}` |
| `PipelineDayHealth` | `date, status, dqs, regimeCallsCount, stepsCompleted, stepsFailed, validationComputed, aiBriefsGenerated, errors` |
| `AccuracyAlert` | `pair, accuracy, threshold, severity: "critical" \| "warning"` |
| `BriefLogRow` | Database row type from `brief_log` |
| `MacroEventRow` | Database row type from `macro_events` |

---

## Notes

- All functions accept `TypedSupabaseClient` (`Awaited<ReturnType<typeof createClient>>` from `server.ts`).
- Row mapping is inline; there is no separate `map-row.ts` file.
- `validation_stats` is a standalone table, not derived from `validation_log` at query time.
- `brief_log` is the current table name (formerly `brief`).
- Regime strings from Postgres may not match strict TS unions — see `docs/DB_STATUS.md` for live schema reference.
