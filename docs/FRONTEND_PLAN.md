# Frontend Plan — FX Regime Lab

> **Scope:** Fix build, update stale docs, audit UI compliance, and prepare for production deploy.  
> **Stack:** Next.js 15.3.9, React 19, Tailwind CSS v4, TypeScript 5, Supabase SSR, Biome.  
> **Identity:** Read `IDENTITY.md` and `AGENTS.md` first. Hard rules apply.  
> **Last updated:** 2026-05-21

---

## 1. Current State

### 1.1 What Exists (and Works in Dev)

The frontend is a **fully built Next.js App Router application** with 16 pages and 68 components. TypeScript compiles cleanly (`npx tsc --noEmit` passes).

| Page | Route | Status |
|------|-------|--------|
| Home (Landing) | `/` | ✅ Live design, hero, validation ticker, live snapshot cards, manifesto, signal architecture, validation trust |
| Terminal (Dashboard) | `/terminal` | ✅ System status, cross-asset matrix, alert strip, macro calendar, 3-pair signal cards, daily brief |
| Pair Detail | `/terminal/fx-regime/[pair]` | ✅ Per-pair regime deep-dive with historical chart |
| Performance | `/performance` | ✅ Accuracy stats, pair breakdown, regime breakdown |
| Methodology | `/methodology` | ✅ KaTeX formulas, 3-layer framework docs, data sources |
| Brief | `/brief` | ✅ Daily systemic brief panel |
| Audit | `/audit` | ✅ Pipeline health dashboard, accuracy alerts |
| Calendar | `/calendar` | ✅ Macro events calendar |
| Memo | `/memo` | ✅ Research memo archive |
| Memo Detail | `/memo/[date]` | ✅ Individual memo page |
| About | `/about` | ✅ Project info |

**Key components:**
- `SignalCard` — per-pair regime card (spot, composite, confidence, regime history sparkline)
- `CrossAssetMatrix` — VIX/DXY/oil/gold/copper/STOXX snapshot
- `DailyBriefPanel` — AI-generated daily narrative
- `AlertStrip` — regime change / stress alerts
- `MacroCalendarStrip` — economic calendar
- `ValidationTable` — T+5 / T+20 outcome table
- `SystemStatusBar` — DQS, stress level, last run timestamp

### 1.2 The Build Blocker

`npm run build` fails with:

```
Error: EISDIR: illegal operation on a directory, readlink
  'D:\...\web\src\app\api\linkedin-alpha-hook\route.ts'
```

This is a **Windows-specific Next.js 15.5.18 / webpack issue** with App Router route handlers. The `next.config.ts` already has `config.resolve.symlinks = false` (a known workaround), but the error persists.

**WSL alternative:** Running `npm run build` inside WSL fails with a different error:
```
Error: Cannot find module '../lightningcss.linux-x64-gnu.node'
```
This is because `node_modules` was installed on Windows (which installs `lightningcss.win32-x64-msvc.node`), and WSL needs the Linux binary. Reinstalling `node_modules` inside WSL would fix this, but the user primarily works on Windows.

### 1.3 Stale Documentation

| Doc | Claim | Reality |
|-----|-------|---------|
| `docs/FRONTEND_ARCHITECTURE.md` | "There is no shipped frontend" | Full Next.js app exists |
| `docs/DESIGN_SYSTEM.md` | "There is no `web/` tree" | `web/` has 104+ source files |
| `docs/DATA_READS_SPEC.md` | References deleted queries | Needs audit |

### 1.4 Identity Compliance

| Rule | Status | Notes |
|------|--------|-------|
| No `position_size` in public UI | ✅ Clean | grep finds zero matches in `src/components/` |
| No `stop_level` in public UI | ✅ Clean | grep finds zero matches in `src/components/` |
| No "signals" language | ⚠️ Check | `SignalCard`, `SignalArchitecture` use "signal" — verify this is acceptable per IDENTITY |
| No educational framing | ✅ Clean | Copy is practitioner-to-practitioner |
| No execution advice | ✅ Clean | `entry_timing` (ENTER/WAIT) is present but not explicit sizing/stops |

---

## 2. Goals (What We Want)

### 2.1 P0 — Build Must Pass

**The frontend is not deployable until `npm run build` succeeds.** This is the only P0 task.

- [ ] **Fix Windows build** — `npm run build` must complete without errors on Windows
- [ ] **Verify WSL build** — `npm run build` must also work inside WSL (for CI/CD parity)
- [ ] **TypeScript clean** — `npx tsc --noEmit` must pass (already ✅)
- [ ] **Biome clean** — `npx biome check .` must pass

### 2.2 P1 — Documentation Accuracy

- [ ] **Update `docs/FRONTEND_ARCHITECTURE.md`** — Replace "no shipped frontend" with actual route map, component layout, data-fetching strategy
- [ ] **Update `docs/DESIGN_SYSTEM.md`** — Remove "no `web/` tree" claim; document the actual design tokens, typography, color system in use
- [ ] **Update `docs/DATA_READS_SPEC.md`** — Audit and update to match current `queries.ts`

### 2.3 P2 — UI Compliance Audit

- [ ] **Audit `SignalCard`** — Verify `entry_timing` display is acceptable (ENTER/WAIT is directional guidance, not explicit sizing)
- [ ] **Audit all pages** — Search for any "learning journey", "framework", or educational framing
- [ ] **Audit copy** — Ensure no em dashes (`U+2014`), no emojis, no hashtags
- [ ] **Audit `SignalArchitecture`** section — The weights shown (~40%, ~30%, etc.) should match the current M.3 pipeline weights (EURUSD: rate=0.45, cot=0.25, vol=0.20, oi=0.05, special=0.05)

### 2.4 P3 — M.5 Diagnostics Visibility

The M.5 diagnostic tools (`permutation_importance.py`, `accuracy_report.py`) generate JSON and Markdown reports. These are currently only accessible via CLI.

- [ ] **Add `/diagnostics` page** (internal-only, no nav link) — Display latest accuracy comparison report
- [ ] **Add permutation importance table** — Read from `pipeline/reports/` or run diagnostics on demand
- [ ] **Add v1 vs v2 accuracy chart** — Simple bar chart showing T+5/T+20 accuracy delta

> **Identity check:** Diagnostics are research artifacts, not execution advice. OK to display.

### 2.5 P4 — Polish & Performance

- [ ] **OG images** — Verify all pages have `opengraph-image.tsx`
- [ ] **Meta descriptions** — Verify all pages have `metadata` export
- [ ] **Mobile responsiveness** — Spot-check SignalCard and Terminal grid on mobile
- [ ] **Loading states** — Add skeleton loaders for `SignalCard` and `DailyBriefPanel`

---

## 3. Constraints (What We DON'T Want)

### 3.1 Hard Constraints (from IDENTITY.md + AGENTS.md)

1. **No execution advice in public UI** — `position_size` and `stop_level` must NEVER appear in any component visible to anonymous users. They are DB-internal only.
2. **No "signals" language in user-facing copy** — The word "signal" is acceptable in component names (`SignalCard`, `SignalArchitecture`) but user-visible copy should say "classifications" or "regime calls". The current `SignalArchitecture` section on the home page uses "signal families" — this is acceptable as it describes the methodology, not a trading recommendation.
3. **No educational framing** — No "Built to learn", "framework", "learning journey" tone. Write as a practitioner describing live work.
4. **No SaaS landing tropes** — No gradient hero, generic three-column feature grid with stock icons, neon blue/purple "AI dashboard" palettes, heavy glassmorphism.
5. **No Unicode em dashes** (`U+2014`) in user-visible strings. Use hyphens or sentence breaks.
6. **No emojis or hashtags** in public UI.
7. **3-pair lock** — Only EURUSD, USDJPY, USDINR. No pair expansion UI.

### 3.2 Technical Constraints

1. **No new data fetchers** — The frontend reads from Supabase via `queries.ts` and `server.ts`. Do not add new API routes that fetch external data.
2. **No pipeline signal logic changes** — Frontend is read-only from the pipeline's perspective.
3. **No threshold changes** — Do not modify any composite, confidence, or regime thresholds in the frontend.
4. **No immutable table edits** — `regime_calls` and `validation_log` are append-only.
5. **No Git mutations** unless explicitly asked.

### 3.3 Design Constraints

1. **Swiss Monochrome** — Inter (UI), Fraunces italic (regime labels only), JetBrains Mono (numbers).
2. **Two-surface rule** — Light shell (`#f5f5f0`) for public pages, dark terminal (`#0a0a0a`) for engine room.
3. **Accent discipline** — Amber `#e8a045` for highest conviction emphasis ONLY.
4. **Greyscale discipline** — Regime badges use semantic colors (emerald/rose/amber) for signal meaning. Avoid neon palettes.
5. **Pair accents** — EUR/USD `#4BA3E3`, USD/JPY `#F5923A`, USD/INR `#D94030`.

---

## 4. Task Breakdown

### Task 1: Fix the Build (P0)

**Problem:** `npm run build` fails on Windows with EISDIR on `api/linkedin-alpha-hook/route.ts`.

**Root cause:** Next.js 15 App Router route handler on Windows triggers a webpack `readlink` call that fails because the path is treated as a directory.

**Options:**

| Option | Description | Risk | Effort |
|--------|-------------|------|--------|
| A | Move `route.ts` to Pages Router (`pages/api/linkedin-alpha-hook.ts`) | Low — only one reference to update in `desk-card.tsx` | 10 min |
| B | Delete the API route and make LinkedIn share client-side only | Low — loses server-side truncation | 15 min |
| C | Upgrade/downgrade Next.js patch version | Medium — might introduce other issues | 30 min |
| D | Rename directory to avoid `\r` escape sequence collision | Medium — need to update reference | 10 min |

**Recommended:** **Option A** — Move to Pages Router. This is the cleanest, most reliable fix for Windows. Next.js Pages Router API routes do not trigger the same `readlink` path.

**Steps:**
1. Create `src/pages/api/linkedin-alpha-hook.ts` with the same POST handler logic
2. Delete `src/app/api/linkedin-alpha-hook/route.ts`
3. Update `src/components/ui/desk-card.tsx` reference from `/api/linkedin-alpha-hook` to `/api/linkedin-alpha-hook` (URL path stays the same)
4. Run `npm run build` to verify

### Task 2: Update Stale Docs (P1)

**Files to update:**
- `docs/FRONTEND_ARCHITECTURE.md` — Full rewrite
- `docs/DESIGN_SYSTEM.md` — Remove "no frontend" claim, add actual token reference
- `docs/DATA_READS_SPEC.md` — Audit against current `queries.ts`

**Content for `FRONTEND_ARCHITECTURE.md`:**
- Route map (all 16 pages)
- Data-fetching strategy (Supabase SSR via `server.ts`, React Query for client)
- Component hierarchy (shell → dashboard → terminal → cards)
- State management (server components for data, client components for interactivity)
- Build/deploy pipeline (Vercel, `npm run build`, Biome lint)

### Task 3: UI Compliance Audit (P2)

**Checklist:**
- [ ] Run `grep -rn "position_size\|stop_level" src/components/` → must be empty
- [ ] Run `grep -rn "learning journey\|framework\|built to learn" src/` → must be empty
- [ ] Run `grep -rn "\\u2014" src/` → must be empty (no em dashes)
- [ ] Verify `SignalArchitecture` weights match `PAIR_COMPOSITE_WEIGHTS` in `pipeline/src/regime/composite.py`
- [ ] Verify no emoji in user-visible strings (except the ticker separator `◆` which is decorative)

### Task 4: M.5 Diagnostics Page (P3)

**New file:** `src/app/diagnostics/page.tsx` (internal research page, no nav link)

**Features:**
- Read `pipeline/reports/accuracy_comparison_*.md` files
- Parse and display as HTML table
- Show permutation importance bar chart (lightweight)
- Add link from `/audit` page for internal access

**Identity check:** This is a research artifact page. No execution advice. OK.

### Task 5: OG Images & Meta (P4)

**Spot-check:**
- [ ] `/` has `metadata` export
- [ ] `/terminal` has `metadata` export
- [ ] `/terminal/fx-regime/[pair]` has `metadata` and `opengraph-image.tsx`
- [ ] `/performance` has `metadata` export
- [ ] `/methodology` has `metadata` export

---

## 5. Verification Commands

```bash
# 1. TypeScript
cd web && npx tsc --noEmit

# 2. Build (the critical check)
cd web && npm run build

# 3. Lint
cd web && npx biome check .

# 4. Pipeline tests (ensure no regression)
cd pipeline && pytest

# 5. Ruff
cd pipeline && ruff check .
```

---

## 6. Success Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | `npm run build` passes on Windows | Run `cd web && npm run build` |
| 2 | `npm run build` passes in WSL | Run in WSL after `npm install` |
| 3 | TypeScript compiles | `npx tsc --noEmit` |
| 4 | Biome is clean | `npx biome check .` |
| 5 | No `position_size`/`stop_level` in UI | `grep -rn "position_size\|stop_level" src/components/` |
| 6 | Docs reflect reality | Read `FRONTEND_ARCHITECTURE.md` and `DESIGN_SYSTEM.md` |
| 7 | Pipeline tests still pass | `cd pipeline && pytest` |

---

## 7. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pages Router move breaks LinkedIn share | Low | Medium | Test the share button after move |
| Next.js upgrade introduces breaking changes | Medium | High | Pin exact version, test thoroughly |
| Biome lint failures on existing code | Medium | Low | Run `biome check --write` to auto-fix |
| WSL `npm install` takes long / fails | Medium | Medium | Use `npm ci` or cache node_modules |

---

## 8. Related Docs

- `IDENTITY.md` — Hard constraints, tone, pair lock
- `AGENTS.md` — Agent workflow, verification commands
- `docs/DESIGN_SYSTEM.md` — Design tokens (needs update)
- `docs/DB_STATUS.md` — DB schema reference
- `docs/DB_AUDIT_STRATEGY.md` — Migration history
- `web/src/lib/supabase/queries.ts` — All data reads
- `web/src/lib/supabase/database.types.ts` — TypeScript schema
