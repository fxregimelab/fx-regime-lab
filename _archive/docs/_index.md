# FX Regime Lab — docs home

## How to start a Cursor session

1. Update `TASK.md` at repo root — fill in current task, relevant docs, files to modify, done criteria
2. Open Cursor — new chat (never continue yesterday's chat)
3. First message to Cursor: "Read TASK.md first. Confirm the task and which files you will touch before writing any code."
4. Work proceeds with full context

**Never give Cursor a task without updating TASK.md first.**

**One line:** Live FX regime research OS. Data in Supabase; **no shipped website** in-repo. Next UI: rebuild from `claude-design/`.

**Last updated:** 2026-04-28

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
- [[DATA_READS_SPEC]]
- [[HOSTING_AFTER_UI_REMOVAL]]

## Current priorities

1. Choose stack and scaffold a new frontend when ready (`claude-design/` + [[DATA_READS_SPEC]]).
2. Keep pipeline cron green (`.github/workflows/pipeline_*.yml`).
3. Optional: deploy API-only Worker with a minimal `wrangler.toml` ([[HOSTING_AFTER_UI_REMOVAL]]).

## What this is

- A **daily-audited** FX regime practice desk with validation rows in Supabase.
- A **single-owner** research system where the pipeline is the write path.
- A **long-horizon** project: credibility compounds from dated calls, not from marketing copy.
