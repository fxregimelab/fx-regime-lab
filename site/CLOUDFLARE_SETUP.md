# Cloudflare Pages + DNS (manual steps)

These steps complete **todo `phase0-dns-cloudflare`** outside the repo.

## Workers & Pages (Git + `wrangler deploy`)

If the project uses **Deploy command** `npx wrangler deploy` (Workers static assets), the repo must include **`wrangler.toml`** at the root with `[assets] directory = "./site"`. Otherwise Wrangler defaults to **`.`** and uploads the whole repository (including `.git`), which breaks routing and UI.

- **Build command:** `python3 scripts/dev/emit_supabase_env_for_site.py`  
  (Requires **Variables and secrets** below so the browser gets `window.__SUPABASE_*` without committing keys. No `pip install` needed.)
- **Deploy command:** `npx wrangler deploy`

### Variables and secrets (Phase 0B — browser reads)

In **Workers & Pages** → your project → **Settings** → **Variables and secrets** → **Add** (Production, and Preview if you use it):

| Name | Type | Value source |
|------|------|----------------|
| `SUPABASE_URL` | Secret or plain text | Supabase → **Project Settings** → **API** → **Project URL** |
| `SUPABASE_ANON_KEY` | **Secret** | Supabase → **Project Settings** → **API** → **anon public** key |

Use the **same names** so the build step can read them. Do **not** put the **service_role** key here (browser-visible bundle).

After saving, trigger a new deployment (push to `main` or **Retry deployment**).

## Classic Pages (upload `site/` only)

1. **Cloudflare Dashboard** → Pages → Create project → Connect Git → select this repo.
2. **Build settings:** Framework = None; build command empty; **output directory = `site`** (publish the `site/` folder).
3. **Custom domains:** Add `fxregimelab.com` and `www.fxregimelab.com`. Enable SSL (automatic).
4. **Redirects:** `_redirects` in `site/` already sends `/newsletter` → Substack (301). Verify in Pages → Custom domains / Redirects if needed.
5. **GoDaddy:** Point apex to Cloudflare (A/CNAME per Pages instructions) or move nameservers to Cloudflare. Preserve **MX** records for `shreyash@fxregimelab.com`.
6. **Environment variables (Phase 0B):** See **Variables and secrets** table above (Workers) or classic Pages → Environment variables; anon + URL only.
