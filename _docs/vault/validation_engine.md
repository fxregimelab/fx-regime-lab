# validation_engine

## Purpose
Scores the accuracy of regime calls after the fact. T+5 and T+20 directional accuracy, Brier scores, and realized returns.

## File
`pipeline/src/validation/engine.py`

## Key Functions

### `log_return_bps(s0, sh)`
```
return = 10_000 * ln(sh / s0)   # in basis points
```

### `realized_direction(bps, deadband=5.0)`
```
if bps > 5:   UP
if bps < -5:  DOWN
else:         NEUTRAL
```
- **Deadband ±5 bps:** Avoids calling tiny moves directional. 5 bps = 0.05%.

### `is_correct(predicted, realized)`
```
BULLISH + UP    → CORRECT
BEARISH + DOWN  → CORRECT
NEUTRAL + NEUTRAL → CORRECT
else → WRONG
```

### `brier_score(confidence, correct)`
```
y = 1.0 if correct else 0.0
B = (confidence - y)²
```

## T+5 / T+20 Mechanics

1. **Call date (T=0):** Model makes a directional call with confidence
2. **T+5:** Look up spot price 5 trading days later
3. **Compute:** log_return_bps(T0, T+5), realized_direction, is_correct, brier_score
4. **T+20:** Same for 20 trading days
5. **Write:** Append to `validation_log`

## Why Log-Returns in Basis Points

1. **Symmetric:** A -1% move and a +1% move have equal magnitude.
2. **Additive:** Log-returns sum over time. Simple returns don't.
3. **Basis points:** 1 bp = 0.01%. Standard in FX. Easy to interpret.

## Why Brier Score

The Brier score measures **probabilistic calibration**:
- Perfect calibration: Brier = 0 (impossible in practice)
- Random guess (50% confidence, 50% accuracy): Brier = 0.25
- Overconfident (90% confidence, 50% accuracy): Brier = 0.41
- Well-calibrated (70% confidence, 70% accuracy): Brier = 0.21

Current model performance:
- T+5 Brier: ~0.25–0.28 (slightly overconfident but reasonable)
- T+20 Brier: ~0.26–0.29 (similar)

## Connections
- **Inputs from:** [[Database]] (`regime_calls` + `historical_prices`)
- **Outputs to:** [[Database]] (`validation_log`)
- **Used by:** [[validation_aggregate]] (stats computation), [[batch_validation_backfill]] (fast backfill)
- **Uses math:** [[Brier Score]], log-returns
- **Tests:** `tests/test_validation_engine.py`
