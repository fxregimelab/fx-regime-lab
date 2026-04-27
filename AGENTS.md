# AGENTS.md — FX Regime Lab

Read this before reading any other file. This is the complete map of the repo.

## What This Is

Daily G10 FX regime research. Three currency pairs (EUR/USD, USD/JPY, USD/INR).
A Python pipeline runs each morning, classifies the FX regime for each pair, and
writes results to Supabase.

**Shipped web UI:** Removed. There is no `web/` app in this repo. Target UX lives under **`claude-design/`** (prototype JSX). Past Supabase read patterns are summarized in **`docs/DATA_READS_SPEC.md`**. Hosting notes: **`docs/HOSTING_AFTER_UI_REMOVAL.md`**.

## Repo Structure

fx-regime-lab/
├── pipeline/               Python 3.11 data pipeline
├── supabase/               Database migrations and config
├── claude-design/          UI prototype reference (not production)
├── workers/                Cloudflare Worker (API-only, see site-entry.js)
├── site/data/              Optional machine-readable pipeline status JSON (not a public site)
├── docs/                   Documentation (includes DATA_READS_SPEC, HOSTING_AFTER_UI_REMOVAL)
├── AGENTS.md               ← YOU ARE HERE
└── TASK.md                 Current sprint tasks (read second)

## Pipeline (`pipeline/`)

**Language:** Python 3.11
**Tooling:** Ruff (lint), mypy (types), pytest (tests), pre-commit
**Config:** `pipeline/pyproject.toml`

### Key Layers

| Layer | Location | Purpose |
|-------|----------|---------|
| Fetchers | `pipeline/src/fetchers/` | One file per data source |
| Signals | `pipeline/src/signals/` | rate, cot, volatility, OI per pair |
| Regime | `pipeline/src/regime/` | composite scorer + label classifier |
| Validation | `pipeline/src/validation/` | next-day outcome validator |
| DB Writer | `pipeline/src/db/writer.py` | ALL Supabase writes |
| AI | `pipeline/src/ai/client.py` | OpenRouter free models, 180 req/day guard |
| Scheduler | `pipeline/src/scheduler/orchestrator.py` | daily + weekly runs |

### Hard Rules

- ALL Supabase writes go through `pipeline/src/db/writer.py` only
- AI calls ONLY from `pipeline/src/ai/client.py` — never inline
- AI via OpenRouter free models (MiniMax M1 primary, Llama 3.1 8B fallback)
- Daily request guard: 180 req/day cap in ai/client.py (OpenRouter free limit ≈ 200)

## Database (`supabase/`)

**Platform:** Supabase (PostgreSQL + Auth + RLS)
**Migrations:** `supabase/migrations/` — numbered, never edited after applied

When a **new** TypeScript frontend is added, regenerate types into that package, for example:

`supabase gen types typescript --local > <frontend>/lib/supabase/database.types.ts`

### Key Tables

| Table | Purpose |
|-------|---------|
| `regime_calls` | Daily regime call per pair |
| `signals` | Raw signal values per pair per day |
| `validation_log` | Next-day outcome for each call |
| `brief` | Daily AI-generated morning brief |
| `macro_events` | Macro calendar events with AI context |
| `ai_usage_log` | Token usage tracking |

## Design Reference (`claude-design/`)

**Read-only reference** — JSX prototypes and layout experiments. Never treat as production code.

| File | Contains |
|------|---------|
| `components.jsx` | Shared components, mock data, brand tokens |
| `shell-pages.jsx` | HomePage, BriefPage, PerformancePage, FxRegimePage |
| `terminal-pages.jsx` | Terminal pages, AiAnalysisPanel, calendar tab |
| `new-pages.jsx` | CalendarPage, PairDetailPage, RegimeHeatmap |
| `about-page.jsx` | AboutPage with PipelineWalkthrough, CompositeSimulator |
| `loading-states.jsx` | Skeleton loaders |
| `error-states.jsx` | Error/empty states |
| `mobile-layouts.jsx` | Mobile responsive designs |

## Pairs Config (for rebuilds)

```typescript
const PAIRS = [
  { label: 'EURUSD', display: 'EUR/USD', urlSlug: 'eurusd', pairColor: '#4BA3E3' },
  { label: 'USDJPY', display: 'USD/JPY', urlSlug: 'usdjpy', pairColor: '#F5923A' },
  { label: 'USDINR', display: 'USD/INR', urlSlug: 'usdinr', pairColor: '#D94030' },
];
```

## Phases

Phases 0–6 described historical frontend work; the **shipped Next.js UI has been removed**. New UI work should start from `claude-design/` and `docs/DATA_READS_SPEC.md`.

## Scheduling

To register the daily cron (runs weekdays at 06:30 IST = 01:00 UTC):

- `crontab -e`
- Add: `0 1 * * 1-5 /home/shreyash/fx_regime_lab/fx-regime-lab/pipeline/run_daily.sh >> /tmp/fxlab_daily.log 2>&1`

To register the weekly AI brief cron (runs Sundays at 08:00 IST = 02:30 UTC):

- `0 2 * * 0 /home/shreyash/fx_regime_lab/fx-regime-lab/pipeline/run_weekly.sh >> /tmp/fxlab_weekly.log 2>&1`

To run manually from repo root:

- `pipeline/run_daily.sh`
- `pipeline/run_weekly.sh`

### Operations

After adding a new frontend: configure the host (Vercel, Cloudflare Pages, etc.), set `NEXT_PUBLIC_SUPABASE_*` at **build** time if using Next, audit Supabase RLS for anon access, and rotate any exposed keys. See `docs/HOSTING_AFTER_UI_REMOVAL.md` for what changed when the old app was removed.
