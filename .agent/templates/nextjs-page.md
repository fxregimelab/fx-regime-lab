# Implementation Spec: [PAGE_NAME] Next.js Page

## Context
Add a new page to the FX Regime Lab research terminal.

## Files
- CREATE: `web/src/app/[route]/page.tsx`
- CREATE: `web/src/app/[route]/layout.tsx` (if needed)
- CREATE: `web/src/components/[name]/[component].tsx`

## Technical Requirements
- Server component by default (use 'use client' only for interactivity)
- Strict TypeScript — use generated Supabase types
- Tailwind CSS 4 — Swiss Monochrome tokens
- No rounded corners, no shadows
- Financial numbers use `tabular-nums`
- KaTeX for math rendering
- Data fetching: server = fetch with revalidate, client = TanStack Query

## Design Tokens
- Terminal bg: `#000000`, text: `#ffffff`
- Shell bg: `#ffffff`, text: `#000000`
- EUR/USD: `#4da6ff`, USD/JPY: `#ff9944`, USD/INR: `#e74c3c`
- Border: `1px solid #1e293b` (dark) / `#e5e7eb` (light)

## Acceptance Criteria
- [ ] Page renders at `/[route]`
- [ ] Uses generated Supabase types
- [ ] No TypeScript errors
- [ ] `cd web && npm run build` passes
- [ ] `cd web && npm run lint` passes
- [ ] Responsive layout works

## Execution Plan
1. Create page component with minimal shell
2. Add data fetching logic
3. Style with Tailwind using design tokens
4. Add to navigation if needed
5. Build and verify
