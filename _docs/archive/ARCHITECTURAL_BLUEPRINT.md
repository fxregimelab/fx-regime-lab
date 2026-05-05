# ARCHITECTURAL_BLUEPRINT.md — FX Regime Lab

This is the **Absolute Source of Truth (SOT)** for the FX Regime Lab architecture, philosophy, and execution methodology. All AI agents must adhere to this blueprint.

---

## 🧭 Vision & Identity
*   **The Goal:** Build the world’s most advanced Macro Context Engine for institutional G10 FX desks.
*   **The Philosophy:** "Signal, not Noise." Synthesize billions of data points into a single, probabilistic, and verified execution target.
*   **The Identity:** A **Tactical Execution Engine for Alpha Generators.**
*   **The Vertical Slice Strategy:** We build the full 4-Pillar Engine and 4-Chapter GTM Shell for the **G10 FX Universe** (EUR/USD, USD/JPY, USD/INR) first.

---

## 🏛️ The 4-Pillar Engine (The Logic)

### Pillar 1: The Apex Target Engine (Relative Value)
*   **Objective:** Eliminate flat pair noise. Identify the single best vehicle for the active Dollar regime.
*   **Logic:** Rank pairs by `Asymmetry Potential`. Subtract quote currency strength from the Dollar Factor.
*   **Output:** `[ TOP ASYMMETRIC TRADE: SHORT JPY vs USD ]`.

### Pillar 2: The Anti-Fragile Squeeze Detector (The Pain Index)
*   **Objective:** Identify trapped crowds confirmed by institutional volume.
*   **Logic:** `Pain_Index` (COT vs Regime) gated by 8-week VWAP and Relative Volume (RVOL) > 1.5x.
*   **Safety:** 15-minute T+0.5 continuous edge function requiring 45-minute persistence for `[ CRISIS MODE ]`.

### Pillar 3: The Execution HUD (Event Risk Radar)
*   **Objective:** Provide probabilistic zones to fade macro spikes (NFP, CPI).
*   **Logic:** Calculate Maximum Intraday Excursion (MIE) and Mean Reversion Probabilities (1SD/2SD zones).
*   **Output:** Tactical zones (e.g., `[ 2nd SD EXHAUSTION ZONE: 48-60 pips ]`).

### Pillar 4: The Rolling Decay Ledger (Verification)
*   **Objective:** Prove real-time validity of the model's edge.
*   **Logic:** Rolling 90-Day Z-Score of the Brier Score.
*   **Output:** Inline sparklines. If accuracy drops below zero-EV, the signal is physically dimmed.

---

## 🏛️ The 4-Chapter Shell (The Interface)

1.  **Visual Prestige:** Pure black (`#000000`), sharp `1px` borders, `tabular-nums`. Institutional palette.
2.  **The Authority Machine:** Automated LinkedIn/SEO alpha distribution.
3.  **The Intelligence Archive:** Unified "House Voice" (Substack sync).
4.  **The Open Vault:** Anonymous-first, zero-barrier access.

---

## 🛡️ The God-Tier Methodology (6-Step Adversarial Alpha)

No feature is built without surviving this methodology:
1.  **The Alpha Pitch:** Define mathematical/functional premise.
2.  **The Pentagon Protocol:** 5-tier expert simulation (Traders, Quants, SRE, Risk, AI) to stress-test.
3.  **The Leo Optimization:** Translate to strict, XML-tagged, zero-ambiguity prompts for Cursor.
4.  **Execution:** Use Cursor/LLM to implement the optimized prompt.
5.  **Team Zeta Verification:** Rigorous line-by-line code audit and typing check.
6.  **The Red Team Polish:** Holistic check for feedback loops and systemic contradictions.

---

## 📂 Repository Context Map
- `/pipeline`: Python 3.11 engine. Strictly modular.
- `/web`: Production Next.js 15+ / Tailwind 4 / React 19 application.
- `/supabase`: Database migrations (PostgreSQL + RLS).
- `/claude-design`: Read-only UI/UX prototypes.
- `MOC.md`: Map of Content for Obsidian/AI navigation.
