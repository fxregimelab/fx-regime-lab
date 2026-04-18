# Tech stack

Exact versions below are taken from [[web/package.json]] at documentation time. Resolve semver ranges with `npm ls` in `web/` when debugging lockfile drift.

## Stack table

| Layer | Choice | Version in package.json | Why it is here |
|-------|--------|---------------------------|----------------|
| Frontend framework | Next.js (App Router) | `next@15.5.2` | App Router, RSC-friendly layout split between shell and terminal; pinned because `@cloudflare/next-on-pages@^1.13.16` peer requires `next` `<=15.5.2`. |
| UI language | TypeScript | `typescript@^5` | Strict typing for agents and humans. |
| React | React 19 | `react@^19.0.0`, `react-dom@^19.0.0` | Paired with Next 15. |
| Styling | Tailwind CSS | `tailwindcss@^3.4.17` | Utility-first; `tailwind.config.ts` extends tokens (`shell-bg`, `terminal-bg`, etc.). |
| CSS pipeline | PostCSS + Autoprefixer | `postcss@^8.4.49`, `autoprefixer@^10.4.20` | Required for Tailwind v3 build. |
| Charts (web only) | TradingView Lightweight Charts | `lightweight-charts@^5.0.3` (lock may resolve newer 5.x) | Line charts in `web/components/charts/TimeSeriesChart.tsx`. |
| Cloudflare adapter | `@cloudflare/next-on-pages` | `^1.13.16` | `web/next.config.js` calls `setupDevPlatform()` in development. |
| Backend | Supabase (Postgres + RLS) | `@supabase/supabase-js@^2.49.4`, `@supabase/ssr@^0.6.1` | Browser and server clients in `web/lib/supabase/`. |
| Lint | ESLint + eslint-config-next | `eslint@^9`, `eslint-config-next@15.5.2` | `npm run lint` in `web/`. |
| Pipeline | Python 3 | CI uses 3.11 per `.github/workflows/daily_brief.yml` | Daily data pulls, merge, brief, validation. |
| Orchestration | `run.py` | N/A | Single entrypoint; see [[PIPELINE_REFERENCE]]. |
| Legacy static host | Cloudflare Worker + assets | `workers/site-entry.js` + `site/` (archived copy under `_archive/v1/`) | Current CI deploy path in GitHub Actions. |
| Target Next host | Cloudflare Pages | Root `wrangler.toml` `pages_build_output_dir = "./web/.vercel/output/static"` | Intended for `@cloudflare/next-on-pages` build output; CI may not yet call `wrangler pages deploy`. |

## Explicitly disallowed in `web/` (policy)

Do **not** add or use:

- Chart.js, ECharts, Plotly, Recharts, or any charting library other than Lightweight Charts.
- Inline `style={}` on React components for layout or theme (Tailwind only).
- CSS Modules (no `*.module.css`).
- styled-components, Emotion, or other CSS-in-JS.
- `any` as a type, or `@ts-ignore` / `@ts-expect-error`, except in the rare case a third-party type is broken and then only with a one-line justification comment (default: **do not**).

Reality check: some files still use type assertions (for example `as BriefLogRow` in hooks). New code should avoid widening casts; remove them when touching those lines.

## Environment variables

### Python / pipeline (`.env` at repo root, CI writes from GitHub Secrets)

| Name | Role | Where read |
|------|------|------------|
| `FRED_API_KEY` | US Treasury yields from FRED | `pipeline.py`, CI fails if missing |
| `SUPABASE_URL` | Supabase project URL | `core/supabase_client.py`, pipelines |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role writes | Pipeline upserts |
| `SUPABASE_ANON_KEY` | Optional; anon reads | CI, some scripts |
| `NOTION_TOKEN` | Optional Notion sync | `run.py` tail calls `notion_sync.py` |
| `TWELVE_DATA_KEY`, `POLYGON_KEY` | Optional market data backups | `config.py` |
| `ANTHROPIC_API_KEY` | Optional AI narrative in `ai_brief.py` | Non-blocking step |
| `SUBSTACK_EMAIL`, `SUBSTACK_PASSWORD` | Optional Substack draft | `scripts/substack_publish.py` |
| `LAYER3_STRICT` | CI env `1` forces strict Layer 3 sidecars | `.github/workflows/daily_brief.yml` |

Worker secrets (legacy static site path): `SUPABASE_URL`, `SUPABASE_ANON_KEY` in Cloudflare for `workers/site-entry.js` (see file header comments).

### Next.js `web/` (`web/.env.local`, not committed)

| Name | Role | Where read |
|------|------|------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Public Supabase URL | `web/lib/supabase/client.ts`, `web/lib/supabase/server.ts` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Public anon key (RLS) | Same |

`web/app/api/brief/route.ts` returns HTTP 503 if these are unset.

## Local development

**Pipeline (repo root, venv recommended):**

```bash
pip install -r requirements.txt
python run.py
```

Common partial runs (from `run.py` help text):

```bash
python run.py --only html
python run.py --skip deploy
python run.py --only cot inr merge
```

**Next.js (from `web/`):**

```bash
cd web
npm install
npm run dev
```

**Production build (no dev server required):**

```bash
cd web
npm run build
```

## Deploy commands (today vs target)

- **What CI does today:** `npx wrangler deploy` after `python deploy.py`, using the Worker entry in the workflow comment (Worker + `site/` assets). See `.github/workflows/daily_brief.yml`.
- **What root `wrangler.toml` describes now:** Cloudflare **Pages** output directory `./web/.vercel/output/static` (build via `@cloudflare/next-on-pages` / Vercel build first). Deploy would be:

```bash
wrangler pages deploy
```

…once the Pages project and build pipeline are wired. Until then, treat Worker deploy and Pages deploy as **two different paths** that must not be confused.

## Related docs

- [[PIPELINE_REFERENCE]]
- [[FRONTEND_ARCHITECTURE]]
- [[DATABASE_SCHEMA]]
