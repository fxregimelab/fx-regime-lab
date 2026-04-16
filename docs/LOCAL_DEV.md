# Local development

## Running the pipeline locally

```bash
cp .env.example .env
```

Add `FRED_API_KEY` to `.env`. Supabase variables are optional for local runs: without `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, remote writes are skipped and a short message is printed once. Errors that would go to `pipeline_errors` are also appended to **`runs/{date}/pipeline_errors_local.jsonl`** when the Supabase client is unavailable.

### Optional integrations (non-blocking in `run.py`)

- **Substack** ([`scripts/substack_publish.py`](../scripts/substack_publish.py)): set `SUBSTACK_EMAIL` and `SUBSTACK_PASSWORD` in `.env` (and GitHub Actions secrets for CI). If login fails with HTTP 401, the step is skipped; the rest of the pipeline still completes.

- **Notion** ([`notion_sync.py`](../notion_sync.py)): requires `NOTION_TOKEN`. If the Home Dashboard page moves or is recreated, set **`NOTION_HOME_DASHBOARD_PAGE_ID`** to the page ID (32 hex chars, no dashes) and ensure the Notion integration is **shared** with that page — otherwise block API calls return 404.

On **Windows**, use **`PYTHONUTF8=1`** (or `PYTHONIOENCODING=utf-8`) when running the pipeline so console output does not fail on Unicode in third-party prints.

```bash
python run.py --skip deploy
```

## Strict Layer 3 (optional)

To match CI behavior locally, run with **`LAYER3_STRICT=1`** so `vol` / `oi` / `rr` exit **1** if Layer 3 cannot produce required data (see [PIPELINE_AUDIT_AND_OPERATIONS.md](./PIPELINE_AUDIT_AND_OPERATIONS.md)).

PowerShell:

```powershell
$env:LAYER3_STRICT="1"; python run.py --skip deploy
```

## Deploy / stale brief

`deploy.py` uses **`config.DATE_SLUG`** for `briefs/brief_{DATE_SLUG}.html`. Locally, if today’s file is missing, the newest `briefs/*.html` may be used with a **WARN**. On **GitHub Actions**, that fallback is **off** unless **`DEPLOY_ALLOW_STALE_BRIEF=1`**.

## CSV vs Supabase spot-check

From repo root (optional):

```bash
python scripts/dev/verify_data_supabase_brief.py
# Non-blocking (prints mismatches, exit 0):
python scripts/dev/verify_data_supabase_brief.py --warn-only
```

## Terminal E2E golden checklist (after pipeline + publish)

Use one **pinned as-of date** (the latest master index date after `run.py`). Full contract matrix: [`docs/TERMINAL_DEEP_REFERENCE.md`](TERMINAL_DEEP_REFERENCE.md) §15.

1. **Console harness:** Open [`site/terminal/index.html`](../site/terminal/index.html) (or deployed `/terminal/`). In DevTools console run `window.FXRLTest.testDataPath()`. Confirm Supabase env, sample `signals` query, and `pipeline_status` behave as expected (see output labels in [`data-client.js`](../site/terminal/data-client.js)).
2. **Home cards:** Regime, confidence, and driver populate for EUR/USD, USD/JPY, USD/INR when `regime_calls` has rows; foot **As of** date matches the pipeline close date.
3. **Provenance strip:** Below the nav, the desk line shows **as-of date**, **regime data source** (Supabase vs offline), and **pipeline UTC** time where `pipeline_status.json` is present.
4. **Ticker vs cards:** Ticker and card spots updated by [`live-prices.js`](../site/terminal/live-prices.js) are **indicative** (stream); card footers and charts from `signals` / CSV are **daily pipeline close**—not expected to match tick-for-tick intraday.
5. **Pair desks:** Open `/terminal/eurusd`, `/terminal/usdjpy`, `/terminal/usdinr`; expand one accordion row per page; confirm chart loads and tooltip units match [`SIGNAL_CHART_MAP`](../site/terminal/data-client.js) (e.g. spreads in `%`, COT in contracts).
6. **Accuracy strip:** If `validation_log` has rows with `correct_1d`, home shows percentages; otherwise “No validation data”.

## Terminal data path

- **Local:** CSV files under `data/` (and optionally `site/data/` after `publish_brief_for_site.py`) power full master series; the browser uses CSV when Supabase globals are absent.
- **Production (fxregimelab.com):** The Cloudflare Worker serves `/assets/supabase-env.js` with `SUPABASE_URL` and `SUPABASE_ANON_KEY`. Terminal pages load the Supabase JS client and read `signals`, `regime_calls`, `brief_log`, and `validation_log` where used.

Terminal scripts detect Worker-injected `window.__SUPABASE_URL__` / `window.__SUPABASE_ANON_KEY__` first, then fall back to empty meta tags for local overrides.

## Backfill Supabase (run once after schema is set up)

From repo root, with service role key in the environment:

```bash
python scripts/backfill_supabase.py
python scripts/backfill_cot.py
python scripts/backfill_inr.py
```

All three run the same merged-master upsert; separate entry points match operator checklists.

## Cloudflare deployment

Production deploys to Cloudflare Pages run automatically from GitHub Actions after each successful daily pipeline (`Deploy to Cloudflare Pages` step), provided `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` are set as repository secrets.

Manual deploy from repo root:

```bash
npx wrangler deploy
```

Ensure the Worker has `SUPABASE_URL` and `SUPABASE_ANON_KEY` configured so `/assets/supabase-env.js` is non-empty.

## Testing the connection

Run from repo root with `.venv` activated:

```bash
python scripts/dev/test_connection.py
```

Expected output:

- `OK: signals table has data`
- `OK: regime_calls table has data`
- `OK: write permission confirmed (service role)`
- `SUPABASE: All tests passed`

If you see `FAIL`, check `.env` has correct values for:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## Testing the browser data path

Open any terminal page, open browser console, run:

```js
window.FXRLTest.testDataPath()
```

Expected output shows Supabase env injection, Supabase query, CSV fallback, and `pipeline_status.json` checks as `OK` when data path is healthy.

## Verifying live prices

Open `site/terminal/index.html` in browser.
Prices in the ticker should update every 30 seconds.
Check browser console for `[LivePrices]` warnings.
