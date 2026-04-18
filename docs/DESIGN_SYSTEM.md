# Design system

This document is the **intent** for FX Regime Lab public surfaces. It also notes **implementation gaps** in the current `web/` tree so agents do not confuse aspiration with code.

## Philosophy

Bold, direct, enjoyable, practitioner-built. The reader should feel a single authored voice, not a template. The intellectual bar is high, but the tone stays concrete: numbers, dates, pairs, and calls on the record.

## Five-second read for a visitor

This person publishes **daily FX regime calls** and leaves the **validation trail** in the open. Seriousness shows through structure and consistency, not through claims.

## Typography (intent vs code)

**Intent (non-negotiable target):**

- **Inter:** All UI copy, body text, navigation, labels.
- **Fraunces italic:** Regime **call labels only** (for example the word styling for `TRENDING_SHORT` on a card), not navigation headings.
- **JetBrains Mono:** All numerical data: percentiles, basis points, timestamps, composite scores.

**Reality in `web/` today:**

- Root layout registers Inter, Fraunces, and JetBrains as CSS variables on `html`.
- Many terminal components use `font-mono` for **entire** blocks (navigation strip, pair desk headings). That is wider than the JetBrains-only-for-numbers rule. Tighten gradually when touching those files.
- `web/components/ui/Badge.tsx` renders regime text with `font-mono` and Tailwind background classes, **not** Fraunces italic. Align Badge with the Fraunces regime label rule when redesigning.

## Color tokens (exact hex)

From `web/tailwind.config.ts` and `web/app/globals.css`:

| Token name | Hex | Role |
|------------|-----|------|
| `shell-bg` | `#f5f5f0` | Public shell background |
| `terminal-bg` | `#0a0a0a` | Terminal background |
| `terminal-surface` | `#1a1a1a` | Terminal panels |
| `accent` | `#e8a045` | Highest conviction emphasis only |

**Greyscale discipline:** regime badge colors in `web/lib/constants/regimes.ts` use Tailwind neutrals and semantic colors (`emerald`, `rose`, `violet`, `amber`, `red`) for regime classes. That is slightly broader than “greyscale only + amber accent”; treat amber `VOL_EXPANDING` and colored regime badges as **signal semantics**, not marketing gradients.

**Pair accent colors:** `web/lib/constants/pairs.ts` includes `pairColor` hex strings for charts and future UI. Those hex values are **data constants**, not ad hoc literals inside random components. Prefer consuming through `PAIRS` rather than new literals.

## Tailwind custom tokens

From `web/tailwind.config.ts` `theme.extend`:

- **Colors:** `shell-bg`, `terminal-bg`, `terminal-surface`, `accent` (each maps to the hex in the table above).
- **Font families:** `font-sans` → `var(--font-inter)`; `font-display` → `var(--font-fraunces)`; `font-mono` → `var(--font-jetbrains-mono)`.
- **Border radii:** `rounded-shell`, `rounded-card`, `rounded-pill` map to `0.75rem`, `1rem`, `9999px`.

## Two-surface rule

Light **shell** is the public face. Dark **terminal** is the engine room. The contrast is intentional: calm reading vs dense monitoring.

## Component anatomy (target)

- **RegimeCard:** Pair name (Inter, medium weight). Regime label (Fraunces italic at appropriate size). Confidence bar (greyscale track; accent only if you deliberately mark conviction peaks). Optional primary driver text (Inter, small).
- **Badge:** Regime label chip: Fraunces italic inside the chip, background from `REGIME_COLORS` mapping (today: mono font; fix when editing).
- **ConfidenceBar:** Greyscale track; fill width proportional to confidence; current code uses `accent` for the fill on all values (consider narrowing accent usage in a later pass).

## Copy rules

- Do not use Unicode em dashes in user-facing strings or docs (`U+2014`). Use a hyphen or sentence break.
- Avoid “framework”, “learning journey”, “we built this to practice” tone. Write as a practitioner describing live work.
- Use numerals for numbers (`87th percentile`, `5%`).

## Anti-patterns (never ship)

- SaaS landing tropes: gradient hero, generic three-column feature grid with stock icons.
- “Built to learn” / coursework framing.
- Neon blue and purple “AI dashboard” palettes, heavy glassmorphism.
- Dense methodology wall at the top of the home page.

## Related docs

- [[FRONTEND_ARCHITECTURE]]
- [[TECH_STACK]]
