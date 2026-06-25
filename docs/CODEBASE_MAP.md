# CODEBASE_MAP — Complete Navigation Guide

> Last updated: 2026-05-10  
> Purpose: Single source of truth for navigating the FX Regime Lab codebase.

---

## Signal Flow (End-to-End)

```
[FRED/Yahoo/CFTC] → [Fetchers] → [Signals] → [Logic Layer 1/2/3] → [Regime Classifier] → [DB Writer] → [Supabase]
                                                                          ↓
                                                                    [Validation Engine]
                                                                          ↓
                                                                    [AI Brief Generator]
```

---

## Pipeline Map (`pipeline/src/`)

### Data Ingestion (`fetchers/`)
| File | Purpose | Key Functions |
|------|---------|---------------|
| `fx_spot.py` | FX spot prices via Alpha Vantage + yfinance fallback | `fetch_fx_spot()` |
| `yields.py` | Treasury yields via FRED API | `fetch_us_yields()`, `fetch_de_yields()` |
| `cot.py` | CFTC Commitment of Traders reports | `fetch_cot_report()` |
| `volatility.py` | Realized vol, implied vol, risk reversal skew | `fetch_vol_data()` |
| `open_interest.py` | CME futures open interest | `fetch_oi_data()` |
| `cross_asset.py` | VIX, DXY, oil, gold, copper, equities | `fetch_cross_asset()` |
| `macro_calendar.py` | ForexFactory high-impact events | `fetch_forexfactory_week_high_impact()` |
| `substack.py` | Published memo RSS feeds | `fetch_substack_posts()` |
| `polymarket.py` | Prediction market odds (experimental) | `fetch_polymarket_odds()` |
| `async_engine.py` | Concurrent fetch orchestrator | `run_all_fetchers()` |
| `buffer_keys.py` | Ingestion buffer key definitions | — |

### Signal Computation (`signals/`)
| File | Purpose | Key Math |
|------|---------|----------|
| `rate.py` | Yield spread signals, robust MAD Z-score | `rate_direction_from_spreads()` — z_tactical threshold ±0.30 |
| `cot.py` | COT net positioning normalization | Percentile ranking over 3-year lookback |
| `volatility.py` | Realized vol rank, vol expanding flag | RV20 annualized, empirical CDF rank |
| `open_interest.py` | OI delta normalization | Z-score of OI change |
| `special.py` | Pair-specific special signals | Breakeven inflation shock, carry fade |

### Core Logic (`logic/`)
| File | Purpose | Key Concepts |
|------|---------|--------------|
| `layer1_gate.py` | Regime classification from macro state | Composite hysteresis, rolling z-score (252d), momentum (20d), spot stress |
| `layer2_directional.py` | Directional bias + conviction (1–5) | COT crowding ramp, Marcus B clash veto, conviction multiplier m_π |
| `layer3_execution.py` | Entry timing, stops, sizing | RVOL rank, skew reversal, MIE proxy, position sizing (FULL/HALF/QUARTER) |
| `math_utils.py` | Shared statistical utilities | Robust MAD Z-score, hysteresis tier, empirical CDF |

### Regime Classification (`regime/`)
| File | Purpose | Key Functions |
|------|---------|---------------|
| `classifier.py` | UI metadata adapter for gate output | `classify_regime_layer1()`, `get_regime_metadata()` |
| `composite.py` | Weighted signal aggregation | `compute_composite()`, `compute_dynamic_betas()`, `get_primary_driver()` |
| `confidence.py` | Confidence computation | `compute_confidence()` — base = \|composite\|/2.0, bonus for alignment |

### Database (`db/`)
| File | Purpose | Key Functions |
|------|---------|---------------|
| `writer.py` | **ALL Supabase writes go through here** | `write_regime_call()`, `write_signal_row()`, `write_validation_row()`, `write_validation_stats()` |
| `rollback.py` | Rollback utilities for failed runs | — |

### Validation (`validation/`)
| File | Purpose | Key Concepts |
|------|---------|--------------|
| `engine.py` | T+5/T+20 outcome scoring | `log_return_bps()`, `realized_direction()`, `is_correct()`, Brier score |
| `aggregate.py` | Per-pair aggregate stats | Win rate, Brier skill, Sharpe-like, calibration buckets |
| `backtest.py` | Historical replay engine | Forward-walking backtest over any date range |
| `ledger.py` | Alpha ledger tracking | EOD calls vs T+1/3/5 outcomes |
| `calendar.py` | Trading day arithmetic | `add_trading_days()` — skips weekends |
| `ingestion_buffer.py` | Idempotency and buffering | Prevents duplicate fetches |

### Backfill (`backfill/`)
| File | Purpose | Key Concepts |
|------|---------|--------------|
| `simulation_engine.py` | Walk-forward historical simulation | Deterministic replay using historical yields + spots |
| `fred_historical.py` | Bulk FRED yield fetcher | Downloads full series observations |
| `historical_fetcher.py` | yfinance spot backfill | `fetch_historical_spot_yfinance()` |
| `validation_backfill.py` | Per-call validation backfill | T+5/T+20 metrics for unvalidated regime_calls |
| `batch_validation_backfill.py` | **Fast batch validation** | pg8000 direct SQL for ~17k rows |
| `batch_validation_stats.py` | **Fast batch stats** | pg8000 aggregate stats computation |
| `orchestrator.py` | Backfill orchestration | — |

### AI Briefs (`ai/`)
| File | Purpose | Key Concepts |
|------|---------|--------------|
| `client.py` | **ALL AI calls go through here** | OpenRouter API, 180 req/day guarding, MiniMax M1 primary |

### Scheduler (`scheduler/`)
| File | Purpose | Key Concepts |
|------|---------|--------------|
| `orchestrator.py` | Prefect daily flow orchestrator | `run_daily()` — fetches → signals → regime → writes → briefs |
| `run_pipeline.py` | Local pipeline runner | — |
| `overnight_check.py` | Pre-run health checks | — |

### Analysis (`analysis/`)
| File | Purpose |
|------|---------|
| `asymmetry.py` | JPY asymmetry analysis (BoJ policy) |
| `event_risk.py` | Event risk scoring from macro calendar |
| `event_name_normalize.py` | Event name canonicalization |
| `markov.py` | Markov regime transition matrices |
| `systemic.py` | Cross-asset systemic risk scoring |

### Auto-Ops (`auto/`)
| File | Purpose |
|------|---------|
| `deploy.py` | Deployment automation |
| `fix.py` | Auto-fix scripts |
| `monitor.py` | Health monitoring |
| `plan.py` | Planning utilities |
| `readiness.py` | Pre-deploy readiness checks |
| `report.py` | Report generation |
| `self_heal.py` | Self-healing logic |
| `triage.py` | Issue triage |

### Research (`research/`)
| File | Purpose |
|------|---------|
| `artifacts.py` | Markdown track-record reports from validation_stats |

### Types (`types.py`)
| File | Purpose |
|------|---------|
| `types.py` | Central dataclasses: `SignalRow`, `RegimeCall`, `Layer1ClassifierContext`, `Layer2DirectionalOutput`, etc. |

---

## Frontend Map (`web/src/`)

### App Router (`app/`)
| Route | File | Purpose |
|-------|------|---------|
| `/` | `page.tsx` | Landing: ticker marquee, latest calls, methodology teaser |
| `/terminal` | `terminal/page.tsx` | Live cross-pair overview, system status |
| `/terminal/fx-regime` | `terminal/fx-regime/page.tsx` | FX basket mosaic: apex targets, bench pairs, outliers |
| `/terminal/fx-regime/[pair]` | `terminal/fx-regime/[pair]/page.tsx` | **Pair Desk**: spot, regime, confidence, composite |
| `/terminal/performance` | `terminal/performance/page.tsx` | Alpha ledger, Brier scores, win rates |
| `/terminal/memos` | `terminal/memos/page.tsx` | Research memo archive |
| `/terminal/calendar` | `terminal/calendar/page.tsx` | Macro event calendar |
| `/methodology` | `methodology/page.tsx` | 3-layer framework docs with KaTeX |
| `/about` | `about/page.tsx` | Operational identity, data sources, disclaimers |
| `/audit` | `audit/page.tsx` | Pipeline run history, DQS scores, error log |
| `/brief` | `brief/page.tsx` | Latest AI-generated daily brief |
| `/memo/[date]` | `memo/[date]/page.tsx` | Individual memo page |

### Components (`components/`)
| Directory | Purpose |
|-----------|---------|
| `dashboard/` | SystemStatusBar, SignalCard, CrossAssetMatrix, DailyBriefPanel, AlertStrip, MacroCalendarStrip |
| `regime/` | RegimeCard, ValidationTable |
| `performance/` | StatsCard, PairBreakdownTable, BrierChart |
| `shell/` | Nav, Footer |
| `terminal/` | TerminalNav, TerminalSubNav |
| `ui/` | Low-level UI: confidence-bar, sparkline, desk-card, skeleton, etc. |
| `layout/` | Command palette, global macro pulse |
| `pages/` | Page-level content wrappers |
| `providers/` | TanStack Query provider |

### Data Layer (`lib/`, `hooks/`)
| File | Purpose |
|------|---------|
| `lib/supabase/client.ts` | Browser Supabase client |
| `lib/supabase/server.ts` | Server-side Supabase client |
| `lib/supabase/queries.ts` | Typed queries |
| `lib/supabase/database.types.ts` | **Generated types** — never edit manually |
| `lib/queries.ts` | React Query hooks |
| `lib/pairProfiles.ts` | Pair metadata (tickers, descriptions) |
| `lib/fxCorrelation.ts` | FX basket correlation matrix |
| `lib/constants.ts` | App constants |
| `hooks/useLocalSettings.ts` | Local storage settings |
| `hooks/useReducedMotion.ts` | Accessibility: reduced motion |
| `hooks/useScrollReveal.ts` | Scroll-triggered animations |

---

## Database Map

### Core Tables
| Table | Purpose | Immutable |
|-------|---------|-----------|
| `signals` | Daily signal rows per pair | Yes (upsert on pair,date) |
| `regime_calls` | Regime classifications | **Yes** — append only, no UPDATE/DELETE |
| `validation_log` | T+5/T+20 outcomes | **Yes** — append only |
| `validation_stats` | Aggregate statistics | No (upsert on as_of_date,pair) |
| `brief_log` | Generated AI briefs | Yes |
| `pipeline_errors` | Operational errors | Yes |
| `desk_open_cards` | Per-pair desk cards | No |
| `strategy_ledger` | Strategy tracking | No |
| `research_analogs` | Research memo analogs | No |
| `historical_prices` | Backfilled spot prices | Yes (upsert on pair,date) |
| `historical_yields` | Backfilled FRED yields | Yes (upsert on series_id,date) |
| `universe` | Supported pairs list | No |
| `audit_log` | Trigger-based audit trail | Yes |

### Key Constraints
- `regime_calls`: CHECK `directional_bias IN ('LONG', 'SHORT', 'NEUTRAL')`
- `regime_calls`: CHECK `predicted_direction IN ('BULLISH', 'BEARISH', 'NEUTRAL')`
- Triggers: `trg_protect_immutable_calls` (blocks UPDATE/DELETE), `trg_protect_immutable_validation` (blocks UPDATE/DELETE on validated rows)

---

## Infrastructure Map

### Orchestration
| Component | Technology | Entrypoint |
|-----------|-----------|------------|
| Daily pipeline | Prefect Cloud | `scheduler/orchestrator.py:run_daily` |
| Weekly pipeline | Prefect Cloud | `scheduler/orchestrator.py:run_weekly` |

### API / Edge
| Component | Technology | Routes |
|-----------|-----------|--------|
| Cloudflare Worker | Workers | `/api/health`, `/api/substack-rss`, `/api/fx-price`, `/proxy/yahoo` |

### Frontend Hosting
| Component | Technology | Notes |
|-----------|-----------|-------|
| Vercel | Next.js 15 | Auto-deploy on `main` push |

### Database
| Component | Technology | Notes |
|-----------|-----------|-------|
| Supabase | PostgreSQL 17 | RLS enabled, service-role key for pipeline writes |

---

## Mathematics Glossary

### Z-Score (Robust MAD)
```
z = (x_t - median(x)) / (MAD * 1.4826)
MAD = median(|x_i - median(x)|)
```
Used in: `rate.py`, `math_utils.py`. More resistant to outliers than standard z-score.

### Composite Score
```
S = β_rate * z_rate + β_cot * z_cot + β_vol * z_vol + β_oi * z_oi + special_signal
β_dynamic = computed from 90-day rolling correlations
```
Used in: `composite.py`. Weights adapt to which signal has been most predictive recently.

### Brier Score
```
B = (p - y)²
p = model confidence (0–1)
y = 1.0 (correct), 0.0 (wrong), 0.5 (neutral)
```
Used in: `validation/engine.py`, `validation/aggregate.py`. Measures probabilistic calibration. Random guess = 0.25.

### Conviction Multiplier
```
m_π = (1 - 0.48 * p_crowd) * align
align = 1.0 if rate_sign == pos_sign else 0.72
p_crowd = max(φ_upper(π), φ_lower(π))
```
Used in: `layer2_directional.py`. Penalizes crowding and misalignment.

### Hysteresis Tiers
```
Tier 4: composite > +0.85        → RISK_OFF_DOLLAR_BID
Tier 3: +0.30 < composite ≤ +0.85 → GROWTH_SURPRISE_USD
Tier 2: -0.30 ≤ composite ≤ +0.30 → NEUTRAL
Tier 1: -0.85 ≤ composite < -0.30 → RISK_ON_DOLLAR_OFF
Tier 0: composite < -0.85        → RISK_ON_DOLLAR_OFF (strong)
```
Used in: `layer1_gate.py`. Prevents regime flickering near thresholds.

### Marcus Invalidation Rules
1. **Marcus A (Stale Data):** Layer 1 invalidated if carry_series < 252 days
2. **Marcus B (Rate-Positioning Clash):** Veto if rate_sign * pos_sign < 0
3. **Marcus C (Composite-Rate Clash):** Veto if composite and rate strongly disagree

Used in: `layer2_directional.py`, `layer1_gate.py`.

---

## Test Coverage

| Test File | Coverage |
|-----------|----------|
| `test_layer1_gate.py` | Regime gate, Marcus invalidation, composite hysteresis |
| `test_layer2_directional.py` | COT percentile, crowding ramp, conviction multiplier |
| `test_layer3_execution.py` | Vol rank, skew reversal, entry timing, stops, sizing |
| `test_signals.py` | Signal calculation correctness |
| `test_regime.py` | Regime classifier output validation |
| `test_validation.py` | Ledger / backtest logic |
| `test_validation_aggregate.py` | Aggregate stats computation |
| `test_validation_engine.py` | Directional accuracy, Brier scoring |
| `test_systemic.py` | Systemic / cross-asset logic |
| `test_ingestion_buffer.py` | Fetcher buffering & idempotency |
| `test_ledger.py` | Database persistence rules |
| `test_backfill.py` | Historical backfill logic |
| `test_fx_spot_fallback.py` | FX spot fetcher fallback chains |
| `test_alerts.py` | Alert generation logic |
| `test_writer.py` | DB writer correctness |
| `test_auto/*.py` | Auto-ops system health |

**Total: 219 tests, all passing.**

---

## File-to-File Dependencies (Critical Paths)

### The Sacred Write Path
```
Any fetcher → signals/ → logic/ → regime/ → db/writer.py → Supabase
```
**Rule:** No module outside `db/writer.py` may call `supabase-py` directly.

### The Immutable Ledger Path
```
scheduler/orchestrator.py → db/writer.py.write_regime_call() → regime_calls table
```
**Rule:** `regime_calls` rows are append-only. Triggers block UPDATE/DELETE.

### The Validation Path
```
regime_calls (existing) → validation/engine.py → db/writer.py.write_validation_row() → validation_log
```
**Rule:** Validation is computed retrospectively (T+5, T+20) and appended. Never modified.

---

## Naming Conventions

| Layer | Convention | Example |
|-------|-----------|---------|
| Python functions | `snake_case` | `compute_composite()` |
| Python classes | `PascalCase` | `Layer1ClassifierContext` |
| Python constants | `UPPER_SNAKE` | `MAD_NORMAL_SCALE = 1.4826` |
| TypeScript components | `PascalCase` | `SignalCard.tsx` |
| TypeScript hooks | `camelCase` with `use` prefix | `useLocalSettings()` |
| Database tables | `snake_case` | `regime_calls` |
| Database columns | `snake_case` | `brier_score_t5` |

---

*This map is append-only. When adding new files, update the relevant section. When changing math, update the Mathematics Glossary.*
