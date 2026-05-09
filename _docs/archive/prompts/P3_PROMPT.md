# P3 PROMPT — Live Signal Dashboard (Institutional Morning Desk)

> **EXECUTE THIS YOURSELF.** Do NOT delegate to Cursor. You MAY use your own Agent/Subagent tools for parallel exploration, implementation, and testing — but the final code changes must pass through your own verification.

---

## 1. CONTEXT & GOAL

The FX Regime Lab now has:
- A proven T+5/T+20 track record (P2 complete, 68 validated calls)
- A live pipeline generating daily regime calls for 3 pairs
- Full 3-layer signal data in Supabase: `signals`, `regime_calls`, `macro_events`

**The `/terminal` page currently shows only spot price + regime + confidence bar.** This is a toy-level overview. For institutional credibility, the landing dashboard must look like what a macro PM sees at 7:00 AM: cross-asset context, system health, per-pair signal decomposition, and actionable Layer 3 execution data.

**This is the highest-EV frontend task remaining.** It is the first impression for every admissions director and recruiter who visits the site.

---

## 2. WHAT EXISTS NOW

### Frontend (`web/`)
- Next.js 15.3.9, React 19, Tailwind CSS v4, TypeScript 5
- `/terminal/page.tsx` — basic cross-pair grid: spot, regime, confidence bar
- `/terminal/fx-regime/[pair]/page.tsx` — pair desk with `RegimeCard`, sparklines, watchlist
- `/components/ui/sparkline.tsx` — existing SVG sparkline component
- `/components/ui/confidence-bar.tsx` — existing confidence bar
- `/lib/supabase/queries.ts` — `getLatestRegimeCalls`, `getLatestSignals`, `getHistoricalRegimeCalls`, `getSignalHistory`
- Swiss Monochrome: pure black `#000000`, white text, sharp 1px borders, `tabular-nums`, no rounded corners

### Database (Supabase)
- `regime_calls` — `pair, date, regime, confidence, signal_composite, rate_signal, primary_driver, entry_timing, position_size, stop_level, data_quality_score, stress_level`
- `signals` — `spot, day_change_pct, rate_diff_2y, rate_diff_10y, cot_percentile, realized_vol_20d, realized_vol_5d, implied_vol_30d, cross_asset_vix, cross_asset_dxy, cross_asset_oil, cross_asset_gold, cross_asset_copper, cross_asset_stoxx, cross_asset_us10y, oi_delta, volume_rvol, structural_instability, skew_alignment, realized_vol_rank`
- `macro_events` — `date, event, impact, pairs, ai_brief`
- `brief_log` — `date, brief_text, macro_context, dollar_dominance, idiosyncratic_outlier, sentiment_json`

### Locked Rules
- 3-pair lock: EURUSD, USDJPY, USDINR only
- Swiss Monochrome aesthetic strictly enforced
- All DB reads use generated types from `database.types.ts`
- `npm run build` must pass
- No decorative animations, no soft shadows, no rounded corners

---

## 3. ACCEPTANCE CRITERIA

### A. Query Layer (`/lib/supabase/queries.ts`)
- [ ] Add `getLatestBriefLog(supabase)` → returns latest `brief_log` row (daily systemic summary)
- [ ] Add `getMacroEventsToday(supabase)` → returns `macro_events` for today with impact = HIGH
- [ ] Add `getSignalHistoryForAllPairs(supabase, limit = 30)` → returns last N signal rows per pair, mapped by pair
- [ ] Add `getCrossAssetSnapshot(supabase)` → returns latest `signals` row's cross-asset columns (VIX, DXY, Oil, Gold, Copper, STOXX, US10Y)
- [ ] Update `getLatestSignals` to also return `data_quality_score` (join or separate query)
- [ ] Type-safe: use `Database["public"]["Tables"]["signals"]["Row"]` as base, no `any`

### B. System Status Bar (new component)
Create `/components/dashboard/SystemStatusBar.tsx`:
- [ ] **DQS Gauge** — `data_quality_score` from latest regime call (0-1). Color: ≥0.75 green, 0.50-0.75 amber, <0.50 red. Label: "DQS"
- [ ] **Stress Badge** — `stress_level` (GREEN/AMBER/RED). Sharp 1px border in respective color. Label: "STRESS"
- [ ] **Last Run** — `created_at` of latest regime call, formatted as "2h ago" or "2026-05-08 09:54 UTC"
- [ ] **Validated Calls Counter** — count from `validation_stats` ALL row `t5_total_calls`
- [ ] Layout: horizontal strip, 4 items, separated by 1px borders, full width

### C. Cross-Asset Matrix (new component)
Create `/components/dashboard/CrossAssetMatrix.tsx`:
- [ ] 7 tiles in a row: VIX | DXY | BRENT | GOLD | COPPER | STOXX | US10Y
- [ ] Each tile: label (9px uppercase), value (large tabular-nums), day-change % (color-coded)
- [ ] Data from `getCrossAssetSnapshot()` — latest signals row's cross-asset columns
- [ ] Null handling: show "—" if data missing
- [ ] Swiss Monochrome: each tile is a bordered box, no rounded corners

### D. Enhanced Pair Cards (upgrade existing `/terminal` grid)
Upgrade the existing `/terminal/page.tsx` pair grid from 3 fields (spot, regime, confidence) to a full signal card:

Create `/components/dashboard/SignalCard.tsx`:
- [ ] **Header**: Pair label (colored), spot price (large), day-change % (colored), regime name
- [ ] **Layer 1 — Regime Gate**: Regime classification + regime age (days since last regime change, computed from `getHistoricalRegimeCalls`)
- [ ] **Layer 2 — Directional**: Rate signal (BULLISH/BEARISH/NEUTRAL), COT percentile bar (0-100), Signal composite value with z-score color
- [ ] **Layer 3 — Execution**: Entry timing (NOW/WAIT), Position size (FULL/HALF/NONE), Stop level (price), RVOL rank (1-5)
- [ ] **Sparkline**: 30-day signal composite history (re-use existing `Sparkline` component)
- [ ] **Confidence Bar**: existing component, but larger
- [ ] **Primary Driver**: 1-line text truncation
- [ ] **Link**: entire card links to `/terminal/fx-regime/${pair}`
- [ ] Responsive: 3-column grid on desktop, 1-column on mobile

### E. Alerts & Watchlist Strip (new component)
Create `/components/dashboard/AlertStrip.tsx`:
- [ ] Query: scan latest signals for threshold breaches:
  - RVOL > 8 → "RVOL ELEVATED"
  - IV > RVOL → "IV PREMIUM"
  - COT percentile > 85 or < 15 → "COT EXTREME"
  - Rate signal ≠ NEUTRAL → "RATE DIVERGENCE"
  - Stress level = RED → "RED STRESS — SIGNALS WITHHELD"
  - DQS < 0.75 → "DQS DEGRADED"
- [ ] Display as horizontal scrolling strip or wrapped tags
- [ ] Each alert: sharp bordered pill, color-coded by severity
- [ ] If no alerts: show "SYSTEM NOMINAL" in muted gray

### F. Macro Calendar Strip (new component)
Create `/components/dashboard/MacroCalendarStrip.tsx`:
- [ ] Query `getMacroEventsToday()` for HIGH impact events
- [ ] Show: Time (if available), Event name, Currency/pair affected
- [ ] If no events: show "NO HIGH-IMPACT EVENTS TODAY"
- [ ] Layout: horizontal strip below alerts

### G. Daily Brief Panel (new component, optional but recommended)
Create `/components/dashboard/DailyBriefPanel.tsx`:
- [ ] Query `getLatestBriefLog()`
- [ ] Show: Date, brief text (first 300 chars with "..." truncation), dollar dominance score if available
- [ ] Link to `/brief` for full text
- [ ] If no brief: show "Today's brief is being generated..."

### H. Page Integration (`/terminal/page.tsx`)
- [ ] Rewrite `/terminal/page.tsx` to use new components in this order:
  1. System Status Bar
  2. Cross-Asset Matrix
  3. Alert Strip
  4. Macro Calendar Strip
  5. Signal Cards (3-pair grid)
  6. Daily Brief Panel (optional, below fold)
- [ ] Keep existing `TerminalNav` and `TerminalSubNav` wrappers
- [ ] Add `export const dynamic = "force-dynamic"`
- [ ] All server fetches wrapped in `Promise.all()` for parallel loading

### I. Build & Test
- [ ] `cd web && npm run build` passes with zero errors
- [ ] `cd web && npm run lint` passes (or only pre-existing errors)
- [ ] `cd pipeline && pytest` still passes (218/218)
- [ ] No runtime errors on `/terminal` when loaded with live Supabase data

---

## 4. DESIGN SPECIFICATIONS

### Swiss Monochrome Compliance
```
Background:    var(--color-void)    (#000000 pure black)
Surface:       var(--color-surface) (#0a0a0a)
Elevated:      var(--color-elevated) (#111111)
Border:        var(--color-border)   (#222222)
Text:          var(--color-text)     (#ffffff)
Text secondary:var(--color-text-secondary) (#aaaaaa)
Text muted:    var(--color-text-muted) (#666666)
Up/Green:      var(--color-up)       (#00c853)
Down/Red:      var(--color-down)     (#ff5252)
Warn/Amber:    var(--color-warn)     (#ffd600)
```

### Typography
- Labels: `font-mono text-[9px] tracking-[0.15em] uppercase`
- Values: `font-mono text-[clamp(20px,2.5vw,28px)] tabular-nums`
- Secondary: `font-mono text-[11px]`
- All numbers: `tabular-nums`

### Spacing
- Component gap: `gap-px` with `bg-[var(--color-border)]` as separator (grid trick)
- Card padding: `p-5 md:p-6`
- Section margin: `mb-10`

---

## 5. FILES TO READ FIRST

1. `web/src/app/terminal/page.tsx` — current terminal index (to be rewritten)
2. `web/src/app/terminal/layout.tsx` — terminal shell layout
3. `web/src/components/ui/sparkline.tsx` — existing sparkline (re-use)
4. `web/src/components/ui/confidence-bar.tsx` — existing confidence bar (re-use)
5. `web/src/components/regime/RegimeCard.tsx` — existing regime card (reference)
6. `web/src/lib/supabase/queries.ts` — existing queries
7. `web/src/lib/supabase/database.types.ts` — generated types
8. `web/src/lib/constants.ts` — PAIRS array, colors, slugs
9. `web/src/app/globals.css` — design tokens

---

## 6. EXECUTION ORDER

Use this sequence. You MAY parallelize steps 3-6 via subagents.

```
1. READ phase (20 min)
   - Read all 9 files above
   - Understand current data flow, component patterns, design tokens
   - Note pre-existing lint/build errors

2. QUERIES phase (30 min)
   - Add getLatestBriefLog, getMacroEventsToday, getSignalHistoryForAllPairs, getCrossAssetSnapshot
   - Update getLatestSignals if needed
   - Verify types compile
   - Test queries against live Supabase (read-only)

3. COMPONENTS phase (90 min) — parallelizable via subagents
   - SystemStatusBar
   - CrossAssetMatrix
   - SignalCard
   - AlertStrip
   - MacroCalendarStrip
   - DailyBriefPanel (optional)

4. PAGE phase (30 min)
   - Rewrite /terminal/page.tsx
   - Integrate all components
   - Ensure responsive layout

5. INTEGRATION phase (30 min)
   - npm run build
   - npm run lint
   - Fix type/build errors
   - Visually verify with live data

6. VERIFICATION phase (15 min)
   - cd pipeline && pytest (218/218)
   - Confirm no new lint errors
   - Confirm no runtime errors on /terminal
```

---

## 7. SUBAGENT USAGE (ALLOWED & ENCOURAGED)

You MAY use your own Agent/Subagent tools for:
- **Explore agents**: Read-only codebase investigation (e.g., "find all files that use cross_asset_* columns")
- **Coder agents**: Implement isolated components (e.g., "build SystemStatusBar following Swiss Monochrome")
- **Parallel agents**: Run build/lint/tests while you continue coding

You MUST NOT:
- Delegate the final page integration to a subagent without reviewing
- Allow a subagent to modify `database.types.ts` (generated file)
- Accept "it should work" — verify with `npm run build`

---

## 8. DELIVERABLES

At completion, confirm:
- [ ] `/terminal` renders a full institutional dashboard on load
- [ ] System Status Bar shows DQS, stress, last run, validated count
- [ ] Cross-Asset Matrix shows VIX/DXY/Oil/Gold/Copper/STOXX/US10Y
- [ ] Signal Cards show Layer 1/2/3 decomposition for all 3 pairs
- [ ] Alert Strip shows threshold-based alerts
- [ ] Macro Calendar Strip shows today's high-impact events
- [ ] `npm run build` passes
- [ ] `pytest` passes (218/218)
- [ ] Live `/terminal` shows actual data (not empty states)

---

## 9. LOCKED DECISIONS CHECK

| Decision | Status |
|----------|--------|
| 3-pair lock | ✅ Only EURUSD, USDJPY, USDINR displayed |
| Design system | ✅ Swiss Monochrome (black/white, sharp borders, tabular-nums) |
| Type safety | ✅ Use generated Supabase types, no `any` |
| Build gate | ✅ `npm run build` must pass |
| Pipeline tests | ✅ `pytest` must remain 218/218 |
| No animations | ✅ No decorative motion, no soft shadows, no rounded corners |

---

*End of P3 Prompt. Execute directly. Do not delegate to Cursor.*
