# TASK.md — Current Sprint

> **Read `IDENTITY.md` first** — it is the hard constraint.  
> **Read `MASTERPLAN.md` second** — it defines all phases, priorities, and gates.  
> Read `HANDOVER.md` for operator identity, locked decisions, and career strategy.  
> Read `OMEGA_PROTOCOL.md` for the council workflow process.

## Current Phase

**Stream C: Research Presence** (MASTERPLAN.md §4 — Stream C)

## Sprint: C.1–C.3 (Research Output Automation)

| Task | Status | Notes |
|------|--------|-------|
| C.1 Weekly Regime Read auto-generation | 🔲 Not started | CLI command to generate markdown + charts from latest pipeline data. Practitioner tone. No trade recommendations. |
| C.2 LinkedIn Research Card | 🔲 Not started | `/api/linkedin-research-card` → PNG with pair + regime classification. Framed as research, not signal alert. |
| C.3 Substack draft automation | 🔲 Not started | Draft weekly regime read via Substack API. Human approval gate. No buy/sell language. |

## Test & Quality Baseline

| Metric | Current | Target |
|--------|---------|--------|
| pytest | 228/228 ✅ | 228+ |
| TypeScript | 0 errors ✅ | 0 |
| Biome | Clean (new files) ✅ | Clean |
| Build | `npm run build` ✅ | Pass |

## Verification (Run Before Any Merge)

```bash
cd pipeline && pytest
cd web && npx tsc --noEmit
cd web && npm run build
cd web && npx biome check . --changed
```

## Last Deploy

- **Commit:** `bd21220` (frontend defensive normalization)
- **Pipeline:** `f3226ce` (ABORTED status fix)
- **Status:** All green. Vercel auto-deploy active.

---

*Historical completion records are in git history. See previous commits for Rounds 1–5, P0–P4, and v2.0 details.*
