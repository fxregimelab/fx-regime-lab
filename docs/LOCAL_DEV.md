# Local development

## Running the pipeline locally

```bash
cp .env.example .env
```

Add `FRED_API_KEY` to `.env`. Supabase variables are optional for local runs: without `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, remote writes are skipped and a short message is printed once.

```bash
python run.py --skip deploy
```

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
