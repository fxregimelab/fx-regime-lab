# Design QA Report — Round 6
## FX Regime Lab Implementation Audit
**Auditor:** Design QA Lead  
**Date:** 2026-05-05  
**Scope:** `page.tsx`, `performance/page.tsx`, `terminal/fx-regime/[pair]/page.tsx`, `Nav.tsx`, `Footer.tsx`, `globals.css`  
**Against:** `round1-creative-director.md`, `round2-analytics-terminal-designer.md`

---

## Executive Summary

The implementation is **strong at the foundation level** — the Obsidian Stone palette is correctly tokenized, containers are disciplined, and the marketing surfaces (`/`, `/performance`) feel coherent. However, **three critical categories of issues** prevent a ship-ready state:

1. **`ValidationTable` is a light-theme component masquerading in dark mode** — hardcoded `text-white`, `bg-white`, `text-[#111]`, and undefined Tailwind classes (`text-up-shell`) make it the single biggest visual regression on the site.
2. **Several P0/P1 spec'd components are entirely missing** from `/performance` and the pair desk.
3. **`[data-fxrl-terminal]` is dead code** — the CSS override exists but the attribute is never applied in the DOM, so the terminal font-shift mechanism does not work.

**Verdict:** Fix all FAIL items and the ValidationTable WARN before shipping. The MISSING items can be queued for a fast-follow release if time-constrained, but the Brier trend and Drawdown+Sharpe panels are credibility-critical.

---

## 1. PASS ✅ — Implemented Correctly

### Color System & Tokens
- **Obsidian Stone palette** is fully and accurately tokenized in `globals.css`. All 12 core colors match Round 1 spec hex-for-hex.
- **Functional colors** (`--color-up`, `--color-down`, `--color-warn`) match spec exactly (`#7a9e7a`, `#b87a7a`, `#a8947a`).
- **Pair colors** correctly defined and consumed (`--color-pair-eurusd`, etc.).
- **Terminal aliases** exist and are used appropriately.
- **No light mode** — dark theme is the only reality. Correct.

### Typography Hierarchy
- **Hero**: `clamp(40px,6vw,72px)` / `font-semibold` / `tracking-tight` — exact match on `page.tsx`.
- **H2**: `28px` / `font-semibold` / `tracking-tight` — exact match in `SectionTitle`.
- **Body**: `15px` / `leading-[1.7]` — used consistently.
- **Label**: `font-mono` / `9–10px` / `tracking-[0.15em]` / `uppercase` — correct across all audited files.
- **Data**: `font-mono` / `24–32px` / `tabular-nums` — spot prices and metrics use this correctly.
- **Editorial serif**: Cormorant is imported and available via `--font-playfair` variable. (Naming mismatch is cosmetic; font works.)

### Layout & Spacing
- **Container**: `max-w-[1152px] mx-auto px-6` — consistent across all audited pages.
- **Section padding**: `py-24` (96px) — used correctly on `page.tsx` sections.
- **Gap rhythm**: `gap-px`, `gap-4`, `gap-8`, `gap-12`, `gap-16` — follows 4px-base system.
- **Border discipline**: `var(--color-border)` (#2a2725) and `var(--color-border-subtle)` (#1f1d1b) used consistently. No drop shadows on cards (except noted in WARN).

### `/` (Home) — page.tsx
- **Hero** matches spec: live dot, mono label, clamp hero, 15px body, CTA pair.
- **Scroll hint** uses gradient line — elegant, non-intrusive.
- **Live Snapshot cards**: correct border/surface/bg, `hover-lift`, staggered `reveal`, confidence bar, 32px spot price.
- **Signal Architecture**: `bg-[var(--color-elevated)]`, `gap-px` grid with border color as separator — excellent execution of the "grid as spine" principle.
- **Validation Trust strip**: 4-column metrics, gap-px pattern, correct label styling.
- **About snippet**: two-column grid, correct hierarchy.

### `/performance` — performance/page.tsx
- **Equity Curve SVG**: pure black pane (`#000000`), grid `#111111`, line `#d6d3d1` (2px), area fill `rgba(214,211,209,0.08)`, drawdown haze `rgba(184,122,122,0.06)` — **all match spec 1.2 exactly**.
- **Metrics Strip**: `gap-px` border pattern, stale `opacity-50` wrapper, correct data computation (cumulative return is actual sum, not `avg * count`).
- **Hit Rate by Horizon**: 4px bars, `var(--color-panel)` track, color-coded fills (`≥60%` green, `40–60%` amber, `<40%` red), `INSTITUTIONAL_SETTLE` easing on width transition.
- **Regime Performance Table**: zebra striping, mono header with `tracking-[0.15em]`, color-coded hit%, avg ret, max DD, streak badges.
- **Monthly Breakdown Table**: same styling as regime table, running cumulative column, correct color coding.
- **Stale indicator**: `[ STALE ]` badge in `var(--color-warn)` with border — exact match.

### `/terminal/fx-regime/[pair]` — pair desk page.tsx
- **Top Data Strip**: 4-column grid, correct metric order (Spot → Regime → Confidence → Composite), pair-colored confidence, composite bar with center marker.
- **Trader's Context Strip**: bias/driver/invalidation/watchlist layout, correct mono typography.
- **Signal Architecture**: stacked horizontal bar with legend, hover tooltips.
- **Signal Table**: zebra rows, z-score column, trend arrows, color coding.
- **Confidence Sparkline**: present with date labels at ends.
- **Regime Timeline**: 30-day dot grid with tooltip on hover, legend.
- **Related Pairs sidebar**: `RegimeCard` components with correct styling.

### Shell Components
- **Nav.tsx**: Fixed header, scroll-triggered bg transition, active indicator with `animate-line-grow`, terminal dropdown with pair links. Correct.
- **Footer.tsx**: Three-column grid, mono section labels, correct link styling, subscribe form with focus state. Correct.

### Animation & Motion
- **Keyframes**: `fade-up`, `fade-in`, `slide-in-left`, `line-grow`, `gentle-pulse` all present.
- **Easing tokens**: `--ease-institutional` (`cubic-bezier(0.16, 1, 0.3, 1)`) and `--ease-crisp` match spec.
- **Duration tokens**: `--duration-micro: 80ms`, `--duration-default: 300ms`, `--duration-emphasis: 600ms` — correct.
- **Stagger tokens**: `--stagger-tight: 50ms`, `--stagger-default: 100ms`, `--stagger-loose: 150ms` — correct.
- **Reduced motion**: full `prefers-reduced-motion: reduce` block — correct.
- **Selection**: warm grey `rgba(168,162,158,0.25)` — correct.

### Accessibility & Polish
- `tabular-nums` used on all numeric displays.
- Scrollbar styling is minimal dark (4px, `rgba(255,255,255,0.1)`).
- Empty states show `—` (em dash), not `0` or `N/A`.

---

## 2. WARN ⚠️ — Minor Inconsistencies (Should Fix)

### W1. Nav uses `backdrop-blur-md` on scroll
**Location:** `Nav.tsx:45`  
**Spec violation:** Round 1 Anti-pattern #8 — "No blur/backdrop-filter."  
**Impact:** Low on marketing pages, but sets a bad precedent. The blur is subtle (`bg-[var(--color-surface)]/80 backdrop-blur-md`).  
**Fix:** Replace with solid `bg-[var(--color-surface)]` when scrolled. The `border-b` already provides enough separation.

### W2. Nav dropdown uses `shadow-lg`
**Location:** `Nav.tsx:97`  
**Spec violation:** Round 1 Anti-pattern #2 — "No drop shadows on cards."  
**Fix:** Remove `shadow-lg`. The border definition is sufficient.

### W3. `hover-lift` utility uses box-shadow
**Location:** `globals.css:237`  
**Spec violation:** Round 1 Anti-pattern #2.  
**Note:** Shadow is `0 8px 30px rgba(0,0,0,0.3)` — extremely subtle on dark bg. Acceptable if kept, but spec is clear.

### W4. Metrics strip label tracking is `0.12em`, spec wants `0.15em`
**Location:** `performance/page.tsx:422`  
**Spec:** Round 2, 1.3 — "Labels: `font-mono text-[9px] tracking-[0.12em]`" actually contradicts Round 1 table which says `0.12–0.2em`. This is within range. **Downgrade to note.**

### W5. Equity Curve is hand-rolled SVG, not Lightweight Charts
**Location:** `performance/page.tsx` `EquityCurveSVG` component  
**Spec:** Round 2, 1.2 — specifies Lightweight Charts by TradingView.  
**Impact:** Visual output is correct, but we lose crosshair interactivity, time-range selector buttons, and auto-resize. The SVG also won't get regime band overlays or the 7D/30D/90D/ALL time range switch.  
**Fix:** Migrate to Lightweight Charts for P1. The SVG is a credible placeholder.

### W6. Terminal layout container is `max-w-[1200px]`
**Location:** `terminal/layout.tsx:10`  
**Spec:** `max-w-[1152px]` everywhere.  
**Impact:** Slight misalignment when navigating between marketing and terminal.  
**Fix:** Change to `max-w-[1152px]`.

### W7. Confidence sparkline height is 50px, not 70px
**Location:** `terminal/fx-regime/[pair]/page.tsx:541`  
**Spec:** Round 2, 3.7 — "Height: Increase from `50px` to `70px`."  
**Fix:** Change `height={50}` to `height={70}`.

### W8. Regime history shows 7 days, spec says 30 days with visual encoding
**Location:** `terminal/fx-regime/[pair]/page.tsx:512`  
**Spec:** Round 2, 3.5 — "Expand to 30 days with visual encoding."  
**Note:** A 30-day dot grid exists below ("Regime Timeline"), but the scrollable history list is capped at 7. The spec wants the list to be 30 days scrollable `max-h-[400px]`.

### W9. Signal architecture bar colors are muted/surface-mixed
**Location:** `terminal/fx-regime/[pair]/page.tsx:113`  
**Spec:** Round 2, 3.3 — "Bar fill: Pair color at `80% opacity`."  
**Current:** Uses `color-mix(in srgb, var(--color-up) 35%, var(--color-surface))` — muted and generic, not pair-colored.  
**Fix:** Use `color-mix(in srgb, var(--color-pair-xxx) 80%, transparent)`.

### W10. `[data-fxrl-terminal]` CSS selector is dead code
**Location:** `globals.css:321-328`  
**Issue:** The CSS rule `[data-fxrl-terminal] p, span, div { font-family: var(--font-mono); }` exists, but **no element in the DOM carries this attribute**. The terminal layout does not apply it; the pair desk page does not apply it.  
**Impact:** The mechanism is non-functional. Terminal pages rely on explicit `font-mono` classes on every element, which works but is brittle.  
**Fix:** Add `data-fxrl-terminal` to the terminal layout root `<div>` or `<main>`, then audit that explicit `font-mono` classes don't double-apply.

### W11. `text-up-shell` / `text-down-shell` classes may be undefined
**Location:** `components/regime/ValidationTable.tsx`  
**Issue:** These classes are used for outcome and return coloring, but they do not appear in `globals.css` or any Tailwind v4 theme definition. If undefined, they render as inherited text color.  
**Fix:** Verify in dev tools. If missing, replace with `text-[var(--color-up)]` / `text-[var(--color-down)]`.

### W12. Performance page H1 is `32px`, not `clamp(40px,6vw,72px)`
**Location:** `performance/page.tsx:351`  
**Spec:** Round 1 says hero is `clamp(40px,6vw,72px)`. The performance page title is arguably a page header, not a hero.  
**Verdict:** Acceptable as an H1 page title, but should ideally use `28px` (H2 spec) for consistency with other page headers. Current `32px` is an orphan size.

---

## 3. FAIL ❌ — Major Deviations (MUST Fix)

### F1. ValidationTable uses hardcoded light-theme colors
**Location:** `components/regime/ValidationTable.tsx`  
**Severity:** CRITICAL — this component renders on `/performance` and anywhere else validation data is shown.

| Current (Broken) | Spec (Correct) |
|---|---|
| `bg-white` | `bg-[var(--color-surface)]` |
| `text-white` | `text-[var(--color-text)]` |
| `text-[#111]` | `text-[var(--color-text)]` |
| `text-[#999]` | `text-[var(--color-text-muted)]` |
| `text-[#aaa]` | `text-[var(--color-text-secondary)]` |
| `text-[#555]` | `text-[var(--color-text-muted)]` |
| `bg-[#fafafa]` | `bg-[var(--color-elevated)]` |
| `border-shell-border` / `border-terminal-border` | OK, but these alias to the right values |

**Impact:** On dark pages, `bg-white` and `text-[#111]` create inverted cards that look like flashbangs. `text-white` on dark bg is acceptable but not tokenized.

**Fix:** Rewrite `ValidationTable` to use **only** CSS custom properties. Reference the Regime Performance Table in `performance/page.tsx` as the canonical dark-table implementation.

### F2. ValidationTable missing all Round 2 enhancements
**Location:** `components/regime/ValidationTable.tsx`  
**Spec:** Round 2, 1.10  
**Missing:**
- ❌ Link to brief per row (`VIEW` → `/brief?date=YYYY-MM-DD`)
- ❌ Filter chips above table (`[ All ] [ EUR/USD ] ... [ STRONG STR ]`)
- ❌ Pair name in pair color
- ❌ Return sparkline per row
- ❌ Outcome badge styling (`✓ CORRECT` bold green, `✗ INCORRECT` bold red)
- ❌ Click header to sort asc/desc
- ❌ Pagination (50 rows per page — currently renders ALL rows)

**Fix:** Enhance `ValidationTable` with filters, pair colors, brief links, and pagination. The table already accepts `tone="dark"` but doesn't fully honor the dark theme.

### F3. Brier Score Trend — COMPLETELY MISSING
**Location:** `/performance`  
**Spec:** Round 2, 1.6 — "Already exists in `AlphaLedger`. Extract and elevate."  
**Status:** No Brier chart, no baseline at 0.25, no dynamic line coloring.  
**Impact:** This is a credibility signal. "Lower = better calibration" is a key trust message.  
**Fix:** Extract from `AlphaLedger` or build new Lightweight Charts line series. Height: 120px.

### F4. Drawdown Display + Sharpe-Like Ratio — COMPLETELY MISSING
**Location:** `/performance`  
**Spec:** Round 2, 1.7 — side-by-side cards.  
**Status:** Max drawdown is shown inline in the equity curve panel, but there is no dedicated drawdown card with recovery time / longest drawdown duration. No Sharpe-like or Sortino ratio.  
**Fix:** Add two-column grid below monthly breakdown with drawdown stats and risk ratios.

### F5. Win/Loss Streak Indicator — COMPLETELY MISSING
**Location:** `/performance`  
**Spec:** Round 2, 1.8  
**Status:** Streak is shown per-regime in the Regime Performance Table, but there is no global streak panel with visual bars.  
**Fix:** Add streak panel below drawdown/sharpe cards.

### F6. Live Indicators Strip — MISSING from Terminal Index
**Location:** `/terminal` (`terminal/page.tsx`)  
**Spec:** Round 2, 2.3 — "SYNCED │ COT AGE: 2D │ VIX: 18.4 │ DXY: 104.2"  
**Status:** Not implemented.  
**Fix:** Add 28px strip below ticker grid.

### F7. Quick Actions Row — MISSING from Terminal Index
**Location:** `/terminal`  
**Spec:** Round 2, 2.5 — "View Mosaic │ View Ledger │ Today's Brief │ ⌘K Command │ ? Shortcuts"  
**Status:** Not implemented.  
**Fix:** Add action strip below strategy cards.

### F8. TradingView Chart + Regime Bands — MISSING from Pair Desk
**Location:** `/terminal/fx-regime/[pair]`  
**Spec:** Round 2, 3.4 — "Embed existing `TradingViewChart` component."  
**Status:** No chart embedded. The pair desk has signal tables and sparklines but no price chart.  
**Fix:** Embed `TradingViewChart` with regime-change markers and pair-colored spot line.

### F9. Invalidation Level Display — MISSING from Pair Desk
**Location:** `/terminal/fx-regime/[pair]`  
**Spec:** Round 2, 3.9  
**Status:** Invalidation level is shown as a single number in the Trader's Context strip, but there is no dedicated panel with status dot, distance bar, and "% to invalidation" progress.  
**Fix:** Add bordered panel below signal table.

### F10. `terminal/fx-regime/page.tsx` (Mosaic) uses cold/neon hardcoded colors
**Location:** `app/terminal/fx-regime/page.tsx`  
**Note:** This file is outside the strict audit list, but it is navigable from the pair desk and terminal index. It uses `#22c55e` (Tailwind green-500), `#ef4444` (Tailwind red-500), `#e8e8e8`, `#888`, `#666`, `#555`, `#000000`, `#080808`, `#111`, `#ccc` — almost none of which are CSS custom properties. The green/red are neon and completely violate the warm muted functional palette.  
**Fix:** Replace all hardcoded colors with `--color-*` tokens. Replace `#22c55e` with `var(--color-up)`. Replace `#ef4444` with `var(--color-down)`.

---

## 4. MISSING 📋 — Features from Spec Not Yet Implemented

### P0 (Blocks Credibility)
| Feature | Spec Ref | Where | Note |
|---|---|---|---|
| Brier Score Trend | 1.6 | `/performance` | Credibility-critical |
| Drawdown + Sharpe Panel | 1.7 | `/performance` | Risk transparency |
| ValidationTable enhancements | 1.10 | `/performance` | Filters, pagination, pair colors, brief links |
| Live Indicators Strip | 2.3 | `/terminal` | System health at a glance |
| TradingView Chart on pair desk | 3.4 | `/terminal/fx-regime/[pair]` | Price context is essential |

### P1 (High Impact)
| Feature | Spec Ref | Where | Note |
|---|---|---|---|
| Streak Indicator (global) | 1.8 | `/performance` | Visual trust signal |
| Monthly Performance Table hover tooltip | 1.9 | `/performance` | Best/worst single call of month |
| Quick Actions Row | 2.5 | `/terminal` | Keyboard shortcut awareness |
| Performance Summary Widget | 2.1 | `/terminal` | Strategy card enhancement |
| Confidence sparkline threshold line | 3.7 | Pair desk | 50% dashed line |
| Confidence sparkline end dot | 3.7 | Pair desk | `r=3` circle at latest point |
| Signal Table row hover tooltip | 3.8 | Pair desk | Raw signal value on hover |
| Invalidation Level Display | 3.9 | Pair desk | Full panel with progress bar |
| Related Pairs correlation signal | 3.10 | Pair desk | `[══]` correlation line |

### P2 (Polish)
| Feature | Spec Ref | Where | Note |
|---|---|---|---|
| Equity curve time range selector | 1.2 | `/performance` | `[7D] [30D] [90D] [ALL]` |
| Equity curve bottom stats row | 1.2 | `/performance` | Vol, Best Month, Worst Month |
| Mini sparkline in 7D Accuracy card | 1.3 | `/performance` | 30px high |
| Hit rate bar stagger animation | 1.4 | `/performance` | 150ms between horizons |
| Regime Performance row click → filter | 1.5 | `/performance` | Filters validation log |
| Strategy card performance strip | 2.4 | `/terminal` | 7D/30D/T+5/Brier mini strip |
| Signal architecture row hover | 3.3 | Pair desk | Raw value + z-score tooltip |
| Regime history expand to 30 days | 3.5 | Pair desk | Scrollable `max-h-[400px]` |
| Mobile regime timeline | 7.4 | Pair desk | Horizontal scrollable cards |
| Mobile validation log cards | 7.2 | `/performance` | Card-based list, 10 per page |

---

## 5. Cross-Cutting Issues

### Issue A: Two Nav Systems = Potential Divergence
The marketing site uses `components/shell/Nav.tsx`; terminal routes use `components/terminal/TerminalNav.tsx`. This is architecturally correct (Principle 4), but we must ensure they never both render simultaneously and that active states stay in sync. Currently correct due to layout separation.

### Issue B: `data-fxrl-terminal` Font Override Is Dead
As noted in W10, the `[data-fxrl-terminal]` base rule in `globals.css` is elegant but unused. Either apply the attribute or remove the rule to avoid confusion.

### Issue C: Color Palette Drift in Non-Audited Files
The `terminal/fx-regime/page.tsx` (Mosaic) and several `components/ui/*` files use hardcoded hexes (`#22c55e`, `#ef4444`, `#e8e8e8`, etc.). These will create visual discontinuity when users navigate between the pair desk (warm stone) and the mosaic (cold/neon). A **project-wide grep for hardcoded colors** is recommended.

### Issue D: Framer Motion vs. Shared Primitives
The Mosaic page uses `framer-motion` with inline `ease: 'easeOut'` and `duration: 0.2`. This does not match the shared `--ease-institutional` token. The spec says: "Audit every page for 'orphan' animations that do not use the shared primitives." The audited files (`page.tsx`, `performance/page.tsx`, `[pair]/page.tsx`) correctly use the CSS animation utilities.

---

## 6. Recommended Fix Priority

| Priority | Item | Effort | Owner |
|---|---|---|---|
| **P0** | F1 — Fix ValidationTable dark theme | 2h | Frontend |
| **P0** | F2 — ValidationTable enhancements (filters, pagination) | 4h | Frontend |
| **P0** | F3 — Brier Score Trend | 3h | Frontend + Data |
| **P0** | F8 — TradingView Chart on pair desk | 2h | Frontend |
| **P1** | F4 — Drawdown + Sharpe Panel | 3h | Frontend + Data |
| **P1** | F5 — Streak Indicator | 2h | Frontend |
| **P1** | F6 — Live Indicators Strip | 2h | Frontend + Data |
| **P1** | F9 — Invalidation Level Display | 2h | Frontend |
| **P1** | W10 — Apply `data-fxrl-terminal` attribute | 30min | Frontend |
| **P1** | F10 — Fix Mosaic page hardcoded colors | 2h | Frontend |
| **P2** | W1–W3 — Remove blur/shadow anti-patterns | 1h | Frontend |
| **P2** | W5 — Migrate equity curve to Lightweight Charts | 4h | Frontend |
| **P2** | All MISSING P2 items | 8h | Frontend |

**Estimated total to ship-ready:** 16–20 hours of focused frontend work.

---

## 7. Sign-Off

**QA Lead:** Design QA  
**Date:** 2026-05-05  
**Status:** ❌ **DO NOT SHIP** — P0 FAIL items must be resolved first.

The foundation is excellent. The palette is locked. The typography hierarchy is coherent. The missing pieces are well-specified and bounded. With 2–3 days of focused work, this will be a ship-grade research terminal.
