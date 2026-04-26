# AGENTS.md — FX Regime Lab

Read this before reading any other file. This is the complete map of the repo.

## What This Is

Daily G10 FX regime research. Three currency pairs (EUR/USD, USD/JPY, USD/INR).
A Python pipeline runs each morning, classifies the FX regime for each pair, and
writes results to Supabase. A Next.js frontend reads from Supabase and displays
the calls, signals, and validation history.

## Repo Structure

fx-regime-lab/
├── web/                    Next.js 15 app (App Router, TypeScript strict)
├── pipeline/               Python 3.11 data pipeline
├── supabase/               Database migrations and config
├── claude-design/          UI prototype reference (JSX only, not production code)
├── AGENTS.md               ← YOU ARE HERE
└── TASK.md                 Current sprint tasks (read second)

## Web App (`web/`)

**Framework:** Next.js 15, React 19, TypeScript strict, Tailwind CSS v4
**Linting:** Biome (never ESLint)
**Charts:** TradingView Lightweight Charts v5 ONLY — no Recharts, Plotly, ECharts, Chart.js
**Fonts:** Inter (UI text) + JetBrains Mono (data values, labels, timestamps)

### Key Files

| File | Purpose |
|------|---------|
| `web/app/layout.tsx` | Root layout, fonts |
| `web/app/globals.css` | Tailwind v4 theme tokens, global keyframes |
| `web/lib/types/index.ts` | All TypeScript interfaces |
| `web/lib/utils/format.ts` | fmt2, fmt4, fmtPct, fmtChg, fmtSpot |
| `web/lib/mock/data.ts` | PAIRS constants + about-page mock only |
| `web/lib/supabase/client.ts` | Supabase browser client |
| `web/lib/supabase/queries.ts` | ALL Supabase query functions (never write supabase.from() elsewhere) |
| `web/lib/supabase/database.types.ts` | GENERATED — never edit manually |
| `web/lib/cache/redis.ts` | Upstash Redis client |

### Routes

| Route | File | Description |
|-------|------|-------------|
| `/` | `app/(site)/page.tsx` | Homepage |
| `/brief` | `app/(site)/brief/page.tsx` | Daily brief |
| `/performance` | `app/(site)/performance/page.tsx` | Validation + track record |
| `/fx-regime` | `app/(site)/fx-regime/page.tsx` | Strategy overview |
| `/calendar` | `app/(site)/calendar/page.tsx` | Macro event calendar |
| `/about` | `app/(site)/about/page.tsx` | Methodology + simulator |
| `/pairs/[pair]` | `app/(site)/pairs/[pair]/page.tsx` | Pair detail page |
| `/terminal` | `app/terminal/page.tsx` | Terminal index |
| `/terminal/fx-regime` | `app/terminal/fx-regime/page.tsx` | Strategy page |
| `/terminal/fx-regime/[pair]` | `app/terminal/fx-regime/[pair]/page.tsx` | Pair desk |

### Hard Rules

- ZERO `style={}` inline styles — Tailwind only
- ZERO `supabase.from()` outside `web/lib/supabase/queries.ts`
- ZERO AI API calls from frontend — only read cached AI text from Supabase
- ZERO manual edits to `database.types.ts`
- Max 300 lines per file

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
- Frontend NEVER calls any AI API directly — reads cached text from Supabase only

## Database (`supabase/`)

**Platform:** Supabase (PostgreSQL + Auth + RLS)
**Types:** Run `supabase gen types typescript --local > web/lib/supabase/database.types.ts` to regenerate
**Migrations:** `supabase/migrations/` — numbered, never edited after applied

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

**Read-only reference** — these JSX files show the target UI. They use inline styles and prototype patterns. Never import from this folder
in production code. Use them only to understand what a component should look like.

| File | Contains |
|------|---------|
| `components.jsx` | Shared components, mock data, brand tokens |
| `shell-pages.jsx` | HomePage, BriefPage, PerformancePage, FxRegimePage |
| `terminal-pages.jsx` | Terminal pages, AiAnalysisPanel, calendar tab |
| `new-pages.jsx` | CalendarPage, PairDetailPage, RegimeHeatmap |
| `about-page.jsx` | AboutPage with PipelineWalkthrough, CompositeSimulator |
| `loading-states.jsx` | Skeleton loaders (Phase 4) |
| `error-states.jsx` | Error/empty states (Phase 4) |
| `mobile-layouts.jsx` | Mobile responsive designs (Phase 6) |

## Pairs Config

```typescript
const PAIRS = [
  { label: 'EURUSD', display: 'EUR/USD', urlSlug: 'eurusd', pairColor: '#4BA3E3' },
  { label: 'USDJPY', display: 'USD/JPY', urlSlug: 'usdjpy', pairColor: '#F5923A' },
  { label: 'USDINR', display: 'USD/INR', urlSlug: 'usdinr', pairColor: '#D94030' },
];
```

## Phases

┌───────┬─────────┬──────────────────────────────────┐
│ Phase │ Status  │ Focus                            │
├───────┼─────────┼──────────────────────────────────┤
│ 0     │ ✅ Done │ Foundation + repo structure      │
├───────┼─────────┼──────────────────────────────────┤
│ 1     │ ✅ Done │ Design system + all shell pages  │
├───────┼─────────┼──────────────────────────────────┤
│ 2     │ ✅ Done │ Terminal UI                      │
├───────┼─────────┼──────────────────────────────────┤
│ 3     │ ✅ Done │ Pipeline rewrite                 │
├───────┼─────────┼──────────────────────────────────┤
│ 4     │ ✅ Done │ Live data + loading/error states │
├───────┼─────────┼──────────────────────────────────┤
│ 5     │ ✅ Done │ Remaining live data + performance stats │
├───────┼─────────┼──────────────────────────────────┤
│ 6     │ ✅ Done │ Mobile + PWA + terminal live data │
└───────┴─────────┴──────────────────────────────────┘

## Scheduling

To register the daily cron (runs weekdays at 06:30 IST = 01:00 UTC):

- `crontab -e`
- Add: `0 1 * * 1-5 /home/shreyash/fx_regime_lab/fx-regime-lab/pipeline/run_daily.sh >> /tmp/fxlab_daily.log 2>&1`

To register the weekly AI brief cron (runs Sundays at 08:00 IST = 02:30 UTC):

- `0 2 * * 0 /home/shreyash/fx_regime_lab/fx-regime-lab/pipeline/run_weekly.sh >> /tmp/fxlab_weekly.log 2>&1`

To run manually from repo root:

- `pipeline/run_daily.sh`
- `pipeline/run_weekly.sh`

### Post-Phase 6 (manual)

After code is merged and verified: production deploy (e.g. Vercel), set `NEXT_PUBLIC_SUPABASE_*`, `REVALIDATE_SECRET`, `NEXT_JS_URL` in the host dashboard; point local `.env` `NEXT_JS_URL` at production for ISR pings; register crontab lines above for daily/weekly pipeline; run a first live pipeline and confirm revalidate logs; replace PWA placeholder icons under `web/public/images/`; audit Supabase RLS for anon write access; rotate any exposed API keys.
