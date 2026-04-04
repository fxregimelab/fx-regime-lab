# FX Regime Lab static site (Cloudflare)

- **Publish directory:** `site/` (see root `wrangler.toml`).
- **UI:** Light editorial v2 — `assets/site.css`, `canvas-bg.js`, `nav.js`; spec in `docs/FX_REGIME_LAB_UI_PROMPT_V2.md`.
- **Brief:** Latest HTML brief at **`/brief/latest.html`**, produced by `scripts/publish_brief_for_site.py` in CI (same-origin Plotly + `/charts/`).
- **Hub:** `/brief/` lists archive rows from Supabase `brief_log` when keys are set.
- **Newsletter:** `_redirects` → Substack (301).
- **Supabase:** `/assets/supabase-env.js` from Worker + dashboard Variables (`CLOUDFLARE_SETUP.md`).
