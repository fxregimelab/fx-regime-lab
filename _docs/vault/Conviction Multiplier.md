# Conviction Multiplier

## Formula
```
m_π = (1.0 - 0.48 * p_crowd) * align

p_crowd = max(φ_upper(π), φ_lower(π))
align = 1.0 if rate_sign == pos_sign else 0.72
```

## Crowding Ramp

```
φ_upper(π) = max(0, (π - 90) / 10)    # upper tail ramp
φ_lower(π) = max(0, (10 - π) / 10)    # lower tail ramp
```

| Percentile | p_crowd | Crowding Penalty |
|------------|---------|-----------------|
| 50 | 0.0 | 0% |
| 90 | 0.0 | 0% |
| 95 | 0.5 | 24% |
| 97 | 0.7 | 34% |
| 100 | 1.0 | 48% |

## Alignment Factor

| Rate Sign | Positioning Sign | align |
|-----------|-----------------|-------|
| +1 (BULLISH) | +1 (long) | 1.00 |
| +1 (BULLISH) | -1 (short) | 0.72 |
| -1 (BEARISH) | +1 (long) | 0.72 |
| -1 (BEARISH) | -1 (short) | 1.00 |

**Why 0.72:** When rate and positioning disagree, the signal is weaker. The market may already be positioned against the rate view.

## Missing Data Penalty

If positioning percentile is None (no COT data):
```
m_π *= 0.88
```

## Range

```
m_π ∈ [0.52, 1.08]
```

## Impact on Conviction

```
base_c = 3.0 + composite (clipped to [-2, 2])
conviction = round(base_c * m_π)
```

| Composite | m_π = 1.0 | m_π = 0.72 | m_π = 0.52 |
|-----------|-----------|------------|------------|
| +2.0 | 5 | 4 | 3 |
| +1.0 | 4 | 3 | 2 |
| 0.0 | 3 | 2 | 2 |
| -1.0 | 2 | 2 | 1 |
| -2.0 | 1 | 1 | 1 |

## Connections
- **Used in:** [[layer2_directional]]
- **Related:** [[COT Percentile]], [[Marcus Invalidation]]
