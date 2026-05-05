# FX Regime Lab — Feature Audit Report
## Round 8 | Product Manager Audit against Master Spec
**Date:** 2026-05-05
**Auditor:** Product Manager (subagent)
**Scope:** P0/P1 features, spec fidelity, user flows, content, data integrity

---

## 1. P0 Features — Status Checklist

### 1. Performance Page Overhaul

| Feature | Status | Notes |
|---------|--------|-------|
| Equity curve (320px, regime bands, drawdown shading) | ✅ Implemented | SVG-based custom render. Drawdown shading present. Missing regime band overlay. Missing 7D/30D/90D/ALL time range selector. |
| Fix cumulative return math | ✅ Implemented | Now uses actual `sum(return_pct)` per day, not `avg * count`. Correct. |
| Hit rate by horizon (T+1 / T+5 / T+20) | ⚠️ Partially implemented | T+1 renders from validation data. T+5 and T+20 are hardcoded placeholders (`hits: 0, trials: 0`). Bars show "—". |
| Regime-specific breakdown table | ✅ Implemented | Full table with calls, hit%, avg ret, max DD, streak. Color-coding correct. |
| Brier score trend (30-day rolling, baseline 0.25) | ❌ Not implemented | No Brier score chart anywhere on `/performance`. |
| Streak indicator | ⚠️ Partially implemented | Streak shown inside regime table rows only. No standalone "CURRENT STREAK" panel with visual bars. |
| Monthly performance table | ✅ Implemented | Full table with running cumulative. Color-coded. Correct sort (newest first). |
| Timestamp + stale indicator | ✅ Implemented | `UPDATED YYYY-MM-DD` shown. `STALE` badge appears if >24h old. Metrics strip dims to `opacity-50` when stale. |

### 2. Homepage — Live Data

| Feature | Status | Notes |
|---------|--------|-------|
| Replace hardcoded stats with real Supabase queries | ✅ Implemented | `getLatestRegimeCalls`, `getLatestSignals`, `getValidationLog` all fetched server-side. |
| Live snapshot cards | ✅ Implemented | 3 cards with spot, regime, confidence bar. Uses real data. |
| Validation trust section | ⚠️ Partially implemented | Uses **all-time** accuracy, not 7D as spec implies for the strip. No "Next validation" countdown. No timestamp on cards. |

### 3. Terminal Pair Desk Enhancement

| Feature | Status | Notes |
|---------|--------|-------|
| Trader's TL;DR box | ✅ Implemented | Bias, driver, invalidation level, watchlist — all present in single strip. |
| Signal architecture visualization | ⚠️ Partially implemented | Simple 4-family stacked bar (6px height) + legend. Missing per-row breakdown with weights, raw values, z-scores, hover tooltips as spec'd in §3.3. |
| TradingView chart embed with regime-change markers | ❌ Not implemented | No chart component exists. `TradingViewChart.tsx` not found in codebase. |
| 30-day historical regime timeline | ⚠️ Partially implemented | 30-day dot heatmap exists. 7-day list view exists. Missing validation outcome indicators (correct/incorrect/pending squares). Missing return % per day. Not scrollable to 30 rows. |
| Invalidation level display | ✅ Implemented | Computed as ±50bps from spot. Displayed in TL;DR strip. |

### 4. Nav Restructure

| Feature | Status | Notes |
|---------|--------|-------|
| Reorder: PERFORMANCE → TERMINAL → METHODOLOGY → BRIEF → ABOUT | ❌ Not implemented | Current order in `Nav.tsx`: Performance, Methodology, Brief, About, **Terminal (dropdown)**. Terminal is visually last, not 2nd. |
| Terminal dropdown: Overview, Pair Desks, Calendar, Memos, Alpha Ledger | ⚠️ Partially implemented | Dropdown exists with correct items. Missing "FX-Regime Mosaic" link. EUR/USD, USD/JPY, USD/INR listed directly instead of nested under "Pair Desks". |
| Active state (Terminal parent highlighted for `/terminal/*`) | ✅ Implemented | `isActive("/terminal")` works. |

### 5. Substack Integration

| Feature | Status | Notes |
|---------|--------|-------|
| Footer email capture (inline, no modal) | ✅ Implemented | Form present. **Not wired** — `handleSubscribe` is `// TODO: wire to newsletter API`. |
| `/terminal/memos` archive page | ✅ Implemented | `MemoSidebar` component renders memo list + Substack embed iframe. Reader overlay works. |
| Bidirectional links between site and Substack | ❌ Not implemented | No "Discuss on Substack" CTA on `/brief`. No "Read on Substack" links in memo list. No Substack URL stored/linked per memo. |

### 6. Motion System

| Feature | Status | Notes |
|---------|--------|-------|
| `useReducedMotion` hook | ✅ Implemented | Hook reads `prefers-reduced-motion: reduce`. |
| `prefers-reduced-motion` CSS override | ⚠️ Partially implemented | `useScrollReveal` respects reduced motion (skips observer, adds `.revealed` immediately). No global CSS override for `animation` / `transition`. |
| Institutional timing tokens | ⚠️ Partially implemented | `cubic-bezier(0.16, 1, 0.3, 1)` used in some places. No systematic 300ms default / 80ms micro / 600ms emphasis enforcement. |

---

## 2. P1 Features — Status Checklist

### 7. Content Enhancements

| Feature | Status | Notes |
|---------|--------|-------|
| Expert / Student mode toggle on methodology | ❌ Not implemented | No toggle. No student-mode plain English expanders. |
| Auto-linking (pairs → desk, regimes → methodology) | ❌ Not implemented | No auto-linking in `/brief` prose. |
| OG image generation for brief/performance/pair pages | ⚠️ Partially implemented | `/api/linkedin-alpha-hook` generates social text. No OG image PNG generation. No `<meta property="og:image">` injection in pages. |

### 8. Terminal Index

| Feature | Status | Notes |
|---------|--------|-------|
| Live indicators strip (sync age, COT age, VIX, DXY) | ❌ Not implemented | No strip. No VIX/DXY display. No COT age. |
| Strategy cards with performance preview | ⚠️ Partially implemented | FX-REGIME card active with pair summaries. Missing 7D/30D/T+5 hit rates and mini sparkline. |
| Quick actions row | ❌ Not implemented | No "View Mosaic / View Ledger / Today's Brief" buttons. No `⌘K` hint. |

### 9. Validation Log Enhancements

| Feature | Status | Notes |
|---------|--------|-------|
| Pair color filter chips | ❌ Not implemented | No filters above validation table. |
| Brief deep-links per row | ❌ Not implemented | No "VIEW" link → `/brief?date=YYYY-MM-DD` per row. |
| Pagination (never infinite scroll) | ❌ Not implemented | Table renders all rows. No pagination. |

---

## 3. Spec Deviations

| Deviation | Location | Spec Requirement | Actual Implementation | Impact |
|-----------|----------|------------------|----------------------|--------|
| **Nav item order** | `Nav.tsx` | PERFORMANCE → **TERMINAL** → METHODOLOGY → BRIEF → ABOUT | Terminal rendered **after** About in DOM (dropdown at end). | Marcus can't find Terminal in expected position. Breaks muscle memory. |
| **Equity curve library** | `performance/page.tsx` | Lightweight Charts by TradingView | Custom SVG renderer. | No crosshair, no time range buttons, no interactive tooltip. Functional but not spec. |
| **Pair desk regime history depth** | `[pair]/page.tsx` | 30 days, scrollable, with validation outcomes | 7 days in list view. 30 days only as dot heatmap (no outcomes). | Diego can't trace 30-day history with outcomes. |
| **Confidence sparkline height** | `[pair]/page.tsx` | 70px | 50px (`height={50}`). | Minor visual deviation. |
| **Validation table typing** | `performance/page.tsx` + `ValidationTable.tsx` | Table uses `ValidationTableRow` from `validation-format.ts` | `performance/page.tsx` passes `ValidationRow[]` from `queries.ts`. Structurally identical but type import mismatch. | Potential build warning or brittle coupling. |
| **About page stats** | `about/page.tsx` | Live data from validation log | Hardcoded: "77.8%", "27", "3". | Priya sees stale/unverifiable numbers. Undermines trust. |
| **Brief page TL;DR** | `brief/page.tsx` | Trader's TL;DR box at top with regime, confidence, driver, invalidation | **Missing entirely.** | Marcus must read prose to find the call. Fails the 10-second trader test. |
| **Methodology toggle** | `methodology/page.tsx` | Expert / Student mode toggle | Missing. | Diego has no plain English path. |
| **Hit rate T+5 / T+20** | `performance/page.tsx` | Real data from `strategy_ledger` | Placeholder zeros. | Misleading — looks like no data rather than "not enough history." |
| **Brier score** | `performance/page.tsx` | 30-day rolling Brier trend chart | Missing. | Missing key calibration signal for allocators. |
| **Footer email wiring** | `Footer.tsx` | Substack email capture functional | `// TODO` — no API call. | Form appears to work but does nothing. |
| **Substack bidirectional links** | `brief/page.tsx`, `terminal/memos/page.tsx` | "Discuss on Substack" / "Read on Substack" CTAs | Missing. | Content loop is broken. |

---

## 4. User Flow Verification

### Priya (Allocator) — "Can she verify track record in <90s?"

**Path:** Homepage → Performance

| Step | Result | Time |
|------|--------|------|
| Homepage shows live snapshot + validation strip | ✅ | 5s |
| Click "View full ledger →" | ✅ | 2s |
| Equity curve visible immediately | ✅ | 3s |
| Metrics strip (7D ACC, CUM RET, CALLS, AVG RET) | ✅ | 5s |
| Regime breakdown table (where edge lives) | ✅ | 15s |
| Monthly breakdown (running cumulative) | ✅ | 15s |
| **Missing:** Brier score (calibration check) | ❌ | — |
| **Missing:** Sharpe-like / Sortino / Max DD panel | ❌ | — |
| **Missing:** Per-pair sparklines | ❌ | — |

**Verdict:** ⚠️ **Partial pass.** Core credibility signals present. Missing Brier, risk ratios, and per-pair accuracy sparklines that allocators use to stress-test. ~60s to surface the story, but gaps remain for deep vetting.

---

### Marcus (Trader) — "Can he check today's call immediately?"

**Path:** Homepage → Terminal → Pair Desk

| Step | Result | Time |
|------|--------|------|
| Homepage live snapshot cards visible | ✅ | 5s |
| Click "Open terminal →" | ✅ | 2s |
| Terminal shows 3 pair cards with regime + confidence | ✅ | 3s |
| Click pair card → desk | ✅ | 2s |
| Top strip: spot, regime, confidence, composite | ✅ | 3s |
| Trader's TL;DR (bias, driver, invalidation, watchlist) | ✅ | 5s |
| Signal chips (RATE, COT, VOL, IV) | ✅ | 5s |
| **Missing:** TradingView chart with regime bands | ❌ | — |
| **Missing:** Quick actions (Today's Brief, View Ledger) | ❌ | — |
| **Missing:** Live indicators strip (VIX, DXY, sync age) | ❌ | — |

**Verdict:** ⚠️ **Partial pass.** Marcus gets the call and context in ~25s. Missing chart for visual confirmation and quick actions for workflow speed.

---

### Diego (Student) — "Can he understand the methodology?"

**Path:** Homepage → Methodology

| Step | Result | Time |
|------|--------|------|
| Homepage signal architecture section | ✅ | 10s |
| Click "Methodology →" | ✅ | 2s |
| Composite score equation (KaTeX) | ✅ | 10s |
| Normalization formula | ✅ | 10s |
| Regime threshold table | ✅ | 10s |
| Confidence derivation formula | ✅ | 10s |
| Signal family cards with metadata | ✅ | 15s |
| **Missing:** Expert / Student toggle | ❌ | — |
| **Missing:** Plain English expanders | ❌ | — |

**Verdict:** ⚠️ **Partial pass.** Full math is there. No student-mode plain English. Diego needs quant literacy to follow. Missing "How to Read the Terminal" section linking to `/terminal/fx-regime`.

---

## 5. Content Audit

### Copy Correctness

| Location | Issue | Severity |
|----------|-------|----------|
| `about/page.tsx` — validation stats | Hardcoded "77.8%", "27", "3" instead of live data. | **High** |
| `performance/page.tsx` — equity curve label | Says "Equity Curve — Cumulative Directional Return". Correct. | ✅ |
| `brief/page.tsx` — header | "MORNING BRIEF · 2026-05-05" format correct. | ✅ |
| `methodology/page.tsx` — H1 | "Signal Architecture" matches spec. | ✅ |
| `Nav.tsx` — Terminal dropdown labels | "Overview", "EUR/USD", "USD/JPY", "USD/INR", "Calendar", "Memos", "Alpha Ledger" — mostly correct. Missing "FX-Regime Mosaic". | Low |

### Timestamp Accuracy

| Location | Issue | Severity |
|----------|-------|----------|
| `performance/page.tsx` — `lastDate` | Uses max date from validation log. Correct format. | ✅ |
| `terminal/page.tsx` — pipeline timestamp | `new Date().toISOString().slice(0, 10)` — renders **today's date**, not actual pipeline run time. | **Medium** |
| `[pair]/page.tsx` — signal chip timestamp | Same issue — `new Date().toISOString().slice(0, 10)` is client-rendered today, not data timestamp. | **Medium** |
| `Footer.tsx` | No timestamp. | — |

### Label Consistency

| Location | Issue | Severity |
|----------|-------|----------|
| `ValidationTable.tsx` — header | Uses "CALL" instead of spec'd "REGIME". | Low |
| `performance/page.tsx` — section labels | "Hit Rate by Horizon", "Regime Performance", "Monthly Breakdown", "Validation Log — All Calls" — all match spec. | ✅ |
| `[pair]/page.tsx` — section labels | "SIGNAL ARCHITECTURE", "SIGNALS TABLE", "OTHER DESKS", "REGIME HISTORY (7D)", "CONFIDENCE TREND (14D)" — match spec intent. | ✅ |

---

## 6. Data Integrity

### Calculations

| Calculation | Status | Notes |
|-------------|--------|-------|
| Cumulative return | ✅ Correct | `reduce((s, r) => s + r.return_pct, 0)` — sum of all daily returns. |
| Equity curve | ⚠️ **Questionable** | Sums **all pair returns per day** into a single point. If 3 pairs each return +0.1%, daily point is +0.3%. This overstates aggregate magnitude vs. per-pair average. Spec says "cumsum of actual_return_1d (directional sign applied)" — ambiguous, but typical aggregate equity curves average across pairs, not sum. |
| 7D accuracy | ⚠️ Minor issue | Uses calendar days (`setUTCDate(-7)`), not trading days. Could include weekends with no data. Low impact. |
| Max drawdown | ✅ Correct | `peak - current` tracked across equity curve. |
| Regime streak | ✅ Correct | Reverse-iterates from last chronological row. |
| Monthly cumulative | ✅ Correct | Running sum across months, newest-first display. |
| Hit rate by horizon | ❌ Broken | T+5/T+20 hardcoded to 0. Should show "insufficient data" or be hidden until `strategy_ledger` populates. |
| Avg next-day return | ✅ Correct | Mean of `return_pct`. |

### Data Flow

| Source → Destination | Status | Notes |
|----------------------|--------|-------|
| `regime_calls` → homepage snapshot cards | ✅ Flowing | `getLatestRegimeCalls` fetches latest per pair. |
| `signals` → homepage spot prices | ✅ Flowing | `getLatestSignals` fetches spot, day_change. |
| `validation_log` → performance page | ✅ Flowing | `getValidationLog` filters `correct_1d !== null`. |
| `brief_log` → `/brief` | ✅ Flowing | `getLatestBrief` fetches latest. |
| `validation_log` → about page stats | ❌ **Broken** | About page uses hardcoded values instead of fetching validation log. |
| `strategy_ledger` → hit rate T+5/T+20 | ❌ **Broken** | No query for `strategy_ledger`. Placeholder data. |
| `desk_open_cards` → invalidation level | ❌ **Broken** | Invalidation computed as ±50bps from spot. Not from `desk_open_cards.telemetry_audit`. |

---

## 7. Priority Recommendations

### 🔴 P0 — Fix Before Ship

1. **Add Trader's TL;DR box to `/brief`**
   - Spec §5.5 requires this at the top. Marcus cannot find the call without reading prose.
   - Pull from `brief_log` + `regime_calls` for the day.

2. **Fix nav order: Terminal must be 2nd**
   - Move Terminal link before Methodology in `Nav.tsx`.
   - Current order breaks the "Performance first, Terminal second" hierarchy.

3. **Wire About page stats to live data**
   - Replace hardcoded "77.8%", "27", "3" with actual `getValidationLog` query.
   - Priya will spot this immediately.

4. **Fix validation table type safety**
   - `performance/page.tsx` passes `ValidationRow[]` to `ValidationTable` which expects `ValidationTableRow[]`.
   - Use `mapValidationLogToTableRows()` or unify types.

5. **Wire footer email capture**
   - Replace `// TODO` with actual Substack signup API call or redirect.
   - Dead form is worse than no form.

### 🟡 P1 — Next Sprint

6. **Add Brier score trend to `/performance`**
   - Key trust signal for allocators. Non-negotiable per spec.
   - Query `strategy_ledger.brier_score_t5`, render as Lightweight Charts line with 0.25 baseline.

7. **Replace equity curve SVG with Lightweight Charts**
   - Enables crosshair, time range selector, and regime band overlay.
   - Spec §1.2 and §4.1 explicitly require Lightweight Charts.

8. **Expand pair desk regime history from 7 → 30 days**
   - Add scrollable container. Add validation outcome squares + return % per row.

9. **Add "Discuss on Substack" CTA to `/brief`**
   - Store `substack_url` in `brief_log`. Link at bottom of brief.

10. **Hide or honest-label T+5 / T+20 hit rates**
    - Show "Insufficient data (N < 5)" instead of 0/0 bars.

### 🟢 P2 — Polish

11. **Expert / Student toggle on `/methodology`**
    - Add state toggle. Render plain English paragraphs in student mode.

12. **Add filter chips + pagination to validation log**
    - Pair filter, regime filter, date sort. 50 rows per page.

13. **Add TradingView chart embed to pair desk**
    - Embed widget with regime-change vertical markers.

14. **Add live indicators strip to `/terminal`**
    - Sync status dot, COT age, VIX, DXY.

15. **Dynamic OG images**
    - `/api/og` route for brief/performance/pair pages.

---

## Summary

| Category | Score | Assessment |
|----------|-------|------------|
| P0 Feature Completeness | 65% | Core pages exist. Equity curve, TL;DR, live data all present. Missing Brier, nav order wrong, brief TL;DR missing, hardcoded About stats. |
| Spec Fidelity | 60% | Major deviations in nav order, chart library, data wiring, and content placement. |
| User Flows | 70% | All three personas can complete primary tasks partially. Friction points exist for each. |
| Content Quality | 75% | Copy is mostly correct and on-brand. Hardcoded stats and missing timestamps drag score down. |
| Data Integrity | 70% | Cumulative math fixed. Equity curve aggregation method questionable. About page disconnected from live data. |

**Bottom line:** The product is **functional and impressive**, but has **critical trust gaps** (hardcoded About stats, missing brief TL;DR, dead email form, wrong nav order) that will undermine credibility with Priya and frustrate Marcus. Fix the 🔴 P0 items before any public share.
