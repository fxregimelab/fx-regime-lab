# FX Regime Lab — IDENTITY.md
# This document defines what FX Regime Lab is, what it is not, and what must remain true before any phase can advance.
# Any AI agent working on this codebase must read and conform to this document before writing a single line.

---

## WHAT IT IS

FX Regime Lab is a public macro research platform.

It detects and classifies macroeconomic regimes for G10 and managed EM currency pairs using a systematic, rules-based signal engine. It publishes those regime classifications, the signals behind them, and a verified accuracy track record — publicly, with timestamps, with full methodology visible.

It is a live proof of analytical edge. It exists to demonstrate that the person who built it understands how currencies move at an institutional level, can build infrastructure to systematize that understanding, and can be held accountable to a public track record over time.

That is its entire purpose. Everything built must serve that purpose. Nothing else.

---

## WHAT IT IS NOT

It is not a trading signal service for other people.
It is not a copy-trading platform.
It is not a wealth management tool.
It is not a portfolio allocation engine.
It is not a fintech product.
It is not a B2B SaaS platform.
It is not a dashboard built to look impressive.
It is not a research article generator.
It is not a backtesting showcase.
It is not a framework for others to follow live signals from.
It is not an Aladdin prototype.
It is not a revenue business.

If any feature, page, or system being built does not directly serve regime detection accuracy, track record verification, or public methodology transparency — it does not belong here.

---

## CURRENT PAIRS — AND THE RULE GOVERNING EXPANSION

### Active Pairs (3)

**EUR/USD**
Primary pair. Rate differential driven. Signal inputs: FRED rate differential (US 2Y minus EUR 2Y), CFTC COT Non-Commercial and Asset Manager positioning, EUR implied volatility (^EVZ), DXY as cross-asset confirmation. Regime classification: Risk-On / Risk-Off / Transitional. This pair must reach and sustain above 55% directional accuracy on a rolling 90-day out-of-sample basis before any new pair is added.

**USD/JPY**
Carry and BoJ policy driven. Structurally different from EUR/USD. Signal inputs: US-JP rate spread, BoJ policy communication signals, leveraged money COT positioning, Brent crude as risk proxy. Regime classification must account for intervention asymmetry — JPY weakness is tolerated, JPY strength triggers BoJ response. This pair has a separate signal architecture from EUR/USD. Do not apply EUR/USD logic to USD/JPY.

**USD/INR**
Managed float. RBI intervention is the dominant driver, not market pricing. Signal inputs: RBI intervention proxies, India-US rate differential, FPI flow data, crude oil (India is a crude importer — oil up means INR pressure). Regime classification must explicitly model intervention probability, not just directional bias. This pair operates under different rules than freely floating pairs. Do not treat it as a G10 pair.

### Expansion Rule

Do not add a fourth pair until:
1. EUR/USD out-of-sample directional accuracy exceeds 55% on a rolling 90-day window.
2. That accuracy is publicly logged with timestamps in the validation table.
3. USD/JPY and USD/INR each have at least 90 days of live out-of-sample signal history.

When expansion happens, the next pair is GBP/USD. Reason: high liquidity, rate differential driven like EUR/USD, BoE policy increasingly divergent from Fed — analytically interesting and architecturally familiar.

Depth before breadth. Always.

---

## PAIR-SPECIFIC STRATEGY ARCHITECTURE

Each pair has a different fundamental driver. A single unified signal strategy applied across all three pairs will always underfit at least two of them. The signal architecture must be pair-specific.

### EUR/USD Signal Architecture
Primary driver: US-EU rate differential direction and momentum.
Secondary driver: COT positioning crowding (Non-Commercial + Asset Manager combined).
Volatility layer: EUR implied vol regime (low vol = trend-following valid, high vol = mean-reversion bias).
Confirmation: DXY direction.
Regime output: Directional bias (Long USD / Long EUR / Neutral) + Crowding risk flag.

### USD/JPY Signal Architecture
Primary driver: Carry attractiveness (US-JP spread level and direction).
Secondary driver: BoJ policy signal (hawkish shift = JPY strength pressure builds).
Positioning driver: Leveraged money COT (crowded carry = unwind risk, not trend-following signal).
Confirmation: Risk sentiment proxy (S&P500 or Brent crude).
Regime output: Carry regime (Intact / Compressing / Unwinding) + Intervention risk flag.

### USD/INR Signal Architecture
Primary driver: RBI intervention probability (inferred from spot fixing deviation, reserve levels, and volatility suppression patterns).
Secondary driver: India-US rate differential.
Flow driver: FPI equity and debt flow direction.
Commodity input: Brent crude direction (oil up = INR pressure, not a simple correlation).
Regime output: Intervention regime (Active Suppression / Passive / Allowing Depreciation) + Directional bias conditional on intervention state.

---

## WHAT MUST BE TRUE BEFORE ADVANCING ANY PHASE

These are non-negotiable checkpoints. No phase advances if these are not satisfied.

### Before Phase A advances (Signal Quality Fix)
- EUR/USD signal accuracy is being measured out-of-sample and logged to validation_log in Supabase with timestamps.
- Brief text output is clean, specific, and free of generic language.
- Pipeline runs daily without errors for 14 consecutive days.

### Before Phase B advances (Product Completeness)
- All three pairs have 90+ days of live out-of-sample signal history in the database.
- Regime history strip is live and showing historical classification changes.
- Methodology page is public and describes signal inputs, regime logic, and accuracy measurement approach in plain language.
- Accuracy above 50% on EUR/USD (floor before 55% target is achieved).

### Before Phase C advances (Regime Divergence Alert)
- EUR/USD rolling 90-day accuracy exceeds 55% and is displayed publicly on the performance page.
- SSRN methodology paper is drafted (not necessarily published).
- Regime Divergence Alert system is architecturally designed before a single line is written.

### Before Phase D advances (Full MFE Application Package)
- Six months of continuous live out-of-sample signal history exists for all three pairs.
- Performance page is live showing accuracy by pair, by regime type, and over time.
- GBP/USD addition is architecturally planned and signal logic is documented before implementation begins.
- SSRN paper is submitted.

---

## DESIGN IDENTITY

The visual and tonal identity of FX Regime Lab must always match the substance.

**It looks like an institutional research terminal, not a retail trading app.**

Typography: Inter for body, Fraunces italic for regime labels only, JetBrains Mono for all data output.
Color: Monochromatic with single amber accent (#e8a045). No color palette expansion.
Shell: Light for public-facing pages. Dark terminal for research workspace.
Tone of all public-facing text: Practitioner-to-practitioner. Never explanatory. Never educational. Never marketing.

Data displayed must be real. No placeholder charts. No synthetic signals. No illustrative examples presented as live data. If the data is not live, the page does not go up.

---

## WHAT AN AI AGENT MUST NOT DO WHEN WORKING ON THIS CODEBASE

Do not add pairs beyond the three defined above without explicit instruction and confirmation that expansion criteria are met.
Do not build any feature that serves an external user's trading decisions — no signal feeds, no alert subscriptions, no copy-trading infrastructure.
Do not redesign the visual identity. Typography, color, and layout are locked.
Do not change the database schema without a full audit of all downstream dependencies first.
Do not touch the _docs/ directory under any circumstances.
Do not apply EUR/USD signal logic to USD/JPY or USD/INR.
Do not treat USD/INR as a freely floating pair.
Do not build aesthetic features — animations, landing page intros, visual transitions — before signal accuracy checkpoints are met.
Do not confuse the research platform identity with a fintech product. There is no monetization layer. There is no user acquisition goal. There is no SaaS pivot planned.
Do not generate placeholder or synthetic data and display it as live output.

---

## THE ONE-SENTENCE IDENTITY TEST

Before building anything, ask: does this make the regime calls more accurate, more transparent, or more publicly verifiable?

If no, do not build it.

---

*Last updated: May 2026*
*Owner: Shreyash Sakhare*
*Do not modify this document without explicit instruction from the owner.*
