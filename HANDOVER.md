# HANDOVER.md — Mission Brief for the Next Agent

## 1. THE MISSION
Transform the FX Regime Lab from a "cool dashboard" into a **Professional Quantamental Research Rig**.
*   **Goal:** Build a verifiable, immutable track record of systematic macro edge.
*   **Target Audience (Internal):** MFE Admissions Boards (NTU/Singapore) and Macro Hedge Funds.
*   **Target Identity (External):** Independent, institutional-grade Research Operation.

## 2. THE SYSTEM (THE OMEGA LOOP)
You are not alone. You lead a **Triple-Chamber Council** of 13 experts (Dr. Aris, Lena, Marcus, etc. - see `OMEGA_PROTOCOL.md`).

**The Workflow:**
1.  **Convene Chamber 1 (Strategy):** Define the mathematical and macro-economic logic.
2.  **Convene Chamber 2 (Engineering):** Design the Supabase schema and Python pipeline architecture.
3.  **Convene Chamber 3 (Perception):** Audit for institutional credibility and research transparency.
4.  **Delegated Execution:** **DO NOT implement complex logic yourself.** Use the **Cursor Agent CLI**:
    ```bash
    agent --print "Your task is to implement..."
    ```
5.  **Docs Sync:** Update `CONTEXT.md`, `TASK.md`, and relevant specs after every iteration.

## 3. CURRENT STATUS
*   **Round 1 (Foundation):** [COMPLETE] Schema is aligned with the 3-Layer Signal Framework.
*   **Round 2 (Core Logic):** [COMPLETE] The 3-layer deterministic classifier is implemented in Python and verified (42/42 tests pass).
*   **Round 3 (Validation Engine):** [ACTIVE] The specification for T+5/T+20 validation and Brier Scores is ready.

## 4. NEXT IMMEDIATE TASKS
1.  **Implement Round 3, Phase 1:** Create `pipeline/src/validation/engine.py` using the Cursor Agent.
2.  **Logic:** Calculate log returns (bps) and Brier scores. Handle the "Marcus Dead-band" (5bps) for Neutral outcomes.
3.  **Data:** Ensure the validation is append-only and immutable.

## 5. REPOSITORY MAP
*   `CONTEXT.md`: The macro thesis and 3-layer framework (Absolute SOT).
*   `ROADMAP.md`: The 5-round master plan.
*   `TASK.md`: Current progress and checklist.
*   `docs/specs/`: Detailed engineering blueprints for each round.
*   `pipeline/src/logic/`: The re-wired brain of the rig.

**Final Rule:** Stay in **"Cloaked Professionalism"** mode. NO student language. NO fluff. Just Alpha.
