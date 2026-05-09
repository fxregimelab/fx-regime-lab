# P4 PROMPT — Terminal Polish: Pair Desk Upgrade + Mobile + Error States

> **EXECUTE THIS YOURSELF.** Do NOT delegate to Cursor. You MAY use your own Agent/Subagent tools for parallel exploration, implementation, and testing — but the final code changes must pass through your own verification.

---

## 1. CONTEXT & GOAL

The FX Regime Lab terminal is functionally complete:
- **P2**: Performance dashboard with T+5/T+20 track record
- **P3**: Live Signal Dashboard with cross-asset context, alerts, macro calendar, signal cards, daily brief
- **Pair desk**: `/terminal/fx-regime/[pair]` has spot, regime, confidence, signal table, regime history, confidence sparkline

**What is missing:**
1. **Pair-specific validation track record** — The pair desk shows today's signals but has NO T+5/T+20 history for that pair. A PM visiting the EUR/USD desk should see how many of the last 20 EUR/USD calls were correct.
2. **Historical spot price context** — No spot price history chart on the pair desk. A 30-day spot sparkline is essential for context.
3. **Mobile layout gaps** — The pair desk sidebar does not stack gracefully on mobile. The performance page equity curve can overflow.
4. **Error & empty states** — No loading skeletons, no graceful empty states when data is missing, no error boundaries.

**This is the final frontend polish round before the terminal is institutionally presentable.**

---

## 2. WHAT EXISTS NOW

### Frontend (`web/`)
- Next.js 15.3.9, React 19, Tailwind CSS v4, TypeScript 5
- `/terminal/page.tsx` — P3 institutional morning desk (SystemStatusBar, CrossAssetMatrix, AlertStrip, MacroCalendarStrip, SignalCard, DailyBriefPanel)
- `/terminal/fx-regime/[pair]/page.tsx` — Pair desk: spot, regime, confidence, composite, signal table, regime history timeline, confidence sparkline, other desks sidebar
- `/performance/page.tsx` — P2 performance dashboard (StatsCard, PairBreakdownTable, BrierChart, EquityCurveSVG, ValidationTable)
- `/components/performance/` — `StatsCard.tsx`, `PairBreakdownTable.tsx`, `BrierChart.tsx`
- `/components/ui/sparkline.tsx` — SVG sparkline (already has aria-label)
- `/components/ui/confidence-bar.tsx` — Confidence bar
- `/lib/supabase/queries.ts` — `getValidationLogForPair`, `getValidationStats`, `getHistoricalRegimeCalls`, `getHistoricalPrices` (to be added), `getLatestRegimeCalls`, `getLatestSignals`
- Swiss Monochrome: pure black `#000000`, white text, sharp 1px borders, `tabular-nums`, no rounded corners

### Database (Supabase)
- `regime_calls` — `pair, date, regime, confidence, signal_composite, rate_signal, primary_driver, entry_timing, position_size, stop_level, data_quality_score, stress_level, predicted_direction, directional_bias, conviction`
- `signals` — `spot, day_change_pct, rate_diff_2y, cot_percentile, realized_vol_20d, realized_vol_5d, implied_vol_30d, ...`
- `validation_log` — `date, pair, predicted_direction, correct_t5, correct_t20, brier_score_t5, brier_score_t20, log_return_t5_bps, log_return_t20_bps, actual_direction_t5, actual_direction_t20`
- `validation_stats` — `pair, as_of_date, t5_win_rate, t5_mean_brier, t5_total_calls, t5_sharpe_like, t20_win_rate, t20_mean_brier, t20_total_calls, t20_sharpe_like`
- `historical_prices` — `pair, date, open, high, low, close, source, fetch_timestamp`

### Locked Rules
- 3-pair lock: EURUSD, USDJPY, USDINR only
- Swiss Monochrome aesthetic strictly enforced
- All DB reads use generated types from `database.types.ts`
- `npm run build` must pass
- No decorative animations, no soft shadows, no rounded corners
- `export const dynamic = "force-dynamic"` on all data-dependent pages

---

## 3. ACCEPTANCE CRITERIA

### A. Query Layer (`/lib/supabase/queries.ts`)
- [ ] Add `getHistoricalPrices(supabase, pair, limit)` → queries `historical_prices` for the pair, ordered by date desc, returns `{ date, close }[]`
- [ ] Add `getPairValidationSummary(supabase, pair)` → queries `validation_stats` for the pair (latest `as_of_date`), returns `{ t5WinRate, t5Brier, t5SampleSize, t5SharpeLike, t20WinRate, t20Brier, t20SampleSize, t20SharpeLike }`
- [ ] Add `getPairValidationHistory(supabase, pair, limit)` → queries `validation_log` for the pair where `brier_score_t5 IS NOT NULL`, ordered by date desc, returns array of `{ date, predicted, t5Outcome, t5ReturnBps, t5Brier, t20Outcome, t20ReturnBps, t20Brier }`
- [ ] Extend `getHistoricalRegimeCalls` selection to include `predicted_direction` (needed for validation alignment display)
- [ ] Ensure all new query functions use `TypedSupabaseClient` (not `any`)

### B. Pair Desk Enhancement (`/terminal/fx-regime/[pair]/page.tsx`)
- [ ] **Spot Price Sparkline**: Add a 30-day spot price sparkline above or beside the signal table, using `getHistoricalPrices`. Use the existing `Sparkline` component.
- [ ] **Validation Stats Card**: Add a compact stats row (T+5 Win Rate, T+5 Brier, T+5 Sharpe, T+20 Win Rate, T+20 Brier) fetched via `getPairValidationSummary`. Display as 5-tile grid with `fmtPct` / `fmt2`. If stats are null, show "—".
- [ ] **Validation History Table**: Add a scrollable table showing the last 20 validation outcomes for this pair. Columns: Date | Predicted | T+5 Outcome | T+5 Return (bps) | T+5 Brier | T+20 Outcome | T+20 Return (bps) | T+20 Brier. Use green/red badges for CORRECT/WRONG, gray for NEUTRAL/"—". Reuse styling from `ValidationTable` if possible.
- [ ] **Layer 3 Execution Panel**: When `entry_timing`, `position_size`, or `stop_level` are non-null, render a small execution panel showing: ENTRY | SIZE | STOP | RVOL RANK. Currently these fields are mostly null in DB — the component must gracefully show "—" when null.
- [ ] **Regime Alignment Check**: In the validation history table, add a small dot indicator showing whether the `predicted_direction` on the call matched the actual `regime` label for that date (optional enhancement if time permits).

### C. Mobile Responsiveness
- [ ] **Pair desk sidebar**: On screens below `lg`, the sidebar (Other Desks, Regime History, Confidence Trend, Regime Timeline) must stack vertically BELOW the main signal table, not beside it. Use `grid-cols-1 lg:grid-cols-[1fr_300px]` already present — verify it collapses correctly.
- [ ] **Signal cards on `/terminal`**: The 3-column grid must collapse to 1 column on mobile (`grid-cols-1 md:grid-cols-3`). Already implemented — verify no overflow.
- [ ] **CrossAssetMatrix**: Verify 7-tile grid collapses gracefully on small screens (`grid-cols-2 sm:grid-cols-4 lg:grid-cols-7`). Already implemented.
- [ ] **Performance page**: Ensure `EquityCurveSVG` and `BrierChart` do not cause horizontal overflow on mobile. Add `overflow-x-auto` wrappers if needed.
- [ ] **Font sizes**: On mobile, reduce large display numbers (e.g., `text-[28px]`, `text-[32px]`) using responsive `clamp()` or `text-[clamp(...)]`. Already partially done — audit and fix any remaining.

### D. Error & Empty States
- [ ] **Loading skeletons**: Create a simple `Skeleton` component in `/components/ui/skeleton.tsx` — a div with animated pulse background (`bg-[var(--color-border-subtle)] animate-pulse`). Use it in:
  - `SystemStatusBar` (4 tiles)
  - `SignalCard` (header + 3 layers)
  - `CrossAssetMatrix` (7 tiles)
  - `DailyBriefPanel`
- [ ] **Empty states**: When `getLatestRegimeCalls` returns empty, show a full-page empty state: "No regime calls available. The pipeline may still be processing today's data." with a muted timestamp.
- [ ] **Error boundaries**: Wrap the main data-fetching sections in `error.tsx` files. The `/terminal/error.tsx` already exists — verify it catches rendering errors gracefully. Add a similar `error.tsx` to `/terminal/fx-regime/[pair]/`.
- [ ] **Graceful null handling**: Every component must handle `null` / `undefined` data without crashing. Audit all dashboard components for missing optional chaining.

### E. General Polish
- [ ] **Consistent section headers**: All dashboard sections should use the same header pattern: `font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase` with a bottom border.
- [ ] **Back navigation**: Add a "← Terminal" link at the top of the pair desk page linking back to `/terminal`.
- [ ] **OpenGraph image**: The existing `/terminal/fx-regime/[pair]/opengraph-image.tsx` should include the pair label, current regime, and confidence. Verify it still works after changes.
- [ ] **Meta titles**: Each pair desk page should have a unique `<title>`: `"EUR/USD Desk | FX Regime Lab"`, etc.

---

## 4. DESIGN SPECIFICATIONS

### Swiss Monochrome (STRICT)
- Background: `var(--color-surface)` / `#000000`
- Borders: `1px solid var(--color-border)` — sharp, no `rounded-*`
- Text: `var(--color-text)` white, `var(--color-text-secondary)` muted, `var(--color-text-muted)` dim
- Numbers: `tabular-nums` everywhere
- Success/up: `var(--color-up)` / `#22c55e`
- Danger/down: `var(--color-down)` / `#ef4444`
- Warning: `var(--color-warn)` / `#F5923A`
- Pair colors: EURUSD `#F5923A`, USDJPY `#4A90E2`, USDINR `#7ED321`
- NO rounded corners, NO shadows, NO gradients (except sparkline fill), NO decorative animations

### Responsive Breakpoints
- Mobile: < 768px (`md:`)
- Tablet: 768px–1024px
- Desktop: > 1024px (`lg:`)

### Skeleton Spec
```tsx
// components/ui/skeleton.tsx
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={`animate-pulse bg-[var(--color-border-subtle)] ${className}`}
    />
  );
}
```

---

## 5. FILES TO READ BEFORE WRITING CODE

Read these in order to understand the current state:

1. `web/src/app/terminal/fx-regime/[pair]/page.tsx` — Current pair desk (708 lines)
2. `web/src/lib/supabase/queries.ts` — Query layer (new functions go here)
3. `web/src/lib/supabase/database.types.ts` — Verify `historical_prices`, `validation_log`, `validation_stats` schemas
4. `web/src/components/performance/ValidationTable.tsx` — Reuse styling patterns for validation history table
5. `web/src/components/ui/sparkline.tsx` — For spot price sparkline
6. `web/src/components/ui/confidence-bar.tsx`
7. `web/src/app/terminal/page.tsx` — For empty-state reference
8. `web/src/app/terminal/error.tsx` — For error boundary pattern
9. `web/src/app/terminal/layout.tsx` — To understand shared terminal layout

---

## 6. IMPLEMENTATION ORDER

**Phase 1 — Query Layer (safe, no UI changes)**
1. Add `getHistoricalPrices`, `getPairValidationSummary`, `getPairValidationHistory` to `queries.ts`
2. Run `npm run build` to verify type safety
3. Run `pytest` to ensure no pipeline regressions

**Phase 2 — Pair Desk Data + Layout**
4. Update `/terminal/fx-regime/[pair]/page.tsx`:
   - Fetch historical prices + validation stats + validation history in parallel
   - Add spot price sparkline
   - Add validation stats row
   - Add validation history table
   - Add Layer 3 execution panel
5. Verify mobile sidebar stacking

**Phase 3 — Skeletons + Empty States**
6. Create `components/ui/skeleton.tsx`
7. Add loading states to `/terminal/page.tsx` using `React.Suspense` or conditional rendering
8. Add empty state to `/terminal/page.tsx`
9. Add `/terminal/fx-regime/[pair]/error.tsx`

**Phase 4 — Mobile Audit**
10. Test all pages at 375px, 768px, 1440px widths
11. Fix any overflow issues

**Phase 5 — Final Verification**
12. `npm run build` → must pass zero errors
13. `pytest` → 218/218 must pass
14. `ruff check .` → clean on modified files
15. `biome check` on all new/modified files → clean
16. `tsc --noEmit` → zero TS errors

---

## 7. QUALITY GATES

| Gate | Command | Must Pass |
|------|---------|-----------|
| Build | `cd web && npm run build` | Zero errors |
| TypeScript | `cd web && npx tsc --noEmit` | Zero errors |
| Tests | `cd pipeline && pytest` | 218/218 |
| Python lint | `cd pipeline && ruff check .` | Clean |
| Frontend lint | `cd web && npx biome check src/...` | Clean on new/modified files |
| Pre-existing lint | Legacy files | 58 errors acceptable if unchanged |

---

## 8. LOCKED DECISIONS (DO NOT VIOLATE)

1. **3-pair lock**: Only EURUSD, USDJPY, USDINR may be queried or displayed.
2. **Immutable ledger**: Never modify `regime_calls` or `validation_log` from the frontend.
3. **No `any` types**: All Supabase client types must be properly typed. No `as any` escapes.
4. **Swiss Monochrome**: Pure black, white text, sharp 1px borders, `tabular-nums`, no rounded corners.
5. **No animations**: Only `transition-colors` for hover states and `animate-pulse` for skeletons.
6. **DB writes**: The frontend is read-only. All writes go through the Python pipeline.
7. **Build gate**: `npm run build` must pass before any commit.

---

*Prompt version: P4-2026-05-06*
