# FX Regime Lab — Agent Quick Start

> **Kimi = Strategy + Execution.**  
> Complex tasks are delegated to Kimi subagents (`Agent` tool) for cross-file consistency.  
> Read `TASK.md` for current sprint state. Read `OMEGA_PROTOCOL.md` for the council workflow.

## Hard Rules
- **3-pair lock:** EUR/USD, USD/JPY, USD/INR ONLY
- **All DB writes** → `pipeline/src/db/writer.py`
- **All AI calls** → `pipeline/src/ai/client.py`
- **Immutable ledger:** `regime_calls` + `validation_log` append-only
- **No GitHub Actions** — Prefect Cloud only
- **Tests:** `pytest` 219+ tests + `npm run build` + `biome check` must pass

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
- `docs/DATABASE_SCHEMA.md` — table specs, indexes
- `docs/PIPELINE_REFERENCE.md` — step order, failure modes
- `OMEGA_PROTOCOL.md` — The 13-persona council and 6-phase workflow
- `CLAUDE.md` — AI persona, locked decisions, session rules

*Last updated: 2026-05-10*
