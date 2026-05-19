# Frontend Architecture

FX Regime Lab ships a **Next.js 15 App Router** frontend under `web/`. It is a TypeScript/React application with 16 pages, 68+ components, and a strict two-surface design system.

## Route Map

| Route | File | Purpose | Surface |
|-------|------|---------|---------|
| `/` | `src/app/page.tsx` | Home — hero, signal architecture, validation trust, about snippet | Shell (light) |
| `/about` | `src/app/about/page.tsx` | Team, research philosophy, contact | Shell |
| `/audit` | `src/app/audit/page.tsx` | Pipeline health dashboard, system integrity log | Terminal (dark) |
| `/brief` | `src/app/brief/page.tsx` | Daily institutional desk brief | Shell |
| `/calendar` | `src/app/calendar/page.tsx` | Redirects to `/terminal/calendar` | — |
| `/memo` | `src/app/memo/page.tsx` | Research memo archive index | Shell |
| `/memo/[date]` | `src/app/memo/[date]/page.tsx` | Individual memo reader | Shell |
| `/methodology` | `src/app/methodology/page.tsx` | Regime detection framework documentation | Shell |
| `/performance` | `src/app/performance/page.tsx` | Public track record dashboard | Shell |
| `/terminal` | `src/app/terminal/page.tsx` | Main terminal dashboard — signal cards, cross-asset matrix, brief panel | Terminal |
| `/terminal/calendar` | `src/app/terminal/calendar/page.tsx` | Convexity radar / macro calendar | Terminal |
| `/terminal/compare` | `src/app/terminal/compare/page.tsx` | Side-by-side pair desk comparison | Terminal |
| `/terminal/fx-regime` | `src/app/terminal/fx-regime/page.tsx` | Multi-pair regime mosaic | Terminal |
| `/terminal/fx-regime/[pair]` | `src/app/terminal/fx-regime/[pair]/page.tsx` | Single-pair deep-dive desk | Terminal |
| `/terminal/memos` | `src/app/terminal/memos/page.tsx` | Terminal-integrated memo sidebar | Terminal |
| `/terminal/performance` | `src/app/terminal/performance/page.tsx` | Performance ledger (terminal view) | Terminal |
| `/diagnostics` | `src/app/diagnostics/page.tsx` | Internal M.5 diagnostic reports | Terminal |

**API Routes (Pages Router):**
- `/api/linkedin-alpha-hook` — `src/pages/api/linkedin-alpha-hook.ts` — Generates LinkedIn posts from Apex Target card data via OpenRouter.

## Data-Fetching Strategy

### Server Components
Most pages are **Server Components** that fetch data at request time via Supabase SSR:

```typescript
import { createClient } from "@/lib/supabase/server";
import { getLatestRegimeCalls } from "@/lib/supabase/queries";

const supabase = await createClient();
const calls = await getLatestRegimeCalls(supabase);
```

Key server queries live in `src/lib/supabase/queries.ts` and use the typed Supabase client generated from `src/lib/supabase/database.types.ts`.

### Client Components
Interactive surfaces (terminal dashboards, comparison views, memo sidebars) are **Client Components** (marked `"use client"`) that use React Query for caching and real-time feels:

- `src/lib/queries.ts` — React Query hooks wrapping client-side Supabase calls
- `src/lib/queries.ts` also contains `useG10CorrelationMatrix`, `useLatestRegimeCalls`, etc.

### Caching Strategy
- `export const dynamic = "force-dynamic"` on terminal pages (always fresh)
- `export const revalidate = 3600` on audit page (hourly stale-while-revalidate)
- Memo and performance pages use static generation where appropriate

## Component Hierarchy

```
shell/                    → Nav, Footer, layout wrappers
├── dashboard/            → SignalCard, CrossAssetMatrix, DailyBriefPanel
├── terminal/             → TerminalNav, TerminalSubNav, VimNavProvider
├── ui/                   → Reusable primitives: DeskCard, ConfidenceBar,
│                           AuditTrailBanner, CircuitBreaker, etc.
├── pages/                → Page-level compositions (performance-ledger,
│                           convexity-radar, etc.)
├── audit/                → PipelineHealthDashboard
├── layout/               → GlobalMacroPulse
├── regime/               → Regime-specific visualizations
└── methodology/          → MethodologyContent
```

## State Management

- **Server state:** Fetched directly in Server Components, passed as props
- **Client state:** React Query for server-state caching; minimal local React state for UI (hover, selection, modal open/close)
- **URL state:** Terminal compare mode uses query params (`?pairs=eurusd,usdjpy`)
- **No global state library** (Redux/Zustand) — prop drilling is shallow enough

## Build & Deploy

```bash
cd web
npm run build        # Production build → .next/
npm run lint         # Biome check
npx tsc --noEmit     # TypeScript validation
```

- **Host:** Vercel (auto-deploy on push to main)
- **Node:** 18+ required
- **Package manager:** npm
- **Lint:** Biome (not ESLint — see `biome.json`)

## TypeScript Schema

The Supabase schema types are in `src/lib/supabase/database.types.ts`. They are kept in sync with the live database schema via `supabase gen types typescript --project-id <id>`.

## Key Files

| File | Role |
|------|------|
| `src/lib/supabase/queries.ts` | All data reads (server + client) |
| `src/lib/supabase/database.types.ts` | Generated Supabase TypeScript types |
| `src/lib/constants.ts` | PAIRS array, regime labels, thresholds |
| `src/lib/g10Correlation.ts` | G10 correlation matrix logic |
| `src/app/globals.css` | Design tokens (CSS custom properties) |
| `next.config.ts` | Next.js config (webpack, eslint ignore during builds) |
