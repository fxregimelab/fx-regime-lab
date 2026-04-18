# Phases

**Current phase:** Phase 1 — FX Regime Lab v2 (Next.js public surface + live Supabase reads). Phase 0 archive and scaffold is complete.

## Phase 0 — Archive and scaffold (COMPLETE)

**Done:**

- Entire pre-v2 tree moved under `_archive/v1/` except `.git`, `.gitignore`, root `.env` / `.env.local`.
- Executable Python tree copied back to root (see scaffold summary in git history).
- `web/` created as Next.js 15.5.2 App Router project with shell vs terminal layouts, hooks, types, constants, Supabase clients, and chart wrapper.
- Root `wrangler.toml` now targets Cloudflare Pages output for `web/` (see [[TECH_STACK]] for CI mismatch note).

**Repo shape now:** pipeline at root, legacy static site only in `_archive/v1/site`, new frontend in `web/`, operator docs in `docs/` (this folder).

## Phase 1 — FX Regime Lab v2 live on Cloudflare Pages (IN PROGRESS)

**Goal:** Public pages on the Next app read live Supabase rows with the design system applied; legacy HTML shell is no longer the primary surface.

**Concrete targets:**

- Home (`/`) and brief (`/brief`) show real `brief_log` / `regime_calls` / `signals` content, not placeholder copy.
- Performance pages read `validation_log` aggregates.
- Terminal pair desks (`/terminal/fx-regime/eurusd` etc.) match desk semantics from pipeline.
- Mobile layout passes basic usability on shell and terminal.
- CI deploy path updated from Worker-only static deploy to **Pages** (or a documented dual deploy) consistent with root `wrangler.toml`.

**Completion check:**

- Production URL serves the Next build.
- All three pairs show current-day or latest-available Supabase rows without manual CSV bridging.

## Phase 2 — Track record layer (PLANNED)

Rolling accuracy windows, richer attribution views, regime transition history, explicit thesis and hypothesis logs in database (tables **do not exist yet**; see [[DATABASE_SCHEMA]]).

## Phase 3 — Research depth and auth (PLANNED)

Supabase Auth, private research notes, divergence feeds, heavier modeling and calendar overlays.

## Phase 4 — Differentiation (PLANNED)

Realtime, peer comparison, paper trading UI backed by `paper_positions` schema, NLP layers per archived roadmap gates in `_archive/v1/docs/PHASES_LATER_GATES.md`.

## Phase 5 — Multi-strategy (PLANNED)

Add `strategy_id` in Postgres and route multi-strategy UX; today only string id `fx-regime` in `web/lib/constants/strategies.ts`.

## Locked decisions (code-enforced or CI-enforced today)

These are **operational locks** grounded in the repo, not aspirational marketing copy:

1. **Single orchestrator:** daily work runs through `run.py` step list; do not fork a second scheduler without updating docs.
2. **Service role for pipeline writes:** `core/supabase_client.py` uses `SUPABASE_SERVICE_ROLE_KEY` for writes. Public anon is read-only under RLS for published tables.
3. **Non-blocking steps:** `ai`, `macro`, `validate`, `substack` may fail without killing the full pipeline (`run.py` `NON_BLOCKING_STEPS`).
4. **Strict Layer 3 in CI:** `LAYER3_STRICT=1` in GitHub Actions enforces sidecar discipline for vol/oi/rr pipelines.
5. **Charts on web:** Lightweight Charts only inside the approved wrapper (see [[CURSOR_RULES]]).
6. **Immutable public call data:** treat published `regime_calls` and `signals` rows as historical facts; fixes go forward on new dates, not silent edits, unless a dedicated admin task says otherwise.

**Archived narrative locks** (product positioning, gated dependencies like FinBERT) still live in `_archive/v1/docs/G10_FX_FRAMEWORK_MASTER_PLAN.md` and `_archive/v1/docs/PHASES_LATER_GATES.md`. Those files are **not automatically kept in sync** with code; verify against pipeline source before relying on them.

## Related docs

- [[PROJECT_OVERVIEW]]
- [[PIPELINE_REFERENCE]]
- [[FEATURE_REGISTRY]]
