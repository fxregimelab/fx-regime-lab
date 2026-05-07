# Phases

**Current status:** Shipped **Next.js `web/`** UI **removed** (2026-04-28). Root **`wrangler.toml`** removed. Pipeline + Supabase remain the live data path. See [[HOSTING_AFTER_UI_REMOVAL]].

## Historical phases 0–1

Phase 0–1 described scaffolding and shipping a Next App Router surface. That tree is gone; treat archived git history if you need file-level detail.

## Next phase (planned)

**Goal:** New public UI from **`claude-design/`** using a stack chosen explicitly for the product (see [[DATA_READS_SPEC]] for read patterns, [[DESIGN_SYSTEM]] for tokens).

**Concrete targets (when you start):**

- Scaffold app package; wire Supabase anon reads with RLS.
- Map each `claude-design` screen to tables in [[DATABASE_SCHEMA]].
- Single deploy target (Vercel, Cloudflare Pages, etc.) documented in ops notes.

## Phase 2+ (unchanged intent)

Rolling accuracy windows, richer attribution, regime transition history, thesis/hypothesis logs — see [[DATABASE_SCHEMA]] for what exists today vs planned tables.

## Related docs

- [[FEATURE_REGISTRY]]
- [[TECH_STACK]]
- [[FRONTEND_ARCHITECTURE]]
