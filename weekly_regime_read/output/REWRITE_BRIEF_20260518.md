# FX Regime Lab — AI Rewrite Brief (2026-05-18)

## Mission
Rewrite the script-generated draft into a practitioner-grade weekly regime read.
Keep the data tables, scorecard, and bullet points. Rewrite ALL prose paragraphs.

## Data Snapshot
## Data Snapshot

**Cross-asset:** DXY 98.0999984741211, VIX 17.479999542236328, Brent $90.37999725341795, Gold $4857.60009765625, US 10Y 4.32%

**EUR/USD:**
  Regime: NEUTRAL | Composite: -0.291 | Confidence: 30%
  Direction: BEARISH | Bias: SHORT | Driver: COT positioning is the primary driver
  Spot: 1.176747441291809 | Rate diff 10Y: 1.2453917254000002
  COT pct: 55.76923076923077 | COT net: 25382.0 | Vol rank: 87.16931216931218%
  Stop: 1.1706145 | Entry: ENTER | Position: HALF

**USD/JPY:**
  Regime: RISK_ON_DOLLAR_OFF | Composite: -0.859 | Confidence: 50%
  Direction: BEARISH | Bias: SHORT | Driver: Rate differential is the primary driver
  Spot: 158.58399963378906 | Rate diff 10Y: None
  COT pct: 34.61538461538461 | COT net: -54445.0 | Vol rank: 18.65079365079365%
  Stop: 160.374075 | Entry: WAIT | Position: HALF

**USD/INR:**
  Regime: INR_NEUTRAL__VOL_EXPANDING | Composite: -0.111 | Confidence: 30%
  Direction: BEARISH | Bias: SHORT | Driver: Rate differential is the primary driver
  Spot: 92.5749969482422 | Rate diff 10Y: -2.79
  COT pct: None | COT net: None | Vol rank: 100.0%
  Stop: 96.8814375 | Entry: ENTER | Position: HALF


## Script Draft (for reference — DO NOT copy its prose)
```
# USD/JPY Bearish Composite at -0.86

*The USD/JPY rate differential reads risk on dollar off with a short bias, while cross-asset correlations held steady.*

May 18, 2026

USD/JPY composite reads -0.859. The framework has a bearish bias. The market has not priced it.

## Framework Scorecard

| Signal | Date Flagged | Status | Pips/Points Since |
|---|---|---|---|
| USDJPY - RISK_ON_DOLLAR_OFF (BEARISH) | Rate differential. | 2026-05-15 | Awaiting | +0 bps (+0.00 pip) |
| USDINR - INR_NEUTRAL__VOL_EXPANDING (BEARISH) | Rate diff. | 2026-05-15 | Awaiting | +0 bps (+0.00 paise) |
| EURUSD - NEUTRAL (NEUTRAL) | COT positioning is the prima. | 2026-05-15 | Awaiting | +0 bps (+0.00 pip) |

EUR/USD: EUR/USD risk on dollar off with composite at -0.98. Confirmed. USD/INR: USD/INR inr appreciation moderate with composite at -0.45. Invalidated. The framework moves on. USD/JPY: USD/JPY risk on dollar off with composite at -0.51. Invalidated. The framework moves on.

## Cross-Asset Context

DXY at 98.10. US 10Y at 4.32%. Brent at $90.38. VIX at 17.5. Complacent. Gold at $4,857.60. The dollar is soft and vol is low. The framework reads this as a regime where carry is fragile.

## Yen Strength Is Outrunning Its Fundamentals

USD/JPY reads Risk On Dollar Off at -0.859. Spot closed at 158.5840, -0.14% on the week. Rate differential is the primary driver.

Net positioning is -54,445.0 contracts. Confidence is 50%. The framework is not committing size.

Special signal: VIX_funding_stress.

## EUR/USD Holds Its Regime

EUR/USD reads Neutral at -0.291. Spot closed at 1.1767, -0.35% on the week. The US-DE 10Y spread is +1.25%. COT is the primary driver.

Net positioning is +25,382.0 contracts. Realized vol is at the 87% percentile. Elevated but readable. Confidence is 30%. The framework is not committing size.

## USD/INR Waits for RBI

USD/INR reads INR Neutral Vol Expanding at -0.111. Spot is at 92.5750. The US-IN 10Y spread is -2.79%. Rate differential is the primary driver.

Realized vol is at the 100% percentile. The signal is degraded. Confidence is 30%. The framework is not committing size.

Special signal: EM_oil_DXY.

## What The Framework Is Watching

- USD/JPY composite at -0.859: If it crosses -0.5, the framework moves to full sizing.
- EUR/USD COT at 56th percentile: If it hits 20, the framework flags a positioning trap.
- USD/INR rate differential at -2.79%: If it moves 20 bps, the regime read changes.

The framework does not predict. It measures. The measurement is done.
```

## Web Research Context
No web research results available.

## Thin Spots to Fix
- [ ] Missing explicit reconciliation: 'The signal and price agree' not found in draft.
- [ ] Missing explicit reconciliation: 'The divergence is the story' not found in draft.
- [ ] Hook uses generic fallback: 'the market has not priced it' — rewrite with specific tension.

## Track Record Context
[
  {
    "pair": "EURUSD",
    "call": "EUR/USD risk on dollar off with composite at -0.98",
    "outcome": "confirmed",
    "call_date": "2026-05-08",
    "predicted_direction": "BEARISH"
  },
  {
    "pair": "USDINR",
    "call": "USD/INR inr appreciation moderate with composite at -0.45",
    "outcome": "invalidated",
    "call_date": "2026-05-10",
    "predicted_direction": "BEARISH"
  },
  {
    "pair": "USDJPY",
    "call": "USD/JPY risk on dollar off with composite at -0.51",
    "outcome": "invalidated",
    "call_date": "2026-05-10",
    "predicted_direction": "BEARISH"
  }
]

## Rewrite Rules
1. **Opening hook:** Must create immediate tension. Use one of: unexpected number, ticking clock, or framing correction.
2. **Data first:** Every claim must have a number in the same or next sentence.
3. **Reconciliation:** For each pair, explicitly state whether framework signal and price action agree or diverge — and why.
4. **Cross-asset spine:** Tie the three pairs together through DXY, VIX, or oil. Explain the macro regime, not just list numbers.
5. **No AI tells:** Never use 'labors in,' 'clings to,' 'what the desk flags as,' 'underscores,' 'highlights.'
6. **No hedging:** Never 'could,' 'may,' 'might,' 'potentially,' 'it seems like.'
7. **Short sentences:** Max 25 words per sentence on average.
8. **Last line:** Punchy and memorable. One sentence.
9. **What The Framework Is Watching:** Exactly 3 bullets with specific thresholds.
10. **Length:** 700–900 words for moderate weeks. 1000–1400 for regime breaks.

## Output Format
Save the final post as WEEKLY_REGIME_READ_YYYYMMDD_FINAL.md
Save the LinkedIn teaser as LINKEDIN_TEASER_YYYYMMDD_FINAL.md