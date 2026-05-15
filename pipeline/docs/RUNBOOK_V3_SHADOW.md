# V3 Shadow Mode Runbook

**Version:** 1.0.0  
**Date:** 2026-05-15  
**Status:** Production Ready

---

## Overview

This runbook describes how to operate the FX Regime Lab pipeline in **v3 shadow mode** — running the new pair-specific model alongside the legacy v2 model without live capital allocation.

---

## Quick Start

### 1. Daily Pipeline (v2 + v3 shadow)

```bash
cd /path/to/fx-regime-lab/pipeline
./run_daily.sh --v3-shadow
```

This runs:
1. **v2 pipeline** (`src.scheduler.run_pipeline`) — the legacy orchestrator
2. **v3 shadow** (`src.pairs.runner --all --dry-run`) — pair-specific composites

### 2. Single-Pair V3 (for debugging)

```bash
# EURUSD only
python -m src.pairs.runner --pair EURUSD --date $(date +%Y-%m-%d)

# All pairs, verbose
python -m src.pairs.runner --all --verbose

# Backtest mode
python -m src.pairs.runner --pair EURUSD --backtest --start 2024-01-01 --end 2024-12-31
```

---

## Architecture

```
run_daily.sh --v3-shadow
    ├── src.scheduler.run_pipeline (v2)
    │   ├── run_daily (orchestrator)
    │   ├── overnight_check
    │   └── validation_aggregate
    └── src.pairs.runner --all --dry-run (v3 shadow)
        ├── EURUSD: fetch → composite → regime → execution
        ├── USDJPY: fetch → composite → regime → execution
        └── USDINR: fetch → composite → regime → execution
```

### Model Version Tagging

Regime calls are tagged in the `meta` JSONB column:

| Model | Query |
|-------|-------|
| v2 (legacy) | `SELECT * FROM regime_calls WHERE meta->>'model_version' = 'v2'` |
| v3 (pair-specific) | `SELECT * FROM regime_calls WHERE meta->>'model_version' = 'v3'` |

---

## Monitoring

### Daily Health Checks

Run after pipeline completion:

```sql
-- Count calls by model version today
SELECT
  meta->>'model_version' AS model,
  COUNT(*) AS n_calls,
  AVG(confidence) AS avg_confidence
FROM regime_calls
WHERE date = CURRENT_DATE
GROUP BY meta->>'model_version';
```

### Alert Thresholds

| Condition | Severity | Action |
|-----------|----------|--------|
| v3 shadow subprocess fails | WARNING | Check `pipeline_errors` table; v2 continues |
| v3 shadow timeout (>600s) | WARNING | Investigate fetcher latency |
| v2/v3 regime divergence on same pair | INFO | Log to `validation_log` for comparison |

### Shadow Comparison Query

```sql
-- Compare v2 vs v3 regimes for the same date
SELECT
  v2.pair,
  v2.regime AS v2_regime,
  v3.regime AS v3_regime,
  v2.confidence AS v2_conf,
  v3.confidence AS v3_conf,
  v2.signal_composite AS v2_score,
  v3.signal_composite AS v3_score
FROM regime_calls v2
LEFT JOIN regime_calls v3
  ON v2.pair = v3.pair AND v2.date = v3.date
  AND v3.meta->>'model_version' = 'v3'
WHERE v2.date = CURRENT_DATE
  AND v2.meta->>'model_version' = 'v2';
```

---

## Rollback

### Disable v3 shadow

```bash
# Edit run_daily.sh or pass no flags
./run_daily.sh   # runs v2 only
```

### Emergency stop

```bash
# Kill any running pair runner processes
pkill -f "src.pairs.runner"
```

---

## Troubleshooting

### "SUPABASE_URL not set"

Ensure `.env` is loaded:
```bash
export $(cat .env | xargs)
```

### "No spot bars for PAIR"

Check Polygon.io / Alpha Vantage API keys:
```bash
echo $POLYGON_API_KEY
echo $ALPHAVANTAGE_API_KEY
```

### v3 shadow returns non-zero

Check logs in `pipeline_errors`:
```sql
SELECT * FROM pipeline_errors
WHERE step LIKE '%shadow%'
ORDER BY created_at DESC
LIMIT 10;
```

---

## Next Phase Transition

**From Shadow → Paper Trading:**

1. Remove `--dry-run` from `run_pipeline.py` `_run_v3_shadow()`
2. Ensure v3 calls write to `regime_calls` with `meta = {"model_version": "v3", "shadow": false}`
3. Update UNIQUE constraint on `regime_calls` to include `model_version` extract
4. Run `supabase/migrations/20260515000001_shadow_to_live.sql`

**From Paper → Live:**

1. Allocate 10% capital to v3 signals
2. Keep v2 running as hedge
3. Monitor daily Sharpe >= 0.30 and max DD < -3%

---

*End of Runbook*
