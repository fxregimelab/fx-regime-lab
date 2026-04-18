# Deploy Reference

## Why `NEXT_PUBLIC_*` must exist at build time

Next.js **inlines** `process.env.NEXT_PUBLIC_SUPABASE_URL` and `process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY` into the **browser bundle** when `next build` runs (invoked by `@cloudflare/next-on-pages`). If those variables are missing at compile time, the client bundle gets empty strings and `web/lib/supabase/client.ts` throws at runtime — which surfaces as:

- Brief page: **Missing NEXT_PUBLIC_SUPABASE_URL…**
- Terminal pair desks: **No regime call for this pair** (hooks fail; empty state)
- Any client-side Supabase fetch failing

**Cloudflare Pages “Secrets” alone do not fix the browser bundle.** Encrypted secrets are intended for **runtime** (Workers/Pages Functions). They are **not** a substitute for passing `NEXT_PUBLIC_*` into the **build** environment so Next can embed them in static client JS.

The anon key is already public (RLS); treat `NEXT_PUBLIC_SUPABASE_*` as **build-time public configuration**, not as classified secrets.

---

## GitHub Actions Secrets Required

### Python pipeline (`daily_brief.yml`)

- `FRED_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `ANTHROPIC_API_KEY`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

### Web deployment (`deploy_web.yml`)

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `NEXT_PUBLIC_SUPABASE_URL` (must be set as a GitHub secret)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (must be set as a GitHub secret)

### How to add GitHub secrets

GitHub → repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

---

## Cloudflare Pages — correct configuration

### 1. Dashboard: Environment variables (Production + Preview)

1. Open **Cloudflare Dashboard** → **Workers & Pages** → project **fx-regime-lab** (or your project name).
2. **Settings** → **Environment variables**.
3. Under **Production**, add (plain text variables — **not** required to be “encrypted” for these two):

   | Variable name | Value |
   |---------------|--------|
   | `NEXT_PUBLIC_SUPABASE_URL` | `https://YOUR_PROJECT_REF.supabase.co` |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Your Supabase **anon** public key |

4. Repeat for **Preview** if you use preview deployments with Supabase.
5. Save.

6. Trigger a **new deployment** so the build runs with these variables in the environment (Connect to Git builds use this automatically on the next push; manual CLI builds must export or use `.env.local` — see below).

### 2. Optional: `wrangler pages secret` vs dashboard vars

- `npx wrangler pages secret put …` stores **runtime** secrets for Pages Functions. It does **not** replace build-time `NEXT_PUBLIC_*` for Next’s client bundle.
- Use **Settings → Environment variables** for `NEXT_PUBLIC_*` so **every build** sees them.

---

## Local development

```bash
cd web
cp .env.local.example .env.local
# Edit .env.local with real URL + anon key
npm run dev
# Opens at http://localhost:3000
```

Next.js loads `web/.env.local` automatically for `next dev` and `next build`.

---

## Build for Cloudflare Pages (WSL only — not PowerShell)

From **`web/`**, `NEXT_PUBLIC_*` must be set **before** `next-on-pages` runs (via `web/.env.local` or `export` in the shell).

```bash
# WSL
cd "/mnt/c/Market Journey 2026/Code/fx_regime/web"
# Ensure .env.local exists with NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
npm run pages:build
```

Or explicitly:

```bash
npx @cloudflare/next-on-pages@1.13.16
```

Output: `web/.vercel/output/static` (see `wrangler.toml` `pages_build_output_dir`).

---

## Deploy to Cloudflare Pages (CLI)

From **repository root** (PowerShell or WSL):

```bash
npx wrangler pages deploy web/.vercel/output/static --project-name=fx-regime-lab --commit-dirty=true
```

---

## Verify after deploy

1. **Brief:** https://fxregimelab.com/brief — latest `brief_text` renders (no red “Missing NEXT_PUBLIC…”).
2. **Terminal:** https://fxregimelab.com/terminal/fx-regime/eurusd — regime card shows data (not “No regime call…”).
3. Browser DevTools → **Network** → any JS chunk: search for your project host string; it should appear if inlined correctly (optional spot-check).

---

## Check deployment logs

```bash
npx wrangler pages deployment tail [DEPLOYMENT_ID] --project-name=fx-regime-lab --format=pretty
```

## List recent deployments

```bash
npx wrangler pages deployment list --project-name=fx-regime-lab
```

## Compatibility requirements

- `wrangler.toml` `compatibility_date`: 2025-01-01 or later
- `compatibility_flags`: `["nodejs_compat"]`
- `@cloudflare/next-on-pages`: 1.13.16 (pinned in docs / `package.json` script)

---

## Common failures and fixes

| Error | Fix |
|-------|-----|
| No such module async_hooks | `compatibility_date` too old; use 2025-01-01+ in `wrangler.toml` |
| Missing NEXT_PUBLIC_SUPABASE_* in browser | Set vars in **Pages → Environment variables** for Production (and Preview), **rebuild**. For local CLI, use `web/.env.local` or `export` before `npm run pages:build` |
| Relying only on `wrangler pages secret` for NEXT_PUBLIC_* | Wrong layer — use **build** env vars as above |
| next-on-pages hangs | Use **WSL**, not Windows PowerShell |
| 500 on all routes | `wrangler pages deployment tail` for runtime error |
| Content-Type: image/x-icon on `/` | `favicon.ico` in `app/` — move to `public/` if mis-served |
