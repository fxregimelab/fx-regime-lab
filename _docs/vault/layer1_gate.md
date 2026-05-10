# layer1_gate

## Purpose
Determines the macro environment for a given pair on a given day. Is the environment tradeable? Is vol expanding? Is there a structural instability?

## File
`pipeline/src/logic/layer1_gate.py` (~215 lines)

## Key Functions

### `run_layer1_gate(ctx)`
Main entry point. Returns `Layer1GateOutput` with:
- `regime`: the classified regime label
- `invalidated`: True if data is too stale to classify
- `z_rate`: rolling z-score of carry
- `m_rate`: momentum of carry
- `delta_pi`: breakeven inflation shock
- `d_spot`: spot return stress

### `regime_from_composite_snapshot(composite, pair, vol_expanding, prior_regime_label)`
Simpler path for notebooks/regressions. Uses composite hysteresis only, skipping Marcus staleness checks.

### `_tier_to_regime(pair, tier)`
Maps composite tier (0–4) to regime label. USDINR has its own INR_* labels.

## Mathematics

### Rolling Z-Score (252-day)
```
z_rate = (carry_t - mean(carry_{t-252:t})) / std(carry_{t-252:t})
```
- **Lookback:** 252 trading days (1 year)
- **Minimum periods:** 90
- **Why:** Captures annual rate cycles. 90-minimum ensures we don't compute z-scores with insufficient data.

### Momentum (20-day lag)
```
m_rate = carry_t - carry_{t-20}
```
- **Why:** Detects fading momentum even when levels are elevated.

### Breakeven Inflation Shock
```
delta_pi = BEI_t - BEI_{t-5}
```
- **Threshold:** |delta_pi| ≥ 0.12 (12 bps in 5 days)
- **Why:** Rapid inflation repricing signals policy divergence.

### Spot Stress
```
d_spot = zscore(log_returns(spot_{t-21:t}), 21d)
```
- **Threshold:** |d_spot| ≥ 2.5
- **Why:** Detects liquidity shocks independent of rate dynamics.

### Hysteresis Tiers
```
Tier 4: composite > +0.85        → RISK_OFF_DOLLAR_BID
Tier 3: +0.30 < composite ≤ +0.85 → GROWTH_SURPRISE_USD
Tier 2: -0.30 ≤ composite ≤ +0.30 → NEUTRAL
Tier 1: -0.85 ≤ composite < -0.30 → RISK_ON_DOLLAR_OFF
Tier 0: composite < -0.85        → RISK_ON_DOLLAR_OFF (strong)
```
- **Why hysteresis:** Prevents regime flickering when composite oscillates near thresholds. Once in Tier 3, you need to drop below +0.30 to exit (not just below +0.85).

## Invalidation Rules (Marcus A)

The gate is **invalidated** (forced to NEUTRAL) if:
- `rate_diff_2y` is None (missing data)
- `realized_vol_20d` is None (missing data)
- `carry_series` has < 252 points (insufficient history)
- `spot_series` has < 22 points (insufficient history)

**Why:** Trading on incomplete data is worse than not trading.

## Connections
- **Inputs from:** [[rate]] (carry), [[volatility]] (rv20), [[composite]] (composite score)
- **Outputs to:** [[classifier]] (UI metadata), [[layer2_directional]] (directional bias)
- **Uses math:** [[Z-Score]], [[Hysteresis Tiers]]
- **Tests:** `tests/test_layer1_gate.py`

## Why This Logic

Layer 1 exists to **prevent trading in wrong environments**. Most alpha destruction comes not from bad directional calls, but from making directional calls when the macro regime is unclear. The gate says "flat" when:
- Data is stale
- Vol is expanding (regime uncertain)
- Composite is near zero (no signal)
- Spot is stressed (liquidity event)

This is the most important layer for capital preservation.
