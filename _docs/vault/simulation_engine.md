# simulation_engine

## Purpose
Walk-forward historical simulation. Replays the daily pipeline logic over every trading day using stored historical yields and spot prices.

## File
`pipeline/src/backfill/simulation_engine.py`

## Key Functions

### `run_pair_simulation(pair, start, end, yields_by_series)`
Main entry point. Loads spots, iterates days, computes all layers, batch writes to DB.

### `simulate_all_days(pair, start, end, yields_by_series)`
Core simulation loop. For each trading day:
1. Compute rate spreads from yields
2. Compute z-score from yield history
3. Compute vol from log returns
4. Compute composite
5. Run Layer 1/2/3
6. Collect results

### `_batch_write(pair, results)`
Batch inserts into `signals` and `regime_calls` via pg8000 direct SQL.

## Data Sources

| Source | Table | Coverage |
|--------|-------|----------|
| FRED yields | `historical_yields` | DGS2, DGS10, DE 10Y, JP 10Y, IN 10Y, T10YIE |
| FX spots | `historical_prices` | USDJPY 1996+, EURUSD 2003+, USDINR 2003+ |

## Simulation Coverage

| Pair | Days | Date Range |
|------|------|------------|
| USDJPY | 7,595 | 1997-01-30 to 2026-05-08 |
| EURUSD | 5,761 | 2004-02-23 to 2026-05-08 |
| USDINR | 3,736 | 2012-01-02 to 2026-05-08 |

## Limitations

1. **No COT data:** `cot_norm=None`, `oi_norm=None` for all historical rows
   - Composite still works: rate (40%) + vol (20%) + special (10%) = 70% weight
2. **Yield gaps:** JP yields from 1989, IN yields from 2011, DE yields monthly
   - Forward-fill handles gaps
3. **Model version:** Historical rows use `model_version='2.0-historical'`

## Key Bug Fixed

Originally, `carry_risk_adjusted_chronological` was passed as a single value `(rate_spread_10y,)` instead of a 252+ element series. This caused `Layer1Gate` to mark **100% of calls as invalidated**, forcing all regimes to NEUTRAL and all biases to NEUTRAL.

**Fix:** Maintain a running `carry_history` list and pass the full chronological series.

## Connections
- **Inputs from:** [[Database]] (`historical_prices`, `historical_yields`)
- **Outputs to:** [[Database]] (`signals`, `regime_calls`)
- **Uses:** [[layer1_gate]], [[layer2_directional]], [[layer3_execution]], [[composite]], [[confidence]]
- **Tests:** `tests/test_backfill.py`
