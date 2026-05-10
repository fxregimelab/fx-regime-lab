# layer2_directional

## Purpose
Computes directional bias (LONG/SHORT/NEUTRAL) and conviction (1–5) from composite score, rate signal, and positioning data.

## File
`pipeline/src/logic/layer2_directional.py` (~192 lines)

## Key Functions

### `run_layer2_directional(composite, z_tactical, z_structural, rate_direction, positioning_percentile, layer1_invalidated)`
Main entry point. Returns `Layer2DirectionalOutput` with:
- `directional_bias`: LONG / SHORT / NEUTRAL
- `conviction`: 1–5 integer
- `crowd_flag`: True if positioning is extreme
- `crowd_veto`: True if positioning is dangerously extreme
- `rate_positioning_clash`: True if Marcus B clash detected

### `effective_rate_sign(rate_direction, z_tactical, z_structural)`
Determines rate signal sign (+1, -1, 0). Prefers z-score when informative (> 0.12 EPS), falls back to BULLISH/BEARISH string.

### `crowding_metrics_pi(pi)`
Computes crowding probability, flag, and veto from COT percentile.

### `conviction_multiplier_pi(pi, p_crowd, rate_sign, pos_sign)`
Penalizes crowding and misalignment to produce final conviction multiplier.

## Mathematics

### Crowding Metrics
```
φ_upper(π) = max(0, (π - 90) / 10)    for π > 90
φ_lower(π) = max(0, (10 - π) / 10)    for π < 10
p_crowd = max(φ_upper, φ_lower)
crowd_flag = π ≥ 90 or π ≤ 10
crowd_veto = π ≥ 97 or π ≤ 3
```

### Marcus B Clash (Rate vs Positioning)
```
clash_b = rate_sign * pos_sign < 0
```
**Why:** If rates say BULLISH but positioning is already extremely long (crowded long), the edge is gone. The market has priced it in.

### Marcus C Clash (Composite vs Rate)
```
comp_sign = 1 if composite > 0.30 else (-1 if composite < -0.30 else 0)
clash_c = comp_sign * rate_sign < 0
```
**Why:** If the composite (which subsumes all signals) disagrees with the rate signal alone, the rate signal is likely noise.

### Conviction Multiplier
```
m_π = (1.0 - 0.48 * p_crowd) * align
align = 1.0 if rate_sign == pos_sign else 0.72
if pi is None: m_π *= 0.88
m_π = max(0.52, min(1.08, m_π))
```
- **Crowding penalty:** Up to 48% reduction when p_crowd = 1.0
- **Misalignment penalty:** 28% reduction when rate and positioning disagree
- **Missing data penalty:** 12% reduction when no COT data

### Conviction (1–5)
```
base_c = 3.0 + composite (clipped to [-2, 2])
c_float = base_c * m_π
if invalidated or crowd_veto or clash_b or clash_c:
    c_float = min(c_float, 3.0)  # cap at 3 when vetoed
c_float = max(1.0, min(5.0, c_float))
conviction = int(round(c_float))
```

### Direction Logic
```
if invalidated or crowd_veto or clash_b or clash_c:
    bias = NEUTRAL
elif abs(composite) > 0.30:
    bias = sign(composite)  # composite drives direction
elif rate_sign != 0:
    bias = sign(rate_sign)   # rate drives direction
else:
    bias = NEUTRAL
```

## Connections
- **Inputs from:** [[layer1_gate]] (invalidated flag), [[composite]] (composite score), [[rate]] (rate_direction), [[cot]] (positioning_percentile)
- **Outputs to:** [[layer3_execution]] (entry timing, sizing), [[writer]] (regime_calls.directional_bias, conviction)
- **Uses math:** [[Conviction Multiplier]], [[Marcus Invalidation]]
- **Tests:** `tests/test_layer2_directional.py`

## Why This Logic

Layer 2 exists to **measure the quality of the directional signal**, not just its sign. A BULLISH signal with conviction 1 is very different from a BULLISH signal with conviction 5:

| Conviction | Interpretation |
|------------|---------------|
| 1 | Weak signal, low confidence |
| 2 | Moderate signal, some crowding |
| 3 | Good signal, aligned |
| 4 | Strong signal, clear edge |
| 5 | Exceptional signal, rare |

The Marcus clash rules are the key innovation. They prevent the model from making directional calls when the signals disagree — which is exactly when human discretion performs worst.
