# Cloudflare Pages + DNS (manual steps)

These steps complete **todo `phase0-dns-cloudflare`** outside the repo.

## Workers & Pages (Git + `wrangler deploy`)

**Asset-only** Workers cannot have dashboard **Variables and secrets**. This repo uses a tiny **`workers/site-entry.js`** plus **`[assets] directory = "./site"`** so env vars are allowed and `/assets/supabase-env.js` is generated at the edge from secrets.

- **Build command:** leave **empty** (no `pip install`).
- **Deploy command:** `npx wrangler deploy`

### Variables and secrets (Phase 0B — browser reads)

In **Workers & Pages** → your project → **Settings** → **Variables and secrets** → **Add** (Production, and Preview if you use it):

| Name | Type | Value source |
|------|------|----------------|
| `SUPABASE_URL` | Plain text or secret | Supabase → **Project Settings** → **API** → **Project URL** |
| `SUPABASE_ANON_KEY` | **Secret** | Supabase → **Project Settings** → **API** → **anon public** key |

Names must match exactly (`SUPABASE_URL`, `SUPABASE_ANON_KEY`). Do **not** add **service_role** here (browser-visible in the JS response).

After saving, redeploy (push to `main` or **Retry deployment**). Verify: open `/assets/supabase-env.js` on your domain — you should see `window.__SUPABASE_URL__` set (not empty strings).

**Morning brief on-domain:** CI runs `scripts/publish_brief_for_site.py` before `deploy.py`, producing `site/brief/latest.html` plus `site/charts/` and `site/static/`. Users open **`/brief/latest.html`** (same origin; no GitHub embed).

### Local preview (`wrangler dev`)

Copy `.dev.vars.example` → **`.dev.vars`** in the repo root (gitignored), same keys as above. Run `npx wrangler dev` from the repo root.

## Classic Pages (upload `site/` only)

1. **Cloudflare Dashboard** → Pages → Create project → Connect Git → select this repo.
2. **Build settings:** Framework = None; build command empty; **output directory = `site`** (publish the `site/` folder).
3. **Custom domains:** Add `fxregimelab.com` and `www.fxregimelab.com`. Enable SSL (automatic).
4. **Redirects:** `_redirects` in `site/` already sends `/newsletter` → Substack (301). Verify in Pages → Custom domains / Redirects if needed.
5. **GoDaddy:** Point apex to Cloudflare (A/CNAME per Pages instructions) or move nameservers to Cloudflare. Preserve **MX** records for `shreyash@fxregimelab.com`.
6. **Environment variables (Phase 0B):** See **Variables and secrets** table above (Workers) or classic Pages → Environment variables; anon + URL only.
