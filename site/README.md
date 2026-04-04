# FX Regime Lab static site (Cloudflare Pages)

- **Publish directory:** `site/` (root = `index.html`).
- **Newsletter:** `_redirects` sends `/newsletter` → Substack (301).
- **Supabase in browser (Phase 0B):** pages load `/assets/supabase-env.js` before the Supabase client. On Cloudflare, `workers/site-entry.js` builds that response from **Variables and secrets** (`CLOUDFLARE_SETUP.md`). For other hosts, you can inline the same `window.__SUPABASE_*` assignments (anon only; never **service_role**).
