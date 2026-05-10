# RVOL Rank

## Formula
```
rvol_rank = empirical_cdf_rank(rv20_current, rv20_history_3y) * 100
```

## Interpretation

| Rank | Vol Regime | Position Size |
|------|-----------|---------------|
| < 50 | Low vol | FULL |
| 50–70 | Elevated vol | HALF |
| > 70 | High vol | QUARTER |
| > 85 | Extreme vol | AVOID |

## Why Volatility Matters for Sizing

Volatility is **clustering** — high vol today predicts high vol tomorrow. The expected return per unit risk is lower in high-vol regimes.

| Vol Regime | Stop Distance | Win Rate | Expected Sharpe |
|-----------|--------------|----------|----------------|
| Low | Tight | Higher | Higher |
| High | Wide | Lower | Lower |

By sizing down in high vol, the model maintains consistent risk-adjusted returns.

## Empirical CDF

```
empirical_cdf(x, history) = count(history_i ≤ x) / len(history)
```

Non-parametric. No assumption about distribution shape. Works for fat-tailed FX returns.

## Connections
- **Used in:** [[volatility]], [[layer3_execution]]
- **Related:** [[layer3_execution]] (position sizing)
