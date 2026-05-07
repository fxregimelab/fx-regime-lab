---
name: regime-validation-logging
description: >-
  Defines Supabase logging for regime predictions and T+1/T+5 validation.
  Use when implementing or changing regime_calls, validation_log, or accuracy stats.
---

# Regime Calls and Validation Logging

## Data flow (two beats)

1. **`regime_calls`** — Upsert after each pipeline run. One row per `(date, pair)`.
2. **`validation_log`** — Upsert on next trading day after prices available for forward returns.

Never backdate `created_at`. It reflects real write time.

## `regime_calls` fields

- `date`, `pair`, `regime`, `confidence`, `predicted_direction` (LONG/SHORT/NEUTRAL)
- Supporting signals as designed in schema.

## `validation_log` fields

| Field | Role |
|-------|------|
| `date` | Trading date of original call |
| `pair` | e.g. `EURUSD` |
| `predicted_direction` | From call |
| `predicted_regime` | From call |
| `confidence` | From call |
| `actual_direction` | `UP` / `DOWN` / `FLAT` from realized 1d move |
| `actual_return_1d` | Forward 1d return (%) |
| `actual_return_5d` | Forward 5d return (%) when available |
| `correct_1d` | Boolean |
| `correct_5d` | Boolean |

Use upsert with `on_conflict='date,pair'`. Wrap in try/except.

## Accuracy metrics

- Rolling **20-trading-day** hit rate from `validation_log`.
- Per pair and/or aggregate as agreed.
- Show at **top** of every morning brief.

## Checklist

- [ ] Post-pipeline writes `regime_calls`
- [ ] Next-day job writes `validation_log`
- [ ] No backdating of timestamps
- [ ] Rolling 20d metrics computed before brief generation
- [ ] Supabase is primary; CSV fallback only where repo already allows
