# GEMINI.md

This file provides guidance to Gemini CLI when working with the FX Regime Lab repository.

## Project Mission
FX Regime Lab is a personal research system for daily G10 FX regime classification (EUR/USD, USD/JPY, USD/INR). It provides a durable record of macro views, signal scoring, and automated validation.

## Architecture Map
Read **`AGENTS.md`** first for the complete system map. Read **`TASK.md`** for the current sprint state.

### Core Stack
- **Pipeline:** Python 3.11 (Fetchers -> Signals -> Regime -> DB Writer)
- **Database:** Supabase (PostgreSQL + RLS)
- **AI:** OpenRouter (MiniMax M1 primary, Llama 3.1 8B fallback)
- **API/Worker:** Cloudflare Workers (`workers/site-entry.js`)
- **UI (Reference):** `claude-design/` (JSX prototypes, no production frontend currently)

## Hard Rules
- **Supabase Writes:** ALL writes to Supabase MUST go through `pipeline/src/db/writer.py`. Never write directly using other clients.
- **AI Calls:** ALL AI interactions MUST go through `pipeline/src/ai/client.py`. This includes a 180 req/day guard for the OpenRouter free tier.
- **Python Quality:** All pipeline code must pass `mypy --strict` and `ruff check`.
- **Database Types:** Never edit generated `database.types.ts` by hand. Use the Supabase CLI to regenerate.

## Python Pipeline Commands (`pipeline/`)
Run these from the `pipeline/` directory:

```bash
pip install -e .                    # install development dependencies
ruff check src/                     # linting
mypy src/                           # strict type checking
pytest                              # run tests (testpaths = tests/)

# Manual pipeline execution from repo root:
pipeline/run_daily.sh               # daily regime calls + signals
pipeline/run_weekly.sh              # weekly AI briefs
```

## Data Flow
1. **Fetchers (`src/fetchers/`):** Ingest from FRED, Yahoo Finance, CFTC.
2. **Signals (`src/signals/`):** Calculate rate diffs, COT percentiles, volatility, etc.
3. **Regime (`src/regime/`):** Classify labels (e.g., `STRONG USD STRENGTH`).
4. **DB Writer (`src/db/writer.py`):** Persist to `regime_calls`, `signals`, `brief`, etc.
5. **Validation (`src/validation/`):** Next-day outcome tracking.

## Design & Frontend
The previous Next.js UI was removed.
- **UX Intent:** Reference `claude-design/` JSX files.
- **Read Patterns:** See `docs/DATA_READS_SPEC.md` for historical Supabase query patterns.
- **New App:** If scaffolding a new frontend, follow `docs/FRONTEND_ARCHITECTURE.md`.

## Key Files
- `AGENTS.md`: Complete architecture map.
- `TASK.md`: Current sprint tasks.
- `docs/DATABASE_SCHEMA.md`: Detailed table structures and RLS policies.
- `docs/PROJECT_OVERVIEW.md`: High-level vision and "North Star".
- `docs/SIGNAL_DEFINITIONS.md`: Logic for each market signal.
