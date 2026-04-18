# TASK.md — Current Session Context
# Update this file before every Cursor session.
# Cursor reads this first on every session.

---

## Current task
[FILL IN BEFORE EACH SESSION]
Example: "Implement brief page dynamic rendering"

## Status
[ ] Not started
[ ] In progress  
[ ] Complete

## Relevant docs to read
[List only the docs needed for this specific task]
- docs/FRONTEND_ARCHITECTURE.md
- docs/DATABASE_SCHEMA.md

## Files to modify
[List specific files. Cursor will not touch files not listed here.]
- 

## Files to NOT touch
- Any Python pipeline file (*.py at repo root and scripts/)
- workers/site-entry.js
- .github/workflows/
- _archive/

## Done when
[Specific, testable completion criteria]
Example: "Brief page renders content from brief_log table.
Build passes with exit code 0. No console errors on fxregimelab.com/brief"

## Known constraints
[Any gotchas Cursor must know about for this specific task]
-

## Discovered issues (add during session, fix after current task)
-

---

## Completed tasks log
| Date | Task | Files changed | Notes |
|------|------|---------------|-------|
| 2026-04-18 | Archive v1, scaffold Next.js | web/, _archive/ | Phase 0 complete |
| 2026-04-18 | Write context docs | docs/ | 10 docs + Obsidian vault |
| 2026-04-18 | Implement home page | web/app/(shell)/page.tsx + components | Live data working |
| 2026-04-18 | Deploy to Cloudflare Pages | wrangler.toml, web/next.config.js | fxregimelab.com live |

---

## Current known issues (not in current task scope)
- Performance / About: iterate copy as needed
- Profile photo: replace placeholder when ready
- If brief or terminal still error after deploy: confirm **Production** build env on Pages has `NEXT_PUBLIC_*` and redeploy (see `DEPLOY.md`)

---

## Architecture reminders (read if uncertain)
- Next.js 15.5.2 App Router, TypeScript strict, Tailwind CSS v3
- Cloudflare Pages via @cloudflare/next-on-pages@1.13.16
- Deploy: WSL → `cd web` → `npm run pages:build` (or `npx @cloudflare/next-on-pages@1.13.16`) → `wrangler pages deploy` from repo root
- All dynamic routes need: export const runtime = 'edge'
- **Browser Supabase:** `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` must be set at **Next compile time** (Cloudflare Pages **Settings → Environment variables** for Production/Preview, or `web/.env.local` for local builds). `wrangler pages secret` does not replace this for the client bundle.
- wrangler.toml compatibility_date must be 2025-01-01 or later
- Never run next-on-pages from Windows PowerShell — WSL only
