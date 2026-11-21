# Pipeline reference

## Supported daily entrypoint — repair branch, 27 September 2026

The checked-in Prefect deployment `Daily_FX_Regime_Engine` selects `src/scheduler/run_pipeline.py:run_pipeline`. This is a local repair; deployed configuration has not been verified or changed. The lower-level legacy `run_daily` and staged `run_multi_pair_flow` do not by themselves provide the complete daily completion boundary.

The wrapper runs:

1. Legacy or staged inference and publication, selected by `USE_V2_PIPELINE`, including required validation.
2. Optional staged shadow comparison when legacy is live and `SHADOW_V2` is enabled. Its fake writer and alert ports keep the comparison separate from live publication.
3. Overnight checks for the current date. Historical dates return unavailable/degraded status instead of using current prices.
4. Validation aggregation for the requested date.
5. The execution health record, followed by a final status notice.

A required-stage exception fails the scheduled flow. Degraded inputs, missing pairs, missing quality scores, empty aggregate output or a shadow problem prevent the healthy heartbeat. A completed Prefect flow with a DEGRADED return means execution finished with limitations; it is not a clean-data or forecasting-skill result. Only EURUSD, USDJPY and USDINR qualify for publication coverage.

The wrapper records evidence returned by this execution, not stages inferred from older rows. AI brief completion remains unknown until an explicit receipt exists. The current health table is a daily snapshot; immutable per-attempt history and the public audit page still need repair. Signal/call/rationale publication is not yet atomic.

For a configured production operator, the corresponding module entrypoint is `python -m src.scheduler.run_pipeline` from `pipeline/`. It performs real pipeline work; the test suite uses fake external ports. The checked-in deployment still clones `main`, so local branch changes require a reviewed release before taking effect.

Prefect managed workers receive runtime settings through deployment/work-pool environment configuration. They do not read a local repository `.env`. No GitHub Actions workflow is used. The current repository contains a Next.js `web/` application; earlier UI-removal notes below are historical.

Local verification and remaining release requirements: [repair checkpoint](../reports/REPAIR_CHECKPOINT.md), [scheduler evidence](../reports/repair-scheduler-health.md), and [repair register](REPAIR_REGISTER.md).

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

## Validation price evidence repair

The current evaluator is `publication-snapshot-v2`; deploy forward migration `20260927000006_validation_price_evidence.sql` with its prerequisite migrations before using the changed writer. It preserves earlier v1 evidence. All validation paths use original publication spot by call ID and exact stored historical closes. Missing evidence remains unavailable. `docs/VALIDATION_PRICE_CONTRACT.md` defines the contract.

Continuous endpoint archival is still an open repair: current daily ingestion does not guarantee completed bars in `historical_prices`. Do not run validation expecting a mutable signal fallback, or label absent outcomes successful research evidence. Source/session/cutoff and archival changes must precede release acceptance.
