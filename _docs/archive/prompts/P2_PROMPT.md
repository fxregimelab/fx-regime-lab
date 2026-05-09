# P2 PROMPT — Frontend Performance Dashboard (T+5/T+20 Validation)

> **EXECUTE THIS YOURSELF.** Do NOT delegate to Cursor. You MAY use your own Agent/Subagent tools for parallel exploration, implementation, and testing — but the final code changes must pass through your own verification.

---

## 1. CONTEXT & GOAL

The FX Regime Lab pipeline now has:
- **62/77 regime calls** with T+5 validation (Brier scores, win rates, log returns)
- **23/77 regime calls** with T+20 validation
- `validation_stats` table with per-pair and aggregate performance metrics
- `validation_log` table with full T+5/T+20 outcome data

**The frontend Performance page (`/performance`) currently shows 1-day validation only.** It filters on `correct_1d` and `actual_return_1d` — these are legacy fields. The page must be upgraded to display the institutional-grade T+5/T+20 track record that admissions committees and recruiters will actually evaluate.

**This is the highest-EV frontend task.** It transforms the project from "has a pipeline" to "has a proven track record with metrics."

---

## 2. WHAT EXISTS NOW

### Frontend (`web/`)
- Next.js 15.3.9, React 19, Tailwind CSS v4, TypeScript 5
- `/performance/page.tsx` — 731 lines, renders `ValidationTable`, equity curve SVG, summary stats
- `/lib/supabase/queries.ts` — `getValidationLog()` filters on `correct_1d` / `actual_return_1d`
- `/lib/supabase/database.types.ts` — generated Supabase types (includes `validation_stats`, `validation_log`)
- Swiss Monochrome design system: pure black `#000000`, white text, sharp 1px borders, no rounded corners

### Database (Supabase)
- `validation_log` — contains `log_return_t5_bps`, `correct_t5`, `brier_score_t5`, `actual_direction_t5`, `log_return_t20_bps`, `correct_t20`, `brier_score_t20`, `actual_direction_t20`
- `validation_stats` — contains `as_of_date`, `pair`, `horizon`, `win_rate`, `brier_score`, `sample_size`, `avg_return_bps`, `sharpe_ratio`
- `regime_calls` — contains `pair`, `date`, `regime`, `confidence`, `rate_signal`, `primary_driver`

### Locked Rules
- 3-pair lock: EURUSD, USDJPY, USDINR only
- All DB reads use generated types from `database.types.ts`
- Swiss Monochrome aesthetic: no soft shadows, no rounded corners, `tabular-nums` for numbers
- `npm run build` must pass before declaring completion

---

## 3. ACCEPTANCE CRITERIA

### A. Query Layer (`/lib/supabase/queries.ts`)
- [ ] Add `getValidationStats(supabase, horizon: "t5" | "t20")` → queries `validation_stats` table, filters by horizon, returns latest `as_of_date` per pair + "ALL"
- [ ] Add `getValidationLogT5T20(supabase, limit?)` → queries `validation_log`, filters rows where `brier_score_t5 IS NOT NULL`, maps to `ValidationRowT5` interface
- [ ] Add `getValidationLogForPair(supabase, pair, limit?)` → pair-specific T+5/T+20 history
- [ ] Deprecate `getValidationLog()` (legacy 1-day) — do not delete yet, just stop using it in `/performance`

### B. Performance Page (`/performance/page.tsx`)
- [ ] **Summary cards** at top: T+5 win rate (ALL), T+5 Brier score (ALL), T+20 win rate (ALL), T+20 Brier score (ALL), total validated calls
- [ ] **Per-pair breakdown table**: Pair | T+5 Win Rate | T+5 Brier | T+5 Sample | T+20 Win Rate | T+20 Brier | T+20 Sample
- [ ] **Validation history table**: Date | Pair | Predicted | T+5 Return (bps) | T+5 Outcome | T+5 Brier | T+20 Return (bps) | T+20 Outcome | T+20 Brier
- [ ] **Equity curve**: Cumulative log-return in bps from T+5 validated calls (not 1-day)
- [ ] **Brier score time series**: Rolling 10-call average Brier score over time
- [ ] Handle `null` gracefully: if T+20 data missing for a call, show "—" (em-dash)
- [ ] All numbers use `tabular-nums`

### C. Components
- [ ] Create `/components/performance/StatsCard.tsx` — reusable metric card (label, value, delta vs previous)
- [ ] Create `/components/performance/PairBreakdownTable.tsx` — per-pair stats table
- [ ] Create `/components/performance/BrierChart.tsx` — simple SVG line chart for rolling Brier (re-use equity curve SVG pattern)
- [ ] Update `/components/regime/ValidationTable.tsx` — add T+5/T+20 columns alongside existing 1-day (or replace 1-day with T+5 as primary)

### D. Type Safety
- [ ] Add `ValidationStatsRow` and `ValidationRowT5` interfaces to queries.ts
- [ ] Use generated `Database["public"]["Tables"]["validation_stats"]["Row"]` as base
- [ ] No `any` types in new code

### E. Build & Test
- [ ] `cd web && npm run build` passes with zero errors
- [ ] `cd web && npm run lint` passes (or has only pre-existing errors)
- [ ] `cd pipeline && pytest` still passes (218/218)
- [ ] No runtime errors on `/performance` when loaded with live Supabase data

---

## 4. IMPLEMENTATION GUIDANCE

### Data Mapping
```typescript
// T+5 row from validation_log → UI row
{
  date: row.date,
  pair: row.pair,
  predicted: row.predicted_direction,
  t5_return_bps: row.log_return_t5_bps,
  t5_outcome: row.correct_t5 ? "CORRECT" : row.actual_direction_t5 === "NEUTRAL" ? "NEUTRAL" : "WRONG",
  t5_brier: row.brier_score_t5,
  t20_return_bps: row.log_return_t20_bps,
  t20_outcome: row.correct_t20 ? "CORRECT" : row.actual_direction_t20 === "NEUTRAL" ? "NEUTRAL" : "WRONG",
  t20_brier: row.brier_score_t20,
}
```

### Color Coding
- CORRECT → `var(--color-up)` (green)
- WRONG → `var(--color-down)` (red)
- NEUTRAL → `var(--color-text-muted)` (gray)

### Stats Calculation
Use `validation_stats` table directly — do NOT compute aggregates in the frontend. The pipeline already computes:
- `win_rate` = fraction of correct calls (excluding neutral)
- `brier_score` = mean Brier score
- `sample_size` = number of validated calls
- `avg_return_bps` = mean log-return in bps

### Brier Score Interpretation (for UI labels)
- `< 0.10` → "Excellent calibration"
- `0.10 – 0.20` → "Good calibration"
- `0.20 – 0.30` → "Fair calibration"
- `> 0.30` → "Poor calibration"

---

## 5. FILES TO READ FIRST

1. `web/src/app/performance/page.tsx` — current performance page
2. `web/src/lib/supabase/queries.ts` — current queries
3. `web/src/lib/supabase/database.types.ts` — generated types (check validation_stats schema)
4. `web/src/components/regime/ValidationTable.tsx` — current validation table
5. `web/src/app/globals.css` — design tokens (colors, spacing)
6. `web/src/lib/constants.ts` — PAIRS array and other constants

---

## 6. EXECUTION ORDER

Use this sequence. You MAY parallelize steps 2-4 via subagents after you understand the codebase.

```
1. READ phase (15 min)
   - Read all 6 files above
   - Understand current data flow and component structure
   - Note pre-existing lint/build errors to avoid blaming yourself

2. QUERIES phase (30 min)
   - Add getValidationStats, getValidationLogT5T20, getValidationLogForPair
   - Verify types compile
   - Test queries against live Supabase (use anon key, read-only)

3. COMPONENTS phase (60 min)
   - Build StatsCard, PairBreakdownTable, BrierChart
   - Follow Swiss Monochrome aesthetic strictly
   - Re-use existing SVG patterns from performance/page.tsx

4. PAGE phase (45 min)
   - Rewrite /performance/page.tsx to use new queries and components
   - Keep equity curve logic, adapt to T+5 cumulative returns
   - Ensure responsive layout

5. INTEGRATION phase (30 min)
   - npm run build
   - npm run lint
   - Fix any type errors or build failures
   - Visually verify with live data (screenshot if possible)

6. VERIFICATION phase (15 min)
   - cd pipeline && pytest (must be 218/218)
   - Confirm no new lint errors
   - Confirm no runtime errors on /performance
```

---

## 7. SUBAGENT USAGE (ALLOWED & ENCOURAGED)

You MAY use your own Agent/Subagent tools for:
- **Explore agents**: Read-only codebase investigation (e.g., "find all files that use validation_log")
- **Coder agents**: Implement isolated components (e.g., "build StatsCard component following Swiss Monochrome")
- **Parallel agents**: Run build/lint/tests while you continue coding

You MUST NOT:
- Delegate the final integration to a subagent without reviewing its output
- Allow a subagent to modify `database.types.ts` (generated file)
- Accept "it should work" — verify with `npm run build`

---

## 8. DELIVERABLES

At completion, confirm:
- [ ] `web/src/lib/supabase/queries.ts` has new T+5/T+20 queries
- [ ] `web/src/app/performance/page.tsx` renders T+5/T+20 metrics
- [ ] New components exist in `/components/performance/`
- [ ] `npm run build` passes
- [ ] `pytest` passes (218/218)
- [ ] Live `/performance` shows actual backfilled data (not empty states)

---

## 9. LOCKED DECISIONS CHECK

| Decision | Status |
|----------|--------|
| 3-pair lock | ✅ Only EURUSD, USDJPY, USDINR |
| Design system | ✅ Swiss Monochrome (black/white, sharp borders, tabular-nums) |
| Type safety | ✅ Use generated Supabase types, no `any` |
| Build gate | ✅ `npm run build` must pass |
| Pipeline tests | ✅ `pytest` must remain 218/218 |

---

*End of P2 Prompt. Execute directly. Do not delegate to Cursor.*
