# About page — April 2026

Structural fixes applied to `site/about/index.html` (v2 shell parity).

## Completed

- **Scripts fix** — Added deferred scripts before `</body>`: `nav.js`, `theme-switch.js`, `canvas-bg.js` (paths: `/assets/...`).
- **Canvas element** — `<canvas id="fx-canvas-bg" aria-hidden="true">` inserted immediately after `<body class="theme-light">`, before `.v2-wrap`.
- **site.css linked** — `<link rel="stylesheet" href="/assets/site.css" />` in `<head>` before the existing inline `<style>` (inline block retained).
- **LinkedIn URL** — Contact link updated from `href="#"` to `https://www.linkedin.com/in/shreyash045/` with `target="_blank"` and `rel="noopener noreferrer"`.
- **Photo path** — Confirmed hero image `src="/assets/images/shreyash.jpg"`; no path change.

## Pending

- Photo asset committed to repo if missing on deploy target.
- Visual QA before deploy.

## Methodology page — April 13 2026
- defer added to all four scripts
- inline styles replaced with meth- CSS class block
- all v2 tokens used, no hardcoded hex

## Deploy — April 13 2026
- Worker deployed: version ebd40961
- All four verification URLs: 200 OK
- supabase-env.js confirmed serving credentials
- About + methodology v2 live on fxregimelab.com

## Methodology Session B complete — April 13 2026
- All four signal cards showing live Supabase data
- Regime decision section live (EUR/USD + USD/JPY)
- CSP fix added to Worker for connect-src
- Root cause: methodology JS was never committed — fixed in ae642c4
