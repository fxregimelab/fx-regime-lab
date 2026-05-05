# FX Regime Lab: Master Phase Roadmap

This document serves as the chronological production schedule for the FX Vertical Slice. It organizes the 5 Pillars of the architecture into 3 high-EV execution phases.

---

## 🟢 PHASE 1: Scaling & Apex Targeting (The G10 Launch)
**Objective:** Refactor the engine for the full G10 universe and deliver the "Apex Target" UI.

*   **Task 1.1: Universe Infrastructure [BACKEND]**
    *   [ ] Implement `universe.json` registry (G10 + INR).
    *   [ ] Refactor all fetchers (`yields`, `spot`, `cot`) to use `asyncio` parallel fetching.
    *   [ ] Build a one-time `backfill_g10_history.py` script for 5-year OHLCV injection.
*   **Task 1.2: MAD-Normalized Brain [BACKEND]**
    *   [ ] Refactor `signals/rate.py` and `composite.py` to use 5-year MAD Z-scores.
    *   [ ] Implement the dynamic Beta-weighting logic (Rolling Spearman).
*   **Task 1.3: Apex Ranking Engine [SYNTHESIS]**
    *   [ ] Build the cross-sectional ranker: `Apex_Score = (Regime_Strength * 0.4) + (Pain_Index * 0.4) + (Rank_Velocity * 0.2)`.
    *   [ ] Update the `desk_open_cards` table to store ranked arrays.
*   **Task 1.4: The Attention UI [FRONTEND]**
    *   [ ] Replace the homepage grid with the **Apex Card** (Rank #1).
    *   [ ] Implement muted "Telemetry Rows" for Ranks 2-7.
    *   [ ] Add the `[ RANK JUMP ]` momentum badge.

---

## 🔵 PHASE 2: Tactical HUD & Squeeze Detection
**Objective:** Deliver the visual execution zones and anti-fragile squeeze alerts.

*   **Task 2.1: The Tactical Event Engine [BACKEND]**
    *   [ ] Implement MIE (Maximum Intraday Excursion) multipliers for all macro events.
    *   [ ] Build the "Sequential Surprise" 48-hour blast radius filter.
*   **Task 2.2: Anti-Fragile Squeeze Logic [BACKEND]**
    *   [ ] Implement the **RVOL Gate** (1.5x volume threshold for squeeze alerts).
    *   [ ] Build the **Time-Weighted Persistence** (45-min check) for Crisis Mode.
*   **Task 2.3: The Execution HUD [FRONTEND]**
    *   [ ] Rebuild the Calendar into the **Convexity Radar**.
    *   [ ] Render the 1SD/2SD visual bands and Mean Reversion targets.

---

## 🟣 PHASE 3: Systemic Synthesis & Validation Truth
**Objective:** Add global correlation context and rolling accountability.

*   **Task 3.1: Systemic Matrix [DATABASE]**
    *   [ ] Build the Supabase RPC for N-Squared Pearson correlations across 7 pairs.
    *   [ ] Calculate the "Dollar Dominance Factor" and "Idiosyncratic Outlier."
*   **Task 3.2: The Fidelity Ledger [FRONTEND]**
    *   [ ] Integrate 90-day rolling Brier Score sparklines into the Validation UI.
    *   [ ] Implement the "Fidelity Gate" (Automatically dimming decayed signals).
*   **Task 3.3: Intelligence Synthesis [AI]**
    *   [ ] Wire the Polymarket Odds API into the AI Brief prompt.
    *   [ ] Generate the "Global Macro Narrative" explaining the Dollar Factor.

---

## 🔴 PHASE 4: Go-To-Market & The Open Vault
**Objective:** Ship the institutional front door, social proof loop, grounded intelligence, and local-first desk continuity.

**Delivery score (tabular):** `4` / `4` chapters · `100` % complete

*   **Chapter 1: Visual Prestige** — [ COMPLETED ]
*   **Chapter 2: The Authority Machine** — [ COMPLETED ]
*   **Chapter 3: The Intelligence Archive** — [ COMPLETED ]
*   **Chapter 4: The Open Vault** — [ COMPLETED ]

---
*Roadmap Revision: 2026-05-02 | CTO Evelyn*
