# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read First

Read `ULTIMATE_MASTER_PLAN.md` before starting any task — it is the absolute source of truth for the 5-Pillar Engine and 4-Chapter GTM Shell. This file codifies the "Tactical Execution Engine" identity and the mandatory 6-Step Adversarial Alpha Protocol. Read `AGENTS.md` for the original architecture map. Then read `TASK.md` for the current sprint state. This file adds commands and non-obvious patterns not covered there.

**There is no `web/` package.** The shipped Next.js UI was removed. Use `claude-design/` for UX intent and `docs/DATA_READS_SPEC.md` for prior Supabase read patterns.

## Commands

### Python pipeline (`pipeline/`)

```bash
cd pipeline
pip install -e .                    # install deps
ruff check src/                     # lint
mypy src/                           # type check (strict mode)
pytest                              # run tests (testpaths = tests/)

# Run pipeline manually from repo root:
pipeline/run_daily.sh               # daily regime calls + signals
pipeline/run_weekly.sh              # weekly AI briefs
```

### Database types (when a TS frontend exists)

```bash
supabase gen types typescript --local > <path-to-new-app>/lib/supabase/database.types.ts
```

Never edit generated `database.types.ts` by hand.

## Environment Setup

Pipeline uses a `.env` file at the repo root. Required vars are documented in `.env.example`.

- Pipeline: `FRED_API_KEY`, `SUPABASE_URL`, `SUPABASE_PROJECT_REF`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENROUTER_API_KEY`

## Hard Rules (from `.cursorrules`)

**Python:**

- All Supabase writes through `pipeline/src/db/writer.py` only
- All AI calls through `pipeline/src/ai/client.py` only (includes 180 req/day guard for OpenRouter free tier)
- mypy strict + Ruff lint on all pipeline code

When a new frontend is added, reintroduce frontend-specific rules in `.cursorrules` / Cursor rules for that stack.

**AI Brainstorming & Simulation Protocol (The God-Tier Playbook):**
Whenever a new Pillar, feature, or complex model is proposed, you MUST explicitly execute the **6-Step Adversarial Alpha Methodology** by default:
1. **Alpha Pitch:** Define base premise.
2. **Pentagon Protocol:** Simulate experts (Quant, UI/UX, Data, CRO, Microstructure, SRE) stress-testing for math purity, cognitive bias, and execution reality.
3. **Leo Optimization:** Prompt Engineer translates the survivor into a strict, XML-tagged, zero-ambiguity execution prompt.
4. **Execution:** Handled by user.
5. **Team Zeta Verification:** You perform a line-by-line code audit of the executed files.
6. **Red Team Polish:** Analyze the integrated feature against the existing codebase to hunt for feedback loops and sequential contamination.

## Data Flow

```
FRED / Yahoo Finance / CFTC
        ↓
pipeline/src/fetchers/
        ↓
pipeline/src/signals/
        ↓
pipeline/src/regime/
        ↓
pipeline/src/db/writer.py   (ALL writes to Supabase)
        ↓
Supabase (regime_calls, signals, brief, validation_log, macro_events)
```

## Design Reference

`claude-design/` contains read-only JSX prototypes. Use them for layout and spacing intent only.

| File | Contains |
|------|---------|
| `components.jsx` | Brand tokens, shared components |
| `shell-pages.jsx` | Homepage, Brief, Performance, FxRegime |
| `terminal-pages.jsx` | Terminal pages |
| `new-pages.jsx` | Calendar, PairDetail, RegimeHeatmap |
| `about-page.jsx` | About page |
| `loading-states.jsx` | Skeleton loaders |
| `error-states.jsx` | Error/empty states |
