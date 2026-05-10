# Marcus Invalidation

## The Three Marcus Rules

Named after Marcus (Macro PM persona), who represents the risk master's perspective on tradeability.

### Marcus A — Stale Data Invalidation
```
if carry_series.size < 252 or spot_series.size < 22:
    invalidated = True
```
- **Why:** Trading on incomplete history is worse than not trading. The z-score and momentum need sufficient data.

### Marcus B — Rate vs Positioning Clash
```
clash_b = rate_sign * pos_sign < 0
```
- **Why:** If rates say BULLISH but positioning is already extremely long, the edge is gone. The market is crowded.
- **Example:** Fed is hiking (BULLISH USD) but COT shows speculators are 97th percentile long USD. Everyone who wants to buy USD already has.

### Marcus C — Composite vs Rate Clash
```
comp_sign = 1 if composite > 0.30 else (-1 if composite < -0.30 else 0)
clash_c = comp_sign * rate_sign < 0
```
- **Why:** The composite subsumes ALL signals (rate, COT, vol, OI). If the composite disagrees with the rate signal alone, the rate signal is likely noise.
- **Example:** Rate z-score is +0.5 (BULLISH) but composite is -0.4 because COT is extremely short and vol is expanding. The composite wins.

## Effect of Invalidation

When ANY Marcus rule triggers:
```
if invalidated or clash_b or clash_c:
    directional_bias = NEUTRAL
    conviction = min(conviction, 3)  # cap at 3
```

## Connections
- **Used in:** [[layer1_gate]] (Marcus A), [[layer2_directional]] (Marcus B, C)
- **Related:** [[Conviction Multiplier]], [[layer2_directional]]
