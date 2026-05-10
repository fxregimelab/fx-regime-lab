# COT Percentile

## Formula
```
cot_percentile = empirical_cdf_rank(cot_net_current, cot_net_history_3y) * 100
```

## Non-Commercial Net Positioning
```
cot_net = non_commercial_long - non_commercial_short
```

## Interpretation

| Percentile | Positioning | Contrarian Signal |
|------------|-------------|-------------------|
| > 97 | Crowded long | Strong BEARISH |
| 90–97 | Extended long | Moderate BEARISH |
| 55–90 | Neutral-long | Weak |
| 45–55 | Neutral | None |
| 10–45 | Neutral-short | Weak |
| 3–10 | Extended short | Moderate BULLISH |
| < 3 | Crowded short | Strong BULLISH |

## Why Contrarian?

Speculators (non-commercials) are **trend-followers**. They buy highs and sell lows. At extremes, they have no one left to trade with.

The academic evidence:
- Non-commercials increase longs as prices rise (momentum chasing)
- Commercials (hedgers) increase shorts as prices rise (hedging)
- At extremes, non-commercial positioning predicts reversals

## Lookback: 3 Years

- **Too short (< 1 year):** Misses historical extremes. Current positioning may seem extreme when it's not.
- **Too long (> 5 years):** Includes market structures that no longer exist (pre-QE, pre-zero rates).
- **3 years:** One full market cycle. Captures bull, bear, and neutral phases.

## Connections
- **Used in:** [[cot]], [[layer2_directional]]
- **Related:** [[Conviction Multiplier]] (crowding penalty)
