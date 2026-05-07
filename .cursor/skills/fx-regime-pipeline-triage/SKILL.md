---
name: fx-regime-pipeline-triage
description: >-
  Diagnoses and fixes FX Regime Lab pipeline failures in isolation.
  Use when Prefect run fails, Supabase shows data gaps, or brief omits series.
---

# FX Regime Lab — Pipeline Triage

Act as a **triage agent**: find the single failing boundary, fix only that, prove it, then document.

## Invoke when

- Prefect Cloud run fails or a step is red
- Supabase tables are stale, partial, or missing today's rows
- Text/HTML brief shows gaps or missing data
- `pipeline_errors` table has new rows

## Evidence order

1. **Supabase `pipeline_errors`** — Query recent rows (explicit columns). Note `source`, error text, timestamps.
2. **Prefect logs** — Identify which flow/step failed and first exception.
3. **Local traceback** — Reproduce by running the failing script in isolation.

## Hard rules

- **Isolate first** — Name the failing step and file before changing anything.
- **Never break working scripts** to unblock a broken one.
- **Minimal diff** — Touch only lines required for the failure.
- **Python stack only** — Same deps as repo (pandas, numpy, requests, supabase-py, yfinance, scipy).

## Test order

1. Run failing module in isolation: `python -m pipeline.src.fetchers.<module>` or relevant script.
2. After isolation passes, run broader slice or full `pytest`.

## Documentation

After a confirmed fix:
- Update `pipeline_errors` with: what failed, root cause, what changed.
- Log to `notes` column if available.

## Output format

- Failure boundary (step + file)
- Evidence (Prefect snippet / Supabase row / traceback)
- Fix summary (1–3 bullets)
- Verification command + result
