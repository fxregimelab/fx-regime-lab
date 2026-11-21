---
title: Project Map — FX Regime Lab and ThesisGraph
date: 2026-11-01
status: current-navigation
tags: [project-hub]
---

# Project map

**Start with [[ThesisGraph/00 Start Here|ThesisGraph — Start Here]].** It connects the product direction, the first analyst workflow, the existing FX research and your learning plan.

ThesisGraph is the planned finance workspace under Metis Labs. FX Regime Lab's recommended long-term home is ThesisGraph Macro. The current code and deployment have not been renamed by this documentation pass.

## One main working note

Use [[ThesisGraph/00 Start Here|ThesisGraph — Product and Learning Notebook]] for the complete plan, architecture, design sequence, risks, PM responsibilities and your own notes. Its contents link to sections within the same document. The earlier topic notes are optional supporting references linked at the end; they are no longer a required reading sequence.

## Evidence and delivery scope

The current task contract and joint design sequence are in [[ThesisGraph/00 Start Here#Task contract and screen decisions|the main notebook]]. Use [[ThesisGraph/CONTEXT|the short context handoff]] to resume. [[reports/strategy-2026-11-01/PILOT-DECISION|PILOT-DECISION]] preserves historical reasoning. Earlier broad workbench plans are indexed in [[reports/strategy-2026-11-01/README|Strategy documents]]; they do not expand the pilot.

Read [[reports/workspace-audit-2026-11-01/FINAL-VERIFICATION|Final audit verification]] before relying on old health or performance claims. Use [[reports/workspace-audit-2026-11-01/FOLDER-MAP|the folder map]] for the two-checkout inventory and physical consolidation plan. The [[reports/vault-organisation-2026-11-01/ORGANISATION-REPORT|organisation receipt]] records this documentation pass.

## Existing implementation authority

Read [[IDENTITY|IDENTITY]] first, [[MASTERPLAN|MASTERPLAN]] second and [[TASK|TASK]] for the recorded sprint state. [[AGENTS|AGENTS]], [[CLAUDE|CLAUDE]] and [[OMEGA_PROTOCOL|OMEGA_PROTOCOL]] contain project rules and process. Their legacy product restrictions need deliberate reconciliation before successor implementation; a new strategy note does not silently replace them.

[[CONTEXT|CONTEXT]], [[HANDOVER|HANDOVER]] and [[project-overview|the historical project overview]] remain useful background. Dates, runtime claims, career statements and production metrics in older notes must be checked against current evidence.

## Code and research locations

| Location | Purpose |
|---|---|
| `pipeline/` | Source collection, research calculations, database writes and validation |
| `web/` | Web application |
| `workers/` | Worker implementation and configuration |
| `supabase/`, `sql/` | Database definitions and migrations |
| `docs/`, `tasks/` | Technical references and work records |
| `data/`, `briefs/`, `charts/`, `weekly_regime_read/` | Research inputs and outputs; check provenance and date |
| `reports/` | Audit evidence, strategy records and verification receipts |
| `claude-design/`, `logos/` | Design references and assets |
| `_archive/`, `_docs/` | Historical records; `_docs/` remains protected |

Check package manifests and actual runtime health when developing. No runtime version or production-health claim is implied by this map. Keep local secrets and private evidence outside public exports.
