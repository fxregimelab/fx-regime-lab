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
npx wrangler pages deploy site/ --project-name fx-regime-lab
```

Ensure the Worker has `SUPABASE_URL` and `SUPABASE_ANON_KEY` configured so `/assets/supabase-env.js` is non-empty.
