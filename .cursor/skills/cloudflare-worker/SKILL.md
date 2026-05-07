---
name: cloudflare-worker
description: >-
  Manages Cloudflare Worker for FX Regime Lab API layer.
  Use when changing API routes, proxy logic, or worker deployment.
---

# Cloudflare Worker

## Entry

- **File**: `workers/site-entry.js`
- **Scope**: API-only. No static HTML.

## Routes

| Route | Purpose |
|-------|---------|
| `/api/health` | Health check |
| `/api/substack-rss` | Substack RSS feed proxy |
| `/api/fx-price` | Current FX price lookup |
| `/proxy/yahoo` | Yahoo Finance API proxy |

## Deployment

```bash
npx wrangler deploy
```

Requires:
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

## Hard rules

- API-only. No static assets, no HTML site.
- Never log API keys or secrets.
- Handle CORS for frontend origin (`fxregimelab.com`).
- Rate-limit proxy routes to prevent abuse.

## Adding a route

1. Add handler in `workers/site-entry.js`.
2. Export route pattern in `addEventListener('fetch')`.
3. Test locally: `npx wrangler dev`.
4. Deploy: `npx wrangler deploy`.
