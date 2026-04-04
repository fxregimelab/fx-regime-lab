# Implementation plan — Phase 0 (executable order)

Use this as the default Cursor/agents task sequence. **Spec detail:** `contaxt files/PLAN.md` Phase 0.

## Track A — Phase 0A (can parallelize where noted)

1. **Cloudflare:** Create/update Pages project; set production branch; configure **`/newsletter` → 301 → fxregimelab.substack.com**.
2. **DNS:** Point fxregimelab.com (and www) to Pages; verify SSL; verify email/MX.
3. **Repo `site/`:** Add static HTML/CSS/JS (vanilla) for `/`, `/dashboard`, `/brief`, `/performance`, `/about` with **Bloomberg-style** tokens from PLAN 0A.
4. **Landing:** 3 regime cards — **static placeholder** data only; correct pair colors and typography (**Inter** + **JetBrains Mono** for numbers).
5. **Dashboard page:** Status board layout + load **`pipeline_status.json`** via fetch (same origin once file is deployed).
6. **`deploy.py` + CI:** After successful pipeline, write **`pipeline_status.json`** with `last_run_utc` (ISO) to a path **committed or deployed** so Pages can read it (e.g. copy into `site/` before Pages build, or push to `static/` and sync — choose one approach and document in AGENTS).
7. **Brief page:** Link or iframe to current GitHub Pages brief URL until `/brief` hosts artifacts directly.
8. **Verify 0A:** All routes, mobile, redirect, real timestamp on dashboard.

## Track B — Phase 0B (start only after 0A checklist complete)

9. **Supabase:** New project; run DDL, indexes, RLS from PLAN (include `pipeline_errors`).
10. **Secrets:** GitHub repo secrets + `daily_brief.yml` `.env` injection.
11. **Python:** `requirements.txt` + lazy `core/supabase_client.py` + `core/signal_write.py`.
12. **Dual-write:** Wire `pipeline.py`, `cot_pipeline.py`, `inr_pipeline.py` and `persist_regime_call` (+ `brief_log` stub).
13. **Pages env:** Add `SUPABASE_URL` + `SUPABASE_ANON_KEY` to Cloudflare.
14. **Frontend:** Replace placeholders with Supabase JS reads (explicit columns); keep RLS-safe queries only.
15. **Verify 0B:** PLAN combined exit criteria + RLS test.

## After Phase 0

16. **Phase 1:** `vol` → `oi` → `rr` in `run.py`; CME + yfinance per PLAN.

## Files you will likely touch (first pass)

- `site/**/*` (new)
- `deploy.py`, `.github/workflows/daily_brief.yml`
- `core/supabase_client.py`, `core/signal_write.py` (new)
- `pipeline.py`, `cot_pipeline.py`, `inr_pipeline.py`, `morning_brief.py` / `create_html_brief.py` (dual-write + regime persist)
- `requirements.txt`
