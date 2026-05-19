# FX Regime Lab — Complete UI/UX Fix Plan
**Date:** 2026-05-15  
**Based on:** Live website audit of 24 screenshots across all pages  
**Pipeline tests:** 234/234 passing  
**Backend code fixes:** Applied (special_signal_label in 3 locations)

---

## What Already Got Fixed (Just Now)

| File | Change |
|------|--------|
| `pipeline/src/backfill/simulation_engine.py:389-393` | `"EURUSD_placeholder"` → `"Bund-BTP + ECB BS"` |
| `pipeline/src/backfill/simulation_engine.py:865-873` | `"frag_risk"/"macro_special"` → `"Bund-BTP + ECB BS"` |
| `pipeline/src/scheduler/orchestrator.py:1484-1506` | Dynamic technical labels → static human-readable labels |
| `pipeline/tests/` | 234/234 still passing ✅ |

**You still need to run this SQL in Supabase Dashboard** (see PROMPT_DB.md).

---

## Session Map

| Session | Tool | What Goes There | Files Modified |
|---------|------|-----------------|----------------|
| **DB Session** | Supabase SQL Editor | SQL fixes for existing rows | `signals` table rows |
| **Backend Session** | Python/pipeline | Any remaining pipeline work | `.py` files in `pipeline/src/` |
| **Frontend Session** | Next.js/TypeScript | All UI/UX improvements | `.tsx`, `.ts`, `.css` in `web/src/` |

---

## Execution Order (Don't Skip)

### Phase A: Data Layer (5 minutes)
1. **DB Session** — Run SQL to fix existing special_signal_label rows

### Phase B: Backend (Already Done + Commit)
2. **Backend Session** — Verify tests pass, commit the label fixes

### Phase C: Frontend — High Priority (2-3 hours)
3. **Frontend Session** — Fix Validation History PRED column
4. **Frontend Session** — Inspector data freshness banner
5. **Frontend Session** — Track Record "[ = ]" → "PENDING"
6. **Frontend Session** — Compare page "+—%" → "N/A"

### Phase D: Frontend — Medium Priority (1 day)
7. **Frontend Session** — Inspector section headers (Rate/Positioning/Vol/Special)
8. **Frontend Session** — Performance page per-pair cards
9. **Frontend Session** — Methodology flowchart SVG
10. **Frontend Session** — Status bar health-linked messaging
11. **Frontend Session** — Calendar tooltip expansion
12. **Frontend Session** — Brief empty state enhancement

### Phase E: Frontend — Low Priority (half day)
13. **Frontend Session** — Keyboard shortcuts
14. **Frontend Session** — Confidence chart reference line
15. **Frontend Session** — Regime timeline square size + tooltips
16. **Frontend Session** — Per-card last updated timestamp

---

## Verification Checklist (I Will Run This After)

- [ ] SQL applied: `SELECT special_signal_label FROM signals WHERE pair='EURUSD' LIMIT 1` returns `"Bund-BTP + ECB BS"`
- [ ] `git diff` shows only intended changes in pipeline + web
- [ ] `pytest` in pipeline: 234 passing
- [ ] `npm run build` in web: zero errors
- [ ] `npm run lint` in web: zero Biome errors
- [ ] Live site: Inspector shows `"Bund-BTP + ECB BS"` not placeholder
- [ ] Live site: Validation History PRED shows actual regime calls
- [ ] Live site: Inspector shows data freshness banner when stale
- [ ] Live site: Track Record shows "PENDING" not "[ = ]"
- [ ] Live site: Compare page shows "N/A" not "+—%"

---

## Prompt Documents

- `PROMPT_DB.md` — Copy into DB session (Supabase SQL Editor)
- `PROMPT_BACKEND.md` — Copy into Backend session (terminal in `pipeline/`)
- `PROMPT_FRONTEND.md` — Copy into Frontend session (terminal in `web/`)

---

*Generated after live audit of fxregimelab.com via WebBridge.*
