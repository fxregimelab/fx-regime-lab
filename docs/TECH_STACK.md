# Tech stack

The **shipped Next.js app** (`web/`) and root **`wrangler.toml`** have been removed. See [[HOSTING_AFTER_UI_REMOVAL]] and [[DATA_READS_SPEC]].

## Current stack (repo reality)

| Layer | Choice | Notes |
|-------|--------|--------|
| Pipeline | Python 3.11 | CI: `.github/workflows/pipeline_daily.yml`, `pipeline_weekly.yml` |
| Database | Supabase (Postgres + RLS) | Writes via `pipeline/src/db/writer.py` only |
| Worker (optional deploy) | Cloudflare Worker | [`workers/site-entry.js`](../workers/site-entry.js) — **API-only** (`/api/health`, RSS, Yahoo proxy). No static HTML site. Add a minimal `wrangler.toml` with `main = "workers/site-entry.js"` if you deploy it. |
| UX reference | `claude-design/` | Prototype JSX — not production |
| Future frontend | TBD | Pick stack when rebuilding; regenerate Supabase types into the new package |

## Environment variables

### Python / pipeline (`.env` at repo root, CI writes from GitHub Secrets)

See [[.env.example]] at repo root. Typical keys: `FRED_API_KEY`, `SUPABASE_URL`, `SUPABASE_PROJECT_REF`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENROUTER_API_KEY`.

`NEXT_JS_URL` and `REVALIDATE_SECRET` are **no longer** used (ISR ping removed).

## Local development

**Pipeline:**

```bash
pip install -e pipeline/
cd pipeline && pytest
```

Run daily/weekly scripts from repo root: `pipeline/run_daily.sh`, `pipeline/run_weekly.sh`.

## Related docs

- [[PIPELINE_REFERENCE]]
- [[DATABASE_SCHEMA]]
- [[DATA_READS_SPEC]]
- [[HOSTING_AFTER_UI_REMOVAL]]
