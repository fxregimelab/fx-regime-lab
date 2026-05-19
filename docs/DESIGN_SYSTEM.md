# Design System

**Intent** for FX Regime Lab public surfaces. The live frontend is under `web/` and implements these principles in `globals.css` and the component tree.

## Philosophy

Bold, direct, enjoyable, practitioner-built. The reader should feel a single authored voice, not a template. The intellectual bar is high, but the tone stays concrete: numbers, dates, pairs, and calls on the record.

## Five-second read for a visitor

This person publishes **daily FX regime calls** and leaves the **validation trail** in the open. Seriousness shows through structure and consistency, not through claims.

## Typography

- **Inter:** UI copy, body text, navigation, labels.
- **Fraunces italic:** Regime **call labels only** on cards, not navigation headings.
- **JetBrains Mono:** Numerical data: percentiles, basis points, timestamps, composite scores.

## Color Tokens

### Target Palette

| Role | Example hex | Notes |
|------|-------------|--------|
| Public shell background | `#f5f5f0` or white `#ffffff` | Calm editorial |
| Terminal background | `#0a0a0a` / `#080808` | Dense monitoring |
| Accent | `#e8a045` | Highest conviction emphasis only |

**Greyscale discipline:** regime badges may use semantic colors for signal meaning (emerald/rose/amber, etc.); avoid neon "AI dashboard" palettes.

### Pair Accent Colors

| Pair | Hex | Usage |
|------|-----|-------|
| EUR/USD | `#4BA3E3` | Pair-specific badges, chart lines, desk cards |
| USD/JPY | `#F5923A` | Pair-specific badges, chart lines, desk cards |
| USD/INR | `#D94030` | Pair-specific badges, chart lines, desk cards |

### Current Implementation

The live CSS variables are defined in `web/src/app/globals.css`:

**Terminal (dark) tokens:**
- `--terminal-bg: #0c0a09`
- `--terminal-fg: #e7e5e4`
- `--terminal-fg-muted: #a8a29e`
- `--terminal-fg-dim: #8a8a8a`
- `--terminal-border: #292524`
- `--terminal-success: #22c55e`
- `--terminal-warning: #f59e0b`
- `--terminal-danger: #ef4444`
- `--terminal-info: #3b82f6`

**Shell (light) tokens:**
- `--shell-bg: #f5f5f0`
- `--shell-fg: #1c1917`
- `--shell-fg-muted: #57534e`
- `--shell-fg-dim: #a8a29e`
- `--shell-border: #d6d3d1`
- `--shell-success: #15803d`
- `--shell-warning: #b45309`
- `--shell-danger: #b91c1c`
- `--shell-info: #1d4ed8`

All surfaces use Tailwind CSS v4 with `@import "tailwindcss"` and custom utility classes mapped to these tokens.

## Two-surface rule

Light **shell** is the public face. Dark **terminal** is the engine room. The contrast is intentional.

## Copy rules

- Do not use Unicode em dashes in user-visible strings (`U+2014`). Use a hyphen or sentence break.
- Avoid "framework", "learning journey" tone. Write as a practitioner describing live work.
- Use numerals for numbers (`87th percentile`, `5%`).

## Anti-patterns (never ship)

- SaaS landing tropes: gradient hero, generic three-column feature grid with stock icons.
- "Built to learn" / coursework framing.
- Neon blue and purple "AI dashboard" palettes, heavy glassmorphism.
- Dense methodology wall at the top of the home page.

## Related docs

- [[FRONTEND_ARCHITECTURE]]
- [[TECH_STACK]]
- [[DATA_READS_SPEC]]
