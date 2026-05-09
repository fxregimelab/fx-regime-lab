# FINAL SWEEP PROMPT — Pre-Launch Audit, Polish, Parameter Notebook & Deploy

> **EXECUTE THIS YOURSELF.** This is the final round before the project goes live. Do NOT delegate to Cursor. You MAY use subagents for parallel exploration, but YOU must verify every gate personally.

---

## 1. CONTEXT & GOAL

All 5 rounds of the master plan are functionally complete:
- **P0**: Validation engine wired, immutable ledger enforced, alerting active
- **P1**: Audit trail (`correlation_id` + `write_hash`), data source upgrade (Polygon → AV → yfinance), validation backfill
- **P2**: Performance dashboard (T+5/T+20 track record, equity curve, Brier chart)
- **P3**: Live Signal Dashboard (institutional morning desk)
- **P4**: Terminal polish (pair desk upgrade, mobile layouts, error states)

**Only one feature remains deferred: P1-T2 Parameter Derivation Notebook.**

This final sweep must:
1. **Hunt for bugs** across the entire codebase (pipeline + frontend)
2. **Fix everything found** — no exceptions
3. **Create the parameter notebook**
4. **Polish documentation** (HANDOVER, TASK, README)
5. **Git hygiene** — clean commit history, push to origin
6. **Pass ALL gates** — only then give the green flag

---

## 2. PHASE 1 — BUG HUNT (Systematic Audit)

### 2A. Frontend Bug Hunt

Run these checks and fix every issue found:

```bash
cd web

# 1. TypeScript — zero errors across ENTIRE codebase
npx tsc --noEmit

# 2. Build — zero errors
npm run build

# 3. Biome — check all modified/new files
npx biome check src/app/terminal/ src/app/performance/ src/components/dashboard/ src/components/performance/ src/components/ui/ src/lib/supabase/queries.ts

# 4. Check for console.log / debugger / TODO / FIXME / HACK in frontend
grep -rn "console\.\|debugger\|TODO\|FIXME\|HACK\|XXX" src/ --include="*.ts" --include="*.tsx" | grep -v "node_modules\|error.tsx\|global-error.tsx"
# Note: console.error in error.tsx and global-error.tsx is ACCEPTABLE (error boundaries)

# 5. Check for any remaining `any` types
grep -rn " as any\|: any\|;" src/ --include="*.ts" --include="*.tsx" | grep -v "node_modules\|maybeSingle\|many"

# 6. Check for unused imports in all new/modified files
npx biome check --max-diagnostics=200 src/app/terminal/ src/app/performance/ src/components/dashboard/ src/components/performance/ src/components/ui/ src/lib/supabase/queries.ts 2>&1 | grep "unused"

# 7. Check all links are valid (no 404s)
# Verify these routes exist and build:
# /, /terminal, /terminal/fx-regime, /terminal/fx-regime/[pair], /performance, /methodology, /about, /brief
```

**Known issues to verify are fixed:**
- [ ] No `@/lib/mockData` imports remain (should all use `@/lib/constants`)
- [ ] No `signal_composite` selected from `signals` table
- [ ] `SupabaseClient` is properly typed (not `any`)
- [ ] Spot sparkline has `overflow-x-auto` wrapper
- [ ] Empty state renders when `regime_calls` is empty
- [ ] Error boundary catches pair desk crashes

### 2B. Pipeline Bug Hunt

```bash
cd pipeline

# 1. All tests pass
pytest

# 2. Ruff clean
ruff check .

# 3. Mypy check (if available)
mypy src/ --ignore-missing-imports 2>/dev/null || echo "mypy not installed, skipping"

# 4. Check for TODO / FIXME / HACK / console prints in pipeline
grep -rn "TODO\|FIXME\|HACK\|XXX\|print(" src/ --include="*.py" | grep -v "__pycache__\|legacy\|\.pyc" | grep -v "logger\."
# Note: logger.* calls are acceptable; bare print() is NOT

# 5. Verify all env vars referenced in code are in .env.example
grep -roh "os\.environ\.get(\"[^\"]*\"" src/ --include="*.py" | sed 's/os.environ.get("//;s/"$//' | sort -u
# Compare against .env.example — every env var must be documented

# 6. Check for hardcoded secrets
grep -rn "sk-\|pk_\|Bearer \|api_key\|password\|secret" src/ --include="*.py" | grep -v "__pycache__\|legacy"
```

### 2C. Schema & Data Integrity Audit

```bash
# Verify database.types.ts matches sql/schema.sql for these tables:
# - regime_calls (all columns)
# - signals (all columns)
# - validation_log (all columns)
# - validation_stats (all columns)
# - historical_prices (all columns)
# - macro_events (all columns)
# - brief_log (all columns)
# - pipeline_errors (all columns)
# - health_checks (all columns)

grep -A30 "CREATE TABLE IF NOT EXISTS regime_calls" sql/schema.sql
grep -A30 '"regime_calls"' web/src/lib/supabase/database.types.ts
# Repeat for each table — every column in schema.sql must exist in database.types.ts
```

**Fix any mismatch found.**

### 2D. Cross-File Consistency Audit

- [ ] `PAIRS` array in `web/src/lib/constants.ts` has exactly 3 pairs: EURUSD, USDJPY, USDINR
- [ ] `PAIR_COLORS` matches the colors used in the UI
- [ ] `urlSlug` values match the dynamic route segments (`eurusd`, `usdjpy`, `usdinr`)
- [ ] Pipeline `PAIRS` in `pipeline/src/models/` or constants matches frontend pairs
- [ ] `.env.example` documents ALL environment variables used in pipeline AND web
- [ ] `docs/SIGNAL_DEFINITIONS.md` is still accurate (thresholds, weights, formulas)
- [ ] `docs/DATABASE_SCHEMA.md` is still accurate

---

## 3. PHASE 2 — BUG FIXES

For every issue found in Phase 1, create a fix. **Do NOT skip any issue.**

Priority order:
1. **Crash bugs** (null pointer, type errors, missing imports)
2. **Logic bugs** (wrong calculations, backwards logic, data mismatches)
3. **Security issues** (hardcoded secrets, exposed keys, missing RLS)
4. **Performance issues** (N+1 queries, unbounded limits)
5. **Style issues** (biome errors, unused imports, formatting)
6. **Tech debt** (mockData imports, any types, stale comments)

After every fix, re-run the relevant gate.

---

## 4. PHASE 3 — Parameter Derivation Notebook (P1-T2)

Create `pipeline/notebooks/parameter_derivation.ipynb` documenting every magic number in the system.

### Required Sections

**1. Layer 1 — Regime Gate Thresholds**
- Rate differential z-score threshold (±0.5)
- CB divergence threshold
- Growth divergence threshold
- Source: Academic literature + walk-forward calibration

**2. Layer 2 — Directional Signal Thresholds**
- COT percentile window (3-year rolling = 156 weeks)
- COT extreme thresholds (>85, <15)
- Crowding penalty ramp (how it scales with percentile distance from 50)
- Conviction multiplier formula
- Source: CFTC guidance + COT report methodology

**3. Layer 3 — Execution Thresholds**
- Realized vol rank threshold (RVOL > 8 = elevated)
- IV premium threshold (IV > RVOL)
- Position sizing formula (inverse vol scaling)
- Stop level formula (Marcus invalidation = 50bps)
- Source: Risk management literature (Alexandre Marcus, JPMorgan quant)

**4. Validation Metrics**
- Brier score formula
- 5bps dead-band justification
- Sharpe-like ratio formula
- Source: Brier (1950), standard financial metrics

**5. Data Source Fallback Chain**
- Why Polygon.io → Alpha Vantage → yfinance
- Rate limits and reliability data
- Source: API documentation + empirical testing

### Notebook Requirements
- [ ] Every threshold has a **literature citation** or **walk-forward calibration evidence**
- [ ] Every formula is written in LaTeX (MathJax)
- [ ] Include small Python cells showing the calibration on historical data
- [ ] Export to markdown: `pipeline/notebooks/parameter_derivation.md`
- [ ] The notebook must run without errors (self-contained or with `pip install -e pipeline/`)

---

## 5. PHASE 4 — Documentation Polish

### Update `TASK.md`
- [ ] Mark P1-T2 as COMPLETE
- [ ] Add a "Project Status: PRODUCTION READY" section
- [ ] Update the test & quality summary with final numbers

### Update `HANDOVER.md`
- [ ] Add a "What's New in P2-P4" section
- [ ] Update the file tree / navigation guide
- [ ] Verify all links work

### Update `README.md` (root level)
- [ ] Add a one-paragraph project description for visitors
- [ ] Link to the live site, Substack, and methodology page
- [ ] Add build badges (tests passing, build passing)

### Update `AGENTS.md` (root level)
- [ ] Verify the technology stack table is accurate
- [ ] Verify the repository structure matches reality
- [ ] Add any new conventions established in P2-P4

### Clean up prompt files
- [ ] Move `P0_COMPLETE_PROMPT.md`, `P1_COMPLETE_PROMPT.md`, `P1_T1_T4_PROMPT.md`, `P2_PROMPT.md`, `P3_PROMPT.md` to `_docs/archive/prompts/`
- [ ] Keep `P4_PROMPT.md` and `FINAL_SWEEP_PROMPT.md` in root for now (or archive them too)

---

## 6. PHASE 5 — Git Hygiene & Deploy

### 6A. Review what's going to be committed

```bash
git status
```

**DO NOT commit these (add to .gitignore if needed):**
- `.agent/` — agent metadata (already tracked, but verify no sensitive data)
- `.cursor/` — cursor rules (already tracked)
- `.kimi/` — kimi metadata (already tracked)
- `P*_PROMPT.md` files — internal working documents
- `supabase/.temp/` — already in .gitignore
- `.env.local`, `.env` — already in .gitignore
- `node_modules/`, `.next/` — already in .gitignore
- `__pycache__/`, `*.pyc` — already in .gitignore

**DO commit these:**
- All `web/src/` changes (P2-P4 frontend)
- All `pipeline/src/` changes (P0-P1 pipeline)
- All `pipeline/tests/` changes
- All `sql/schema.sql` changes
- All `supabase/migrations/` changes
- Updated `.env.example`
- Updated `docs/` files
- Updated `TASK.md`, `HANDOVER.md`, `README.md`, `AGENTS.md`
- New `pipeline/notebooks/`

### 6B. Commit Strategy

Make **ONE clean commit** (or a few logical commits) with a comprehensive message:

```bash
# Stage only what should be committed
git add web/src/ pipeline/src/ pipeline/tests/ sql/ supabase/migrations/ docs/ .env.example TASK.md HANDOVER.md README.md AGENTS.md pipeline/notebooks/

# Check the staged diff
git diff --cached --stat

# Commit
git commit -m "feat(terminal): P2-P4 institutional dashboard + pair desk + mobile polish

Frontend:
- /performance: T+5/T+20 track record, equity curve, Brier chart
- /terminal: Live Signal Dashboard (system status, cross-asset, alerts, macro calendar, signal cards, daily brief)
- /terminal/fx-regime/[pair]: Pair desk with spot sparkline, validation history, execution panel
- Mobile responsive layouts across all pages
- Error boundaries, empty states, loading skeletons
- OpenGraph images for social sharing

Pipeline:
- Polygon.io → Alpha Vantage → yfinance fallback chain
- Audit trail: correlation_id + write_hash on regime_calls
- validation_stats aggregate table
- Historical price backfill
- Parameter derivation notebook

Quality:
- 218/218 pytest passing
- npm build zero errors
- tsc --noEmit zero errors
- biome clean on all new files"
```

### 6C. Push to Origin

```bash
git push origin main
```

Verify Vercel auto-deploys successfully:
- Check the Vercel dashboard for the build status
- The build should be green

---

## 7. PHASE 6 — Final Verification Gates

These are the FINAL gates. **Every single one must pass before you declare victory.**

| # | Gate | Command | Must Pass |
|---|------|---------|-----------|
| 1 | Frontend build | `cd web && npm run build` | Zero errors |
| 2 | TypeScript | `cd web && npx tsc --noEmit` | Zero errors |
| 3 | Frontend lint | `cd web && npx biome check src/app/terminal/ src/app/performance/ src/components/dashboard/ src/components/performance/ src/components/ui/ src/lib/supabase/queries.ts` | Clean |
| 4 | Pipeline tests | `cd pipeline && pytest` | 218/218 |
| 5 | Pipeline lint | `cd pipeline && ruff check .` | Clean |
| 6 | No console.logs | `grep -rn "console\.\|debugger" web/src/ --include="*.ts" --include="*.tsx" \| grep -v "error.tsx\|global-error.tsx"` | Empty |
| 7 | No any types | `grep -rn " as any\|: any\|any;" web/src/ --include="*.ts" --include="*.tsx" \| grep -v "maybeSingle\|many"` | Empty |
| 8 | No mockData imports | `grep -rn "@/lib/mockData" web/src/` | Empty |
| 9 | Git push | `git log --oneline -1` | Commit is on origin/main |
| 10 | Vercel deploy | Check Vercel dashboard | Build green |

---

## 8. POST-DEPLOY CHECKLIST

After pushing and Vercel is green, verify these URLs manually:

- [ ] `https://fxregimelab.com/` — Landing page loads
- [ ] `https://fxregimelab.com/terminal` — Morning desk loads with data
- [ ] `https://fxregimelab.com/terminal/fx-regime/eurusd` — Pair desk loads
- [ ] `https://fxregimelab.com/performance` — Performance dashboard loads
- [ ] `https://fxregimelab.com/methodology` — Methodology page loads
- [ ] `https://fxregimelab.com/about` — About page loads
- [ ] Mobile view — No horizontal overflow on iPhone SE width (375px)

---

## 9. LOCKED DECISIONS (Final Reminder)

1. ✅ 3-pair lock: Only EURUSD, USDJPY, USDINR
2. ✅ Swiss Monochrome: Pure black, sharp borders, tabular-nums, no rounded corners
3. ✅ Type safety: No `any` in new code
4. ✅ Immutable ledger: Never modify regime_calls or validation_log
5. ✅ Build gate: `npm run build` must pass
6. ✅ Read-only frontend: No DB writes from frontend
7. ✅ No hardcoded secrets in code

---

**When ALL 10 gates pass and ALL 7 post-deploy checks are green, give yourself the FINAL GREEN FLAG.**

*Prompt version: FINAL-2026-05-06*
