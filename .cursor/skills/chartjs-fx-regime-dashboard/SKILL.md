---
name: chartjs-fx-regime-dashboard
description: >-
  Builds single-file Chart.js HTML for FX Regime Lab morning brief or dashboard
  pages with enforced palette, Inter typography, KPI header (value, percentile,
  day-over-day arrow), mobile layout, and standard footer. Use when creating or
  editing Chart.js charts, standalone HTML cards in pages/, or brief-adjacent
  visualizations for this repository.
---

> **Deprecated for active repo work:** The shipped web UI and standalone dashboard HTML paths described elsewhere were removed. Use this skill only when the user explicitly asks for Chart.js HTML artifacts or when rebuilding dashboards.

# Chart.js — FX Regime Lab (dashboard / morning brief)

## When this applies

Any **new or edited** Chart.js chart meant for **FX Regime Lab** (e.g. `pages/`, standalone brief cards, dashboard HTML). Follow every rule below unless the user explicitly overrides.

## Hard constraints

| Rule | Detail |
|------|--------|
| **One file** | Single self-contained `.html`; no separate CSS/JS assets unless the user explicitly asks. |
| **External deps** | **Only**: Chart.js (UMD) from **cdnjs**, and **Inter** from **Google Fonts**. No other CDNs, npm, or bundlers. |
| **Viewport** | Include `<meta name="viewport" content="width=device-width, initial-scale=1">`. |

## Color system (use exactly)

| Role | Hex / value |
|------|-------------|
| Page background | `#0a0e1a` |
| Card / surface | `#111827` |
| EUR/USD series or accent | `#4da6ff` |
| USD/JPY series or accent | `#ff9944` |
| USD/INR series or accent | `#e74c3c` |
| Chart grid | `rgba(30, 41, 59, 0.90)` |
| Tick labels | `#6b7280` |
| Default body text | `#e5e7eb` or `#f3f4f6` (keep contrast on dark bg) |

**Font**: Load **Inter** from Google Fonts; set `font-family: 'Inter', system-ui, sans-serif` on `body` and pass the same in Chart.js `font.family` for scales and legends.

## Chart.js includes

Use cdnjs UMD build, Chart.js **4.x**, for example:

- `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js`

(Adjust patch version if needed; stay on 4.x and cdnjs only.)

## Required UI (above or beside the chart)

Every chart page must expose:

1. **Current value** — latest observation formatted clearly (e.g. large figure + unit or pair label).
2. **Percentile badge** — compact label (e.g. `72nd pct` or `Pct: 72`) with subtle pill styling using card/bg contrast.
3. **Direction vs yesterday** — arrow or symbol (↑ / ↓ / →) with color: green or red vs neutral for unchanged; compare **last point to previous trading day** (or document the series’ date rule if not daily).

Implement these as HTML elements in the card header, not only as chart annotations, so they stay readable on mobile.

## Mobile responsiveness

- Wrap chart in a responsive container (e.g. max-width ~100%, horizontal padding on small screens).
- Chart options: `responsive: true`, `maintainAspectRatio: false` with a **min-height** on the canvas wrapper (e.g. `min-height: 220px`–`320px` depending on density), **or** a reasonable fixed aspect-ratio box that still fits narrow viewports.
- Avoid horizontal overflow: `overflow-x: auto` only if unavoidable; prefer stacking header KPIs vertically on narrow widths (`flex-wrap` or media queries).

## Footer (required, exact string)

Every page must include this footer (allow wrapping in `<footer>`; same text):

```text
Source: FX Regime Lab Pipeline · fxregimelab.substack.com
```

Link the Substack URL if appropriate: `https://fxregimelab.substack.com` — keep the visible copy consistent with the string above.

## Minimal HTML skeleton

Use this pattern; replace placeholders and datasets with real values from the pipeline or user data.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title><!-- Chart title --></title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
  <style>
    :root {
      --bg: #0a0e1a;
      --card: #111827;
      --eurusd: #4da6ff;
      --usdjpy: #ff9944;
      --usdinr: #e74c3c;
      --grid: rgba(30, 41, 59, 0.9);
      --tick: #6b7280;
      --text: #e5e7eb;
      --up: #34d399;
      --down: #f87171;
      --muted: #9ca3af;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: Inter, system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 1rem;
    }
    .card {
      max-width: 960px;
      margin: 0 auto;
      background: var(--card);
      border-radius: 12px;
      padding: 1rem 1.25rem 1.25rem;
      border: 1px solid rgba(30, 41, 59, 0.8);
    }
    .kpi-row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.75rem 1rem;
      margin-bottom: 1rem;
    }
    .current { font-size: 1.5rem; font-weight: 700; }
    .badge {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.2rem 0.55rem;
      border-radius: 999px;
      background: rgba(77, 166, 255, 0.15);
      color: var(--eurusd);
      border: 1px solid rgba(77, 166, 255, 0.35);
    }
    .dod { font-size: 0.95rem; font-weight: 600; display: inline-flex; align-items: center; gap: 0.35rem; }
    .dod.up { color: var(--up); }
    .dod.down { color: var(--down); }
    .dod.flat { color: var(--muted); }
    .chart-wrap { position: relative; width: 100%; min-height: 280px; }
    footer {
      max-width: 960px;
      margin: 1.25rem auto 0;
      font-size: 0.8rem;
      color: var(--tick);
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="kpi-row">
      <span class="current" id="currentValue"><!-- e.g. 1.0842 --></span>
      <span class="badge" id="pctBadge"><!-- e.g. 72nd pct --></span>
      <span class="dod flat" id="dodArrow"><!-- e.g. → vs yesterday --></span>
    </div>
    <div class="chart-wrap"><canvas id="chart"></canvas></div>
  </div>
  <footer>Source: FX Regime Lab Pipeline · fxregimelab.substack.com</footer>
  <script>
    const tickFont = { family: 'Inter', size: 11 };
    const gridColor = 'rgba(30, 41, 59, 0.90)';
    const tickColor = '#6b7280';
    // TODO: set currentValue, pctBadge, dodArrow from data; init Chart with scales: { x: { grid: { color: gridColor }, ticks: { color: tickColor, font: tickFont } }, y: { ... } }
  </script>
</body>
</html>
```

## Checklist before finishing

- [ ] One HTML file; only cdnjs Chart.js + Google Fonts Inter
- [ ] Colors match the table; grid and ticks match spec
- [ ] Current value, percentile badge, and vs-yesterday direction present
- [ ] Layout works on narrow screens; chart resizes
- [ ] Footer line included exactly as specified
