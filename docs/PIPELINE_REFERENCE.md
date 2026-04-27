# Pipeline reference

## Current state (April 2026)

- **Daily / weekly automation:** `.github/workflows/pipeline_daily.yml` and `pipeline_weekly.yml` run `python -m src.scheduler.orchestrator` from the **`pipeline/`** package (see that tree for the live orchestrator).
- **No `web/` app** and **no root `wrangler.toml`**. ISR pings to Next were removed from `pipeline/src/scheduler/orchestrator.py`.
- **Worker:** [`workers/site-entry.js`](../workers/site-entry.js) is **API-only** (no static `ASSETS`, no `/assets/supabase-env.js`). See [[HOSTING_AFTER_UI_REMOVAL]].

The sections below about root `run.py`, `daily_brief.yml`, `deploy_web.yml`, and HTML brief steps are **legacy** documentation; cross-check paths against the repo before using them.

---

Everything below is tied to **historical** or **parallel** pipeline layouts, not an idealized flow.

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
- **Consumers:** optional operators or a future site; no in-repo Next.js reader.

## GitHub Actions (`.github/workflows/daily_brief.yml`)

- **Trigger:** `cron: '0 23 * * *'` (23:00 UTC daily) plus `workflow_dispatch`.
- **Concurrency:** `group: daily-brief`, `cancel-in-progress: true`.
- **Python:** 3.11, `pip install -r requirements.txt`.
- **Secrets:** workflow writes `.env` from `FRED_API_KEY` (required), optional `NOTION_TOKEN`, `SUPABASE_*`, market data keys, `ANTHROPIC_API_KEY`, Substack credentials. Cloudflare deploy uses `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
- **Env:** `LAYER3_STRICT=1` in CI (forces strict Layer 3 sidecars per comment in YAML).
- **Sequence:** `python run.py --skip deploy` (with retry sleep 60s on failure) → verify `briefs/brief_${SLUG}.html` → `python scripts/publish_brief_for_site.py` → `python deploy.py` → `npx wrangler deploy` (Worker + `site/` assets).

## `workers/site-entry.js` routes (Worker, current)

Exported `fetch` handler branches:

- `GET /api/health` → JSON `{ status: "ok", timestamp }`.
- `GET /api/substack-rss` → proxies Substack feed XML with cache TTL 3600s.
- `GET /api/fx-price?symbol=...` → Yahoo chart API proxy JSON.
- `GET /proxy/yahoo` or `/proxy/yahoo/...` → Yahoo REST proxy with CORS `*`.
- **Any other path** → `404` JSON `{ error: "not_found", path }`.

There is **no** static asset binding, HTML CSP injection, or `/assets/supabase-env.js` in the current Worker.

## Frontend environment (when you add a new app)

If you reintroduce Next.js or another SPA, supply public Supabase URL and anon key at **build time** for any `NEXT_PUBLIC_*` pattern the framework uses. See historical notes in git history for Cloudflare Pages + `next-on-pages` pitfalls.

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
