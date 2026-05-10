# MAD Normalization

## Formula
```
MAD = median(|x_i - median(x)|)
Scaled MAD = MAD * 1.4826
```

## Why 1.4826

Under a normal distribution, `E[MAD] = σ / 1.4826`. Therefore, `MAD * 1.4826 ≈ σ`. This makes the robust z-score numerically comparable to the standard z-score.

## Comparison: Standard vs Robust

| Scenario | Standard Z-Score | Robust Z-Score |
|----------|-----------------|----------------|
| Clean data | Accurate | Accurate |
| One outlier | Blown up | Stable |
| Heavy tails | Inflated | Correct |
| FX yields (often have shocks) | Unreliable | Reliable |

## Example

Data: [1, 2, 3, 4, 100] — one outlier at 100

Standard:
- mean = 22, std = 43.5
- z(4) = (4 - 22) / 43.5 = -0.41

Robust:
- median = 3, MAD = median([2, 1, 0, 1, 97]) = 1
- z(4) = (4 - 3) / (1 * 1.4826) = +0.67

The robust z-score correctly identifies 4 as above median. The standard z-score is distorted by the outlier.

## Connections
- **Used in:** [[rate]], [[math_utils]]
- **Related:** [[Z-Score]]
