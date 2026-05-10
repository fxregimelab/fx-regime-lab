# rate

## Purpose
Computes yield spread signals from Treasury yields. The dominant driver of G10 FX.

## File
`pipeline/src/signals/rate.py` (~234 lines)

## Key Functions

### `rate_direction_from_spreads(spread_2y, spread_10y, z_tactical)`
Maps rate spread to BULLISH/BEARISH/NEUTRAL.

### `build_carry_history_from_rows(historical_rows)`
Builds risk-adjusted carry history (2Y / RV20).

### `median_abs_deviation(values)`
Robust MAD about the median.

## Mathematics

### Rate Spread
```
rate_spread_10y = US_10Y - Quote_10Y
rate_spread_2y = US_2Y - Quote_2Y
```
- EURUSD: US vs Germany
- USDJPY: US vs Japan
- USDINR: US vs India

### Robust MAD Z-Score
```
z = (spread_t - median(spread_history)) / (MAD * 1.4826)
MAD = median(|spread_i - median(spread)|)
```
- **Why MAD:** More resistant to outliers than standard deviation. A single policy shock doesn't blow up the z-score.
- **Scale factor 1.4826:** Makes MAD comparable to standard deviation under normality.

### Tactical Z-Score (90-day)
```
z_tactical = MAD_zscore(spread, 90 days)
```
- **Why 90 days:** Captures quarterly rate cycles. Detects recent shifts.

### Structural Z-Score (10-year)
```
z_structural = MAD_zscore(spread, 10 years)
```
- **Why 10 years:** Captures secular trends. Detects when spreads are historically extreme.

### Direction Mapping
```
if z_tactical > 0.30:  BULLISH
if z_tactical < -0.30: BEARISH
else:                   NEUTRAL
```
- **Threshold ±0.30:** Avoids always-BULLISH bias from persistent differentials (e.g., USDJPY ~+3pp for years).

## Connections
- **Inputs from:** [[yields]] (FRED data)
- **Outputs to:** [[composite]] (rate_norm), [[layer2_directional]] (rate_direction, z_tactical)
- **Uses math:** [[Z-Score]], [[MAD Normalization]]
- **Tests:** `tests/test_signals.py`

## Why This Logic

Rate differentials are the **most persistent driver of G10 FX**. The academic foundation is Uncovered Interest Rate Parity (UIP), which states that currencies with higher yields should depreciate. In practice, UIP fails — high-yield currencies tend to appreciate because carry trades attract capital.

The z-score approach is superior to raw spread levels because:
1. It detects **changes**, not levels. A +3pp spread that was +1pp a year ago is BULLISH. A +3pp spread that was +4pp a year ago is BEARISH.
2. It normalizes across pairs. USDJPY's +3pp and EURUSD's +1pp are not directly comparable, but their z-scores are.
