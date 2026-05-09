# MOC.md — Map of Content (FX Regime Lab)

Welcome to the **FX Regime Lab** research rig. Use this file to navigate the repository and understand the relationships between code and research.

## 🧭 High-Level Context
- [[HANDOVER]]: **START HERE.** Operator identity, locked career path, locked decisions, session rules, macro backdrop, and networking status. This is the complete personal/career context.
- [[CONTEXT]]: The macro thesis, signal framework, and technical project context (Absolute SOT for technical decisions).
- [[OMEGA_PROTOCOL]]: The 13-persona council and 6-phase OMEGA loop.
- [[GEMINI]]: Repository instructions and hard rules.
- [[CLAUDE]]: The Quant Research Assistant persona, locked decisions, and session operating rules.
- [[TASK]]: Current sprint state and the rebuild rounds.

## 🏛️ The 3-Layer Framework (Signal Logic)
- **Layer 1: Regime Gate** ➔ [[pipeline/src/regime/]]
- **Layer 2: Directional Signal** ➔ [[pipeline/src/signals/]]
- **Layer 3: Timing & Entry** ➔ [[pipeline/src/signals/volatility.py]]

## 📂 Codebase Navigation
- **/pipeline**: Python 3.11 Quant Rig.
    - [[pipeline/src/fetchers/]]: Data ingestion logic (FRED, CFTC, yfinance).
    - [[pipeline/src/signals/]]: Mathematical signal calculation (Z-scores, Percentiles).
    - [[pipeline/src/regime/]]: Classification and gating logic.
    - [[pipeline/src/db/]]: Database persistence (Surgical Writes).
    - [[pipeline/src/validation/]]: Immutable track record validation.
- **/web**: Research Terminal (Next.js 16+ / Swiss Monochrome).
    - [[web/src/lib/supabase/database.types.ts]]: The type-safe schema.
- **/supabase**: Database schema and migrations.
- **/claude-design**: Research UI/UX reference prototypes.
- **/_docs/archive/**: Legacy OMEGA institutional project documents.

## 🔗 External Assets
- [Substack (FX Regime Lab)](https://fxregimelab.substack.com)
- [Supabase Dashboard](https://supabase.com)
- [Vercel Dashboard](https://vercel.com)

---
*Generated for Institutional Research & AI Agentic Navigation.*
