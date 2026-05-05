# FX Regime Lab: The Master Architecture Plan

This document serves as the absolute, unchanging blueprint for the FX Regime Lab. It codifies the transition from a 3-pair script to an Institutional Multi-Asset Context Engine.

## 🧭 The Vision & Core Mandate
*   **The Goal:** Build an unbreakable, 50+ asset Global Macro Context Engine.
*   **The Philosophy:** "Signal, not Noise." Synthesize billions of data points into probabilistic, mathematically proven execution notes.
*   **The Execution Strategy (The Vertical Slice):** We do NOT build horizontally. We build the complete 6-Pillar architecture for the **G10 FX Universe** first. Only when the FX slice is a flawless 10/10 do we adapt the math engine to support Commodities (Gold/Oil) and Equities.

---

## 🏛️ The 6 Pillars of the Master Architecture

### Pillar 1: The Asynchronous Ingestion Engine (The Nervous System)
*   **Objective:** Fetch data for 50+ assets in under 5 seconds without triggering API bans or database lockups.
*   **Architecture:** 
    *   Driven dynamically by `universe.json` (No hardcoded tickers).
    *   `asyncio` concurrency bounded by strict `Semaphore(5)` limits.
    *   I/O buffering: Fetches write to a Python dictionary in-memory.
    *   SRE Gates: `validate_ingestion_buffer` drops poisoned rows (e.g., missing Spot prices) before they taint the bulk-upsert to Supabase.
*   **Status:** *Completed for FX.*

### Pillar 2: The Asset-Agnostic Math Engine (The Brain)
*   **Objective:** Calculate structural regimes, squeeze risks, and transition probabilities without look-ahead bias or overfitting.
*   **Architecture:**
    *   **MAD Z-Scores:** Uses Median Absolute Deviation over a 5-year lookback to ignore black-swan spikes.
    *   **The Pain Index:** Measures divergence between Fundamental Regime and crowd positioning (COT/Options Skew). Gated by an 8-week VWAP "Underwater" trigger.
    *   **Markov Chains:** Calculates 5-day transition probabilities using a 3-year exponential time decay.
    *   **T+0.5 Edge Function:** A 15-minute continuous script that checks Spot/VIX/DXY against NY Close to trigger "Crisis Mode" invalidations.
*   **Status:** *Completed for FX.*

### Pillar 3: The Regime-Conditioned Event Risk Radar (The Catalyst)
*   **Objective:** Predict the volatility and directional asymmetry of macroeconomic events (NFP, CPI) based on the active regime.
*   **Architecture:**
    *   **$0 Hybrid Data:** Ingests deep historical CSVs (Actual vs. Consensus) and scrapes live weekly XML feeds (ForexFactory).
    *   **MIE Multipliers:** Normalizes the event's Maximum Intraday Excursion against the 20-day Realized Volatility.
    *   **Pure Date Filter:** Excludes historical dates where multiple high-impact events collided to prevent data pollution.
    *   **CRO Sample Gate:** Suppresses directional probabilities if historical occurrences `N < 5`.
*   **Status:** *Completed for FX.*

### Pillar 4: The Forward-Walking Ledger (The Truth)
*   **Objective:** Provide mathematically unarguable, out-of-sample proof of the system's edge.
*   **Architecture:**
    *   **Zero-Lookahead Tracking:** Logs the intent at Day T. Steps forward chronologically in the price array to calculate pure directional hits at T+1, T+3, and T+5.
    *   **Brier Scoring:** Calculates the Expected Value of the regime's confidence score, decaying rapidly to warn traders of breaking models.
*   **Status:** *Completed for FX.*

### Pillar 5: The G10 Systemic Matrix (The Global Command Center)
*   **Objective:** Isolate the "Dollar Factor" from idiosyncratic market shocks across the entire G10 complex.
*   **Architecture:**
    *   **RPC Correlation Offloading:** A Supabase PL/pgSQL function calculates the N-Squared Pearson correlation matrix for all universe assets, saving Python RAM.
    *   **Dollar Dominance Score:** Calculates the percentage of G10 pairs sharing the exact same rate-signal vector against the USD.
    *   **Idiosyncratic Outlier:** Identifies the single asset breaking from the systemic correlation matrix.
*   **Status:** *Pending Execution.*

### Pillar 6: The Institutional Intelligence Layer (The Analyst)
*   **Objective:** Deliver deterministic, unhallucinated "Market Color" explaining *why* the systemic matrix is shifting.
*   **Architecture:**
    *   **Prediction Market Sentiment:** Ingests live odds from Polymarket APIs (e.g., "72% chance of Fed Cut") as mathematical proxies for global fear/greed.
    *   **Cross-Model Synthesis:** The LLM prompt is injected with the Pillar 5 Dominance Score, the Pillar 2 Event Risk, and the Polymarket odds.
    *   **JSON Structured Outputs:** Forces the AI to return strict JSON arrays, with deterministic Python string fallbacks on timeout.
*   **Status:** *Pending Execution.*

---

## 🛡️ The Standard Operating Procedure (The God-Tier Playbook)

To maintain absolute institutional integrity, no new feature, Pillar, or asset class expansion may be executed without surviving the **6-Step Adversarial Alpha Methodology**:

1.  **The Alpha Pitch:** Define the mathematical premise and goal.
2.  **The Pentagon Protocol:** A multi-round simulation where a virtual expert team (Quants, Traders, SREs, Risk Officers) brutally stress-tests the pitch for data dependencies, cognitive bias, and execution reality.
3.  **The Leo Optimization:** A Prompt Engineer translates the surviving concept into a strict, zero-ambiguity, XML-tagged prompt for Cursor.
4.  **Cursor Execution:** The user executes the prompt.
5.  **Team Zeta Verification:** A rigorous code audit of the executed files to ensure strict typing, safe fail-overs, and DB security.
6.  **The Red Team Polish:** A holistic check against the entire codebase to hunt for feedback loops and systemic contradictions.