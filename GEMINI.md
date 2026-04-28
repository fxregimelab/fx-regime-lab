# GEMINI.md — FX Regime Lab

This document provides foundational instructions and context for the FX Regime Lab project.

## Project Overview

FX Regime Lab is a quantitative research platform focused on G10 FX regime classification. It tracks three primary currency pairs: **EUR/USD**, **USD/JPY**, and **USD/INR**. 

The system consists of a robust Python data pipeline that classifies market regimes daily and an interactive Next.js dashboard for visualizing research, performance, and AI-generated intelligence.

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
2. **AI Centralization**: All AI/LLM calls MUST go through `pipeline/src/ai/client.py`. This ensures proper 180 req/day guarding for the OpenRouter free tier.
3. **Type Safety**: 
   - Python: Strict `mypy` is required for all pipeline code.
   - Web: Strictly use generated Supabase types. Never edit `database.types.ts` manually.
4. **Cinematic UI**: Follow the "Shell to Terminal" dual-shell design pattern. Light mode "Shell" for reports; Dark mode "Terminal" (#050505) for desks.
5. **Environment Variables**: Managed via `.env` at the repo root. Required keys include `FRED_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and `OPENROUTER_API_KEY`.

### Interactivity Standards
- Use `framer-motion` for "Power-On" boot sequences when loading terminal desks.
- Implement fixed-width tabular numbers (`tabular-nums`) for all data points to prevent layout shifts.
- Favor sharp, 1px border transitions over soft shadows for institutional-grade aesthetic.
