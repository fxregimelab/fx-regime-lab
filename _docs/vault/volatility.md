# volatility

## Purpose
Computes realized volatility signals, vol rank, and vol expanding flag. Essential for regime classification and position sizing.

## File
`pipeline/src/signals/volatility.py`

## Key Functions

### `compute_rvol(volumes)`
Realized volatility from volume data.

### `compute_vol_signal(rv5, rv20, vol_90th)`
Maps vol metrics to signal label.

### `empirical_cdf_rank(current, history)`
Percentile rank of current value in historical distribution.

### `realized_vol21_series_annualized_pct(log_returns)`
21-day realized vol annualized in percentage.

## Mathematics

### Realized Volatility (20-day)
```
rv20 = std(log_returns_{t-20:t}) * sqrt(252) * 100
```
- **Annualization:** sqrt(252) converts daily to annual
- **Percentage:** *100 for readability

### Volatility Signal
```
if rv5 > rv20 and rv20 > vol_90th:
    vol_signal = VOL_EXPANDING
elif rv20 < vol_10th:
    vol_signal = VOL_COMPRESSING
else:
    vol_signal = NEUTRAL
```
- **Vol expanding:** Short-term vol > long-term vol AND long-term vol is historically high
- **Why this matters:** Vol expansion precedes regime shifts. The model stays NEUTRAL when vol is expanding.

### RVOL Rank
```
rvol_rank = empirical_cdf_rank(rv20, rv20_history_3y) * 100
```
- **Why 3 years:** Matches the COT percentile lookback for consistency.

## Connections
- **Inputs from:** [[fx_spot]] (price history for log returns)
- **Outputs to:** [[composite]] (vol_norm), [[layer1_gate]] (vol_expanding flag), [[layer3_execution]] (position sizing)
- **Uses math:** [[RVOL Rank]], empirical CDF
- **Tests:** `tests/test_signals.py`

## Why This Logic

Volatility is not a directional signal — it is a **regime filter**. The model uses vol to answer: "Is the market calm enough to trade?"

High vol means:
- Wider stops needed (Layer 3 sizes down)
- Regime uncertainty (Layer 1 may invalidate)
- Noise dominates signal (Layer 2 caps conviction)

Low vol means:
- Tighter stops possible (Layer 3 sizes up)
- Regime is stable (Layer 1 is more confident)
- Signal is clear (Layer 2 can have high conviction)
