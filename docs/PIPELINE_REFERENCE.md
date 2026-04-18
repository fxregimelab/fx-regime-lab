# Pipeline reference

Everything here is tied to **files in this repo**, not an idealized flow.

## Canonical step order (`run.py`)

`STEPS` in `run.py` (name → script):

1. `fx` → `pipeline.py`
2. `cot` → `cot_pipeline.py`
3. `inr` → `inr_pipeline.py`
4. `vol` → `vol_pipeline.py`
5. `oi` → `oi_pipeline.py`
6. `rr` → `rr_pipeline.py`
7. `merge` → `scripts/pipeline_merge.py`
8. `text` → `morning_brief.py`
9. `macro` → `macro_pipeline.py`
10. `ai` → `ai_brief.py`
11. `substack` → `scripts/substack_publish.py`
12. `html` → `create_html_brief.py`
13. `validate` → `validation_regime.py`
14. `deploy` → `deploy.py`

CLI:

- `python run.py` runs all steps subject to skip flags.
- `python run.py --skip deploy` skips deploy (CI uses this).
- `python run.py --only html` runs a single step.
- `python run.py --only cot inr merge` runs a subset.

**Non-blocking failures:** `NON_BLOCKING_STEPS = {"ai", "macro", "validate", "substack"}` in `run.py`. If one of these exits non-zero, the orchestrator prints a warning and **continues** instead of aborting the chain.

**Dedup note:** `run.py` still contains a comment about deduplicating `fx` and `merge` when they shared `pipeline.py`. Today `merge` uses `scripts/pipeline_merge.py`, so **both `fx` and `merge` run** when not skipped.

## What each step tends to write

| Step | Disk outputs (examples) | Supabase |
|------|---------------------------|----------|
| `fx` | `data/latest.csv`, yield joins in master build | Via later merge sync for wide row |
| `cot` | `data/cot_latest.csv` | |
| `inr` | INR columns merged into master CSV path used by INR pipeline | |
| `vol`, `oi`, `rr` | `data/vol_latest.csv`, `data/oi_latest.csv`, `data/rr_latest.csv` | |
| `merge` | Updates `data/latest_with_cot.csv` (merge_main in `pipeline.py`) | `signals` upsert via `sync_signals_from_master_csv` |
| `text` | `briefs/brief_YYYYMMDD.txt` | `regime_calls` + `brief_log` upsert via `persist_regime_calls_and_brief` in `morning_brief.py` |
| `macro` | `data/macro_cal.json` | |
| `ai` | AI JSON artifacts under `data/` (see `ai_brief.py`) | Reads `brief_log`, does not own the canonical daily upsert |
| `substack` | Substack draft via API | |
| `html` | `briefs/brief_YYYYMMDD.html` | |
| `validate` | none | `validation_log` upsert |
| `deploy` | copies brief into site entry for legacy static deploy | git push in `deploy.py` |

## `brief_log` ownership (reality)

- **Upsert:** `core/regime_persist.py` `persist_regime_calls_and_brief`, called from **`morning_brief.py` (text step)** with the generated desk brief string and three pair regime labels.
- **`ai_brief.py`:** reads prior `brief_log` rows for continuity and fallback; it is **not** the writer of the primary daily `brief_log` row.

## `pipeline_status.json`

- **Writer:** `core/pipeline_status.py` `write_pipeline_status`, invoked from `run.py` on full success or on hard failure before break.
- **Path:** `core/paths.py` sets `PIPELINE_STATUS_JSON` to `site/data/pipeline_status.json` (under repo `site/` directory). If `site/` is absent, `os.makedirs` in the writer creates `site/data/`.
- **Fields:** `last_run_utc`, `last_run_status` (`ok` / `failed`), `steps_completed` (string list), `source` (`fx_regime_pipeline`), optional `error_message`, plus merged fields from `site/data/supabase_sync_sidecar.json` if present: `supabase_write_status`, `supabase_rows_written`, `last_supabase_write`.
- **Sidecar writer:** `core/signal_write.py` `_write_supabase_sidecar` writes `site/data/supabase_sync_sidecar.json` after signal sync attempts.
- **Next.js today:** no reader component for `pipeline_status.json` in `web/` (legacy static dashboard used this under the old `site/` shell).

## GitHub Actions (`.github/workflows/daily_brief.yml`)

- **Trigger:** `cron: '0 23 * * *'` (23:00 UTC daily) plus `workflow_dispatch`.
- **Concurrency:** `group: daily-brief`, `cancel-in-progress: true`.
- **Python:** 3.11, `pip install -r requirements.txt`.
- **Secrets:** workflow writes `.env` from `FRED_API_KEY` (required), optional `NOTION_TOKEN`, `SUPABASE_*`, market data keys, `ANTHROPIC_API_KEY`, Substack credentials. Cloudflare deploy uses `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
- **Env:** `LAYER3_STRICT=1` in CI (forces strict Layer 3 sidecars per comment in YAML).
- **Sequence:** `python run.py --skip deploy` (with retry sleep 60s on failure) → verify `briefs/brief_${SLUG}.html` → `python scripts/publish_brief_for_site.py` → `python deploy.py` → `npx wrangler deploy` (Worker + `site/` assets).

## GitHub Actions — Next.js web (`deploy_web.yml`)

- **Trigger:** `push` to `main` when paths under `web/**` change.
- **Does not** run the Python pipeline.
- **Build:** Node 20, `npm ci` in `web/`, `npx @cloudflare/next-on-pages`; deploy with `wrangler pages deploy web/.vercel/output/static --project-name=fx-regime-lab`.
- **Secrets / env:** `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`; `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` must be available at **build time** (see **Frontend Environment Variables** below).

## Frontend Environment Variables

`NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` must be available at **Next.js build time**, not only at runtime. Next inlines `NEXT_PUBLIC_*` into the client bundle when `next build` runs (including under `@cloudflare/next-on-pages`). If they are missing during the build, the browser bundle can end up empty and client-side Supabase code fails.

Set them in **all** of these places as appropriate:

1. **`web/.env.local`** — local development (`next dev` / local `pages:build`).
2. **GitHub Actions secrets** — referenced as `secrets.NEXT_PUBLIC_SUPABASE_*` in `deploy_web.yml` so CI builds embed the values.
3. **Cloudflare Pages → Settings → Environment variables** — for Connect-to-Git builds or manual `wrangler pages deploy` runs that build on Cloudflare or need the dashboard to inject build env.

**Cloudflare Pages “Secrets” alone are not enough for the client bundle.** Encrypted secrets are for **runtime** (Pages Functions / Workers). They do not replace passing `NEXT_PUBLIC_*` into the **build** environment so Next can embed them in static client JavaScript.

## `workers/site-entry.js` routes (Worker)

Exported `fetch` handler branches:

- `GET /api/health` → JSON `{ status: "ok", timestamp }`.
- `GET /api/substack-rss` → proxies Substack feed XML with cache TTL 3600s.
- `GET /api/fx-price?symbol=...` → Yahoo chart API proxy JSON.
- `GET /proxy/yahoo` or `/proxy/yahoo/...` → Yahoo REST proxy with CORS `*`.
- `GET /assets/supabase-env.js` → injects `window.__SUPABASE_URL__` and `window.__SUPABASE_ANON_KEY__` from Worker env.
- Paths starting `/data/` or `/static/` → `env.ASSETS.fetch` with optional CORS for `.json` under `/static/`.
- **Default:** `env.ASSETS.fetch(request)` for static site, with HTML CSP helper `withHtmlCsp`.

This Worker is **orthogonal** to the Next.js Pages `wrangler.toml` at repo root unless you explicitly wire both in ops.

## `pipeline_errors`

- **Writer:** `core/signal_write.log_pipeline_error` inserts into `pipeline_errors` when Supabase client exists; otherwise appends JSON lines to `runs/{TODAY}/pipeline_errors_local.jsonl`.
- **Query (operators):** use Supabase service role in a SQL client or build an internal admin query; anon has **no read policy** on `pipeline_errors` per `sql/schema.sql`.

## Common failure modes (first checks)

1. **`FRED_API_KEY` missing in CI:** workflow fails at “Write .env from secrets”.
2. **Supabase env missing locally:** `get_client()` returns `None`; upserts skipped with console warnings.
3. **`LAYER3_STRICT` in CI:** vol/oi/rr sidecars must exist and pass checks or CI fails early in those pipelines (see respective pipeline files).
4. **Merge master missing:** `merge_main` returns false if `data/latest_with_cot.csv` missing.
5. **Validation step:** depends on Yahoo via `yfinance` for realized returns; network failures yield step failure but step is non-blocking.

## Related docs

- [[SIGNAL_DEFINITIONS]]
- [[DATABASE_SCHEMA]]
- [[TECH_STACK]]
