# FX Regime Lab — Complete Project Overview

> **Purpose of this document:** A resume-ready, ultra-detailed technical narrative of the FX Regime Lab project. It covers the full system architecture, every major module, the engineering decisions behind it, what is production-grade, and where the project is deliberately thin or experimental.

---

## 1. Executive Summary

**FX Regime Lab** is an open-source research infrastructure for transparent macro regime classification in foreign exchange. It publishes daily regime calls for three currency pairs — **EUR/USD, USD/JPY, and USD/INR** — before the outcome is known, then validates them at T+5 and T+20 horizons against realized spot returns. The entire operation is built around radical transparency: every signal, every call, and every mistake is logged in an immutable ledger and displayed publicly.

The project is intentionally **not a signal service or fintech product**. It is a research credibility engine designed to demonstrate production-grade data engineering, statistical rigor, and disciplined model governance.

**Current status:** v2.1 Experimental, live on Vercel + Prefect Cloud, with ~100 production calls and publicly disclosed near-random accuracy (~49% T+5 gross).

---

## 2. The Product & Mission

### 2.1 What It Does

- Fetches macro market data every day (yields, COT positioning, vol, FX spot, cross-asset inputs).
- Computes five signal families per pair: **Rate, COT, Volatility, OI/Risk Reversal, and Special Factor**.
- Combines signals into a pair-specific weighted composite.
- Classifies the current FX regime using a deterministic two-layer logic engine.
- Publishes a directional call with confidence before the market resolves.
- Validates every call after 5 and 20 trading days using log-returns and Brier scores.
- Renders everything on a public Next.js frontend with methodology, terminal, audit trail, and performance pages.

### 2.2 What It Explicitly Is Not

- Not a profitable trading strategy.
- Not execution advice (no public stop-losses, position sizes, or trade recommendations).
- Not a backtesting showcase (backfill is only for calibration).
- Not monetized; no subscriptions, no API for signals, no white-labeling.

### 2.3 The Transparency Principle

The project’s identity test is:

> *Does this make the regime calls more accurate, more transparent, or more publicly verifiable?*

If a feature does not pass this test, it is rejected.

---

## 3. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL DATA SOURCES                          │
│  FRED · Yahoo Finance · CFTC COT · NSE India VIX · RBI/SEBI · FBIL      │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                         PIPELINE (Python / Prefect)                      │
│  Fetchers → Signal Computation → Composite → Regime Logic → Validation   │
│  Daily flow orchestrated by Prefect Cloud; immutable ledgers in Postgres │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ writes via src/db/writer.py
┌─────────────────────────────────▼───────────────────────────────────────┐
│                         DATABASE (Supabase Postgres)                     │
│  signals · regime_calls · validation_log · brief_log · health_checks     │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ reads via Supabase SSR client
┌─────────────────────────────────▼───────────────────────────────────────┐
│                         FRONTEND (Next.js 15 / React 19)                 │
│  Landing · Terminal · Pair Desk · Performance · Methodology · Audit      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Deployment & Operations

| Layer | Technology | Deployment |
|-------|-----------|------------|
| Pipeline | Python 3.11, Prefect 3.7.0 | Prefect Cloud |
| Database | Supabase PostgreSQL | Managed Postgres |
| Frontend | Next.js 15.3.9, React 19, TypeScript 5, Tailwind CSS v4 | Vercel |
| Validation & Stats | PostgreSQL RPCs + Python engine | Cloud-scheduled |
| Monitoring | Pipeline health dashboard, Slack accuracy alerts | Internal ops only |

---

## 4. The Pipeline: Module-by-Module

The pipeline is the core of the project. It is organized as a staged, testable, and observable system.

### 4.1 Orchestration

**File:** `pipeline/src/staged/orchestrator.py`

The pipeline is orchestrated by **Prefect flows**. The main entry points are:

- `run_single_pair_flow(pair, as_of, ...)` — runs the full daily pipeline for one pair.
- `run_multi_pair_flow(...)` — runs all three pairs concurrently.

The orchestrator uses **adapter ports** for clean separation of concerns:

- `FetcherPort` — abstracts market data sources.
- `WriterPort` — abstracts database writes.
- `AlertPort` — abstracts alerting (Slack).

This port architecture makes the pipeline testable without real data sources and allows swapping infrastructure later (e.g., moving from Supabase to a different store).

### 4.2 Data Fetchers

**Files:** `pipeline/src/fetchers/`, `pipeline/src/sources/`

Fetchers pull raw market data:

- **FX spot prices** — via Yahoo Finance.
- **Sovereign yields** — 2Y and 10Y US, EU, Japan, India via FRED.
- **CFTC COT reports** — non-commercial, asset manager, and leveraged money positioning.
- **Volatility series** — EUR implied vol (`^EVZ`), India VIX (`INDIAVIX`).
- **Cross-asset inputs** — DXY, VIX, Brent crude, gold, copper, STOXX, US 10Y.
- **Pair-special inputs** — ECB balance sheet, Bund-BTP spread, BoJ policy rate, INR forward premium, FPI flows.

All fetchers return normalized dataframes and handle weekends/holidays with forward-fill and stale-data guards.

### 4.3 Signal Computation

**Files:** `pipeline/src/signals/*.py`

Five signal families are computed per pair.

#### 4.3.1 Rate Differential (`rate.py`)

- Computes US-EU, US-JP, and US-IN 2Y and 10Y yield spreads.
- Produces **dual-horizon robust MAD Z-scores**: 60% tactical (252-day) + 40% structural (2520-day).
- Returns `z_tactical`, `z_structural`, and `z_blended`.

```python
@dataclass(frozen=True)
class RateNormZ:
    z_tactical: float | None
    z_structural: float | None
    z_blended: float | None
```

This prevents the model from overreacting to short-term noise while still respecting long-term regime shifts.

#### 4.3.2 COT Positioning (`cot.py`)

- Reads weekly CFTC Commitment of Traders data.
- Computes net positioning percentile vs a trailing 3-year history.
- **Causal design:** the current observation is excluded from its own percentile calculation to prevent look-ahead bias.

#### 4.3.3 Volatility (`vol.py`)

- Computes 5-day and 20-day realized volatility.
- Compares realized vs 30-day implied vol.
- Produces a vol rank and a vol-expanding overlay that can force a neutral regime label when markets are too noisy.

#### 4.3.4 Open Interest / Risk Reversal (`oi.py`, `rr.py`)

- Open-interest delta as a flow signal.
- Risk reversal 25D skew alignment (currently a synthetic proxy; real OTC data planned for v3.0).

#### 4.3.5 Special Factor (`special.py`)

Pair-specific cross-asset signals:

| Pair | Special Inputs |
|------|---------------|
| EUR/USD | ECB balance sheet growth + Bund-BTP spread (fragmentation proxy) |
| USD/JPY | VIX stress, BoJ policy rate, intervention proximity heuristic |
| USD/INR | Brent crude, DXY, India VIX, INR forward premium, FPI flows |

### 4.4 Composite Score (`composite.py`)

**File:** `pipeline/src/regime/composite.py`

Signals are combined into a single composite score in `[-2, 2]`.

Key features:

- **Pair-specific weights:** EUR/USD is rate-heavy (45% rate), USD/INR is special-heavy (20% special + 15% FPI).
- **Dynamic Spearman betas:** Rolling 30-day Spearman correlation between each signal family and spot returns, smoothed with a 5-day EMA. Stronger historical signal-return relationships get more weight.
- **Redundancy penalty:** If multiple signals agree strongly, the composite confidence is slightly penalized to avoid double-counting correlated information.
- **Missing-leg handling:** If a signal is missing, its weight is redistributed among available signals rather than failing the pipeline.

```python
PAIR_COMPOSITE_WEIGHTS = {
    "EURUSD": PairWeightConfig(rate=0.45, cot=0.25, vol=0.20, oi=0.05, special=0.05, fpi=0.0),
    "USDJPY": PairWeightConfig(rate=0.40, cot=0.20, vol=0.25, oi=0.05, special=0.10, fpi=0.0),
    "USDINR": PairWeightConfig(rate=0.30, cot=0.10, vol=0.20, oi=0.05, special=0.20, fpi=0.15),
}
```

### 4.5 Confidence Score (`confidence.py`)

**File:** `pipeline/src/regime/confidence.py`

Confidence is an internal consistency metric:

- Base = `|composite| / 2.0`
- +0.05 if rate and COT agree directionally.
- +0.05 if both `|rate|` and `|cot|` are materially non-zero.
- Pair-specific adjustments (e.g., JPY carry stress, INR oil shock).
- Institutional −3pp haircut to under-promise.
- Heuristic Platt scaling maps raw confidence toward an empirical probability.

> **Known limitation:** confidence is not yet calibrated against real out-of-sample accuracy. Platt fitting is planned for Stream B.

### 4.6 Regime Classification — Two-Layer Logic

#### Layer 1: Deterministic Regime Gate

**File:** `pipeline/src/logic/layer1_gate.py`

Maps the composite score to a discrete regime label using **hysteresis tiers** and override rules.

For non-INR pairs:

| Tier | Regime |
|------|--------|
| 4 | `RISK_OFF_DOLLAR_BID` |
| 3 | `GROWTH_SURPRISE_USD` |
| 2 | `NEUTRAL` |
| 1 | `RISK_ON_DOLLAR_OFF` |
| 0 | `RISK_ON_DOLLAR_OFF` (strong) |

For USD/INR the labels are INR-specific (`INR_DEPRECIATION_STRONG`, `INR_NEUTRAL`, etc.).

Override rules:

- **Structural instability** → `CARRY_COLLAPSE`
- **Inflation shock + rate Z-score** → `USD_POLICY_BREAKOUT`
- **Elevated carry Z + negative momentum** → `CARRY_COLLAPSE`
- **Spot stress Z > 2.5** → `LIQUIDITY_SHOCK`
- **Vol expanding overlay** → appends `__VOL_EXPANDING` to neutral labels

The gate can be **invalidated** if required inputs are stale or missing (e.g., no 2Y rate differential, insufficient spot history).

#### Layer 2: Directional Conviction

**File:** `pipeline/src/logic/layer2_directional.py`

Produces:

- A directional bias: `LONG`, `SHORT`, or `NEUTRAL`.
- A conviction score from 1 to 5.
- Crowding flags and vetoes from COT percentiles.
- Marcus clash rules:
  - **Marcus B:** strong rate view vs opposing positioning → neutralize.
  - **Marcus C:** composite strongly disagrees with rate direction → neutralize.

Direction logic:

1. If invalidated / crowd veto / Marcus clash → `NEUTRAL`.
2. Else if `|composite| > 0.30`, composite drives direction.
3. Else rate sign drives direction.
4. Else `NEUTRAL`.

### 4.7 Validation Engine

**File:** `pipeline/src/validation/engine.py`

The validation engine is the credibility backbone. It:

- Scans `regime_calls` for calls that have reached T+5 or T+20.
- Fetches the spot price on the horizon date.
- Computes **log-return in basis points**: `10,000 * ln(S_h / S_0)`.
- Applies a 5bps dead-band to classify realized direction as `UP`, `DOWN`, or `NEUTRAL`.
- Checks correctness against the published predicted direction.
- Computes **Brier score**: `(confidence - outcome)^2`.
- Stores everything in `validation_log` with cost-adjusted net metrics.

Cost assumptions (round-trip, bps):

| Pair | Cost |
|------|------|
| EUR/USD | 0.2 |
| USD/JPY | 0.3 |
| USD/INR | 10.0 |

The `validation_log` is append-only with superseded versioning: if a validated row is recomputed with materially different inputs, the old row is marked `is_superseded = true` and a new row is appended. Historical rows are never mutated.

### 4.8 Database Writer

**File:** `pipeline/src/db/writer.py`

This is the **only** module allowed to write to the database. It centralizes all persistence:

- `write_signal_row()` — upserts daily signal rows.
- `write_regime_call()` — inserts regime calls with conflict detection.
- `write_validation_row()` — append-only validation ledger with versioning.
- `write_brief()` / `write_brief_log()` — daily narrative briefs.
- `write_desk_open_card()` — per-pair desk cards.
- `write_pipeline_error()` — structured error logging.

It also includes emergency rollback helpers (`delete_pipeline_data_for_date`) that require `force=True` and write to `audit_log` before deletion.

---

## 5. The Frontend

### 5.1 Stack

- **Framework:** Next.js 15.3.9 with App Router.
- **Language:** TypeScript 5 with strict types.
- **Styling:** Tailwind CSS v4, custom design tokens in CSS variables.
- **Database client:** `@supabase/ssr` for server-side rendering.
- **Charts:** Lightweight Charts, custom sparklines, KaTeX for math.
- **Animation:** Framer Motion.
- **Linting:** Biome.

### 5.2 Design System

The UI follows a **Swiss Monochrome institutional terminal** aesthetic:

- Background: deep void (`--color-void`).
- Surfaces: elevated panels (`--color-elevated`, `--color-surface`).
- Accent: single amber `#e8a045` (`--color-brand-amber`).
- Typography: Inter (sans), Cormorant (serif quotes), JetBrains Mono (data).
- Density: standard / compact toggle.

### 5.3 Page Inventory

| Page | Route | Purpose |
|------|-------|---------|
| Home | `/` | Hero, live snapshot cards, validation snapshot, signal architecture, about snippet |
| Terminal | `/desk` / `/terminal` | Main dashboard with pair desks, macro pulse, calendar |
| Pair Desk | `/desk/fx-regime/[pair]` | Per-pair regime detail, signal decomposition, historical calls |
| Performance | `/desk/performance` | Win rates, Brier score, Sharpe-like ratio, regime breakdown |
| Track Record | `/track-record` | Full validation ledger table |
| Methodology | `/methodology` | KaTeX formulas, signal math, data sources, validation rules |
| Audit | `/audit` | Pipeline health dashboard, error log, data lineage |
| Brief | `/brief` / `/memo/[date]` | Daily macro brief and research memos |
| About | `/about` | Author identity, project principles |
| Limitations | `/limitations` | Public honesty page about model weaknesses |

### 5.4 Key Frontend Components

- **`RegimeBadge`** — color-coded regime labels.
- **`ConfidenceMeter`** — visual confidence indicator.
- **`MetricCard`** — institutional-style KPI cards.
- **`SignalDecomposition`** — interactive 8-signal breakdown on methodology page.
- **`PairAccuracyCards`** / **`BrierChart`** / **`RegimeBreakdown`** — performance visualizations.
- **`PipelineHealthDashboard`** — operational health UI.
- **`AuditTrailBannerServer`** — immutability notice.

### 5.5 Data Fetching

**File:** `web/src/lib/supabase/queries.ts`

All server-side data access flows through typed Supabase queries:

- `getLatestRegimeCalls()` — latest call per pair.
- `getLatestSignals()` — latest signal snapshot per pair.
- `getValidationStats()` — aggregated win rate / Brier stats.
- `getValidationLogT5T20()` — full T+5/T+20 validation table.
- `getPipelineHealth()` — daily pipeline health status.
- `getCrossAssetSnapshot()` — VIX, DXY, oil, gold, etc.

The frontend is mostly **SSR** with `revalidate = 3600` on the home page, keeping it fast and cache-friendly.

---

## 6. Database Schema Overview

The Supabase PostgreSQL database has **30 active tables** across 49 migrations.

### 6.1 Core Tables

| Table | Purpose |
|-------|---------|
| `universe` | Pair registry: ticker mappings, yield series, COT tickers |
| `signals` | Daily computed signal metrics per pair |
| `regime_calls` | Immutable daily regime classifications |
| `validation_log` | Append-only T+5/T+20 outcomes and Brier scores |
| `validation_stats` | Pre-aggregated per-pair + aggregate statistics |
| `desk_open_cards` | Per-pair narrative desk cards |
| `brief` / `brief_log` | Daily macro briefs and structured summaries |
| `health_checks` | Daily pipeline health telemetry |
| `pipeline_errors` | Structured error log |
| `audit_log` | Tamper-evident ledger of sensitive operations |
| `macro_events` / `historical_macro_surprises` | Economic calendar and surprise history |
| `research_memos` / `research_analogs` | Research artifacts and historical analogs |

### 6.2 Immutability Guarantees

- `regime_calls` and `validation_log` are append-only by convention and enforced by Postgres triggers.
- `writer.py` checks for existing rows before insert to avoid immutable-trigger UPDATE errors.
- Validation versioning uses `is_superseded` rather than in-place updates.

---

## 7. Key Engineering Decisions

### 7.1 Why Only 3 Pairs?

Hard constraint from `IDENTITY.md`: no expansion until EUR/USD rolling 90-day accuracy ≥ 55%. This prevents overfitting to many instruments before the core model is proven.

### 7.2 Why Prefect Cloud Instead of GitHub Actions?

Hard rule: no GitHub Actions. Prefect Cloud gives:

- Native async flow support.
- Built-in retries, observability, and concurrency.
- Separation of CI/CD from data orchestration.

### 7.3 Why a Two-Layer Logic Engine Instead of ML?

- Interpretability: every regime label has a deterministic explanation.
- Auditability: no black-box model drift.
- Career alignment: demonstrates rule-based quant reasoning before adding ML.

### 7.4 Why Append-Only Ledgers?

- Prevents hindsight editing of calls.
- Enables public verifiability.
- Aligns with the project’s transparency identity.

### 7.5 Why Pair-Specific Weights?

EUR/USD is driven by rate differentials and ECB policy. USD/JPY is sensitive to carry and BoJ communication. USD/INR is sensitive to oil, FPI flows, and RBI intervention. A universal weighting scheme would underfit all three.

---

## 8. What Is Built Well

### 8.1 Production Engineering

- **319 Python tests** collected via pytest, plus TypeScript type-checking and Biome linting.
- **Strict typing:** mypy strict mode on the pipeline; TypeScript strict on the frontend.
- **Immutable ledgers** with audit trails.
- **Centralized DB writer** — all writes go through one module.
- **Adapter ports** in the staged pipeline for testability and infrastructure swaps.
- **Schema migration discipline:** 49 Supabase migrations applied.

### 8.2 Statistical Rigor

- Causal percentile computation (current obs excluded).
- Dual-horizon robust Z-scores.
- Dynamic Spearman betas.
- Hysteresis in regime classification to prevent label whipsaw.
- Brier score calibration metric alongside win rate.
- Cost-adjusted net returns and net accuracy.

### 8.3 Transparency & Governance

- Public limitations page disclosing near-random accuracy.
- Methodology page with full formulas and data sources.
- Audit trail UI showing pipeline health.
- Identity compliance audit completed (removed alert subscriptions, public stop levels, etc.).
- Masterplan tied to career gates (MFE application, boutique internship, quant fund).

### 8.4 Frontend Quality

- Responsive, accessible (skip-link, focus states).
- OG images for social sharing on terminal, performance, and memo pages.
- Schema.org Dataset JSON-LD for SEO.
- Sitemap and robots.txt.
- Performance metrics via Vercel Analytics and Speed Insights.

### 8.5 Operational Maturity

- Daily Prefect Cloud runs.
- Pipeline health dashboard.
- Slack accuracy alerts at 50% and 55% gates.
- Daily brief generation and research memo pipeline.

---

## 9. Current Limitations & Gaps

The project is deliberately honest about its weaknesses.

### 9.1 Model Performance

- **Accuracy is near random:** ~49% T+5 gross, ~47% net for EUR/USD; USD/JPY ~48%; USD/INR ~41%.
- Confidence is not yet calibrated against real OOS accuracy.
- Risk reversal signal uses a synthetic proxy; real OTC data not yet integrated.

### 9.2 Feature Gaps

- **No feature interactions** in the composite (e.g., `rate × cot`, `vol × oi`).
- **No regime-conditional weight adjustment** (weights are static regardless of vol regime).
- **No cohort analysis** on the performance page (accuracy by regime type, vol regime, confidence bucket).
- **No automated PDF research artifacts**; weekly regime read is still partly manual.

### 9.3 Data Gaps

- BoJ policy rate is a proxy via FRED rather than direct market data.
- RBI intervention is inferred synthetically, not from official intervention data.
- Real OTC risk reversal data is pending.

### 9.4 Architectural Gaps

- Pipeline is not yet fully pair-specific; special signals are injected through a shared `special_signal` slot.
- No async parallel fetching across pairs at the fetcher level.
- Backfill is limited to calibration; long historical backtests are intentionally avoided.

### 9.5 Why These Gaps Are Acceptable Now

The masterplan explicitly prioritizes **signal depth (Stream A)** and **credibility** over complexity. Architecture rebuild (Stream D) is locked until Phase C is met (>200 validated calls, EUR/USD > 55% rolling 90-day). This prevents over-engineering before the model is proven.

---

## 10. Roadmap & Career Alignment

### 10.1 Phases

| Phase | Gate | Status |
|-------|------|--------|
| **A — Signal Quality Fix** | EUR/USD OOS logged; 14 error-free pipeline days | ✅ Met |
| **B — Product Completeness** | 90+ days OOS; methodology public; EUR/USD > 50% | 🔄 In Progress |
| **C — Regime Divergence Alert** | EUR/USD > 55%; SSRN paper drafted | 🔒 Locked |
| **D — Full MFE Package** | 6 months OOS; GBP/USD planned; SSRN submitted | 🔒 Locked |

### 10.2 Work Streams

- **Stream A: Signal Depth** — Add pair-specific macro data (6 signals already deployed).
- **Stream B: Model Sophistication** — Feature interactions, regime-conditional weights, Platt calibration, cohort analysis.
- **Stream D: Architecture Evolution** — Pair-specific pipeline classes, async fetching, GBP/USD planning.

### 10.3 Career Deliverables

| Target | Timeline | What the Project Must Show |
|--------|----------|---------------------------|
| NTU MFE Application | Dec 2027 – Jan 2028 | 200+ validated calls, SSRN paper, documented methodology, production engineering |
| Boutique Internship | Summer 2028 | Divergence alert system, 6+ months OOS, GBP/USD architecture |
| Quantamental Macro Fund | Post-graduation 2028+ | Pair-specific pipelines, 500+ calls, feature interactions, institutional credibility |

---

## 11. Notable Files & Entry Points

### Pipeline

| File | Purpose |
|------|---------|
| `pipeline/src/staged/orchestrator.py` | Prefect flow orchestration |
| `pipeline/src/signals/rate.py` | Rate differential Z-scores |
| `pipeline/src/signals/cot.py` | COT positioning percentiles |
| `pipeline/src/signals/special.py` | Pair-specific cross-asset signals |
| `pipeline/src/regime/composite.py` | Weighted composite + dynamic betas |
| `pipeline/src/regime/confidence.py` | Confidence calibration |
| `pipeline/src/logic/layer1_gate.py` | Regime classification |
| `pipeline/src/logic/layer2_directional.py` | Directional bias + conviction |
| `pipeline/src/validation/engine.py` | T+5/T+20 validation |
| `pipeline/src/db/writer.py` | All database writes |

### Frontend

| File | Purpose |
|------|---------|
| `web/src/app/page.tsx` | Landing page |
| `web/src/app/desk/page.tsx` | Terminal dashboard |
| `web/src/app/desk/fx-regime/[pair]/page.tsx` | Pair desk |
| `web/src/app/desk/performance/page.tsx` | Performance analytics |
| `web/src/app/methodology/page.tsx` | Methodology docs |
| `web/src/lib/supabase/queries.ts` | Typed data access |
| `web/src/components/ui/` | Design system components |

### Docs & Governance

| File | Purpose |
|------|---------|
| `IDENTITY.md` | Hard constraints and identity test |
| `MASTERPLAN.md` | Product direction and career alignment |
| `TASK.md` | Current sprint state |
| `CLAUDE.md` | AI persona and session rules |
| `docs/SIGNAL_DEFINITIONS.md` | Exact math and thresholds |
| `docs/DB_STATUS.md` | Live schema reference |

---

## 12. Quantifiable Project Metrics

| Metric | Value |
|--------|-------|
| Currency pairs | 3 (EUR/USD, USD/JPY, USD/INR) |
| Signal families | 5 (Rate, COT, Vol, OI/RR, Special) + FPI for INR |
| Python tests | 319 |
| Frontend pages | 17+ |
| Database tables | 30 active |
| Database migrations | 49 applied |
| Validation horizons | T+5 and T+20 |
| Current model version | v2.1 Experimental |
| T+5 gross accuracy (EUR/USD) | ~49.2% |
| T+5 gross accuracy (USD/JPY) | ~48.3% |
| T+5 gross accuracy (USD/INR) | ~41.4% |
| Production calls since May 2026 | ~100 |
| CI/CD | Prefect Cloud + Vercel |
| Linting | ruff, mypy, Biome |

---

## 13. Personal Contribution Narrative

This project was built end-to-end as a solo research engineering effort. As the author, I:

- Designed the full system architecture from data ingestion to public frontend.
- Implemented the deterministic regime engine with hysteresis, dynamic betas, and pair-specific weighting.
- Built the immutable validation ledger and cost-adjusted performance metrics.
- Wrote the entire Next.js frontend with a custom design system, SSR, and public methodology documentation.
- Established governance documents (`IDENTITY.md`, `MASTERPLAN.md`) that constrain scope and prevent scope creep.
- Deployed and operate the system on Prefect Cloud + Vercel with daily automated runs.
- Maintained 319 passing Python tests and a clean TypeScript/Biome frontend.
- Made the operation radically transparent by publishing limitations and near-random accuracy openly.

The project demonstrates **production-grade data engineering**, **statistical discipline**, **frontend craftsmanship**, and **research integrity** — the combination expected by MFE admissions committees and macro/quantitative investment teams.

---

## 14. Conclusion

FX Regime Lab is not a finished predictive product. It is a **living research infrastructure** designed to become more accurate and more credible over time. Its current value lies not in market-beating signals, but in the rigor of its process: signals are computed systematically, calls are logged before resolution, outcomes are validated honestly, and limitations are published openly.

The architecture is built to evolve: adapter ports allow infrastructure changes, the composite is designed to accept feature interactions and conditional weights, and the frontend is ready for richer analytics. The next milestones — calibration, cohort analysis, and pair-specific pipeline classes — are already specified in the masterplan and gated by observable accuracy thresholds.
