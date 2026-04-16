---
title: FX Regime Lab — docs index
description: Map of committed documentation (Obsidian-friendly). Vault root is usually the repo root.
tags:
  - index
  - hub
---

# Documentation index (`docs/`)

Use this file as a **map of content** in Obsidian. Links to `contaxt files/` and `reports/` assume the vault root is the **repository root** (recommended).

## Pipeline and operations

| Note | Topic |
|------|--------|
| [[PIPELINE_AUDIT_AND_OPERATIONS]] | Canonical `run.py` order, CI env (`LAYER3_STRICT`, deploy strictness), merge exit codes, links to audit report |
| [Pipeline E2E audit](../reports/pipeline_e2e_audit.md) | Contract matrix, remediation status, triple-check procedure |
| [[CODEBASE_AND_PROJECT_REFERENCE]] | Repository map, data flow, Cloudflare, GitHub Actions |
| [[LOCAL_DEV]] | Local `.env`, `run.py`, Supabase backfill, wrangler |

## Product and UI

| Note | Topic |
|------|--------|
| [[FX_REGIME_ROADMAP]] | Phased roadmap aligned with PLAN |
| [[G10_FX_FRAMEWORK_MASTER_PLAN]] | Long-form framework |
| [[FX_REGIME_LAB_UI_PROMPT_V2]] | Public site UI v2 (light editorial) |
| [[UI_UX_DEEP_REFERENCE]] | Site shell, nav, tokens, Chart.js vs ECharts |
| [[TERMINAL_DEEP_REFERENCE]] | Bloomberg-style terminal (`site/terminal/`) |

## Phase 0 and implementation

| Note | Topic |
|------|--------|
| [[PHASE0_CHECKLIST]] | Phase 0 exit criteria |
| [[IMPLEMENTATION_PLAN_PHASE0]] | Ordered implementation order |
| [[PHASES_LATER_GATES]] | Later phase gates |

## Infrastructure

| Note | Topic |
|------|--------|
| [[SUPABASE_SETUP]] | Supabase project setup |
| [Cloudflare setup](../site/CLOUDFLARE_SETUP.md) | Worker + Pages deploy |

## Context files (repo root)

Not under `docs/` but linked from PLAN/CONTEXT:

- `contaxt files/PLAN.md`
- `contaxt files/CONTEXT.md`
- `contaxt files/CURSOR_RULES.md`
- `AGENTS.md`

---

*If you use a vault that only contains `docs/`, use relative paths or duplicate key notes into `docs/` and link with `[[wikilinks]]` within the folder.*
