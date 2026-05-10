# Frontend Hub

> Next.js 15 App Router research terminal. Swiss Monochrome aesthetic.

## App Router (`app/`)

| Route | Purpose |
|-------|---------|
| `/` | Landing page |
| `/terminal` | Cross-pair overview |
| `/terminal/fx-regime` | G10 mosaic |
| `/terminal/fx-regime/[pair]` | **Pair Desk** — the main research view |
| `/terminal/performance` | Track record, Brier scores, win rates |
| `/methodology` | 3-layer framework documentation with KaTeX |
| `/about` | Operational identity |

## Component Architecture

| Layer | Directory | Examples |
|-------|-----------|----------|
| Page wrappers | `components/pages/` | `performance-ledger-page-content.tsx` |
| Dashboard | `components/dashboard/` | `SignalCard`, `CrossAssetMatrix`, `SystemStatusBar` |
| Regime | `components/regime/` | `RegimeCard`, `ValidationTable` |
| Performance | `components/performance/` | `StatsCard`, `BrierChart`, `PairBreakdownTable` |
| Terminal chrome | `components/terminal/` | `TerminalNav`, `TerminalSubNav` |
| Shell | `components/shell/` | `Nav`, `Footer` |
| UI primitives | `components/ui/` | `confidence-bar`, `sparkline`, `desk-card` |

## Data Layer

| File | Purpose |
|------|---------|
| `lib/supabase/client.ts` | Browser Supabase client |
| `lib/supabase/server.ts` | Server-side Supabase client |
| `lib/supabase/database.types.ts` | **Generated types** — never edit manually |
| `lib/queries.ts` | React Query hooks for all data fetching |
| `lib/pairProfiles.ts` | Pair metadata |

## Design System

- **Light Mode ("Shell")**: Reports, briefings, summaries
- **Dark Mode ("Terminal")**: Pure black (#050505) for research desks
- **Typography**: Tabular nums for all financial data
- **Borders**: Sharp 1px, no rounded corners
- **Math**: KaTeX for formula display

## Connections
- Frontend reads from: [[Database]] (via Supabase client)
- Frontend displays: [[Pipeline]] outputs (signals, regimes, validation stats)
- Frontend styled by: Swiss Monochrome tokens
