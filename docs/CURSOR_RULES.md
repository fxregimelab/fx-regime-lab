# Cursor rules (AI agents)

Read the relevant doc before editing:

- Frontend surface: [[FRONTEND_ARCHITECTURE]], [[DESIGN_SYSTEM]]
- Data and Supabase: [[DATABASE_SCHEMA]]
- Pipeline and cron: [[PIPELINE_REFERENCE]]
- Signal math: [[SIGNAL_DEFINITIONS]]

## Frontend rules (`web/`)

1. Framework is **Next.js 15 App Router** only (`web/app/`). Do not add `pages/` router routes.
2. **TypeScript strict** is on. No `any`. No `@ts-ignore` / `@ts-expect-error`. Prefer narrowing and proper generics. Remove unsafe `as` casts when you touch a file that contains them.
3. **Tailwind only** for styling in React components. No inline `style={{}}`. No CSS Modules. No styled-components / Emotion.
4. **Charts:** `lightweight-charts` is allowed **only** inside `web/components/charts/TimeSeriesChart.tsx` (and thin wrappers like `RegimeChart.tsx`). Do not add Chart.js, ECharts, Plotly, Recharts.
5. **Supabase reads:** prefer `web/lib/supabase/queries.ts`. **Current codebase still queries in hooks and in `web/app/api/brief/route.ts`:** when you change those files, migrate the query into `queries.ts` instead of extending the sprawl.
6. **Clients:** server components and route handlers import `web/lib/supabase/server.ts`. Client components and hooks import `web/lib/supabase/client.ts`. Never swap them.
7. **Constants:** use `web/lib/constants/pairs.ts`, `regimes.ts`, `strategies.ts`. Do not introduce new scattered string literals for pairs, strategy ids, or regime display keys.
8. **Route quality:** when adding or restructuring routes, add matching `loading.tsx` and `error.tsx` in the same folder. (They are missing today; treat absence as debt.)
9. **Shell vs terminal:** no `dark:` hacks inside shell-only marketing pages. Terminal pages assume dark background; do not force light theme there.
10. **Typography:** move toward the rules in [[DESIGN_SYSTEM]] when editing UI (Fraunces for regime labels only, JetBrains for numerics). Do not introduce third-party fonts.
11. **Copy:** no Unicode em dash characters in user-visible strings.
12. **Colors in JSX:** prefer Tailwind tokens (`bg-shell-bg`, `text-accent`, `border-neutral-800`, etc.). Keep hex literals confined to shared constants files when needed for chart APIs.

## Pipeline rules (repo root Python)

1. Do not edit any `*.py` file unless the task explicitly says you are changing the Python pipeline.
2. Do not edit `workers/site-entry.js` unless the task explicitly says you are changing Worker routing or headers.
3. Do not edit `.github/workflows/*` unless the task explicitly says you are changing CI.
4. **Writers:** only Python (and Supabase SQL operators) write financial tables. `signals`, `regime_calls`, `brief_log`, `validation_log`, `pipeline_errors` inserts originate in pipeline modules and `core/`.
5. **Upserts:** follow existing `upsert(..., on_conflict=...)` patterns. Do not switch fragile tables to blind `insert`.
6. **Next.js writes:** do not add Supabase writes from the Next app except future authenticated user-specific tables explicitly approved in a task. `web/app/api/brief/route.ts` is **GET read-only** today; keep it that way unless a task expands scope.

## General rules

1. Verify table and column names against [[DATABASE_SCHEMA]] before writing SQL or Supabase queries.
2. One task, one focused diff. No drive-by refactors.
3. After completing a task, list **files touched** and **what changed** in each file in your final message to the operator.

## Related docs

- [[PHASES]]
- [[FEATURE_REGISTRY]]
