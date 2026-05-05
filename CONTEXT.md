# CONTEXT.md — FX Regime Lab

## IDENTITY

I am an independent quantamental macro researcher based in Pune, India.
I operate a live research operation focused on G10 FX regime classification and systematic alpha generation.

This platform is a live research operation. It is the primary evidence of a rigorous, institutional-grade methodology executed in public, in real time.

## LONG-TERM STRATEGIC VISION

The objective of this operation is twofold:
1. **Academic Contribution:** To contribute to the field of systematic macro through a series of published research papers and technical theses (targeting SSRN and academic peer review).
2. **Institutional Transition:** To transition this proprietary methodology into a full-scale quantamental macro fund, specifically targeting expansion into global financial hubs (Singapore/Dubai).

---

## WHAT QUANTAMENTAL MACRO MEANS

Quantamental = discretionary macroeconomic judgment executed through systematic signal generation.

The human layer sets the thesis (discretionary judgment).
The systematic layer executes it (signal generation).
This removes emotion and inconsistency while maintaining the depth of macro analysis.

FX Regime Lab is the public documentation and execution of this approach.

---

## WHAT FX REGIME LAB IS

FX Regime Lab is a live quantamental macro research platform.

It does three things:
1. Generates systematic FX regime calls using a three-layer signal framework.
2. Publishes weekly macro FX analysis on Substack (fxregimelab.substack.com).
3. Builds a verifiable, out-of-sample track record of regime detection and directional calls.

Domain: fxregimelab.com
Substack: fxregimelab.substack.com

The platform covers three pairs:
- EUR/USD — primary, rate differential + ECB/Fed divergence.
- USD/JPY — primary, carry trade mechanics + BoJ policy asymmetry.
- USD/INR — secondary, RBI intervention + managed float dynamics.

---

## THE SIGNAL FRAMEWORK — THREE LAYERS

### Layer 1: Regime Gate
Determines the macro environment governing each pair.

Inputs:
- Rate differential direction and momentum (sourced from FRED).
- Central bank posture (hawkish / pausing / easing).
- Growth divergence between currency blocs.

Output: regime label (e.g., risk-on carry, carry collapse, breakout).

### Layer 2: Directional Signal
Given the regime, what is the directional bias and with what conviction?

Inputs:
- Rate differential momentum.
- CFTC COT positioning: NonCommercial + Asset Manager categories.
- Positioning percentile (3-year rolling history).
- Crowding flag: if positioning percentile > 90th, reversal risk dominates.

Output: directional bias (long / short / neutral) + conviction score (1–5).

### Layer 3: Timing and Entry
Given direction and conviction, when do you enter and where do you stop?

Inputs:
- 25-delta risk reversals (implied vol skew).
- Realized volatility (21-day).
- Options market skew direction.

Output: entry timing recommendation, stop placement level, position sizing guidance.

---

## TRACK RECORD — THE IMMUTABLE LEDGER

Every regime call is logged in `regime_calls` with:
- Date of call, Pair, Regime label, Directional bias, Conviction score.
- Signal inputs at time of call (rate differential, COT percentile, vol level).

Every call is timestamped and immutable once written. 
This is the out-of-sample record. It cannot be retroactively adjusted.

Validation logic (Round 3 — Immutable Ledger):
- Each call is evaluated at **T+5** and **T+20** trading-day horizons.
- Returns are computed as **log returns in basis points**: `bps = 10,000 × ln(Sₕ/S₀)`.
- The **Marcus Dead-band** (±5 bps) defines Neutral outcomes — no directional credit is given inside the band.
- **Brier Scores** are calculated at both horizons using the call's confidence as the predicted probability `p`.
- All results are append-only and written to `validation_log` with `call_date` as the immutable anchor.
- Legacy T+1 arithmetic-return validations remain in `validation_log` for backward compatibility.
- This dataset serves as the basis for professional research theses and performance audits.

---

## THE RESEARCH TERMINAL

The website is a live research terminal. It must demonstrate that the framework is real, the methodology is rigorous, and the track record is genuine.

### Key Requirements:
1. **Live Regime Status:** Current status for all three pairs. Daily updates.
2. **Signal History:** Chronological log of every call with inputs and outcomes.
3. **Methodology Transparency:** Detailed explanation of the 3-layer framework.
4. **Data Visualization:** Rate differentials, COT percentiles, and volatility over time.
5. **Weekly Research:** Substack integration for written macro analysis.
6. **Performance Metrics:** Win rate, Brier scores, and accuracy by regime type.

This platform is held to institutional research standards. 
Every data point must be verifiable; every formula must be transparent.
