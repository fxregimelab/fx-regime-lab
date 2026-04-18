---
name: regime-validation-logging
description: >-
  Defines Supabase logging for G10 regime predictions and next-day validation,
  timing rules (no backdating), and rolling 20-day accuracy in the morning
  brief. Use when implementing or changing regime_calls, validation_log,
  pipeline post-run hooks, validation jobs, or brief accuracy headers.
---

# Regime calls and validation logging

## When this applies

Use whenever you add or change:

- Writes after the daily pipeline (FX regime outputs)
- `regime_calls` or `validation_log` schema, upserts, or ETL
- A job that fills actual returns and correctness flags
- Morning brief text/HTML that shows hit-rate stats

Read `AGENTS.md` for orchestration; do not reorder the fixed pipeline sequence—**extend** it (e.g. a final step or scheduled follow-up job).

## Data flow (two beats)

1. **`regime_calls`** — Insert/upsert **immediately after each successful pipeline run** (same calendar run as `morning_brief` / regime output). One row per `(date, pair)` for that run’s predictions.
2. **`validation_log`** — Insert/upsert on the **next trading day** after prices needed to compute 1d (and 5d when available) returns are available. This row ties the **prior day’s call** to realized outcomes.

Never batch-write historical validation rows to pretend they were recorded on the correct day: **`created_at` reflects the real write time** (DB default `now()`). Do not backdate `created_at` or falsify row timing to “catch up.”

## Field contract

### `regime_calls` (at pipeline time)

Minimum alignment with the project plan: `date`, `pair`, regime label, `confidence`, supporting signals as designed in `PLAN.md` / schema.

Semantically the call must be recoverable for validation:

- Store **predicted_regime** as the table’s regime column (`regime` in SQL) if that is the canonical name.
- Store **predicted_direction** (`LONG` / `SHORT` / `NEUTRAL`) if the schema has a column; otherwise derive it consistently in code and persist it when `validation_log` is written so the pair `(date, pair)` matches `regime_calls`.

### `validation_log` (T+1 trading day)

Each row must include:

| Field | Role |
|-------|------|
| `date` | **Trading date of the original regime call** (the day being validated), not the day the row is written |
| `pair` | e.g. `EURUSD` |
| `predicted_direction` | Copied or derived from the call |
| `predicted_regime` | Copied from the call |
| `confidence` | Copied from the call |
| `actual_direction` | `UP` / `DOWN` / `FLAT` from realized 1d move (define threshold for FLAT consistently) |
| `actual_return_1d` | Forward 1 trading day return (%) |
| `actual_return_5d` | Forward 5 trading day return (%) when data exists; nullable until horizon completes |
| `correct_1d` | Boolean: predicted direction vs 1d outcome |
| `correct_5d` | Boolean: predicted direction vs 5d outcome (or defined rule—document in code) |

Use **upsert** with the project’s conflict target for daily tables (e.g. `on_conflict='date,pair'` where that is the unique key). Wrap Supabase calls in `try/except` so one failure does not kill the pipeline.

## Accuracy metrics (morning brief)

- Compute **rolling 20-trading-day hit rate** from `validation_log` (separate rates for 1d and 5d if both populated).
- Scope: define in code whether metrics are **per pair** and/or **aggregate**; the brief must show the agreed headline numbers **at the top** of every morning brief (text brief and HTML brief stay consistent).
- Use only rows with non-null `correct_1d` / `correct_5d` as appropriate for each metric.

## Implementation checklist

- [ ] Post-pipeline hook writes `regime_calls` for each pair with today’s `date` and real `created_at`
- [ ] Separate job or next-run step writes `validation_log` for **previous** session’s `date` on the next trading day
- [ ] No manual backdating of timestamps; no inserting “as of” past dates for audit fields
- [ ] Rolling 20d metrics queried before brief generation and injected at the **top** of `morning_brief` / `create_html_brief` output
- [ ] CSV fallback only where the rest of the repo already allows it; Supabase is primary for persistent tables

## Related project docs

- Table DDL and indexes: `contaxt files/PLAN.md` (Phase 0 Supabase section)
- Pipeline order and folders: `AGENTS.md`
