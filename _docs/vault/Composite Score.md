# Composite Score

## Formula

### Static Weights (Fallback)
```
S = 0.40 * rate_norm + 0.20 * cot_norm + 0.20 * vol_norm + 0.10 * oi_norm + 0.10 * special_signal
```

### Dynamic Betas (Preferred)
```
β_i = max(0, correlation(signal_i_returns, pair_returns, 90d))
β_i = β_i / sum(β_i)  # normalize
S = Σ β_i * signal_i
```

## Signal Weights

| Signal | Static Weight | Why |
|--------|--------------|-----|
| Rate | 40% | Most persistent FX driver |
| COT | 20% | Best contrarian signal |
| Vol | 20% | Regime filter |
| OI | 10% | Flow confirmation |
| Special | 10% | Pair-specific shocks |

## Dynamic Adaptation

Dynamic betas adapt to which signal has been most predictive recently. If COT has outperformed rate in the last 90 days, COT gets more weight.

**Floor:** Minimum weight of 0.05 for any signal. Prevents overfitting to recent noise.

## Missing Data

If a signal is None (e.g., no COT data), its weight is redistributed proportionally to the other signals. The composite still computes.

## Range

Typical composite range: **-2.0 to +2.0**

| Composite | Interpretation |
|-----------|---------------|
| > +0.85 | Strong USD bullish |
| +0.30 to +0.85 | Moderate USD bullish |
| -0.30 to +0.30 | Neutral |
| -0.85 to -0.30 | Moderate USD bearish |
| < -0.85 | Strong USD bearish |

## Connections
- **Computed in:** [[composite]]
- **Inputs from:** [[rate]], [[cot]], [[volatility]], [[open_interest]], [[special]]
- **Outputs to:** [[layer1_gate]], [[layer2_directional]], [[confidence]]
