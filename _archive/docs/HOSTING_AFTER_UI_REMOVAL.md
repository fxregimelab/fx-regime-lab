# Hosting after UI removal

The shipped **Next.js** app under `web/` and root **`wrangler.toml`** (Cloudflare Pages build pointer) have been removed.

## What to do in dashboards

1. **Cloudflare Pages** — Disable or delete the project that built the former Next app, or leave it unused until a new frontend exists.
2. **GitHub Actions secrets** — `NEXT_JS_URL` and `REVALIDATE_SECRET` are no longer used by workflows in this repo; remove them from the environment to avoid confusion.
3. **Cloudflare Worker** — [`workers/site-entry.js`](../workers/site-entry.js) is **API-only** (`/api/health`, `/api/substack-rss`, `/api/fx-price`, `/proxy/yahoo/*`). There is **no** static asset site or HTML CSP path. To deploy this Worker again, add a minimal `wrangler.toml` with `main = "workers/site-entry.js"` (no `pages_build_output_dir`, no `ASSETS` binding).

## Design source for the next UI

UX and layout experiments live under **`claude-design/`**. Supabase read patterns from the old app are summarized in [`DATA_READS_SPEC.md`](./DATA_READS_SPEC.md).
