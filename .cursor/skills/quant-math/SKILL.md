---
name: quant-math
description: >-
  Enforces mathematical conventions for FX Regime Lab quant pipeline.
  Use when implementing signals, regime logic, or statistical computations.
---

# Quant Math Conventions

## Data types

- Use `np.float64` explicitly.
- Vectorized operations preferred over loops.
- Rolling statistics must be causal (today scored against t-1 history only).

## Percentiles

- **260-trading-day** rolling window (52 weeks).
- Clip result to **[0, 100]**.
- If < 260 obs, use `min(len(series), 260)`.
- Use `scipy.stats.percentileofscore` or equivalent with `method='strict'`.

## Returns

- Log returns: `np.log(p_t / p_{t-1})` for FX spot.
- Forward returns computed from entry date, not calendar date.
- Define "FLAT" threshold consistently (e.g., |return| < 0.05%).

## Z-scores

- Causal rolling mean and std (t-1 window).
- Handle zero std by returning 0 or NaN, never inf.

## Regime classification

- Layer 1 (Regime Gate): macro environment from rate differential momentum, CB posture, growth divergence.
- Layer 2 (Directional): COT percentiles, crowding flags, rate/positioning alignment. Conviction 1–5.
- Layer 3 (Execution): vol rank, RR skew, ADR/MIE proxies. Entry timing, stops, sizing.

## Signal thresholds

Document all thresholds in module docstring:
- Bullish / Bearish / Neutral percentile cutoffs
- Regime label mapping
- Confidence multiplier rules

## Checklist

- [ ] Uses `np.float64`.
- [ ] Causal windows only.
- [ ] Percentiles clipped [0, 100].
- [ ] Zero-std handled gracefully.
- [ ] All thresholds documented.
- [ ] `pytest` passes.
