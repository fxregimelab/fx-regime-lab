---
name: fx-regime-html-dashboards-briefs
description: >-
  Builds HTML dashboards and morning brief outputs for FX Regime Lab.
  Supabase-backed data, dark theme, regime/confidence/driver panels.
---

# FX Regime Lab — HTML dashboards and morning brief

## Scope

- Daily text brief generation
- HTML brief / dashboard pages
- Standalone chart HTML

## Data sourcing

1. **Dashboard-facing HTML**: load metrics via **Supabase** (REST or `@supabase/supabase-js`). Do NOT fetch `data/*.csv` as source of truth in browser context.
2. Prefer reads from Supabase with explicit column lists (no `select("*")`).
3. Follow `fx-regime-supabase-writes` skill for client env vars, upsert patterns.

## Color system (strict)

| Role | Hex |
|------|-----|
| Page background | `#0a0e1a` |
| Cards | `#111827` |
| EUR/USD accent | `#4da6ff` |
| USD/JPY accent | `#ff9944` |
| USD/INR accent | `#e74c3c` |

## Dashboard sections (per pair)

Each panel must show:
1. **Current regime** (label consistent with framework)
2. **Confidence** (numeric or high/med/low)
3. **Top signal driver** (single primary factor)

## Morning brief — text structure

```
DATE | MACRO CONTEXT (1 sentence)

REGIME CALLS
EUR/USD: [REGIME] | Confidence: [X%] | Change from yesterday: [Yes/No]
USD/JPY: [REGIME] | Confidence: [X%]
USD/INR: [REGIME] | Directional only

KEY SIGNAL CHANGES (only materially changed)
[Signal]: [Previous] → [Current] | Implication: [1 sentence]

CROSS-ASSET CONTEXT
[Oil / VIX / DXY: 1 sentence each, only if regime-relevant]

ACTIVE PAPER POSITIONS
[Pair | Direction | Entry | Current | P&L in R]

REGIME CALL ACCURACY (last 20 days)
EUR/USD: X% | USD/JPY: X% | USD/INR: X%

WATCH LIST (1–2 setups forming)
```
