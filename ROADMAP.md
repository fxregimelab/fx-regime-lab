# ROADMAP.md — The Alpha Blueprint

This is the **Highest Expected Value (EV) Plan** to transform the current codebase into a world-class professional Quantamental Research Rig. 

## How the Council Operates

For every single feature, data point, or UI change, the workflow moves sequentially through the chambers:

1.  **Chamber 1 (Strategy & Alpha):** Defines the *Math*. 
    *   *Example:* Lena (Quant) and Marcus (PM) debate whether COT positioning should be a 3-year or 5-year rolling percentile. Dr. Aris (Macro) confirms if it aligns with the EUR/USD regime logic.
2.  **Chamber 2 (Engineering & Infrastructure):** Builds the *Engine*.
    *   *Example:* Xavier (Architect) and Elias (Data) design the Supabase schema to store the new COT percentile without look-ahead bias. Viktor (Python) writes the `mypy`-strict calculation. Sasha (SRE) ensures the FRED/CFTC fetchers won't break if an API goes down.
3.  **Chamber 3 (Perception & Institutional Audit):** Shapes the *Proof*.
    *   *Example:* The Peer Reviewer demands the formula be written in KaTeX on the frontend for research transparency. Hugo (Design) and Elena (UX) ensure the terminal displays this new data point in a dense, monochrome table that a PM can read in 5 seconds. Coach Silas (Performance) verifies this task directly improves the rig's alpha generation.

---

## The 5-Round Master Plan

### Round 1: The Foundation (Data & Schema Audit)
**Goal:** Ensure the database can support a rigorous research backtest and an immutable live track record.
*   **Phase 1:** Audit `signals` and `regime_calls` tables in Supabase for exact math/data storage compliance.
*   **Phase 2:** Implement strict immutable constraints on daily calls (cannot edit once logged).
*   **Phase 3:** Establish the `validation_log` schema for T+5 and T+20 PnL tracking.

### Round 2: The Core Logic (Pipeline Refactoring)
**Goal:** Rewrite the Python pipeline to strictly enforce the **3-Layer Signal Framework**.
*   **Phase 1 (Layer 1):** Refactor the Regime Gate logic (FRED rates + CB divergence).
*   **Phase 2 (Layer 2):** Refactor the Directional Signal logic (COT percentiles + Crowding penalties).
*   **Phase 3 (Layer 3):** Implement the Timing & Entry logic (Realized Vol + Risk Reversals).

### Round 3: The Validation Engine (The Immutable Ledger)
**Goal:** Build the system that automatically proves the model's edge.
*   **Phase 1:** Create the daily validation script that checks the price of EUR/USD, USD/JPY, and USD/INR 5 days and 20 days after a regime call.
*   **Phase 2:** Calculate live Brier Scores, Win Rates, and Sharpe Ratios per regime.
*   **Phase 3:** Automate the logging of these stats into Supabase.

### Round 4: The Research Construction (Historical Backtest)
**Goal:** Prove the hypothesis that "Layer 1 Regime Gating materially improves Layer 2 Signal Accuracy."
*   **Phase 1:** Backfill data from 2018 to 2025.
*   **Phase 2:** Run the exact Python pipeline logic over the historical data.
*   **Phase 3:** Generate the statistical outputs (Drawdown, Alpha, Beta) required for institutional-grade research documentation.

### Round 5: The Research Terminal (Institutional Interface)
**Goal:** Build the Next.js web interface to display the research to institutional counterparts.
*   **Phase 1:** Build the "Live Regime Status" dashboard (Dense, monochrome, tabular-nums).
*   **Phase 2:** Build the "Methodology" page with LaTeX formulas and interactive charts.
*   **Phase 3:** Integrate the live validation stats and the Substack analysis briefs.
