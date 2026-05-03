# FX Regime Lab: The Master Architecture Plan

This document serves as the absolute, unchanging blueprint for the FX Regime Lab. It codifies the transition from a 3-pair script to an Institutional Multi-Asset Context Engine, as refined through 5 rounds of Architecture Simulation and 5 rounds of Consumer Trial.

## 🧭 The Vision & Identity
*   **The Goal:** Build the world’s most advanced Macro Context Engine for institutional G10 FX desks.
*   **The Philosophy:** "Signal, not Noise." Synthesize billions of data points into a single, probabilistic, and verified execution target.
*   **The Identity:** A **Tactical Execution Engine for Alpha Generators.**
*   **The Vertical Slice Strategy:** We build the full 5-Pillar Engine and 4-Chapter GTM Shell for the **G10 FX Universe** first. No horizontal expansion (Commodities/Equities) will occur until the FX product is a flawless 10/10 masterpiece.

---

## 🏛️ Part 1: The Engine (The 5 Pillars)

### Pillar 1: The Apex Ingestion Engine (The Nervous System)
*   **Architecture:** Parallel `asyncio` fetching driven by a dynamic `universe` DB table.
*   **Math:** Implements Median Absolute Deviation (MAD) for robust z-score normalization over a 5-year structural window.
*   **SRE Gate:** A "Data Readiness Guard" that prevents calculation on stale or partial data.

### Pillar 2: The Core Analytical Engine (The Brain)
*   **Math:** Dynamic Beta (Rolling 30D Spearman + EMA10) + Time-Decayed Markov Transition Matrix.
*   **Alpha:** The Pain Index (Fundamental vs Positioning divergence) gated by an 8-week VWAP "Underwater" trigger and RVOL confirmation.
*   **SRE Check:** 15-minute T+0.5 continuous edge function with 45-minute persistence checks for Crisis Mode.

### Pillar 3: The Tactical Execution HUD (The Catalyst)
*   **Math:** Maximum Intraday Excursion (MIE) multipliers normalized by RV20 volatility.
*   **Visual:** Probabilistic Convexity Bands (1SD/2SD) and Post-Event Mean Reversion targets.
*   **Data Integrity:** 48-hour sequential surprise "Blast Radius" filtering to prevent event contamination.

### Pillar 4: The Systemic Apex Hub (The Hub)
*   **Math:** RPC-driven Dollar Dominance Score and Idiosyncratic Outlier detection (20d/60d agreement).
*   **UI:** "Winner-Take-All" homepage showing exactly ONE massive card: **The Apex Target**. Ranks 2-3 are muted rows; 4-7 are hidden.

### Pillar 5: The Edge Integrity Ledger (The Truth)
*   **Verification:** Forward-walking, out-of-sample directional validation (T+1, T+3, T+5).
*   **Accountability:** Inline SVG Sparklines plotting 90-day rolling Brier Z-scores.
*   **Gating:** If accuracy drops below zero-EV, the signal is physically dimmed in the UI.

---

## 🏛️ Part 2: The Shell (The 4 GTM Chapters)

### Chapter 1: Visual Prestige (The Front Door)
*   **Identity:** Abandon "Marketing Copy." Hero section is a live, SSG-cached readout of the G10 Systemic Matrix.
*   **Palette:** Strict, muted "Institutional Palette" (Emerald/Coral) to reduce cognitive stress.
*   **Ingress:** A "Visual Zoom" transition from Landing ➔ Terminal using Framer Motion.

### Chapter 2: The Authority Machine (Social Distribution)
*   **LinkedIn Alpha:** Automated daily post generator in a "Sell-Side Strategist" tone.
*   **SEO Snapshot:** Auto-generated static "Daily Memo" pages to build a permanent, searchable archive of accuracy.

### Chapter 3: The Intelligence Archive (The House View)
*   **Substack Sync:** Rebrand newsletter as "The Weekly Macro Memo." Embed the feed into the Terminal.
*   **Contextual AI:** Pass Sunday's memo text into the week's AI prompts to ensure a unified "House Voice."

### Chapter 4: The Open Vault (Anonymous-First)
*   **Zero Barrier:** 100% of the Terminal is accessible without an account.
*   **Service Gating:** Emails are collected only for Slack/Symphony/Inbox delivery services.

---

## 🛡️ The Standard Operating Procedure (The God-Tier Playbook)

No feature is built without surviving the **6-Step Adversarial Alpha Methodology**:
1. **The Alpha Pitch:** Define the mathematical and functional premise.
2. **The Pentagon Protocol:** A 5-tier expert simulation (Traders, Quants, SRE, Risk, AI) to stress-test for math purity, cognitive bias, and execution reality.
3. **The Leo Optimization:** Translate surviving concepts into strict, XML-tagged, zero-ambiguity prompts for Cursor.
4. **Execution:** User executes the prompt via Cursor.
5. **Team Zeta Verification:** A rigorous line-by-line code audit.
6. **The Red Team Polish:** A holistic check for feedback loops across the system.
