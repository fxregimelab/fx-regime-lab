# TASK.md — Current Sprint

**Phase:** 6 — COMPLETE
**Started:** 2026-04-26
**Status:** Complete

## Active Tasks

- [x] Phase 6 — Mobile polish, PWA manifest, terminal live data (no `MOCK_` under `app/`)

## Completed

- [x] Phase 0–5 complete
- [x] `getLastPipelineRun`, terminal index + terminal fx-regime live Supabase
- [x] Mobile horizontal scroll (heatmap, brief tabs, performance/calendar chips, home hint)
- [x] PWA `manifest.json`, icons, root `metadata` + `viewport`

## Notes

Site is feature-complete. See post-Phase 6 checklist under **Scheduling → Post-Phase 6 (manual)** in AGENTS.md.

Design reference for loading states: `claude-design/FX Regime Lab/loading-states.jsx`
Design reference for error states:   `claude-design/FX Regime Lab/error-states.jsx`
Supabase types: run `supabase gen types typescript --local > web/lib/supabase/database.types.ts`
NEVER edit database.types.ts manually.
ALL supabase.from() calls go in `web/lib/supabase/queries.ts` ONLY.
