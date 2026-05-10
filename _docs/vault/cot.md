# cot

## Purpose
Computes CFTC Commitment of Traders positioning signals. The contrarian edge.

## File
`pipeline/src/signals/cot.py`  
Fetcher: `pipeline/src/fetchers/cot.py`

## Key Functions

### `compute_cot_signal(cot_net, cot_history)`
Normalizes COT net positioning to [-1, 1] using 3-year percentile.

### `compute_cot_percentile(cot_net, history)`
Returns percentile (0–100) of current net positioning.

## Mathematics

### COT Net Positioning
```
cot_net = non_commercial_long - non_commercial_short
```
- **Non-commercial:** Speculators (hedge funds, CTA, etc.)
- **Why non-commercial:** Commercials (hedgers) are offsetting business risk, not making directional bets.

### Percentile Ranking
```
cot_percentile = empirical_cdf_rank(cot_net, cot_history_3y) * 100
```
- **Lookback:** 3 years (156 weeks)
- **Why 3 years:** Captures a full market cycle without going so far back that the market structure has changed.

### Signal Normalization
```
cot_norm = (cot_percentile - 50) / 50  # maps [0, 100] to [-1, 1]
```
- **50th percentile:** Neutral (speculators are at median positioning)
- **0th percentile:** Extremely short → contrarian BULLISH signal
- **100th percentile:** Extremely long → contrarian BEARISH signal

## Crowding Interpretation

| Percentile | Interpretation | Signal |
|------------|---------------|--------|
| > 97 | Crowded long | Strong contrarian BEARISH |
| 90–97 | Extended long | Moderate contrarian BEARISH |
| 55–90 | Neutral-bullish | Weak signal |
| 45–55 | Neutral | No signal |
| 10–45 | Neutral-bearish | Weak signal |
| 3–10 | Extended short | Moderate contrarian BULLISH |
| < 3 | Crowded short | Strong contrarian BULLISH |

## Connections
- **Inputs from:** [[cot_fetcher]] (CFTC reports)
- **Outputs to:** [[composite]] (cot_norm), [[layer2_directional]] (positioning_percentile)
- **Uses math:** [[COT Percentile]], empirical CDF
- **Tests:** `tests/test_signals.py`

## Why This Logic

COT positioning is the **purest contrarian signal** in FX. When speculators are extremely long, they have no more buyers to sell to. The market is crowded. When they are extremely short, they have no more sellers to buy from. The market is washed out.

The academic evidence is strong:
- Speculators are trend-followers (they buy highs, sell lows)
- Commercials are contrarian (they hedge against trends)
- At extremes, speculator positioning predicts reversals

The 3-year lookback is important because:
- Too short: captures only the current trend, misses historical extremes
- Too long: includes market structures that no longer exist (e.g., pre-QE era)
