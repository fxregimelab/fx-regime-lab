---
name: nextjs-frontend
description: >-
  Builds Next.js 15+ frontend components for FX Regime Lab. Enforces Swiss
  Monochrome design system, TanStack Query, Recharts, and generated Supabase types.
---

# Next.js Frontend — FX Regime Lab

## When this applies

Any new or edited file in `web/src/` — pages, components, hooks, lib, styles.

## Stack

- Next.js 15+ (App Router)
- React 19, TypeScript 5
- Tailwind CSS 4
- TanStack Query
- Recharts
- KaTeX
- lightweight-charts

## Design System — Swiss Monochrome

| Token | Value |
|-------|-------|
| Terminal bg | `#000000` |
| Shell bg | `#ffffff` |
| Terminal text | `#ffffff` |
| Shell text | `#000000` |
| Border dark | `1px solid #1e293b` |
| Border light | `1px solid #e5e7eb` |
| EUR/USD | `#4da6ff` |
| USD/JPY | `#ff9944` |
| USD/INR | `#e74c3c` |
| Muted text | `#6b7280` |

- **No rounded corners** (`rounded-*` forbidden).
- **No soft shadows** (`shadow-*` forbidden).
- **No decorative animations**. Functional transitions only.
- All financial numbers use `tabular-nums`.
- Font: JetBrains Mono for numbers, Inter for body.

## Component Conventions

- **Server components by default**. Use `'use client'` only for:
  - Hooks (`useState`, `useEffect`, `useQuery`)
  - Event handlers
  - Browser APIs (`localStorage`, `WebSocket`)
- Co-locate page-specific components with their route.
- Shared primitives in `web/src/components/ui/`.
- Chart components in `web/src/components/charts/`.

## Data Fetching

- Server: `fetch` with `revalidate` or `cache: 'force-cache'`.
- Client: TanStack Query `useQuery` / `useSuspenseQuery`.
- Supabase: `createServerClient` (server) or `createBrowserClient` (client).
- Never expose service role key to frontend.

## TypeScript

- `strict: true` — never disable.
- Use `web/src/lib/supabase/database.types.ts` for all DB types.
- Explicit return types on all `fetch` calls.
- No `any` without explicit eslint disable.

## Routing

- App Router only. No `pages/` directory.
- Route groups: `(shell)/`, `(terminal)/`.
- 18 routes defined in `OMEGA_UI_SWARM_PROMPT.md`.

## Checklist

- [ ] Colors match design tokens exactly.
- [ ] No `rounded-*` or `shadow-*` classes.
- [ ] Financial numbers use `tabular-nums`.
- [ ] Uses generated Supabase types.
- [ ] `npm run build` passes zero errors.
