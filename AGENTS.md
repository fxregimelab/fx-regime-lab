# FX Regime Lab — Agent Quick Start

> **Kimi = Strategy + Execution.**  
> Complex tasks are delegated to Kimi subagents (`Agent` tool) for cross-file consistency.  
> **Read `IDENTITY.md` first** — it is the hard constraint. No task may violate it.  
> **Read `MASTERPLAN.md` second** — it is the single source of truth for all planning and product direction.  
> Read `TASK.md` for current sprint state. Read `OMEGA_PROTOCOL.md` for the council workflow rules (not roadmap).

## Hard Rules
- **3-pair lock:** EUR/USD, USD/JPY, USD/INR ONLY
- **All DB writes** → `pipeline/src/db/writer.py`
- **All AI calls** → `pipeline/src/ai/client.py`
- **Immutable ledger:** `regime_calls` + `validation_log` append-only
- **No GitHub Actions** — Prefect Cloud only
- **Tests:** `pytest` 235 tests + `biome check` must pass
- **Build:** `npm run build` must pass (Vercel Linux deployment is the canonical build; local Windows builds may fail due to a known Next.js 15.3.9 + Windows `readlink` EISDIR bug — see Known Issues below)
- **Primary success metric:** EUR/USD rolling 90-day directional accuracy (target ≥ 55%)
- **No new pairs until EUR/USD ≥ 55% on 90-day window** (3-pair lock)

## Kimi Workflow

### Simple Tasks (Single-file fixes, quick questions)
1. Read `TASK.md` → current sprint
2. Read relevant source files
3. **Execute directly** — modify, test, commit

### Complex Tasks (Multi-file features, refactoring, architecture)
1. Read `TASK.md` → current sprint
2. **Plan** → Use `EnterPlanMode` for non-trivial implementation
3. **Explore** → Use `Agent(subagent_type="explore")` to investigate codebase
4. **Execute** → Use `Agent(subagent_type="coder")` for cross-file implementation
5. **Verify** → Run tests (`pytest`, `ruff`, `npm run build`)

### Subagent Types
| Type | Use When |
|------|----------|
| `explore` | Need to understand a module, find files, trace code paths |
| `coder` | Need to implement across multiple files, run commands, debug |
| `plan` | Need architecture decisions before writing code |

## Verification Commands
```bash
# Pipeline
cd pipeline && pytest              # all tests
cd pipeline && ruff check .        # lint
cd pipeline && mypy .              # type check

# Frontend
cd web && npm run build            # production build
cd web && npm run lint             # biome/eslint
```

## Deep Docs (Read When Needed)
- `docs/SIGNAL_DEFINITIONS.md` — exact math, weights, thresholds
- `docs/DB_STATUS.md` — canonical live schema reference (table specs, indexes, migration history, cleanup log)
- `docs/DATABASE_SCHEMA.md` — (legacy, use DB_STATUS.md instead)
- `docs/PIPELINE_REFERENCE.md` — step order, failure modes
- `MASTERPLAN.md` — Ultimate product roadmap (THIS is the plan)
- `OMEGA_PROTOCOL.md` — The 13-persona council and workflow rules (process, not product direction)
- `CLAUDE.md` — AI persona, locked decisions, session rules

*Last updated: 2026-05-16*

## Current Status (v1.0 Launch Complete)

| Component | Status |
|-----------|--------|
| Rolling 90-day accuracy (backend) | ✅ Computed + backfilled |
| Rolling 90-day accuracy (frontend) | ✅ Landing, Terminal, Performance pages |
| OG Images (social sharing) | ✅ Terminal pairs, Performance, Memo |
| About page | ✅ Author identity + methodology summary |
| SEO | ✅ Sitemap.xml, robots.txt, Schema.org Dataset |
| Pipeline health dashboard | ✅ Backend + frontend (audit page) |
| Accuracy alert system | ✅ Slack alerts at 50%/55% gates |
| WSL2 dev environment | ✅ Ubuntu 24.04 + Node 24 + Python 3.11 |
| Methodology interactive signals | ✅ 8-signal decomposition component |
| Accuracy milestone tracker | ✅ Performance page integration |
| SSRN paper draft | ✅ docs/SSRN_PAPER_DRAFT.md |
| NSDL FPI research | ✅ docs/V2_NSDL_FPI_RESEARCH.md |
| OTC Risk Reversal research | ✅ docs/V2_RISK_REVERSAL_RESEARCH.md |

## Known Issues

### Local Windows Build: `EISDIR: illegal operation on a directory, readlink`
- **Symptom:** `npm run build` fails on Windows with `readlink` errors for app-directory files (`sitemap.ts`, `robots.ts`, `opengraph-image.tsx`, dynamic routes like `[date]/page.tsx`).
- **Root cause:** Known Next.js 15.3.9 + Windows filesystem interaction bug (not project code).
- **Workaround:** Vercel deployment (Linux) builds successfully. Local frontend validation can use `npx tsc --noEmit` instead.
- **Status:** Monitoring Next.js releases for a fix. Upgrading to 15.4.x/15.5.x did not resolve.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **fx-regime-lab** (13752 symbols, 19366 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/fx-regime-lab/context` | Codebase overview, check index freshness |
| `gitnexus://repo/fx-regime-lab/clusters` | All functional areas |
| `gitnexus://repo/fx-regime-lab/processes` | All execution flows |
| `gitnexus://repo/fx-regime-lab/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
