# layer3_execution

## Purpose
Determines entry timing, stop levels, and position sizing from realized volatility, skew, and market microstructure.

## File
`pipeline/src/logic/layer3_execution.py` (~234 lines)

## Key Functions

### `run_layer3_execution(layer2, spot, spot_bars, realized_vol_rank, risk_reversal_series_bps)`
Main entry point. Returns execution dict with:
- `entry_timing`: IMMEDIATE / WAIT / AVOID
- `position_size`: FULL / HALF / QUARTER / FLAT
- `stop_level`: price level for stop-loss
- `realized_vol_rank`: current RVOL percentile
- `skew_alignment`: skew direction vs bias alignment

## Mathematics

### RVOL Rank (Realized Volatility Percentile)
```
rvol_rank = empirical_cdf(rv20_current, rv20_history_3y) * 100
```
- **Why:** High RVOL (>70th percentile) means the market is volatile. Size down.
- **Sizing rule:**
  - rvol_rank < 50 → FULL size
  - rvol_rank 50–70 → HALF size
  - rvol_rank > 70 → QUARTER size

### Skew Reversal
```
skew_alignment = 1 if (bias == LONG and skew < 0) or (bias == SHORT and skew > 0)
                  -1 if opposite
                   0 if neutral
```
- **Why:** Risk reversal skew tells you what the options market is pricing. If skew is negative (puts expensive) and you're LONG, the market is hedging downside — confirming your bias.

### MIE Proxy (Maximum Intraday Excursion)
```
stop_distance = max(1.5 * ATR20, 0.3% of spot)
stop_level = spot - stop_distance (for LONG)
             spot + stop_distance (for SHORT)
```
- **Why:** The stop must be wide enough to avoid noise (hence 1.5× ATR) but tight enough to limit loss (hence 0.3% cap).

### Entry Timing
```
if layer1_invalidated or rvol_rank > 85:
    timing = AVOID
elif skew_alignment > 0 and rvol_rank < 60:
    timing = IMMEDIATE
else:
    timing = WAIT
```
- **AVOID:** Don't enter when vol is spiking or gate is invalidated
- **IMMEDIATE:** Enter when skew confirms bias and vol is calm
- **WAIT:** Otherwise wait for better entry

## Connections
- **Inputs from:** [[layer2_directional]] (bias, conviction), [[volatility]] (rv20, rv_rank), [[fx_spot]] (spot price, bars)
- **Outputs to:** [[writer]] (regime_calls.entry_timing, stop_level, position_size)
- **Uses math:** [[RVOL Rank]], empirical CDF
- **Tests:** `tests/test_layer3_execution.py`

## Why This Logic

Layer 3 exists because **being right on direction is not enough**. You also need:
1. **Good entry timing** — entering at the wrong time turns a correct directional call into a loss
2. **Proper sizing** — betting the same size in calm and volatile markets is irrational
3. **Defined stops** — without stops, one wrong call destroys the track record

The model sizes down in high vol because volatility clustering means high vol today predicts high vol tomorrow. The expected return per unit risk is lower.
