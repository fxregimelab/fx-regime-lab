# Phase 0 Checklist (0A + 0B)

Full narrative: **`contaxt files/PLAN.md`** Phase 0. Exit criteria must pass before **Phase 1**.

---

## Phase 0A — UI shell (before Supabase code)

### DNS and domain

- [ ] fxregimelab.com → Cloudflare Pages with SSL
- [ ] www policy explicit (redirect OK)
- [ ] shreyash@fxregimelab.com OK after DNS (MX preserved if nameservers moved)

### Cloudflare Pages — site

- [ ] Repo connected; build/root points at **`site/`** (or chosen static output)
- [ ] **`/newsletter`** — 301 redirect to `https://fxregimelab.substack.com`
- [ ] **`/`** — header (wordmark + nav: Dashboard · Brief · Performance · About · Newsletter), hero (no SaaS “Get Started”), **3 static regime cards** (Bloomberg tokens from PLAN)
- [ ] **`/dashboard`** — designed “integration status” UI; **last pipeline run** from **`pipeline_status.json`** (written by CI / `deploy.py`) — real timestamp
- [ ] **`/brief`** — embed, iframe, or link to current brief (GitHub Pages URL OK initially)
- [ ] **`/performance`** — styled coming soon + CTA to `/newsletter`
- [ ] **`/about`** — styled coming soon blurb
- [ ] Mobile responsive sitewide

### Pipeline artifact for dashboard

- [ ] `deploy.py` (or CI step) writes **`pipeline_status.json`** (path agreed in repo, e.g. under `static/` or `site/` for Pages) with ISO **last_run_utc** (and optional step status later)

---

## Phase 0B — Supabase + live UI

### Supabase

- [ ] Project; DDL + indexes + RLS from PLAN; **`pipeline_errors`**
- [ ] Anon SELECT policies; no public read on `pipeline_errors`

### Python

- [ ] `supabase` pinned in `requirements.txt`
- [ ] Lazy client — **no import-time raise** if keys missing
- [ ] `core/signal_write.py` — upsert, batch, `pipeline_errors`, CSV fallback

### Dual-write

- [ ] `pipeline.py`, `cot_pipeline.py`, `inr_pipeline.py` → `signals`
- [ ] `regime_calls` + `brief_log` stub from brief path

### GitHub Actions

- [ ] Secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, optional `POLYGON_KEY`, `TWELVE_DATA_KEY`
- [ ] `daily_brief.yml` injects secrets; cron **`0 23 * * *`**

### Cloudflare env (0B)

- [ ] Pages: `SUPABASE_URL`, `SUPABASE_ANON_KEY` for browser reads

### Wire live data

- [ ] Landing regime cards → Supabase
- [ ] `/dashboard` → replaces “coming soon” core with live reads (basic panels OK; full in Phase 3)

---

## Combined exit (before Phase 1)

- [ ] All **0A** items satisfied
- [ ] All **0B** items satisfied
- [ ] One clean CI run: three pairs upserted; CSV regression none
- [ ] Forced `pipeline_errors` test does not kill job
- [ ] RLS: anon SELECT ok; INSERT rejected

### Doc sync (`contaxt files/`)

- [ ] CONTEXT / CURSOR_RULES / AGENTS reflect **0A before 0B**, lazy client, Cloudflare-only hosting target
