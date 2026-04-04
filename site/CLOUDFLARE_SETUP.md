# Cloudflare Pages + DNS (manual steps)

These steps complete **todo `phase0-dns-cloudflare`** outside the repo.

## Workers & Pages (Git + `wrangler deploy`)

If the project uses **Deploy command** `npx wrangler deploy` (Workers static assets), the repo must include **`wrangler.toml`** at the root with `[assets] directory = "./site"`. Otherwise Wrangler defaults to **`.`** and uploads the whole repository (including `.git`), which breaks routing and UI.

- **Build command:** leave **empty** (this site is static; do **not** run `pip install -r requirements.txt` on every deploy).
- **Deploy command:** `npx wrangler deploy`

## Classic Pages (upload `site/` only)

1. **Cloudflare Dashboard** → Pages → Create project → Connect Git → select this repo.
2. **Build settings:** Framework = None; build command empty; **output directory = `site`** (publish the `site/` folder).
3. **Custom domains:** Add `fxregimelab.com` and `www.fxregimelab.com`. Enable SSL (automatic).
4. **Redirects:** `_redirects` in `site/` already sends `/newsletter` → Substack (301). Verify in Pages → Custom domains / Redirects if needed.
5. **GoDaddy:** Point apex to Cloudflare (A/CNAME per Pages instructions) or move nameservers to Cloudflare. Preserve **MX** records for `shreyash@fxregimelab.com`.
6. **Environment variables (Phase 0B):** In Pages → Settings → Environment variables add `SUPABASE_URL` and `SUPABASE_ANON_KEY` for live dashboard reads.
