---
name: chartjs-fx-regime-dashboard
description: >-
  Builds Chart.js visualizations for FX Regime Lab internal tooling or legacy
  dashboard pages. Use only when explicitly asked for Chart.js artifacts.
---

# Chart.js — FX Regime Lab (internal tooling only)

## When this applies

Any **new or edited** Chart.js chart for FX Regime Lab internal tooling. The primary frontend is Next.js + Recharts in `web/` — use this skill only when the user explicitly asks for Chart.js HTML artifacts.

## Hard constraints

| Rule | Detail |
|------|--------|
| **One file** | Single self-contained `.html`; no separate CSS/JS assets unless explicitly asked. |
| **External deps** | **Only**: Chart.js (UMD) from **cdnjs**, and **Inter** from **Google Fonts**. |
| **Viewport** | Include `<meta name="viewport" content="width=device-width, initial-scale=1">`. |

## Color system (use exactly)

| Role | Hex / value |
|------|-------------|
| Page background | `#0a0e1a` |
| Card / surface | `#111827` |
| EUR/USD | `#4da6ff` |
| USD/JPY | `#ff9944` |
| USD/INR | `#e74c3c` |
| Chart grid | `rgba(30, 41, 59, 0.90)` |
| Tick labels | `#6b7280` |
| Default body text | `#e5e7eb` |

**Font**: Inter from Google Fonts; pass same in Chart.js `font.family`.

## Chart.js includes

Use cdnjs UMD build, Chart.js **4.x**:
```
https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js
```

## Required UI

Every chart page must expose:
1. **Current value** — latest observation formatted clearly.
2. **Percentile badge** — compact label (e.g. `72nd pct`).
3. **Direction vs yesterday** — arrow (↑/↓/→) with color.

## Mobile responsiveness

- `responsive: true`, `maintainAspectRatio: false` with `min-height` on wrapper.
- Avoid horizontal overflow.

## Footer (required)

```
Source: FX Regime Lab Pipeline · fxregimelab.substack.com
```
