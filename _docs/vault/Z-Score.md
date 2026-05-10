# Z-Score

## Formula (Standard)
```
z = (x - μ) / σ
μ = mean(x)
σ = standard deviation(x)
```

## Formula (Robust MAD)
```
z = (x - median(x)) / (MAD * 1.4826)
MAD = median(|x_i - median(x)|)
```

## Why Robust MAD

Standard z-score uses mean and standard deviation, which are **sensitive to outliers**. A single policy shock (e.g., Fed emergency rate cut) can blow up the standard deviation for months, making all subsequent z-scores meaningless.

MAD (Median Absolute Deviation) is resistant to outliers because it uses medians, not means. The scale factor 1.4826 makes MAD comparable to standard deviation under normality.

## Where Used

| Module | Application | Lookback |
|--------|-------------|----------|
| [[rate]] | Rate spread normalization | 90d tactical, 10y structural |
| [[layer1_gate]] | Carry momentum z-score | 252d |
| [[math_utils]] | Generic robust z-score | Configurable |

## Thresholds

| |z| | Interpretation |
|------|---------------|
| > 2.0 | Extreme (top/bottom 2.5%) |
| 1.0–2.0 | Significant |
| 0.3–1.0 | Moderate |
| < 0.3 | Negligible |

In the model:
- `|z| > 0.30` → BULLISH/BEARISH (not NEUTRAL)
- `|z| > 1.15` → Elevated carry (regime classification)
- `|z| > 2.0` → Policy breakout (rare)

## Connections
- **Used in:** [[rate]], [[layer1_gate]], [[math_utils]]
- **Related:** [[MAD Normalization]]
