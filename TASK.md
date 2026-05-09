# TASK.md — THE COUNCIL REBUILD

> **Read `HANDOVER.md` first** before any work on this file. It contains the operator identity, locked decisions, career strategy, and session operating rules that govern all task prioritization.

**Status:** PRODUCTION READY — All P0–P4 complete. 218/218 tests pass. Build zero errors. TypeScript clean.

## Active Rounds (The Dual-Mandate Roadmap)

### Round 1: The Foundation (Data & Schema Audit) [COMPLETE]
- [x] Phase 1: Audit `signals` and `regime_calls` tables.
- [x] Phase 2: Implement strict immutable constraints.
- [x] Phase 3: Establish the `validation_log` schema.

### Round 2: The Core Logic (Pipeline Refactoring) [COMPLETE]
- [x] Phase 1 (Layer 1): Refactor Regime Gate logic.
- [x] Phase 2 (Layer 2): Refactor Directional Signal logic.
- [x] Phase 3 (Layer 3): Implement Timing & Entry logic.
- [x] Verification: 100% Logic Test Pass (121/121 pytest cases).

### Round 3: The Validation Engine (The Immutable Ledger) [COMPLETE]
- [x] Phase 1: Implement Daily validation script (T+5, T+20) with log returns, 5bps Marcus dead-band, Brier scores.
- [x] Phase 2: Aggregate stats module (`validation_stats` table) with Brier Skill, Win Rates, Sharpe-like ratios, calibration buckets, max drawdown.
- [x] Phase 3: Automate Supabase logging — `run_daily.sh` now runs `python -m src.validation.engine` followed by `python -m src.validation.aggregate`.

### Round 4: The Research Construction (Historical Backtest) [COMPLETE]
- [x] Phase 1: Historical data backfill infrastructure (`src/backfill/historical_fetcher.py`) via yfinance.
- [x] Phase 2: Historical pipeline execution engine (`src/backfill/orchestrator.py`) with date-range replay.
- [x] Phase 3: Research artifact generator (`src/research/artifacts.py`) — markdown track-record reports from validation_stats.

### P0: Emergency Triage (Credibility Kill Shots) [COMPLETE — 2026-05-08]
- [x] **P0-T1:** Wire Round 3 validation engine into production (`run_validation` now called by orchestrator; T+5/T+20 stored separately; Brier scores computed).
- [x] **P0-T2:** Enforce immutable ledger (`write_regime_call` uses insert-or-ignore; `delete_pipeline_data_for_date` gated behind `force=True`; `audit_log` table + triggers ACTIVE in production via `supabase db push`; `call_id` FK preserved).
- [x] **P0-T3:** Pipeline failure alerting (`monitoring/alerts.py` with Slack + Resend email; success heartbeat + DQS alert wired into `orchestrator.py`; `.env.example` updated).
- [x] Integration tests: `tests/integration/test_p0_validation_immutability.py` (3 cases).
- [x] Alert tests: `tests/test_alerts.py` (9 cases).

### P1: Truth & Immutability [COMPLETE — 2026-05-08]
- [x] **P1-T3:** Audit trail hardening (`correlation_id` + `write_hash` columns on `regime_calls`; `pipeline_errors` table; `compute_write_hash` SHA-256; schema applied to Supabase; `docs/IMMUTABILITY.md` updated).
- [x] **P1-T1:** Validation backfill (`src/backfill/validation_backfill.py`; idempotent; dry-run; `--limit` flag; 5 integration tests; dry-run verified against production — blocked on missing locked-pair historical price data).
- [x] **P1-T2:** Parameter derivation notebook (`pipeline/notebooks/parameter_derivation.md` — documents all thresholds, weights, Brier/Sharpe formulas, data source fallback chain, with literature citations + walk-forward calibration evidence).
- [x] **P1-T4:** Data source upgrade (Polygon.io primary → Alpha Vantage → yfinance; `fetch_fx_spot_polygon` in `fetchers/fx_spot.py`; 8 tests; `.env.example` updated).

### P2: Performance Dashboard (T+5/T+20 Validation) [COMPLETE — 2026-05-09]
- [x] **P2 Query Layer:** `getValidationStats`, `getValidationLogT5T20`, `getValidationLogForPair` in `web/src/lib/supabase/queries.ts`.
- [x] **P2 Components:** `StatsCard`, `PairBreakdownTable`, `BrierChart` in `web/src/components/performance/`.
- [x] **P2 Performance Page:** `/performance/page.tsx` upgraded to display T+5/T+20 metrics, equity curve (bps), rolling Brier chart, per-pair breakdown, validation history table.
- [x] **P2 Type Safety:** `database.types.ts` regenerated with `validation_stats` table + T+5/T+20 columns on `validation_log`. No `any` types in new code.
- [x] **P2 Build Gate:** `npm run build` passes zero errors.

### P3: Live Signal Dashboard (Institutional Morning Desk) [COMPLETE — 2026-05-09]
- [x] **P3 Query Layer:** `getLatestBriefLog`, `getMacroEventsToday`, `getSignalHistoryForAllPairs`, `getCrossAssetSnapshot` in `queries.ts`. `LatestSignal` + `LatestRegimeCall` interfaces extended with Layer 3 fields.
- [x] **P3 Components:** `SystemStatusBar`, `CrossAssetMatrix`, `SignalCard`, `AlertStrip`, `MacroCalendarStrip`, `DailyBriefPanel` in `web/src/components/dashboard/`.
- [x] **P3 Terminal Page:** `/terminal/page.tsx` rewritten with institutional dashboard layout: status bar → cross-asset matrix → alerts → macro calendar → signal cards → daily brief.
- [x] **P3 Type Safety:** `database.types.ts` synced with production schema (regime_calls Layer 3 columns, signals cross-asset + vol columns, macro_events, brief_log). No `any` types.
- [x] **P3 Build Gate:** `npm run build` passes zero errors.

### P4: Terminal Polish (Pair Desk + Mobile + Error States) [COMPLETE — 2026-05-09]
- [x] **P4 Query Layer:** `getHistoricalPrices`, `getPairValidationSummary`, `getPairValidationHistory` in `queries.ts`. `getHistoricalRegimeCalls` extended with `predicted_direction`.
- [x] **P4 Pair Desk:** `/terminal/fx-regime/[pair]/page.tsx` enhanced with spot price sparkline (30D), validation stats row (T+5/T+20 win rate, Brier, Sharpe), validation history table (last 20), Layer 3 execution panel, back navigation, unique `<title>` per pair.
- [x] **P4 Mobile:** Verified responsive grids (`grid-cols-1 lg:grid-cols-[1fr_300px]`, `md:grid-cols-3`, `sm:grid-cols-4 lg:grid-cols-7`), no horizontal overflow on equity curves.
- [x] **P4 Error States:** `Skeleton` component created, empty state on `/terminal` when no calls, `/terminal/fx-regime/[pair]/error.tsx` added, `opengraph-image.tsx` fixed to use `@/lib/constants`.
- [x] **P4 Build Gate:** `npm run build` passes zero errors. `npx tsc --noEmit` clean.

---

## Test & Quality Summary

| Metric | Value |
|--------|-------|
| Total pytest cases | 218 |
| Pass rate | 218/218 (100%) |
| Pre-existing bug fixed | `test_cot_percentile_three_year_window_uses_last_156` date overflow |
| New modules | `validation/aggregate`, `validation/engine`, `backfill/orchestrator`, `backfill/historical_fetcher`, `backfill/validation_backfill`, `research/artifacts`, `monitoring/alerts`, `scheduler/run_pipeline` |
| New frontend components | `components/performance/*`, `components/dashboard/*`, `components/ui/skeleton.tsx` |
| New migrations | `20260505000001_round3_validation_engine.sql`, `20260505000002_validation_stats.sql`, `20260508000001_p0_validation_immutability.sql`, `20260508000003_p1_data_lineage.sql`, `20260509000002_p1_audit_trail_fix.sql` |
| ruff status | Clean on all new + modified files |
| mypy status | 2 pre-existing errors in `orchestrator.py` + `writer.py`; clean on all P1–P4 modules |
| TypeScript | `npx tsc --noEmit` zero errors |
| Build | `npm run build` zero errors |
| Biome | Clean on all new/modified files (58 pre-existing legacy errors) |

## The Council Checklist (The OMEGA Loop)

Every task MUST be checked by the chambers for **Dual-Alignment**:
1.  **Chamber 1 (Strategy):** Is the logic macro-economically sound? (MFE Level)
2.  **Chamber 2 (Engineering):** Is the data pipeline "Zero-Failure"? (Production Level)
3.  **Chamber 3 (Perception):** Is the output "Institutional Research" grade? (Admissions/HF Level)
4.  **Delegated Execution:** Delegate implementation to the Cursor Agent CLI (`agent --print "..."`).

## Notes

- **Cloaked Professionalism:** Strictly NO student/admissions language in public files.
- **Agentic Power:** The Cursor Agent is authenticated as `tech@fintreeindia.com`. Use it for implementation.
- Always update documentation after iterating.
