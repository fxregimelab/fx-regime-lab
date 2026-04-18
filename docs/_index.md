# FX Regime Lab — docs home

## How to start a Cursor session

1. Update `TASK.md` at repo root — fill in current task, relevant docs, files to modify, done criteria
2. Open Cursor — new chat (never continue yesterday's chat)
3. First message to Cursor: "Read TASK.md first. Confirm the task and which files you will touch before writing any code."
4. Work proceeds with full context

**Never give Cursor a task without updating TASK.md first.**
**One task per session. Scope creep goes in "Discovered issues" in TASK.md.**

**One line:** Live FX regime research OS. Strategy `fx-regime` today; multi-strategy is schema- and product-future.

**Current phase:** Phase 1 — FX Regime Lab v2 (see [[PHASES]]).

**Last updated:** 2026-04-18

## All docs

- [[PROJECT_OVERVIEW]]
- [[TECH_STACK]]
- [[FRONTEND_ARCHITECTURE]]
- [[DESIGN_SYSTEM]]
- [[DATABASE_SCHEMA]]
- [[PIPELINE_REFERENCE]]
- [[SIGNAL_DEFINITIONS]]
- [[CURSOR_RULES]]
- [[PHASES]]
- [[FEATURE_REGISTRY]]

## Top three priorities (Phase 1)

1. Wire `/` and `/brief` to live Supabase reads using `queries.ts` (collapse duplicate `.from()` calls in hooks and API route).
2. Add `loading.tsx` and `error.tsx` for shell and terminal route segments.
3. Align CI deploy with Cloudflare Pages for `web/` (or document an explicit dual deploy) so production matches root `wrangler.toml`.

## What this is

- A **daily-audited** FX regime practice desk with public validation rows and brief history.
- A **single-owner** research system where the pipeline is the write path and the website is the read path.
- A **long-horizon** project: credibility compounds from dated calls, not from marketing copy.
