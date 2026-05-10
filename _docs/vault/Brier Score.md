# Brier Score

## Formula
```
B = (p - y)²

p = model confidence (0–1)
y = outcome: 1.0 (correct), 0.0 (wrong), 0.5 (neutral)
```

## Interpretation

| Brier | Calibration |
|-------|-------------|
| 0.00 | Perfect (impossible) |
| 0.04 | Excellent (90% conf, 90% correct) |
| 0.09 | Good (70% conf, 70% correct) |
| 0.16 | Fair (60% conf, 60% correct) |
| 0.25 | Random (50% conf, 50% correct) |
| > 0.25 | Worse than random (overconfident) |

## Brier Skill Score
```
Skill = (0.25 - Brier) / 0.25
```
- **0.0:** No better than random
- **1.0:** Perfect calibration
- **Negative:** Worse than random

## Why This Metric

The Brier score is the **standard metric for probabilistic forecasting** in meteorology, epidemiology, and finance. It measures not just whether you were right, but whether your confidence matched your accuracy.

A model that says "I'm 90% confident" and is right 90% of the time is more valuable than a model that says "I'm 90% confident" and is right 50% of the time — even if both have the same hit rate.

## Current Performance

| Pair | T+5 Brier | T+5 Skill | T+20 Brier | T+20 Skill |
|------|-----------|-----------|------------|------------|
| EURUSD | 0.247 | +1.2% | 0.253 | +1.2% |
| USDJPY | 0.279 | -11.6% | 0.286 | -14.4% |
| USDINR | 0.230 | +8.0% | 0.242 | +3.2% |
| ALL | 0.256 | -2.4% | 0.264 | -5.6% |

**Interpretation:** The model is slightly overconfident overall (Brier > 0.25 for USDJPY and ALL). EURUSD and USDINR are reasonably calibrated.

## Connections
- **Used in:** [[validation_engine]], [[validation_aggregate]]
- **Depends on:** [[confidence]] (the p in the formula)
- **Related:** [[Sharpe-Like Ratio]] (return-based metric)
