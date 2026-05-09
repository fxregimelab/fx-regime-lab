# UI/UX Multi-Agent Council Audit — Round 16

**Date:** 2026-05-08  
**Scope:** `fx-regime-lab/web/` — Next.js 15.3.9, Tailwind CSS v4  
**Council:** 6 specialists simulated  
**Verdict:** P0 critical fixes required before any public visibility.

---

## Council Members

| # | Specialist | Focus |
|---|------------|-------|
| 1 | **Design Systems Architect** | CSS tokens, Tailwind v4 `@theme inline`, color architecture |
| 2 | **Frontend Engineer** | Component contracts, type safety, data fetching, build health |
| 3 | **UI/UX Designer** | Visual hierarchy, layout, information architecture, light/dark coherence |
| 4 | **Content Strategist** | Factual accuracy, claims integrity, tone of voice, institutional credibility |
| 5 | **Accessibility Auditor** | Color contrast ratios, semantic HTML, keyboard navigation, ARIA |
| 6 | **Performance Engineer** | Bundle size, data fetching patterns, static vs dynamic routes, caching |

---

## Executive Summary

| Severity | Count | Categories |
|----------|-------|------------|
| 🔴 P0 Critical | 4 | Missing color tokens (547+ refs), false "7 pairs" claim, false "G10" claim, phantom nav links |
| 🟡 P1 High | 6 | Thin wrapper pages, signal architecture inaccuracy, "no ex-post edits" overstatement, stale "today's calls", missing date labels, body bg conflict |
| 🟢 P2 Medium | 4 | Unused design system, Nav/Footer hardcoded hexes, missing `@theme inline` mappings, no dark-mode infra |

**Overall:** The UI rebuild introduced a two-surface design system (light shell + dark terminal) but the merge broke the CSS token bridge. The result is a site that compiles but renders with undefined colors, mixed light/dark surfaces, and factual claims that undermine institutional credibility.

---

## Specialist 1: Design Systems Architect

### Findings

1. **Missing `--color-*` token definitions (P0)**
   - `globals.css` defines `--terminal-*` (28 tokens) and `--shell-*` (28 tokens).
   - Components reference `--color-void`, `--color-text`, `--color-surface`, `--color-border`, `--color-up`, `--color-down`, etc. **547+ times**.
   - **Zero definitions** exist for the `--color-*` namespace.
   - Result: browser falls back to transparent or default colors. Pages look broken.

2. **Orphaned design system (P1)**
   - The carefully architected `--terminal-*` / `--shell-*` families are **completely unused** by any component.
   - Either the components should use them, or the tokens should be removed.

3. **Tailwind v4 `@theme inline` incomplete (P2)**
   - Only maps `--color-terminal-bg` → `var(--terminal-bg)` and similar for shell/pair.
   - Does **not** map the generic `--color-*` namespace.
   - Therefore `bg-void`, `text-text-muted` utilities do not exist.

### Recommendations

1. **Define `--color-*` tokens in `globals.css`** using the canonical dark palette:
   ```css
   :root {
     --color-void: #0c0a09;
     --color-surface: #141210;
     --color-elevated: #1c1917;
     --color-text: #e7e5e4;
     --color-text-secondary: #a8a29e;
     --color-text-muted: #78716c;
     --color-text-dim: #57534e;
     --color-border: #292524;
     --color-border-subtle: #1c1917;
     --color-accent: #e7e5e4;
     --color-accent-hover: #ffffff;
     --color-up: #7a9e7a;
     --color-down: #b87a7a;
     --color-warn: #a8947a;
   }
   ```
2. **Map them in `@theme inline`** so utilities work.
3. **Deprecate or align `--terminal-*`** — either remap them to `--color-*` or delete them to avoid confusion.

---

## Specialist 2: Frontend Engineer

### Findings

1. **Type safety regressions from rebuild (P1)**
   - Multiple `as` casts needed to work around `createBrowserClient` inference returning `never[]`.
   - `supabase/queries.ts` restored from old version but some new functions (`getEquityCurve`) assumed non-existent DB columns (`exit_date`, `pnl_pct`).

2. **Component API mismatches (P1)**
   - Rebuild components (`DeskCard`, `RegimeCard`, `ValidationTable`, etc.) had incompatible prop interfaces.
   - Fixed by restoring old components, but this means the rebuild's new visual design is not active.

3. **Phantom routes (P0)**
   - Nav and CommandPalette link to `/terminal/mosaic` and `/terminal/alpha-ledger` — neither directory exists in `app/`.
   - Users will hit 404.

### Recommendations

1. Remove phantom routes from Nav and CommandPalette.
2. Add `page.tsx` stubs for future routes or remove links entirely.
3. Consider migrating old components to new APIs incrementally rather than wholesale replacement.

---

## Specialist 3: UI/UX Designer

### Findings

1. **Light/dark surface clash (P1)**
   - Nav (`#ffffff` bg, `#0a0a0a` text) and Footer (`#f5f5f0` bg) are hardcoded light.
   - All pages expect dark void (`--color-void`).
   - Result: a bright white nav bar sits on a dark page with no visual bridge.

2. **Blank/thin pages (P1)**
   - `terminal/calendar`, `terminal/memos`, `terminal/performance` are 15–17 line wrappers.
   - They delegate to components that are themselves minimal (56–108 lines).
   - Compared to `terminal/fx-regime` (506 lines) and pair detail (708 lines), these feel like placeholders.

3. **Information density imbalance**
   - FX Regime mosaic page is extremely dense (3×3 lattice, correlation matrix, macro drift, ghost whispers).
   - Calendar page is just a convexity radar with event list.
   - Performance page is just an alpha ledger table.
   - The terminal feels like 2 real pages + 3 stubs.

### Recommendations

1. **Unify the surface palette** — either make the entire app dark (including nav/footer) or create a proper light/dark theme switch.
2. **Elevate thin pages** — add cross-navigation, contextual data, and richer layouts to calendar/memos/performance.
3. **Add visual hierarchy markers** — section labels, consistent spacing rhythm, and clear "you are here" indicators in the terminal.

---

## Specialist 4: Content Strategist

### Findings

1. **"Seven pairs" — unambiguously false (P0)**
   - Hardcoded copy. `PAIRS.length === 3`.
   - Undermines the "institutional-grade" claim instantly.

2. **"G10 FX regime calls" — misleading (P0)**
   - G10 implies 10 currencies. Only EUR/USD, USD/JPY, USD/INR are tracked.
   - Suggests broader coverage than exists.

3. **"Four signal families" — incomplete (P1)**
   - There are five: rate, cot, vol, oi, special.
   - The special signal is 30% weighted for USD/INR but invisible on the homepage.

4. **"Published before market open" — unverified (P1)**
   - Prefect runs on 24h interval, not a fixed pre-market cron.
   - Aspirational copy that may not match reality.

5. **"No ex-post edits" — overstates technical guarantee (P1)**
   - DB uses `upsert` with conflict resolution. Append-only is a convention, not a constraint.

6. **"Today's regime calls" — potentially stale (P1)**
   - Shows latest DB call, not necessarily today's. Missing date label.

7. **Phantom nav links — factual error by implication (P0)**
   - UI asserts pages exist that don't.

### Recommendations

1. **Change "Seven pairs" → "Three pairs"** or list them explicitly.
2. **Change "G10 FX" → "Major FX pairs"** or remove the G10 qualifier.
3. **Update SignalArchitecture** to show 5 families with pair-specific weight ranges.
4. **Reword "before market open" → "Published daily"**.
5. **Reword "No ex-post edits" → "Append-only by convention"**.
6. **Add call date to snapshot cards**.
7. **Remove Mosaic and Alpha Ledger from nav** until they exist.

---

## Specialist 5: Accessibility Auditor

### Findings

1. **Color contrast failures (P1)**
   - `--color-text-muted: #78716c` on `--color-void: #0c0a09` → ratio ~3.8:1 (fails WCAG AA for small text).
   - `--color-text-dim: #57534e` on void → ratio ~2.9:1 (fails AA).
   - `--color-border: #292524` on void → ratio ~1.9:1 (invisible to low-vision users).

2. **Missing semantic elements (P2)**
   - Command palette uses `<div role="dialog">` instead of `<dialog>`.
   - Tables use div grids instead of `<table>` / `<thead>` / `<tbody>`.
   - No `<main>` landmark on some pages.

3. **Focus indicators (P2)**
   - No visible `:focus` styles defined in globals.css.
   - Keyboard navigation is possible but invisible.

### Recommendations

1. **Lighten text-muted to `#a8a29e`** (ratio 5.4:1 on void — passes AA).
2. **Lighten text-dim to `#8a8a8a`** (ratio 4.6:1 — passes AA).
3. **Lighten border to `#3a3633`** (visible but subtle).
4. **Use `<dialog>` element** for command palette.
5. **Add `:focus-visible` rings** using `outline: 2px solid var(--color-accent)`.

---

## Specialist 6: Performance Engineer

### Findings

1. **Route strategy mismatch (P2)**
   - Homepage and terminal index are server components that fetch from Supabase on every request.
   - No ISR, no `revalidate`, no edge caching.
   - Suboptimal for a site that could be largely static with periodic revalidation.

2. **Data fetching patterns (P2)**
   - `terminal/fx-regime/page.tsx` is a client component that fetches 6+ queries in parallel.
   - No query deduplication or prefetching from the server.
   - Suspense boundaries are minimal.

3. **Bundle size (P2)**
   - Framer Motion loaded in client pages but not tree-shaken effectively.
   - Recharts imported but unused in current pages.

### Recommendations

1. **Add `export const revalidate = 3600`** to static pages (homepage, about, methodology).
2. **Use React Server Components + streaming** for terminal pages.
3. **Defer Framer Motion** to interactive sections only.

---

## Implementation Priority Matrix

| # | Fix | Owner | Effort | Impact |
|---|-----|-------|--------|--------|
| 1 | Define `--color-*` tokens in globals.css | Design Systems | 30 min | 🔴 Visual restoration |
| 2 | Fix homepage claims (7→3, G10, 4→5 families) | Content | 20 min | 🔴 Credibility |
| 3 | Remove phantom nav links | Frontend | 5 min | 🔴 No 404s |
| 4 | Align Nav/Footer with dark palette | UI/UX | 30 min | 🟡 Visual unity |
| 5 | Add date labels to snapshot cards | Frontend | 15 min | 🟡 Accuracy |
| 6 | Lighten muted/dim text for a11y | A11y | 10 min | 🟡 WCAG AA |
| 7 | Elevate thin wrapper pages | UI/UX | 2h | 🟡 Depth |
| 8 | Add `@theme inline` mappings | Design Systems | 15 min | 🟢 Utility parity |
| 9 | Add focus-visible rings | A11y | 20 min | 🟢 Keyboard nav |
| 10 | ISR on static pages | Performance | 30 min | 🟢 Speed |

---

*Council convened by Kimi. Execution delegated to Cursor per operating model.*
