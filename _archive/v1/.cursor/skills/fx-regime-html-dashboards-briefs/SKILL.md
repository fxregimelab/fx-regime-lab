---
name: fx-regime-html-dashboards-briefs
description: >-
  Builds and updates HTML dashboards, morning brief HTML, and standalone chart
  HTML for FX Regime Lab. Enforces Supabase-sourced data on dashboard surfaces,
  dark-theme pair colors, regime/confidence/driver panels, and PLAN.md Phase 3.2
  text brief structure. Use when changing create_html_brief.py,
  Cloudflare Pages / fxregimelab.com dashboard HTML, charts/*.html generators,
  global workspace layout, or morning brief section order and copy.
---

# FX Regime Lab — HTML dashboards and morning brief

## Scope

- `create_html_brief.py`; **fxregimelab.com** (Cloudflare Pages) dashboard and static pages
- Standalone / embedded chart HTML under `charts/`, workspace shells
- Plotly builders: `create_charts_plotly.py`, `charts/base.py` (layout and styling only—data sourcing follows rules below)

## Data sourcing

1. **Dashboard-facing HTML and client-side JS** (pages that render live or “product” UI): load metrics via **Supabase** (REST/`@supabase/supabase-js` or equivalent). Do **not** fetch or parse `data/*.csv`, file URLs, or static CSV dumps as the source of truth in those files.
2. **`create_html_brief.py`** (and site dashboard pages): When adding or changing regime, signal, or accuracy blocks, **prefer reads from Supabase** (explicit column lists, no `select("*")`); follow `.cursor/skills/fx-regime-supabase-writes/SKILL.md`. Do not add new dependencies without project approval.
3. **Legacy exception**: Static Plotly generation that still uses merged CSV via `charts/base._load_and_filter` may remain until migrated; **when you touch those code paths for dashboard or brief output**, move toward Supabase-backed loads in line with PLAN Phase 3.1.

## Color system (strict)

Match `charts/base.py` and `config.py` pair styling. Do not invent new pair accent colors.

**fxregimelab.com (Cloudflare Pages):** use **PLAN.md Phase 0A** tokens — Bloomberg-style (card `#0d1117`, borders `#1e293b` / `#161e2e`, **JetBrains Mono** for numeric values). Plotly brief may keep `#111827` cards but stay visually consistent where both appear.

| Role | Hex |
|------|-----|
| Page / iframe background | `#0a0e1a` |
| Cards, hover labels, chrome | `#111827` |
| Plot area (secondary) | `#0d1225` |
| EUR/USD accent | `#4da6ff` |
| USD/JPY accent | `#ff9944` |
| USD/INR accent | `#e74c3c` |

Plotly: `paper_bgcolor='#0a0e1a'`, `hoverlabel.bgcolor='#111827'`, axes/grid per `_style_axes` in `charts/base.py`. HTML/CSS brief cards: same pair colors for borders and tickers (see `scripts/dev/check_phase1.py` / `check_phase23.py` expectations).

## Dashboard sections (every major pair / regime panel)

Each dashboard section that summarizes a pair or regime must surface:

1. **Current regime** (label consistent with rest of product)
2. **Confidence** (numeric or high/med/low—match existing brief semantics)
3. **Top signal driver** (single primary explanatory signal or factor, not a dump)

If data is missing, show an explicit “unavailable” state; do not omit the three-slot layout.

## Morning brief — text structure (PLAN.md Phase 3.2)

The **text** brief (`morning_brief.py` output) must follow this structure **exactly** (section order and headings as below). Fill only allowed placeholders; omit optional blocks only when the plan says “only if” / “only materially changed.”

```
DATE | MACRO CONTEXT (1 sentence)

REGIME CALLS
EUR/USD: [REGIME] | Confidence: [X%] | Change from yesterday: [Yes/No]
USD/JPY: [REGIME] | Confidence: [X%]
USD/INR: [REGIME] | Directional only

KEY SIGNAL CHANGES (only materially changed signals)
[Signal]: [Previous] → [Current] | Implication: [1 sentence]

CROSS-ASSET CONTEXT
[Oil / VIX / DXY: 1 sentence each, only if regime-relevant]

ACTIVE PAPER POSITIONS
[Pair | Direction | Entry | Current | P&L in R]

REGIME CALL ACCURACY (last 20 days)
EUR/USD: X% | USD/JPY: X% | USD/INR: X%

WATCH LIST (1–2 setups forming, not yet triggered)
```

When editing **HTML** brief layout (`create_html_brief.py`), keep the **narrative order and grouping** aligned with this structure even if the visual template uses cards or iframes.

## Workflow checklist

- [ ] Confirm no duplicate of pipeline steps; order stays `pipeline.py → … → create_html_brief.py → deploy.py` (extend only).
- [ ] Dashboard HTML: Supabase for live data; no CSV file reads in browser context.
- [ ] Colors and pair accents match the table above.
- [ ] Each new or revised dashboard section includes regime, confidence, top driver.
- [ ] Text brief matches Phase 3.2; HTML brief sections map to the same story order.
- [ ] Run relevant `scripts/dev/check_phase*.py` or `check_brand_v2.py` after visible HTML/CSS changes when applicable.

## Related project docs

- Full plan: `contaxt files/PLAN.md` (Phase 3.1–3.2)
- Supabase patterns: `.cursor/skills/fx-regime-supabase-writes/SKILL.md`
- Repo map: `AGENTS.md`
