# Cloudflare Pages + DNS (manual steps)

These steps complete **todo `phase0-dns-cloudflare`** outside the repo.

1. **Cloudflare Dashboard** → Pages → Create project → Connect Git → select this repo.
2. **Build settings:** Framework = None; build command empty; **output directory = `site`** (publish the `site/` folder).
3. **Custom domains:** Add `fxregimelab.com` and `www.fxregimelab.com`. Enable SSL (automatic).
4. **Redirects:** `_redirects` in `site/` already sends `/newsletter` → Substack (301). Verify in Pages → Custom domains / Redirects if needed.
5. **GoDaddy:** Point apex to Cloudflare (A/CNAME per Pages instructions) or move nameservers to Cloudflare. Preserve **MX** records for `shreyash@fxregimelab.com`.
6. **Environment variables (Phase 0B):** In Pages → Settings → Environment variables add `SUPABASE_URL` and `SUPABASE_ANON_KEY` for live dashboard reads.
