# Supabase read inventory (removed Next.js app)

This document snapshots the data-access surface that lived in `web/lib/supabase/queries.ts` before the shipped UI was removed. Use it when rebuilding from `claude-design/` or another stack.

**Tracked pairs (UI):** `EURUSD`, `USDJPY`, `USDINR` (see also pair accent hexes: EURUSD `#4BA3E3`, USDJPY `#F5923A`, USDINR `#D94030`).

## Tables and operations

| Function | Table(s) | Select / filter (summary) |
|----------|----------|---------------------------|
| `getLatestRegimeCalls` | `regime_calls` | `*`, `pair` in tracked pairs, order `date` desc, dedupe latest per pair |
| `getRegimeHeatmap` | `regime_calls` | `date, pair, regime`, last 30 days, tracked pairs |
| `getRegimeHistory` | `regime_calls` | `date, regime, confidence`, `pair` eq, limit 90 |
| `getLatestSignals` | `signals` | `*`, `pair` eq, limit 10 |
| `getLatestBrief` | `brief` | `*`, `pair` eq, limit 1 latest |
| `getUpcomingMacroEvents` | `macro_events` | `*`, date window today→+14d, `impact` in HIGH/MEDIUM |
| `getValidationLog` | `validation_log` | `*`, order `date` desc, default limit 30 |
| `getValidationStats` | `validation_log` | `correct_1d, actual_return_1d, date` — aggregates win rate, median return, days live |
| `getAllValidationRows` | `validation_log` | `*`, order `date` desc |
| `getEquityCurve` | `validation_log` | `date, pair, actual_return_1d`, tracked pairs, order `date` asc |
| `getLastPipelineRun` | `regime_calls` | `created_at` only, latest row |
| `getHomepageKpis` | `validation_log` | derived KPIs (calls since 2026-04-01, rolling 7d accuracy, pair count) |
| `getShellPerformanceMetrics` | `validation_log` + `getEquityCurve` | rolling 7d, totals, per-pair rolling, cumulative equity last |
| `getRegimeCallsForTransitions` | `regime_calls` | `date, pair, regime`, ~730d window, tracked pairs, order `date` asc |

**Client:** All calls used `createClient()` from `web/lib/supabase/client.ts` (browser/server per import site).

**Row shaping:** `web/lib/supabase/map-row.ts` mapped validation rows for equity curves (`mapEquityCurve`).

Regime strings from Postgres may not match strict TS unions — see `docs/DATABASE_SCHEMA.md`.
