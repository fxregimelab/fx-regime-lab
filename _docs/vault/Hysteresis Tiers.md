# Hysteresis Tiers

## Problem

Without hysteresis, the regime would flicker between BULLISH and NEUTRAL every time the composite oscillates near +0.30. This creates noise, not signal.

## Solution

Once the composite crosses into a tier, it must cross the **opposite boundary** to exit. This creates stable regime regimes.

## Tier Map

```
Tier 4: composite > +0.85        → RISK_OFF_DOLLAR_BID
Tier 3: +0.30 < composite ≤ +0.85 → GROWTH_SURPRISE_USD
Tier 2: -0.30 ≤ composite ≤ +0.30 → NEUTRAL
Tier 1: -0.85 ≤ composite < -0.30 → RISK_ON_DOLLAR_OFF
Tier 0: composite < -0.85        → RISK_ON_DOLLAR_OFF (strong)
```

## Hysteresis in Action

**Scenario:** Composite rises from 0.20 to 0.35 to 0.25 to 0.40

Without hysteresis:
- 0.20 → NEUTRAL
- 0.35 → GROWTH_SURPRISE_USD
- 0.25 → NEUTRAL
- 0.40 → GROWTH_SURPRISE_USD

With hysteresis (prior = GROWTH_SURPRISE_USD):
- 0.20 → GROWTH_SURPRISE_USD (stays until drops below +0.30)
- 0.35 → GROWTH_SURPRISE_USD
- 0.25 → GROWTH_SURPRISE_USD
- 0.40 → GROWTH_SURPRISE_USD

The regime stays stable until there is a genuine shift below +0.30.

## USDINR Tiers

USDINR has its own regime labels:
- Tier 4: INR_DEPRECIATION_STRONG
- Tier 3: INR_DEPRECIATION_MODERATE
- Tier 2: INR_NEUTRAL
- Tier 1: INR_APPRECIATION_MODERATE
- Tier 0: INR_APPRECIATION_STRONG

## Connections
- **Used in:** [[layer1_gate]]
- **Related:** [[Composite Score]]
