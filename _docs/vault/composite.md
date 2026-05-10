# composite

## Purpose
Aggregates individual signals (rate, COT, vol, OI) into a single composite score that drives regime classification and directional bias.

## File
`pipeline/src/regime/composite.py`

## Key Functions

### `compute_composite(rate_norm, cot_norm, vol_norm, oi_norm, pair, special_signal)`
Returns the composite score (float, typically -2 to +2).

### `compute_dynamic_betas(historical_rows)`
Computes adaptive weights based on recent signal performance.

### `get_primary_driver(betas)`
Returns which signal family is currently dominant.

## Mathematics

### Static Weights (Fallback)
```
S = 0.40 * rate_norm + 0.20 * cot_norm + 0.20 * vol_norm + 0.10 * oi_norm + 0.10 * special_signal
```
- **Rate 40%:** Dominant driver. Rate differentials are the most persistent FX driver.
- **COT 20%:** Positioning extremes are powerful contrarian signals.
- **Vol 20%:** Vol regime affects all strategies.
- **OI 10%:** Flow confirmation.
- **Special 10%:** Pair-specific shocks (inflation, policy surprises).

### Dynamic Betas (Preferred)
```
β_i = correlation(signal_i_returns, pair_returns) over 90 days
β_i = max(0, β_i)  # no negative weights
β_i = β_i / sum(β_i)  # normalize to sum to 1
```
- **Why dynamic:** If COT has been more predictive than rate recently, COT gets more weight.
- **Floor:** Minimum weight of 0.05 for any signal to prevent overfitting to recent noise.

### Missing Data Handling
If a signal is None (e.g., no COT data), its weight is redistributed proportionally to the other signals. The composite still computes.

## Connections
- **Inputs from:** [[rate]], [[cot]], [[volatility]], [[open_interest]], [[special]]
- **Outputs to:** [[layer1_gate]] (regime classification), [[layer2_directional]] (directional bias), [[confidence]] (confidence computation)
- **Tests:** `tests/test_regime.py`

## Why This Logic

The composite is the **core information fusion** of the model. It answers: "Given all available signals, what is the net directional pressure?"

Static weights are the fallback because they represent institutional consensus on signal importance. Dynamic betas are preferred because they adapt to changing market regimes — what worked in 2022 (rate-driven) may not work in 2026 (positioning-driven).
