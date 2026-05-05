# FX Regime Lab: The "Consumer Reality" Master Plan

This document supersedes all previous architectural plans. It is the result of a brutal 5-round "Consumer Trial" simulation involving top-tier institutional personas (Macro PMs, Systematic Quants, Execution Traders, and HFT Market Makers). 

The goal of FX Regime Lab is no longer to be a "General Research Dashboard" for corporate hedgers or bank strategists. It is a **Tactical Execution Engine for Alpha Generators.**

---

## 🧭 The Core Identity (Post-Trial Pivot)
*   **The Problem We Solve:** Information overload and "Trust Me, Bro" mathematics. PMs don't want a dashboard of 20 pairs; they want the single most asymmetric trade on the planet, mathematically verified.
*   **The Target Audience:** The Macro PM allocating capital (Elena), the Quant demanding mathematical proof (Viktor), and the Execution Trader pulling the trigger (Raj).
*   **The Anti-Target:** Corporate Treasury (Chloe) and Strategy Writers (Alistair). We do not build features for them.

---

## 🏛️ The Revised 4-Pillar Architecture

The 6-Pillar plan was bloated. The Consumer Trial stripped it down to 4 hyper-lethal, anti-fragile components.

### Pillar 1: The Apex Target Engine (Relative Value)
*Replaces: The Generic Systemic Matrix / 7-Pair Grid.*
*   **Objective:** Eliminate the noise of flat pairs. Calculate the "Dollar Factor" and instantly identify the single best vehicle to trade it.
*   **The Math:** Instead of listing 7 pairs equally, the Python engine ranks them by `Asymmetry Potential`. If the global regime is `USD_STRENGTH`, the engine subtracts the underlying strength of the quote currencies to output: `[ TOP ASYMMETRIC TRADE: SHORT JPY vs USD ]`.
*   **The UI (The Apex Card):** The Homepage displays **only** Rank #1 (The Apex Card) at 60% scale. Ranks #2 and #3 are muted telemetry rows. The rest are hidden behind a toggle. It includes a `[ +3 RANK JUMP ]` momentum badge if a pair surged overnight.

### Pillar 2: The Anti-Fragile Squeeze Detector (The Pain Index V2)
*Replaces: The Naive "Pain Index" / Desk Open Card.*
*   **Objective:** Identify when the crowd is trapped on the wrong side of the regime, but *only* alert when institutional volume confirms the break.
*   **The Math (Volume Gate):** The `Pain_Index` (COT vs Regime divergence) is gated by the 8-week VWAP.
*   **The HFT Safeguard (RVOL):** The squeeze alert ONLY triggers if the VWAP break occurs on Relative Volume (`RVOL`) > 1.5x the historical average for that specific 1-hour window. A price break on dead Asian-session volume is ignored.
*   **The Time-Weighted Gate:** The 15-minute T+0.5 continuous edge function requires 3 consecutive breaches (45 minutes) of the Volatility Threshold before triggering `[ CRISIS MODE ]` to prevent spoofing.
*   **The Managed EM Fork:** USD/INR explicitly ignores G10 rate-spread logic, relying entirely on Reserve Depletion proxies or Options Skew to detect peg breaks.

### Pillar 3: The Execution HUD (Post-Event Mean Reversion)
*Replaces: The Event Risk Radar (Static Predictions).*
*   **Objective:** Give the execution trader (Raj) specific, probabilistic zones to fade intraday macro spikes (NFP, CPI), rather than chasing zero-liquidity initial moves.
*   **The Math:** Calculates the `Maximum Intraday Excursion (MIE)` and the **Post-Event Mean Reversion Probability** based on historical surprises in the current regime.
*   **The UI:** No text paragraphs. A minimalist tactical map:
    *   `[ 1st SD EXCURSION ZONE: 30-40 pips (68% hit rate) ]` (Where to place limit orders).
    *   `[ 2nd SD EXHAUSTION ZONE: 48-60 pips (95% reversion rate) ]` (Where the algo runs out of ammo).
    *   `[ 4H REVERSION TARGET: Open Price (82% Probability) ]`.

### Pillar 4: The Rolling Decay Ledger (Visual Truth)
*Replaces: The Alpha Ledger (Lifetime Averages).*
*   **Objective:** Prove to the Systematic Quant (Viktor) that the model's edge is currently valid, not just historically backtested.
*   **The Math:** Instead of lifetime win rates, calculates a **Rolling 90-Day Z-Score of the Brier Score**.
*   **The UI (Edge Sparklines):** Banish isolated numbers. Embed inline SVG Sparklines (30x100px) directly in the data table plotting the rolling 90-day Brier Score. 
*   **The Correlation Overlay:** Overlay a faint gray line representing `Realized_Vol_20d` on the exact same sparkline so the trader can visually confirm if the model's decay is perfectly correlated to a drop in global volatility. If the sparkline drops below zero-EV, the entire row dims to 30% opacity.

---

## 🛡️ The Development Mandate

From this point forward, every single line of code written must answer one question:

**"Does this feature provide an execution trader or a macro PM with a mathematically verified, anti-fragile edge at 07:05 AM?"**

If the answer is no, it is deleted.