# FX Regime Lab — Ultimate Masterplan

> **Read `IDENTITY.md` first.** It is the hard constraint. Nothing in this plan may violate it.  
> This document is the single source of truth for product direction.  
> All other roadmap, plan, and spec documents are deprecated.  
> Last updated: 2026-05-18

---

## 0. Identity Compliance

Every task below must pass the **One-Sentence Identity Test** from `IDENTITY.md`:

> *Does this make the regime calls more accurate, more transparent, or more publicly verifiable?*

If no, it is not in this plan.

Hard constraints from `IDENTITY.md` that govern this plan:
- **Not a signal service.** No API for external signal consumption. No alert subscriptions. No white-label embeds. No RSS feed of raw regime calls.
- **Not a backtesting showcase.** No 5-year backfill for display purposes. Backfill only for calibration and methodology validation.
- **Not execution advice.** No stop-loss levels, position sizing, or trade recommendations in public output.
- **Not a fintech product.** No monetization layer. No user acquisition features.
- **3-pair lock.** EUR/USD, USD/JPY, USD/INR only. No expansion until EUR/USD ≥ 55% on 90-day rolling window.
- **Pair-specific architecture.** EUR/USD logic does not apply to USD/JPY or USD/INR.

### Step 0 — Identity Compliance Audit (COMPLETED 2026-05-18)

Annual/phase-gate review: audit all public text, UI, APIs, and database schema against `IDENTITY.md`.

| Violation | Action | Status |
|-----------|--------|--------|
| `connect-desk` API + `webhook_subscriptions` table | Alert subscription infrastructure. **Removed API route, dropped DB table, removed from types.** | ✅ Done |
| `position_size` displayed on pair desk, SignalCard, data lineage | Execution advice in public output. **Removed from all UI components.** Kept in DB for internal research. | ✅ Done |
| `stop_level` displayed on pair desk, SignalCard, data lineage | Execution advice in public output. **Removed from all UI components.** Kept in DB for internal research. | ✅ Done |
| "educational purposes" in research disclaimer | Educational tone. **Changed to "research purposes only."** | ✅ Done |
| "RESEARCH AND LEARNING ONLY" in brief page | Educational tone. **Changed to "RESEARCH ONLY."** | ✅ Done |
| "publicly accessible daily signals" in about page | Signal-service framing. **Changed to "daily regime classifications."** | ✅ Done |
| "[REGIME ALERT]" in LinkedIn hook prompt | Alert-like framing. **Changed to "[REGIME NOTE]."** | ✅ Done |
| "COPY LINKEDIN ALPHA" button label | Signal-like language. **Changed to "SHARE REGIME NOTE."** | ✅ Done |

**Permanent rule:** `position_size` and `stop_level` are internal research parameters only. They must never be rendered on any public page. Any future feature that displays trade parameters (stops, sizes, entry prices) is automatically rejected.

---

## 1. Current State (As-Of)

### What Exists & Works

| Layer | Status | Details |
|-------|--------|---------|
| **Data Pipeline** | ✅ Live | Prefect Cloud daily run. 5 signal families (RATE, COT, VOL, OI, SPECIAL + FPI for USDINR). 3-pair lock (EURUSD, USDJPY, USDINR). |
| **Validation Engine** | ✅ Live | T+5/T+20 directional validation, 5bps Marcus dead-band, Brier scores, immutable ledger with timestamps. |
| **Validation Stats** | ✅ Live | Per-pair + aggregate win rates, Sharpe-like ratios, max drawdown, calibration buckets. |
| **Frontend** | ✅ Live | Next.js 15, 17+ pages, SSR Supabase, Swiss Monochrome design system (Inter / Fraunces / JetBrains Mono, amber #e8a045), responsive, OG images. Identity-audited and clean. |
| **Methodology Page** | ✅ Live | KaTeX formulas, 3-layer framework docs, per-pair methodology, validation math, data sources. Plain-language practitioner tone. No educational language. |
| **Terminal** | ✅ Live | Live regime dashboard, pair desks, mosaic grid, correlation matrix, macro calendar. No execution advice displayed. |
| **Audit Trail** | ✅ Live | Pipeline health dashboard, accuracy alerts (internal ops only), immutable ledger UI. |
| **Tests** | ✅ 228 pass | pytest full suite. TypeScript zero errors. Biome clean. |
| **Deployment** | ✅ Auto | Vercel (frontend) + Prefect Cloud (pipeline). Git push → auto-deploy. |

### What's Thin / Missing

| Gap | Impact | Priority |
|-----|--------|----------|
| ~~No pair-specific macro fetchers~~ | ✅ COMPLETE — 6 signals deployed (ECB BS, Bund-BTP, BoJ rate, intervention proximity, India VIX, INR forward premium) | — |
| No feature interactions in composite | RATE×COT, VOL×OI terms missing — easy alpha left on table | High |
| No automated research artifacts | Weekly regime read is manual; no institutional PDF output | High |
| No public research distribution | Substack, LinkedIn presence exists but not automated | Medium |
| No regime-conditional weight adjustment | Weights are static regardless of vol regime | Medium |
| No cohort analysis on Performance page | Cannot see accuracy by regime type, vol regime, confidence bucket | Medium |
| No confidence calibration | Raw confidence may be poorly calibrated; no Platt scaling | Low |

---

## 2. Strategic Framework

### The Dual Mandate

Every task is evaluated against two axes:

1. **External Credibility:** Does this make the research operation look more rigorous to a macro PM or MFE admissions committee?
2. **Internal Alpha:** Does this improve signal quality, validation accuracy, or the information ratio of the regime classifier?

**Priority rule:** External Credibility wins when sample size is small (< 200 validated calls). Internal Alpha wins when sample size is large (> 500 calls) and track record is established.

**Current mode:** Credibility-building. ~100 production calls since April 2026.

### Career Trajectory Alignment

| Target | Timeline | What Masterplan Must Deliver |
|--------|----------|------------------------------|
| **NTU MFE Application** | Dec 2027 – Jan 2028 | Public track record with 200+ validated calls, SSRN paper submitted, methodology fully documented, production-grade engineering demonstrated |
| **Boutique Internship** | Summer 2028 | Regime divergence alert system live, GBP/USD expansion architecturally planned, 6+ months continuous OOS history, published research presence |
| **Quantamental Macro Fund** | Post-graduation 2028+ | Pair-specific pipeline architecture (Stream D), 500+ validated calls, feature interactions + conditional weights deployed and backtested, institutional credibility established |

**Consequence:** Every stream is timed to produce a deliverable for the next career gate. No stream exists for its own sake.

### IDENTITY Phase Gates

This plan is organized into work-streams, but no work-stream advances past an IDENTITY phase gate until the gate conditions are met.

| IDENTITY Phase | Gate Condition | Status | Career Gate |
|----------------|----------------|--------|-------------|
| **Phase A** — Signal Quality Fix | EUR/USD accuracy measured OOS + logged; brief text is clean; 14 consecutive error-free pipeline days | ✅ Met | — |
| **Phase B** — Product Completeness | 90+ days live OOS for all 3 pairs; regime history strip live; methodology public; EUR/USD accuracy > 50% | 🔄 In Progress | MFE portfolio |
| **Phase C** — Regime Divergence Alert | EUR/USD rolling 90-day accuracy > 55%; SSRN paper drafted; divergence alert architecturally designed | 🔒 Locked | MFE submission |
| **Phase D** — Full MFE Package | 6 months live OOS all pairs; performance page live; GBP/USD architecturally planned; SSRN paper submitted | 🔒 Locked | MFE application |

---

## 3. Pair-Specific Signal Architecture

This is the canonical signal architecture. Any new signal must map to the correct slot for its pair.

### EUR/USD
| Slot | Input | Status |
|------|-------|--------|
| Primary | US-EU 2Y rate differential (FRED) | ✅ Live |
| Secondary | COT Non-Commercial + Asset Manager positioning | ✅ Live |
| Vol layer | EUR implied vol (^EVZ) regime | ✅ Live |
| Confirmation | DXY direction | ✅ Live |
| **Missing** | ECB balance sheet (ECBASSETSW) | ✅ Stream A.1 |
| **Missing** | Bund-BTP spread (fragmentation proxy) | ✅ Stream A.2 |

### USD/JPY
| Slot | Input | Status |
|------|-------|--------|
| Primary | US-JP rate spread (FRED) | ✅ Live |
| Secondary | BoJ policy rate + communication | ✅ Proxy only |
| Positioning | Leveraged money COT | ✅ Live |
| Confirmation | S&P 500 / Brent crude | ✅ Partial |
| **Missing** | BoJ policy rate (IRSTCI01JPM156N) | ✅ Stream A.3 |
| **Missing** | Intervention proximity flag (spot near 160) | ✅ Stream A.4 |

### USD/INR
| Slot | Input | Status |
|------|-------|--------|
| Primary | RBI intervention probability (synthetic) | ✅ Proxy only |
| Secondary | India-US rate differential | ✅ Live |
| Flow | FPI equity + debt flow (SEBI) | ✅ Live |
| Commodity | Brent crude | ✅ Live |
| **Missing** | India VIX (INDIAVIX) | ✅ Stream A.5 |
| **Missing** | INR 1M forward premium | ✅ Stream A.6 |

---

## 4. The Work-Stream Plan

### Stream A: Signal Depth
**Goal:** Add pair-specific macro data to reduce underfitting. No architecture rebuild.  
**IDENTITY Gate:** May start now (Phase A met). May not expand to new model layers until Phase B met.  
**Career Gate:** MFE portfolio (demonstrates macro depth + data engineering)

| Task | Tier | Identity Test | Description | Gate |
|------|------|---------------|-------------|------|
| A.1 | 2 | ✅ Accuracy | **EURUSD: ECB balance sheet** — Fetch `ECBASSETSW` from FRED. Normalize as z-score vs 2-year history. Add to `special_factor`. | Phase A |
| A.2 | 2 | ✅ Accuracy | **EURUSD: Bund-BTP spread** — Compute 10Y Bund - 10Y BTP. Store in `signals` table as fragmentation proxy. | Phase A |
| A.3 | 2 | ✅ Accuracy | **USDJPY: BoJ policy rate** — Fetch `IRSTCI01JPM156N` from FRED (OECD proxy, current). Compute rate differential vs US. | Phase A |
| A.4 | 2 | ✅ Accuracy | **USDJPY: Intervention proximity** — Synthetic flag: when spot approaches 160, raise special factor weight. Document as heuristic, not prediction. | Phase A |
| A.5 | 2 | ✅ Accuracy | **USDINR: India VIX** — Fetch `INDIAVIX` from NSE. Add as stress indicator. | Phase A |
| A.6 | 2 | ✅ Accuracy | **USDINR: Forward premium** — RBI reference rate → 1M forward premium. Add to rate differential context. | Phase A |

**Architecture constraint:** All new signals feed into the EXISTING composite via the `special_signal` slot or new columns. No pair-specific pipeline classes yet.

---

### Stream B: Model Sophistication
**Goal:** Make the composite smarter without changing pipeline architecture.  
**IDENTITY Gate:** Phase B must be met before any Tier 3 task begins.  
**Career Gate:** HF recruiting (demonstrates quant rigor)

| Task | Tier | Identity Test | Description | Gate |
|------|------|---------------|-------------|------|
| B.1 | 2 | ✅ Accuracy | **Feature interactions** — Add interaction terms: `rate × cot` (policy + positioning alignment), `vol × oi` (vol + flow confirmation). Weight ~0.10 each. Backtested vs baseline. | Phase B |
| B.2 | 3 | ✅ Accuracy | **Regime-conditional weights** — Adjust composite weights based on vol regime: High Vol → reduce rate/cot weight, increase vol weight. Trending → increase rate weight. | Phase B |
| B.3 | 2 | ✅ Transparency | **Confidence recalibration** — Map raw confidence to calibrated probability using Platt scaling on historical validation data. Publish calibration curve. | Phase B |
| B.4 | 2 | ✅ Transparency | **Cohort analysis** — Break down accuracy by: regime type, vol regime, confidence bucket. Display on /performance. | Phase B |

**Tier 3 note:** Regime-conditional weights touch core composite logic. Requires explicit approval before merge.

---

### Stream D: Architecture Evolution
**Goal:** Rebuild for scale. Only after Streams A–C are complete and track record > 200 calls.  
**IDENTITY Gate:** Phase C met AND >200 validated calls.  
**Career Gate:** Boutique internship + HF recruiting (demonstrates systems engineering at institutional scale)

| Task | Tier | Identity Test | Description | Gate |
|------|------|---------------|-------------|------|
| D.1 | 3 | ✅ Accuracy | **Pair-specific pipeline classes** — `pipeline/src/pairs/eurusd/`, `usdjpy/`, `usdinr/` with dedicated fetchers, signals, thresholds. Base class in `pairs/base.py`. | Phase C |
| D.2 | 3 | ✅ Accuracy | **Async parallel fetching** — All pair fetchers run concurrently via `asyncio.gather`. | Phase C |
| D.3 | 2 | ✅ Transparency | **Backfill for calibration only** — Run validation on historical data sufficient for Platt scaling and weight optimization. Not for display. Not a backtesting showcase. | Phase C |
| D.4 | 2 | ✅ Verifiable | **SSRN paper finalization** — Submit methodology paper. | Phase D |
| D.5 | 2 | ✅ Accuracy | **GBP/USD architectural planning** — Document signal logic, data sources, and regime framework before any code is written. | Phase D |

---

## 5. Risk & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| EUR/USD accuracy stalls below 55% | Medium | High — blocks Phase C, D, and pair expansion | Stream A (pair-specific signals) is prioritized to address underfitting. If still below 55% at 200 calls, review signal architecture rather than add complexity. |
| Pipeline data degradation | Low | High — corrupts validation ledger | Immutable ledger + daily health checks + manual review before any backfill. No retroactive edits to validation_log. |
| Research output becomes marketing | Medium | Medium — violates IDENTITY | Every research artifact passes the One-Sentence Identity Test before publish. No trade recommendations. No "buy/sell" language. |
| Over-engineering before track record | High | Medium — wasted effort, missed deadlines | Stream A (signal depth) prioritized over B+D (complexity). No architecture rebuild until >200 calls. |

---

## 6. Safety Tiers (Autonomy Rules)

| Tier | Description | Examples | Autonomy |
|------|-------------|----------|----------|
| **Tier 1** | UI/content only. No data layer. No pipeline. | Methodology copy, chart components, CSS, research artifact formatting | **Full auto** |
| **Tier 2** | New signals, fetchers, queries. No threshold changes. No immutable table edits. | FRED fetcher, cohort analysis query, confidence recalibration | **Auto + Approval Gate** |
| **Tier 3** | Core logic changes. Composite weights, regime thresholds, validation formulas. | Regime-conditional weights, feature interactions, Platt scaling | **Human Required** |
| **Tier 4** | Immutable ledger. Historical changes. | Backfill execution, validation_log edits | **Human Required + Audit Trail** |

**Pre-merge check for ANY Tier 2+ task:**
```bash
cd pipeline && pytest          # must pass
cd web && npx tsc --noEmit     # must pass
cd web && npx biome check .    # must pass
```

---

## 7. Career Alignment Checklist

Every task must answer "yes" to at least one:

- [ ] **MFE Admissions:** Does this demonstrate statistical rigor, financial modeling, or data engineering at graduate level?
- [ ] **HF Recruiting:** Does this produce an output a macro PM would find useful or impressive?
- [ ] **Research Credibility:** Does this make the track record more trustworthy or transparent?
- [ ] **Technical Depth:** Does this demonstrate production-grade engineering (tests, types, CI/CD)?

**Current focus (Streams A + C):** MFE Admissions + Research Credibility.  
**Future focus (Streams B + D):** HF Recruiting + Technical Depth.

---

## 8. Metrics & Gates

### Stream A Gate
- [x] ≥ 3 new pair-specific signals deployed and populating daily (6 signals: ECB BS, Bund-BTP, BoJ rate, intervention proximity, India VIX, INR forward premium)
- [ ] Each new signal documented on /methodology with formula + data source
- [ ] No regression in validation accuracy (Brier score stable or improving)

### Stream B Gate
- [ ] Feature interactions backtested: win rate delta vs baseline documented
- [ ] Regime-conditional weights deployed for 2+ weeks without crash
- [ ] Cohort analysis tables live on /performance
- [ ] Confidence calibration curve published

### Stream D Gate
- [ ] Pair-specific pipeline classes run independently
- [ ] Production validated calls > 200
- [ ] Backfill calibration data generated (not displayed)
- [ ] GBP/USD architecture document complete

---

## 9. What This Plan Delivers

At the end of this masterplan (all streams complete), FX Regime Lab will be:

1. **A verified public track record** — 200+ out-of-sample validated regime calls with Brier scores, calibration curves, and cohort analysis
3. **A pair-specific signal engine** — Each pair has dedicated macro data (ECB, BoJ, RBI), feature interactions, and regime-conditional weights
4. **A documented methodology** — SSRN paper submitted, KaTeX formulas public, full transparency on signal logic
5. **A scalable architecture** — Pair-specific pipeline classes, async fetching, ready for GBP/USD expansion
6. **A career asset** — The entire operation demonstrates statistical rigor, macro understanding, and production engineering at the level expected by NTU MFE admissions and macro PMs

---

## 10. Deprecated Documents

The following are **DEPRECATED** and no longer govern project direction. Retained in git history only:

- `ROADMAP.md` (Rounds 1–5) — Historical; all complete
- `MASTER_PHASE_ROADMAP.md` (Phases 1–4) — Historical; mostly complete
- `PLAN_v2_0.md` — Completed feature release (FPI + RR)
- `OMEGA_EXECUTION_PLAN.md` — Superseded; pair-specific architecture deferred to Stream D
- `PLAN_EXECUTION_10_10.md` — Superseded autonomy plan
- `docs/CRITIQUE_AND_PLAN.md` — Old frontend audit; resolved in UI/UX overhaul
- `docs/specs/15_10_FULL_AUTONOMY_PLAN.md` — Agent infrastructure; non-product
- `docs/specs/ROUND2_PHASE*.md` — Completed engineering specs
- `docs/specs/ROUND3_VALIDATION_ENGINE.md` — Completed spec
- `OMEGA_COMPLETION_REPORT.md` — Historical completion report
- `OMEGA_UI_SWARM_PROMPT.md` — One-off prompt artifact
- `web/_design/MASTER_IMPLEMENTATION_PLAN.md` — Completed UI plan
- `web/_design/round*.md` — Completed design round artifacts

**Active documents (read in this order):**
1. `IDENTITY.md` — Hard constraints
2. `MASTERPLAN.md` — Product direction (this file)
3. `TASK.md` — Current sprint state
4. `OMEGA_PROTOCOL.md` — Council workflow process (not roadmap)
