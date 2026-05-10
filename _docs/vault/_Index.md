# FX Regime Lab — Knowledge Vault Index

> This vault contains the complete cognitive map of the FX Regime Lab codebase. Every significant module, mathematical concept, and data flow is documented here with explicit connections.

## How to Use This Vault

1. **Start here** — read the hub notes for your domain of interest
2. **Follow links** — every note uses `[[wiki-links]]` to connect to related concepts
3. **Open Graph View** — `Ctrl+G` to see the full connection map
4. **Search** — `Ctrl+Shift+F` to find any concept across all notes

## Domain Hubs

| Hub | Contains |
|-----|----------|
| [[Pipeline]] | All Python pipeline modules: fetchers, signals, logic, regime, validation |
| [[Frontend]] | Next.js app router, components, hooks, data layer |
| [[Database]] | Schema, tables, constraints, RLS policies |
| [[Mathematics]] | All formulas, statistical methods, and why they were chosen |
| [[Agent Workflow]] | How to use Kimi subagents for development |

## Critical Data Flows

| Flow | Description |
|------|-------------|
| [[Signal Flow]] | End-to-end: ingestion → computation → classification → persistence |
| [[Validation Flow]] | T+5/T+20 backtest mechanics and accuracy scoring |
| [[Immutable Ledger]] | Why regime_calls and validation_log are append-only |

## Most-Referenced Modules

| Module | Why It Matters |
|--------|---------------|
| [[layer1_gate]] | Determines if the macro environment is tradeable |
| [[layer2_directional]] | Computes directional bias + conviction (1–5) |
| [[layer3_execution]] | Entry timing, stop levels, position sizing |
| [[composite]] | Weighted aggregation of all signals |
| [[confidence]] | How sure is the model? |
| [[writer]] | The only file allowed to write to Supabase |
| [[validation_engine]] | T+5/T+20 directional accuracy |
| [[simulation_engine]] | Historical backfill for 17k+ regime calls |

## Mathematical Core

| Concept | Used In |
|---------|---------|
| [[Z-Score]] | [[rate]], [[volatility]] — robust normalization |
| [[MAD Normalization]] | Outlier-resistant alternative to standard deviation |
| [[Composite Score]] | [[composite]] — weighted signal aggregation |
| [[Brier Score]] | [[validation_engine]] — probabilistic calibration |
| [[Conviction Multiplier]] | [[layer2_directional]] — crowding penalty |
| [[Hysteresis Tiers]] | [[layer1_gate]] — prevents regime flickering |
| [[Marcus Invalidation]] | [[layer1_gate]], [[layer2_directional]] — signal clash vetoes |
| [[COT Percentile]] | [[cot]] — positioning extremity |
| [[RVOL Rank]] | [[volatility]] — realized volatility percentile |

---

*This vault is append-only. When adding new files, update the relevant hub and create a note with connections.*
