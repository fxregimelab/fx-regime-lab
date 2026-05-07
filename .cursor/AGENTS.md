# AGENTS.md — FX Regime Lab `.cursor/` Configuration

> This file documents the **complete Cursor agent configuration** for the FX Regime Lab repository. Both Cursor IDE and `agent` CLI use these files.

---

## Directory Map

```
.cursor/
├── rules/              # Auto-applied and conditional rules (*.mdc)
│   ├── FX-Regime-Lab-Core.mdc      # Always applies (hard rules)
│   ├── Session-Start.mdc           # Always applies (session protocol)
│   ├── Pipeline-Rules.mdc          # Applies to pipeline/src/**/*.py
│   ├── Frontend-Rules.mdc          # Applies to web/src/**/*.{ts,tsx,css}
│   ├── Database-Rules.mdc          # Applies to migrations + db code
│   └── Deployment-Rules.mdc        # Applies to prefect.yaml, workers, web config
├── skills/             # Reusable capability modules (SKILL.md)
│   ├── chartjs-fx-regime-dashboard/
│   ├── fx-regime-html-dashboards-briefs/
│   ├── fx-regime-pipeline-triage/
│   ├── fx-regime-signal-pipeline/
│   ├── fx-regime-supabase-writes/
│   ├── pipeline-data-fetch/
│   ├── regime-validation-logging/
│   ├── nextjs-frontend/            # NEW: Next.js + Tailwind 4
│   ├── prefect-deploy/             # NEW: Prefect Cloud
│   ├── cloudflare-worker/          # NEW: Cloudflare Worker
│   └── quant-math/                 # NEW: Quant conventions
├── commands/           # Slash commands available in chat
│   ├── daily-run.md
│   ├── test-suite.md
│   ├── new-migration.md
│   ├── frontend-build.md
│   ├── db-health.md
│   └── validate-signal.md
├── hooks/              # Pre/post session automation
│   ├── pre-session.md
│   └── post-session.md
├── subagents/          # Swarm agent configurations
│   ├── pipeline-engineer.json
│   ├── frontend-engineer.json
│   ├── database-engineer.json
│   ├── devops-engineer.json
│   └── ui-swarm-lead.json
├── mcp.json            # MCP server definitions
└── settings.json       # Workspace-specific Cursor settings
```

---

## Rules System

Rules are `.mdc` files with YAML frontmatter. They auto-apply based on `alwaysApply` or `globs`.

| Rule | Trigger | Purpose |
|------|---------|---------|
| `FX-Regime-Lab-Core.mdc` | Always | Hard rules, 3-pair lock, architecture |
| `Session-Start.mdc` | Always | Pre-session read list, canonical flow |
| `Pipeline-Rules.mdc` | `pipeline/src/**/*.py` | Python coding standards |
| `Frontend-Rules.mdc` | `web/src/**/*.{ts,tsx,css}` | Next.js / Tailwind standards |
| `Database-Rules.mdc` | Migrations + db code | Schema, RLS, write patterns |
| `Deployment-Rules.mdc` | `prefect.yaml`, `workers/*.js` | Prefect, Cloudflare, Vercel |

---

## Skills System

Skills are directories containing `SKILL.md`. They define reusable capabilities that agents can invoke.

| Skill | Use When |
|-------|----------|
| `fx-regime-signal-pipeline` | Adding a new signal module |
| `pipeline-data-fetch` | Building/refactoring fetchers |
| `fx-regime-supabase-writes` | Any Supabase read/write code |
| `regime-validation-logging` | Changing regime/validation tables |
| `fx-regime-pipeline-triage` | Debugging pipeline failures |
| `nextjs-frontend` | Building Next.js components/pages |
| `prefect-deploy` | Changing orchestration/deployment |
| `cloudflare-worker` | Changing API worker routes |
| `quant-math` | Signal math, percentiles, z-scores |

---

## Commands

Type `/command-name` in Cursor chat to invoke.

| Command | Action |
|---------|--------|
| `/daily-run` | Check Prefect + Supabase for today's data |
| `/test-suite` | Run pytest + build + lint + typecheck |
| `/new-migration` | Scaffold a new Supabase migration |
| `/frontend-build` | Build and verify Next.js frontend |
| `/db-health` | Query DB health and row counts |
| `/validate-signal` | End-to-end validate a signal module |

---

## Hooks

Hooks run automatically at session boundaries.

| Hook | When | Action |
|------|------|--------|
| `pre-session` | Session start | Read AGENTS.md, TASK.md, check git status, verify pytest loads |
| `post-session` | Session end | Run pytest, build, lint, suggest commit message |

---

## Subagents

Subagent configs define specialized agents for swarm execution.

| Agent | Role | Skills |
|-------|------|--------|
| `pipeline-engineer` | Quant pipeline dev | signal-pipeline, data-fetch, quant-math, supabase-writes |
| `frontend-engineer` | Next.js dev | nextjs-frontend |
| `database-engineer` | DB architect | supabase-writes, validation-logging |
| `devops-engineer` | Deployment | prefect-deploy, cloudflare-worker |
| `ui-swarm-lead` | Coordinates UI swarm | nextjs-frontend, supabase-writes |

---

## MCP Servers

| Server | Purpose | Auth |
|--------|---------|------|
| `supabase-fx-regime-lab` | Database queries, schema introspection | OAuth via Cursor |
| `github` | PRs, issues, repo ops | `GITHUB_TOKEN` env var |
| `vercel` | Deployments, domains | `VERCEL_TOKEN` env var |
| `cloudflare` | Workers, DNS, zones | `CLOUDFLARE_API_TOKEN` env var |

---

## Global Config

Global Cursor settings live in `~/.cursor/`:
- `~/.cursor/settings.json` — user defaults
- `~/.cursor/mcp.json` — global MCP servers
- `~/.cursor/skills-cursor/` — Cursor-built-in skills

This repo's `.cursor/settings.json` overrides global settings for this workspace.

---

## Keeping Config in Sync

When architecture changes (new directories, new tools, new rules):
1. Update the relevant `.cursor/rules/*.mdc`
2. Update or create `.cursor/skills/<skill>/SKILL.md`
3. Update `.cursor/AGENTS.md` (this file)
4. Update `.cursorrules` at repo root (summary for non-Cursor agents)
5. Run `git add .cursor/ .cursorrules && git commit`

---

## 12. Operating Model: Kimi = Strategy, Cursor = Execution

> **Kimi is the brain. Cursor is the hands.**  
> Kimi plans, researches, architects, and decides. Cursor implements.  
> This is not a cost optimization — it is a quality optimization.

### Division of Labor

| Responsibility | Agent | Why |
|----------------|-------|-----|
| **Research & discovery** | Kimi | Better web search, long context, cross-domain reasoning |
| **Architecture & design** | Kimi | Systems thinking, trade-off analysis, pattern recognition |
| **Planning & spec writing** | Kimi | Precise requirements, edge-case identification |
| **Code implementation** | Cursor | Deep codebase understanding, IDE-grade refactoring, TypeScript precision |
| **Testing & verification** | Kimi | Runs tests, interprets failures, decides if fix is needed |
| **Debugging strategy** | Kimi | Root-cause analysis, hypothesis generation |
| **Debugging execution** | Cursor | Applies fixes across files, handles mechanical changes |

### The Rule

**Kimi NEVER writes production code.** Kimi writes Implementation Specs. Cursor executes them.

The only code Kimi writes directly:
- One-line fixes (typos, import corrections)
- Configuration tweaks (env vars, config files)
- Test assertions (after analyzing failures)
- Documentation

Everything else → delegated to Cursor Agent.

### Implementation Spec Format

Before delegating, Kimi MUST write a spec:

```markdown
# Implementation Spec: [Task Name]

## Context
[Why this is being built, what user story it serves]

## Files
- CREATE: `path/to/new/file.ts`
- MODIFY: `path/to/existing/file.py`
- DELETE: `path/to/obsolete/file.tsx`

## Technical Requirements
- [Specific requirement 1]
- [Specific requirement 2]
- [Design pattern to follow]
- [Types/interfaces to use or create]

## Acceptance Criteria
- [ ] Criterion 1 (testable)
- [ ] Criterion 2 (testable)
- [ ] All existing tests pass
- [ ] `npm run build` or `pytest` passes

## Execution Plan
1. [Step 1 — what to do first]
2. [Step 2 — what to do next]
3. [Step 3 — final verification]

## Context Snippets
[Relevant code excerpts Cursor needs to see]
```

### Delegation Protocol

1. **Kimi writes the spec** (see format above)
2. **Kimi delegates execution**:
   ```bash
   agent --print --trust --approve-mcps --yolo \
     --workspace /home/shreyash/Projects/fx_regime_lab/fx-regime-lab \
     --model claude-sonnet-4-5 \
     "Execute this implementation spec: [paste spec]"
   ```
3. **Cursor executes** with full codebase context
4. **Kimi verifies**:
   - Run tests: `cd pipeline && pytest` or `cd web && npm run build`
   - Check git diff: `git diff --stat`
   - Validate acceptance criteria
5. **If failures**: Kimi analyzes, writes a "Fix Spec," delegates to Cursor
6. **If success**: Kimi reports completion with summary

### When Kimi Handles Directly (No Delegation)

- Pure research questions ("What is the current ECB rate?")
- Architecture decisions without code changes ("Should we use zustand or context?")
- Code review / analysis ("Explain what this function does")
- One-line fixes (single import, single typo)
- Running diagnostics (`pytest`, `npm run lint`, database queries)
- Git operations (commit, branch, merge — but NEVER push --force)

---

## 13. Orchestration System (Advanced)

For complex projects with multiple tasks, use the **Kimi-Cursor Orchestrator**.

See workspace `AGENTS.md` section 12 for full orchestration documentation.

Quick reference:

```bash
# Queue specs
cp spec-*.md .cursor/delegation/queue/

# Process with parallel execution
./scripts/kimi-cursor-orchestrator.sh --process-queue --parallel 3 --yolo

# Read report
.cat .cursor/delegation/logs/*-report.md
```

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/kimi-cursor-orchestrator.sh` | Master orchestrator |
| `scripts/cursor-delegate.sh` | Single-task wrapper |
| `scripts/cursor-verify.sh` | Verification suite |
| `scripts/cursor-warmup.sh` | Pre-warm index |

- Pure research questions ("What is the current ECB rate?")
- Architecture decisions without code changes ("Should we use zustand or context?")
- Code review / analysis ("Explain what this function does")
- One-line fixes (single import, single typo)
- Running diagnostics (`pytest`, `npm run lint`, database queries)
- Git operations (commit, branch, merge — but NEVER push --force)

---

## 12. Agent Interoperability (Kimi ↔ Cursor)

This repo supports **both Kimi and Cursor** agents with unified configuration.

### Shared config
- **Skills**: 11 `SKILL.md` files in `.cursor/skills/` — loaded by both agents
- **Rules**: `.cursorrules` + `AGENTS.md` — readable by both
- **Hard rules**: 3-pair lock, Supabase write patterns, design tokens — enforced by both

### Kimi → Cursor Delegation

For tasks requiring deep cross-file analysis or complex refactoring, Kimi can delegate to Cursor Agent CLI:

```bash
# Plan-only (safe, read-only)
agent --print --trust --workspace . --mode plan "Plan: refactor regime classifier"

# Full execution (use with caution)
agent --print --trust --approve-mcps --yolo \
  --workspace . \
  --model claude-sonnet-4-5 \
  "Task description with full context"
```

Wrapper script for structured delegation:
```bash
./scripts/cursor-delegate.sh \
  --task "Add new signal module" \
  --files "pipeline/src/signals/new.py" \
  --tests "cd pipeline && pytest" \
  --mode auto
```

See `.kimi/skills/cursor-delegation/SKILL.md` for the full delegation protocol.

### What each agent handles best

| Task type | Preferred agent | Why |
|-----------|----------------|-----|
| Research & planning | Kimi | Better web search, long context |
| Single-file edits | Kimi | Faster, cheaper |
| Multi-file refactoring (>3 files) | Cursor | Deep codebase analysis |
| Complex Next.js architecture | Cursor | Better TypeScript/React understanding |
| Pipeline math & signals | Kimi or Cursor | Both capable; use skills |
| Database migrations | Kimi | Safer, more deliberate |
| Deployment ops | Kimi | Shell command precision |

---

*Last updated: 2026-05-06*
