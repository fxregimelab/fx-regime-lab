# FX Regime Lab — execution roadmap

Sequenced map aligned with **`contaxt files/PLAN.md`**, **`contaxt files/CONTEXT.md`**, **`contaxt files/CURSOR_RULES.md`**, and [AGENTS.md](../AGENTS.md). **Orchestration truth:** `run.py` — `fx → cot → inr → vol → oi → rr → merge → text → macro → ai → substack → html → validate → deploy` (no `create_dashboards.py`). Details: [PIPELINE_AUDIT_AND_OPERATIONS.md](./PIPELINE_AUDIT_AND_OPERATIONS.md).

**Conflict order:** CURSOR_RULES → PLAN → CONTEXT → AGENTS.md.

## Infrastructure (locked)

| Component | Decision |
|-----------|----------|
| Domain | **fxregimelab.com**; email **shreyash@fxregimelab.com** |
| Public UI | **Cloudflare Pages** — **UI + branding (Phase 0A) ship before Supabase Python** |
| Database | **Supabase** PostgreSQL |
| Pipeline | **GitHub Actions** — **`0 23 * * *`** UTC daily |
| Newsletter | **`/newsletter`** → 301 → **fxregimelab.substack.com** |
| Python Supabase client | **Lazy init** — never raise on import; skip writes if keys missing |

**Not Vercel** for primary public surface; **not Firebase** for this architecture.

## Phase 0 split

| Subphase | What | When |
|----------|------|------|
| **0A** | Full site shell on fxregimelab.com: `/`, `/dashboard`, `/brief`, `/performance`, `/about`, `/newsletter`; Bloomberg dark UI; **static placeholders**; **`pipeline_status.json`** for real last-run time on dashboard | **First** — next ~48h target |
| **0B** | Supabase DDL + RLS + `pipeline_errors`; pin `supabase`; dual-write; GHA secrets; **live** landing + dashboard reads | After **0A** verified |

**Phase 1** blocked until **combined 0A + 0B exit criteria** in PLAN.md pass.

## Later phases (summary)

- **Phase 1** — `vol_pipeline.py`, `oi_pipeline.py`, `rr_pipeline.py`; panels go live on deploy.
- **Phase 2** — `validation_log` parallel; mandatory brief accuracy line; dashboard accuracy panel.
- **Phase 3** — Full panels; locked brief; `/about` methodology; GitHub Pages retired from dashboard role after stability window.
- **Phases 4–9** — Paper `/performance`, backtest, GBP, FinBERT (gated), cross-asset, product layer — per PLAN.md.

## Principles

- **Build-to-explain** — every module: ~2 min verbal without code.
- **Session discipline** — state: build target, Supabase tables, `run.py` step, **fxregimelab.com path**, signal rationale.

**Checklists:** [PHASE0_CHECKLIST.md](PHASE0_CHECKLIST.md) · **implementation order:** [IMPLEMENTATION_PLAN_PHASE0.md](IMPLEMENTATION_PLAN_PHASE0.md) · **docs index:** [README.md](README.md).
