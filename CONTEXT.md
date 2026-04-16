# FX Regime Lab — context snapshot (read this first)

**Extended narrative:** `contaxt files/CONTEXT.md` (career, philosophy, deep product history). This file stays short for agents.

---

## Project name & purpose

**FX Regime Lab** is a daily **G10 FX regime** research pipeline: public market data → merged signals → text + interactive HTML morning brief → optional deploy to GitHub Pages / Cloudflare. **Not investment advice** — research and learning only.

---

## Tech stack

- **Python 3.9+** — pipeline scripts, `pandas` / `numpy` / `scipy`, `requests`, `supabase-py`, `yfinance`
- **Data:** FRED, CFTC COT, yfinance, CME (where wired); **Supabase** first for persistent signal writes, CSV fallback
- **Outputs:** `morning_brief.py` (text), `create_html_brief.py` + Plotly → `briefs/`; `charts/` tracked for Pages
- **Site:** `site/` static shell (fxregimelab.com on Cloudflare Pages); `deploy.py` / `scripts/publish_brief_for_site.py` as in `AGENTS.md`
- **CI:** GitHub Actions (e.g. `FRED_API_KEY` and other secrets as documented); no hardcoded keys in repo

---

## Folder map

| Path | Role |
|------|------|
| `run.py` | Canonical orchestrator; `STEPS` order is fixed — extend only with care |
| `pipeline.py` | FX/yields ETL + merge → `data/` |
| `*_pipeline.py` | Signal layers (COT, INR, vol, OI, RR, macro, etc.) |
| `core/` | `paths.py`, Supabase helpers, shared utilities |
| `config.py` | Shared constants |
| `morning_brief.py` / `create_html_brief.py` / `create_charts_plotly.py` | Brief + charts |
| `site/` | Public dashboard + brief mirror for Cloudflare |
| `charts/` | Generated HTML fragments (often tracked for GitHub Pages) |
| `scripts/` | Publish, dev checks, backfill |
| `docs/` | Long-form planning and references (committed project docs) |
| `_docs/` | **Obsidian** notes only (ADRs, tasks, research) — agents ignore unless user asks |
| `contaxt files/` | `CONTEXT.md` (long), `PLAN.md`, `CURSOR_RULES.md` |

---

## Current sprint / active task

**Phases 1-4 complete — terminal redesign live. Next: Phase 5 nav rollout + Phase 6 final QA**

---

## Key decisions made (ADR summary)

- **Orchestration:** Single entry `run.py` with explicit `STEPS`; no ad-hoc reordering of the pipeline sequence.
- **Persistence:** Signal tables: upsert `on_conflict='date,pair'`; never plain insert-only for daily signals.
- **Public UI:** `site/` follows UI Prompt v2 (light editorial); pipeline/brief Plotly channel may remain dark-themed until restyled.
- **No ML / FinBERT / social sentiment** unless explicitly instructed.
- **New ADRs:** add under `_docs/architecture/` and link from `_docs/_index.md` when central.

---

## Known issues / blockers

*(Update as needed.)* — e.g. CI secrets, API limits, data gaps: ______

---

## What NOT to touch

- **`run.py` `STEPS` order** — only extend per `AGENTS.md` / explicit instruction; no duplicate orchestrators for the same job
- **`deploy.py` / path rewrites** — `index.html`, `charts/`, `static/` assumptions break Pages if changed blindly
- **Tracked `charts/`** — intentional for GitHub Pages unless project direction changes
- **`_docs/**`** — user’s Obsidian vault; do not edit unless explicitly asked

**Canonical map:** `AGENTS.md`
