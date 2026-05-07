# FX Regime Lab — Cursor Agent Reference

> **Cursor = Execution.** Read `.cursorrules` first. Execute Kimi's Implementation Specs exactly.

## Quick Links
- **Master manifest:** `../.agent/index.json`
- **Code map:** `../.agent/maps/CODEMAP.json`
- **Skill map:** `.cursor/skills/*/SKILL.md`
- **Rules:** `.cursor/rules/*.mdc`

## Auto-Applied Rules
| Rule | Applies To |
|------|-----------|
| `FX-Regime-Lab-Core.mdc` | Always — hard rules, 3-pair lock |
| `Session-Start.mdc` | Always — pre-session protocol |
| `Pipeline-Rules.mdc` | `pipeline/src/**/*.py` |
| `Frontend-Rules.mdc` | `web/src/**/*.{ts,tsx,css}` |
| `Database-Rules.mdc` | migrations + db code |
| `Deployment-Rules.mdc` | `prefect.yaml`, workers |

## Execution Protocol
1. Receive Implementation Spec from Kimi
2. Read `.cursorrules` and relevant `.mdc` rules
3. Read all files listed in the spec
4. Implement exactly as written — no deviation
5. Run tests specified in the spec
6. Report: files changed, tests passed/failed

## Delegation Scripts
```bash
# Single spec
./scripts/cursor-delegate.sh --spec spec.md --yolo

# Full orchestrator
./scripts/kimi-cursor-orchestrator.sh --process-queue --parallel 3

# Verify
./scripts/cursor-verify.sh --all

# Warm-up
./scripts/cursor-warmup.sh
```

## Subagents
| Agent | Role | Load Skill |
|-------|------|-----------|
| `pipeline-engineer` | Quant dev | `fx-regime-signal-pipeline` |
| `frontend-engineer` | Next.js dev | `nextjs-frontend` |
| `database-engineer` | Schema/RLS | `fx-regime-supabase-writes` |
| `devops-engineer` | Deploy | `prefect-deploy`, `cloudflare-worker` |
| `ui-swarm-lead` | UI swarm | `nextjs-frontend` |
| `cursor-executor` | Pure execution | all relevant |

*Last updated: 2026-05-06*
