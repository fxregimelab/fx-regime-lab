# GEMINI.md — FX Regime Lab

This document provides foundational instructions and context for the FX Regime Lab project.

## Project Overview

FX Regime Lab is a quantitative research platform focused on a global multi-asset universe (starting with the G10 FX vertical slice). It operates as an Institutional Context Engine, synthesizing data into probabilistic execution signals rather than just displaying raw data.

**Crucial Reference:** Always read `ULTIMATE_MASTER_PLAN.md` for the absolute source of truth regarding the 5-Pillar Engine and 4-Chapter GTM Shell. This document codifies the "Tactical Execution Engine" identity and the mandatory 6-Step Adversarial Alpha Protocol.

### Core Stack
- **Pipeline**: Python 3.11+ (yfinance, pandas, fredapi, supabase-py)
- **Frontend**: Next.js 15+ (App Router, Tailwind CSS 4, TanStack Query, Recharts, Framer Motion)
- **Database**: Supabase (PostgreSQL + RLS)
- **AI/LLM**: OpenRouter (MiniMax M1 primary, Gemini 2.0 Flash secondary)

## Repository Structure

- `/pipeline`: Data ingestion, signal calculation, and regime classification.
- `/web`: Production Next.js 15+ web application.
- `/supabase`: Database migrations and local development config.
- `/claude-design`: Read-only UI/UX reference prototypes.
- `/docs`: Detailed specifications (e.g., `DATA_READS_SPEC.md`).

## Building and Running

### Data Pipeline (`pipeline/`)
The pipeline handles all data processing and database writes.

```bash
# Setup
cd pipeline
pip install -e .

# Manual Execution (from repo root)
pipeline/run_daily.sh   # Fetches signals and updates regime calls
pipeline/run_weekly.sh  # Generates AI briefs via OpenRouter

# Development
ruff check src/         # Linting
mypy src/               # Type checking (strict)
pytest                  # Unit tests
```

### Web Application (`web/`)
The web app provides the interactive research desk and institutional reports.

```bash
# Setup
cd web
npm install

# Development
npm run dev

# Build
npm run build

# Generate Database Types
supabase gen types typescript --local > web/src/lib/supabase/database.types.ts
```

## Development Conventions & Hard Rules

### Data Flow & Integrity
1. **Surgical Writes**: All Supabase writes MUST go through `pipeline/src/db/writer.py`. Never write directly from the frontend or other scripts.
2. **AI Centralization**: All AI/LLM calls MUST go through `pipeline/src/ai/client.py` and utilize exponential backoff to handle rate-limiting.
3. **Type Safety**: 
   - Python: Strict `mypy` is required for all pipeline code.
   - Web: Strictly use generated Supabase types. Never edit `database.types.ts` manually.
4. **Data Resilience**: Never assume external APIs (Yahoo, CME, OpenRouter) are stable. Always implement fallbacks, explicit `None` handling, and exponential backoff.
5. **Zero-Trust Database**: While RLS `SELECT` policies are enabled for public reads, the database strictly relies on Service Role keys for mutation. Ensure explicit `INSERT/UPDATE/DELETE` block policies exist for `anon` and `authenticated` roles.
6. **Environment Variables**: Managed via `.env` at the repo root. Required keys include `FRED_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and `OPENROUTER_API_KEY`.

### Institutional UI/UX Standards (Obsidian Glass)
- **The Core Aesthetic**: Pure black (`#000000`) terminal backgrounds, sharp `1px` borders (`#111` or `#1a1a1a`), and crisp typography.
- **No Consumer Artifacts**: Strictly NO soft shadows (`shadow-sm`, `shadow-md`, etc.) and NO rounded corners (`rounded-none`).
- **Data Density**: Implement fixed-width tabular numbers (`tabular-nums`) for all data points to prevent layout shifts. High contrast for actual values, muted gray (`#888`, `#555`) for labels.
- **Chart Engine**: Use `lightweight-charts` for high-performance, multi-pane synchronized data visualization.
- **Print Optimization**: Ensure `@media print` rules strip all UI chrome and format output as a professional "Sell-Side" research brief.

### AI Brainstorming & Simulation Protocol (The God-Tier Playbook)
Whenever a new Pillar, feature, or complex model is proposed, the AI MUST explicitly execute the **6-Step Adversarial Alpha Methodology** by default. Do NOT write code or generate execution plans until this pipeline is complete.

1. **The Alpha Pitch:** Define the base mathematical and functional premise.
2. **The Pentagon Protocol (Crucible):** Simulate a 5-tier virtual expert team (Quant Lead, UI/UX Architect, Backend Engineer, Chief Risk Officer, Microstructure Trader, Data Scientist). They must aggressively stress-test the idea for data dependencies, cognitive bias, mathematical purity (overfitting/look-ahead bias), and execution reality (flash crashes, liquidity vacuums).
3. **The Leo Optimization:** Adopt the 'Prompt Engineer' persona. Translate the surviving architecture into a strict, zero-ambiguity, XML-tagged prompt for Cursor/LLM execution. Define exact JSON schemas, math formulas, and DB security policies.
4. **Execution:** (Handled by the User via Cursor using Leo's prompt).
5. **Team Zeta Verification:** The AI must perform a rigorous, line-by-line code audit of the executed files to ensure zero deviation from the strict typing and institutional math established in Step 2.
6. **The Red Team Polish:** Analyze the newly integrated feature against the entire existing codebase. Hunt for "Feedback Loops" or "Sequential Contaminations" across models before giving the final green light.
