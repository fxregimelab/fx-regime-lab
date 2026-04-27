# Design system

**Intent** for FX Regime Lab public surfaces when a new frontend is built. There is **no** `web/` tree in this repo anymore; **`claude-design/`** carries layout and styling experiments. Pair accents for rebuilds: EUR/USD `#4BA3E3`, USD/JPY `#F5923A`, USD/INR `#D94030` (see [[DATA_READS_SPEC]] and `AGENTS.md`).

## Philosophy

Bold, direct, enjoyable, practitioner-built. The reader should feel a single authored voice, not a template. The intellectual bar is high, but the tone stays concrete: numbers, dates, pairs, and calls on the record.

## Five-second read for a visitor

This person publishes **daily FX regime calls** and leaves the **validation trail** in the open. Seriousness shows through structure and consistency, not through claims.

## Typography (target)

- **Inter:** UI copy, body text, navigation, labels.
- **Fraunces italic:** Regime **call labels only** on cards, not navigation headings.
- **JetBrains Mono:** Numerical data: percentiles, basis points, timestamps, composite scores.

## Color tokens (target)

| Role | Example hex | Notes |
|------|-------------|--------|
| Public shell background | `#f5f5f0` or white `#ffffff` | Calm editorial |
| Terminal background | `#0a0a0a` / `#080808` | Dense monitoring |
| Accent | `#e8a045` | Highest conviction emphasis only |

**Greyscale discipline:** regime badges may use semantic colors for signal meaning (emerald/rose/amber, etc.); avoid neon “AI dashboard” palettes.

## Two-surface rule

Light **shell** is the public face. Dark **terminal** is the engine room. The contrast is intentional.

## Copy rules

- Do not use Unicode em dashes in user-visible strings (`U+2014`). Use a hyphen or sentence break.
- Avoid “framework”, “learning journey” tone. Write as a practitioner describing live work.
- Use numerals for numbers (`87th percentile`, `5%`).

## Anti-patterns (never ship)

- SaaS landing tropes: gradient hero, generic three-column feature grid with stock icons.
- “Built to learn” / coursework framing.
- Neon blue and purple “AI dashboard” palettes, heavy glassmorphism.
- Dense methodology wall at the top of the home page.

## Related docs

- [[FRONTEND_ARCHITECTURE]]
- [[TECH_STACK]]
- [[DATA_READS_SPEC]]
