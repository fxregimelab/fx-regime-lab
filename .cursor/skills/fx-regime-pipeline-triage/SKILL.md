---
name: fx-regime-pipeline-triage
description: >-
  Diagnoses and fixes FX Regime Lab pipeline failures in isolation without
  changing working modules. Use when GitHub Actions fails, Supabase shows data
  gaps or empty rows, the morning brief omits expected series, the user asks to
  debug the daily pipeline, or when investigating rows in pipeline_errors.
---

# FX Regime Lab — pipeline triage (subagent mode)

Act as a **triage agent**: find the single failing boundary, fix only that, prove it, then document. Do not refactor unrelated code.

## Invoke when

- GitHub Actions workflow fails or a step is red
- Supabase tables are stale, partial, or missing today’s rows
- Text/HTML morning brief shows gaps, placeholders, or missing charts
- The user points at `pipeline_errors` or asks why a step broke

## Evidence order (do this before editing code)

1. **Supabase `pipeline_errors`** — Query recent rows (explicit columns, never `select("*")`). Note `source`, error text, timestamps, and any `notes` / remediation fields. This is the institutional memory of failures.
2. **GitHub Actions logs** — Identify which step failed (`pipeline.py`, `cot_pipeline.py`, etc.) and the first exception / non-zero exit.
3. **Local traceback** — Reproduce by running the **failing script or step only** (see below), not the full chain, until the failure is understood.

## Hard rules

- **Isolate first** — Name the failing *step* and *file* before changing anything. If logs implicate `inr_pipeline.py`, do not “fix” `pipeline.py` unless evidence shows that file is the root cause.
- **Never break working scripts to unblock a broken one** — No silent defaults that hide upstream bugs, no removing validation in a green module, no reordering the global pipeline without explicit instruction.
- **Minimal diff** — Touch only lines required for the failure; preserve behavior elsewhere.
- **Python stack only** — Same dependency policy as the repo (pandas, numpy, requests, supabase-py, yfinance, scipy; no new packages without approval).

## Test order

1. Run the **failing module in isolation** — From repo root, prefer `python run.py --only <step>` when the step maps cleanly (see `run.py` `STEPS`), or `python <script>.py` if that is how the script is meant to run. Confirm exit 0 and expected artifacts (e.g. rows in `data/`, brief sections).
2. Only after isolation passes, run a **broader** slice (e.g. `--only fx cot merge`) or the full pipeline if the user needs end-to-end confirmation.

Execution order in this project is fixed: do not reorder `pipeline.py → cot_pipeline.py → …` in orchestrators unless the user explicitly requests it.

## Documentation in Supabase

After a confirmed fix (or a verified operational workaround):

- **Update `pipeline_errors`** with a clear narrative of **what failed**, **root cause**, and **what changed** (PR/commit reference if applicable).
- Prefer a dedicated **`notes`** (or equivalent free-text) column if it exists in the live schema. If the table only has `error_message` / `message`, append a structured suffix there *only if* that matches project convention—do not add columns without a migration. Align with [.cursor/skills/fx-regime-supabase-writes/SKILL.md](../fx-regime-supabase-writes/SKILL.md) for client env vars, upsert patterns, and explicit `select` lists.

## Output to the user

Summarize:

- Failure boundary (step + file)
- Evidence (GHA snippet / Supabase row / traceback line)
- Fix summary (1–3 bullets)
- How it was verified (isolation command + result)

## Related

- Supabase write and error-logging patterns: `fx-regime-supabase-writes` skill
- Orchestrator steps: `run.py` (`STEPS`, `NON_BLOCKING_STEPS`)
