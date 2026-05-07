---
name: fx-regime-signal-pipeline
description: >-
  Scaffolds a new FX Regime Lab signal module. Use when adding a new daily
  signal pipeline or extending the quant pipeline.
---

# FX Regime Lab — New Signal Pipeline Module

## When this applies

Use only for **new** signal ETL modules. Confirm signal passes:
- institutional validity
- independence
- data availability
- regime relevance

## Deliverable shape

- **File**: `{signal_name}_pipeline.py` in `pipeline/src/signals/`
- **Stack**: Python only; approved deps only.
- **Persistence**: Supabase first (via `src/db/writer.py`), CSV fallback second.

## Required structure

```
fetch(...) → compute(...) → write via db/writer → return signal_dict
```

1. **`fetch(...)`** — Pull from API/files. Wrap every external call in try/except.
2. **`compute(...)`** — Derive signal: raw level, **260-trading-day rolling percentile**, direction, regime classification.
3. **Write via `src/db/writer.py`** — Use upsert with `on_conflict='date,pair'`.
4. **Return `signal_dict`** — Dict summarizing latest observation.

## Percentile (260-day window)

- 260-trading-day rolling window.
- Clip to **[0, 100]**.
- If < 260 obs, use `min(len(series), 260)`.

## `signal_dict` contents

| Key | Requirement |
|-----|-------------|
| `value` | Latest level (float or nullable) |
| `percentile` | 260-day percentile, clipped [0, 100] |
| `direction` | `BULLISH` / `BEARISH` / `NEUTRAL` |
| `regime` | String label consistent with framework taxonomy |

## Module docstring (required)

- **Inputs**: data sources, env vars, lookback, pairs covered.
- **Outputs**: Supabase table(s), shape of `signal_dict`.
- **Failure modes**: API timeout, partial history, NaNs, Supabase errors.

## Orchestration

- Add to `src/scheduler/orchestrator.py` in correct sequence position.
- New step goes after data dependencies exist and before brief generation.

## Checklist

- [ ] `{signal}_pipeline.py` follows fetch → compute → write → return.
- [ ] Percentile uses 260-day window and [0, 100] clip.
- [ ] `signal_dict` includes value, percentile, direction, regime.
- [ ] Writes through `src/db/writer.py` with upsert.
- [ ] Module docstring covers inputs, outputs, failure modes.
- [ ] Orchestrator order updated.
- [ ] `pytest` passes.
