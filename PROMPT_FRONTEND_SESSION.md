# Prompt: Frontend Session — Build Fix, Docs Update, UI Audit

> **Session Type:** Frontend / Next.js  
> **Tier:** 1 (UI/content only, no data layer, no pipeline changes)  
> **Scope:** Fix build blocker, update stale docs, audit UI compliance, add M.5 diagnostics visibility  
> **Hard Rule:** No execution advice in public UI. No position_size/stop_level display. No "signals" language in user copy. 3-pair lock.

---

## Context

The FX Regime Lab frontend is a **fully built Next.js 15 App Router app** (16 pages, 68 components) that compiles cleanly in TypeScript but **fails to build on Windows** with:

```
Error: EISDIR: illegal operation on a directory, readlink
  'D:\...\web\src\app\api\linkedin-alpha-hook\route.ts'
```

The full plan is in `docs/FRONTEND_PLAN.md`. Read it before starting.

---

## Task 1: Fix the Build (P0 — Must Complete First)

**Problem:** `npm run build` fails on Windows. WSL build also fails (missing `lightningcss.linux-x64-gnu.node`).

**Recommended fix:** Move the App Router API route to Pages Router.

**Steps:**
1. Create `web/src/pages/api/linkedin-alpha-hook.ts` with the same POST handler logic from `web/src/app/api/linkedin-alpha-hook/route.ts`
2. Delete `web/src/app/api/linkedin-alpha-hook/route.ts` and the empty directory
3. Update `web/src/components/ui/desk-card.tsx` — the fetch URL `/api/linkedin-alpha-hook` stays the same
4. Run `cd web && npm run build` to verify
5. If build still fails, try `rm -rf .next && npm run build`
6. If still failing, try upgrading Next.js to `15.5.19` or downgrading to `15.3.10`

**Success criterion:** `npm run build` completes with `✓ Compiled successfully` and outputs to `.next/`.

---

## Task 2: Update Stale Documentation (P1)

**Files:**
- `docs/FRONTEND_ARCHITECTURE.md` — Currently says "There is no shipped frontend." This is wrong.
- `docs/DESIGN_SYSTEM.md` — Currently says "There is no `web/` tree." This is wrong.

**For `FRONTEND_ARCHITECTURE.md`:**
- Replace the entire file with the actual architecture:
  - Route map: all 16 pages with their purposes
  - Data-fetching strategy: Supabase SSR via `server.ts`, React Query for client
  - Component hierarchy: shell → dashboard → terminal → cards
  - State management: server components for data, client components for interactivity
  - Build/deploy: Vercel, `npm run build`, Biome lint
- Reference `web/src/lib/supabase/queries.ts` for data reads
- Reference `web/src/lib/supabase/database.types.ts` for TypeScript schema

**For `DESIGN_SYSTEM.md`:**
- Remove "no `web/` tree" claim
- Keep the design philosophy, typography, color tokens, copy rules, anti-patterns
- Add a section: "Current Implementation" referencing the actual CSS variables in `globals.css`
- Document the pair accent colors: EUR/USD `#4BA3E3`, USD/JPY `#F5923A`, USD/INR `#D94030`

---

## Task 3: UI Compliance Audit (P2)

Run these checks and fix any violations:

```bash
cd web
# Check 1: No execution advice
grep -rn "position_size\|stop_level" src/components/
# Expected: empty

# Check 2: No educational framing
grep -rni "learning journey\|built to learn\|coursework" src/
# Expected: empty

# Check 3: No em dashes
grep -rn "\\u2014" src/
# Expected: empty

# Check 4: Verify SignalArchitecture weights match pipeline
grep -A20 "SignalArchitecture" src/app/page.tsx
# Compare weights against pipeline/src/regime/composite.py PAIR_COMPOSITE_WEIGHTS
```

**Fix any mismatches:**
- If `SignalArchitecture` shows weights that don't match M.3 (e.g., "~30%" for COT when actual is 0.25), update the copy to reflect the real weights.
- Current M.3 weights: EURUSD(rate=0.45, cot=0.25, vol=0.20, oi=0.05, special=0.05)

---

## Task 4: Add M.5 Diagnostics Visibility (P3)

Create a lightweight internal diagnostics page.

**New file:** `web/src/app/diagnostics/page.tsx`

**Requirements:**
- Read markdown files from `pipeline/reports/accuracy_comparison_*.md`
- Parse the Markdown and render it as HTML (use a simple markdown parser or pre-rendered HTML)
- Display a table of permutation importance results
- Style with the existing design system (monospace for numbers, sans-serif for labels)
- No nav link — access via `/diagnostics` directly
- Add a small link from `/audit` page: "View diagnostic reports →"

**Identity check:** This page displays research artifacts (accuracy comparisons, permutation importance). It does NOT contain execution advice. It is acceptable.

---

## Task 5: OG Images & Meta Audit (P4)

Spot-check that all major pages have proper metadata:

```bash
cd web
grep -l "export const metadata" src/app/*/page.tsx src/app/terminal/*/page.tsx src/app/memo/page.tsx
```

**For any page missing metadata:**
- Add `export const metadata: Metadata = { title: "...", description: "..." }`

**Check OG images:**
```bash
ls src/app/*/opengraph-image.tsx src/app/terminal/*/opengraph-image.tsx
```

**For any page missing OG image:**
- Add a simple `opengraph-image.tsx` using the existing pattern (pair color + regime label)

---

## Verification (Run Before Any Commit)

```bash
# 1. Build MUST pass
cd web && npm run build

# 2. TypeScript MUST pass
cd web && npx tsc --noEmit

# 3. Biome MUST pass
cd web && npx biome check .

# 4. Pipeline tests MUST still pass
cd pipeline && pytest

# 5. Ruff MUST be clean
cd pipeline && ruff check .
```

---

## What NOT to Do

- **Do NOT** add `position_size` or `stop_level` to any UI component
- **Do NOT** use "signals" language in user-facing copy (component names like `SignalCard` are OK)
- **Do NOT** add educational framing ("learning journey", "framework", "built to learn")
- **Do NOT** add SaaS landing tropes (gradient heroes, generic feature grids, neon palettes)
- **Do NOT** add emojis or hashtags to public UI
- **Do NOT** add new data fetchers or API routes that call external services
- **Do NOT** modify pipeline signal logic
- **Do NOT** change thresholds
- **Do NOT** edit immutable tables (`regime_calls`, `validation_log`)
- **Do NOT** expand beyond 3 pairs (EURUSD, USDJPY, USDINR)
- **Do NOT** run `git commit`, `git push`, or any git mutations

---

## Files You Will Create / Modify

| File | Action | Notes |
|------|--------|-------|
| `web/src/pages/api/linkedin-alpha-hook.ts` | **New** | Pages Router API route |
| `web/src/app/api/linkedin-alpha-hook/route.ts` | **Delete** | Remove after move |
| `web/src/components/ui/desk-card.tsx` | **Modify** | Verify fetch URL |
| `docs/FRONTEND_ARCHITECTURE.md` | **Rewrite** | Full architecture doc |
| `docs/DESIGN_SYSTEM.md` | **Modify** | Remove "no frontend" claim |
| `docs/DATA_READS_SPEC.md` | **Audit** | Update if needed |
| `web/src/app/diagnostics/page.tsx` | **New** | M.5 diagnostics page |
| `web/src/app/audit/page.tsx` | **Modify** | Add link to diagnostics |
| `web/src/app/page.tsx` | **Modify** | Fix SignalArchitecture weights if needed |
| Various `opengraph-image.tsx` | **New/Modify** | Add missing OG images |

---

## Success Criteria

| # | Criterion | Command |
|---|-----------|---------|
| 1 | Build passes | `cd web && npm run build` |
| 2 | TypeScript clean | `cd web && npx tsc --noEmit` |
| 3 | Biome clean | `cd web && npx biome check .` |
| 4 | No execution advice in UI | `grep -rn "position_size\|stop_level" web/src/components/` → empty |
| 5 | Docs reflect reality | Read `FRONTEND_ARCHITECTURE.md` and `DESIGN_SYSTEM.md` |
| 6 | Pipeline tests pass | `cd pipeline && pytest` |
| 7 | Ruff clean | `cd pipeline && ruff check .` |
