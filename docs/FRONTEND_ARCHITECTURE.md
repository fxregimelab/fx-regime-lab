# Frontend architecture

Source of truth: the `web/` tree as it exists in the repo. This doc lists **actual** routes, components, and data paths. Where the repo still diverges from a strict layering rule, that divergence is called out.

## Next.js 15.5.2 App Router layout

- **Root layout:** `web/app/layout.tsx` loads Google fonts (Inter, Fraunces, JetBrains Mono via `next/font/google`), applies `web/app/globals.css`, and wraps all pages.
- **Shell route group:** `web/app/(shell)/layout.tsx` imports `web/styles/shell.css`, renders `Nav`, `Footer`, `CanvasBg`, and `{children}`. URL paths **omit** the group name `(shell)`.
- **Terminal tree:** `web/app/terminal/layout.tsx` imports `web/styles/terminal.css` and `TerminalNav`, then `{children}`.

There is **no** client-side theme toggle: shell vs terminal is purely **which segment** of the app you are in.

## Route table

| URL path | File | Server or client | What it renders | Supabase usage today |
|----------|------|-------------------|------------------|----------------------|
| `/` | `web/app/(shell)/page.tsx` | Server | Home intro and links | None |
| `/brief` | `web/app/(shell)/brief/page.tsx` | Server shell; embeds client child | Morning brief heading + `BriefRenderer` | Client hook reads `brief_log` (see below) |
| `/about` | `web/app/(shell)/about/page.tsx` | Server | Static about copy | None |
| `/performance` | `web/app/(shell)/performance/page.tsx` | Server | Placeholder performance copy | None |
| `/[strategy]` | `web/app/(shell)/[strategy]/page.tsx` | Server (async params) | Strategy title from `params.strategy` | None |
| `/[strategy]/performance` | `web/app/(shell)/[strategy]/performance/page.tsx` | Server | Placeholder | None |
| `/terminal` | `web/app/terminal/page.tsx` | Server | Lists `STRATEGIES` from constants | None |
| `/terminal/[strategy]` | `web/app/terminal/[strategy]/page.tsx` | Server | Pair links from `PAIRS` | None |
| `/terminal/[strategy]/[pair]` | `web/app/terminal/[strategy]/[pair]/page.tsx` | Server wrapper | Embeds client `PairDesk` | Client hooks read `regime_calls` and `signals` |
| `/api/brief` | `web/app/api/brief/route.ts` | Route handler | JSON `{ brief }` latest row | Server `createClient()` `.from('brief_log')` |
| 404 | `web/app/not-found.tsx` | Server | Not found message | None |

**Missing relative to stated policy:** there are **no** `loading.tsx` or `error.tsx` files next to routes yet (glob returns zero). Add them when touching those route folders.

## Component inventory (`web/components/`)

| File | Client? | Props / behavior |
|------|---------|------------------|
| `shell/Nav.tsx` | Client (`'use client'`) | No props; links Home, Brief, Research dropdown, About. |
| `shell/Footer.tsx` | Server | No props; footer links. |
| `shell/CanvasBg.tsx` | Client | No props; canvas grid background. |
| `terminal/TerminalNav.tsx` | Client | No props; terminal strip links. |
| `terminal/PairDesk.tsx` | Client | `strategy: string`, `pairSlug: string`; resolves pair label, calls hooks. |
| `terminal/SignalDepth.tsx` | Client | `values: SignalValue \| null`, `loading?: boolean`. |
| `regime/RegimeCard.tsx` | Client | `call: RegimeCall \| null`, `loading?: boolean`. |
| `regime/SignalStack.tsx` | Client | `call: RegimeCall \| null`. |
| `regime/ValidationTable.tsx` | Client | `rows: ValidationRow[]`, `loading?: boolean`. |
| `regime/ConfidenceBar.tsx` | Client | `value: number \| null \| undefined`. |
| `charts/TimeSeriesChart.tsx` | Client | `data: TimePoint[]`, optional `className`; wraps Lightweight Charts `LineSeries`. |
| `charts/RegimeChart.tsx` | Client | `title: string`, `series: TimePoint[]`. |
| `brief/BriefRenderer.tsx` | Client | No props; uses `useBrief`. |
| `ui/Badge.tsx` | Server | `regime: string`; maps through `REGIME_COLORS`. |
| `ui/Skeleton.tsx` | Server | `className?: string`. |
| `ui/Button.tsx` | Server | `variant?`, spreads native `button` props. |

## Two theme surfaces

- **Shell:** Light background token `shell-bg` `#f5f5f0` (see `web/tailwind.config.ts` and CSS variables in `web/app/globals.css`). Body default is light.
- **Terminal:** Classes `terminal-root`, `terminal-surface`; tokens `terminal-bg` `#0a0a0a`, `terminal-surface` `#1a1a1a`. Typography mix matches design intent (see [[DESIGN_SYSTEM]]); implementation still uses `font-mono` in several terminal components for whole blocks, not only numerics (gap vs design doc).

## Data fetching pattern (actual)

**Central module:** `web/lib/supabase/queries.ts` defines `fetchLatestBrief`, `fetchLatestRegimeCall`, `fetchLatestSignalsRow`, `fetchValidationRecent`.

**Reality today:** hooks and the API route still call `supabase.from(...)` **inline**:

- `web/hooks/useBrief.ts`, `useRegimeCalls.ts`, `useSignalValues.ts`, `useValidationLog.ts` each build a browser client and query directly.
- `web/app/api/brief/route.ts` builds a server client and queries `brief_log` directly.

**Target rule for new work:** move all Supabase reads into `queries.ts` functions and call those from hooks and route handlers so there is a single edit surface (see [[CURSOR_RULES]]).

**Clients:**

- Browser: `web/lib/supabase/client.ts` (`createBrowserClient` from `@supabase/ssr`).
- Server / Route handlers: `web/lib/supabase/server.ts` (`createServerClient` with Next `cookies()`).

## TradingView Lightweight Charts rules

- **Wrapper:** `web/components/charts/TimeSeriesChart.tsx` is the only place that should call `createChart` / `addSeries` for line charts.
- **Do not** import `lightweight-charts` from pages or arbitrary components; compose through `TimeSeriesChart` or `RegimeChart`.
- Charts depend on browser APIs and client hooks: keep chart components under `'use client'` (current code does).

## Middleware

File: `web/middleware.ts`.

- **Matcher:** `['/terminal/:path*']` only.
- **Behavior:** `NextResponse.next()` for every matched request. No auth, no redirects. This is a stub for future private terminal routes.

## Related docs

- [[DESIGN_SYSTEM]]
- [[DATABASE_SCHEMA]]
- [[TECH_STACK]]
