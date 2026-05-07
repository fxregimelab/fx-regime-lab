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

*Last updated: 2026-05-06*
