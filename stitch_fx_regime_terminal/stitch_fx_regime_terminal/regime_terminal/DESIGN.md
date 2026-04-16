# Design System Document: The Quantitative Authority

## 1. Overview & Creative North Star
**Creative North Star: "The Brutalist Architect"**
This design system rejects the "fluff" of consumer software. It is a high-density, data-first framework engineered for speed, precision, and cognitive efficiency. Inspired by the legacy of Bloomberg and the modern clarity of Koyfin, the aesthetic is "Institutional Minimalism."

We move beyond the template look by embracing **Absolute Flatness**. In a world of glassmorphism and soft shadows, this system finds its premium feel through mathematical precision, razor-sharp edges (0px border radius), and intentional information density. It is not "crowded"; it is "efficient." The design communicates authority through a total lack of decoration, forcing the user to focus entirely on the signal within the noise.

---

## 2. Colors
The palette is rooted in deep obsidian tones, providing a low-strain environment for 12-hour trading sessions. 

### Core Palette
- **Background (`surface-dim`):** `#0a0a0f` — The primary canvas.
- **Card Surface (`surface-container`):** `#0f0f18` — For primary data modules.
- **Border/Stroke (`outline-variant`):** `#1c1c2e` — The only permitted separator.

### Signal Palette (The Semantic Layer)
- **Primary Signal:** `#3b82f6` (Blue) — System-level actions and focus.
- **Warning/Neutral:** `#f59e0b` (Amber) — Mid-range volatility or pending states.
- **Alert/Bearish:** `#ef4444` (Red) — Critical failure or downward price action.
- **Bullish:** `#22c55e` (Green) — Upward price action and healthy regimes.
- **Neutral:** `#8c909f` (Grey) — Stable or inactive data points.

### The "Precision Stroke" Rule
Prohibit the use of shadows or glow effects. Boundaries are defined by the 1px `outline-variant` (`#1c1c2e`). To maintain institutional quality, use "Double-Stroking" for active states: a 1px `primary` border inside a 1px `outline-variant` container to create a "nested" focus effect without increasing the component's physical footprint.

---

## 3. Typography
**Typeface:** Inter (Variable)
We utilize Inter for its high x-height and exceptional legibility at small sizes. In a high-density terminal, typography *is* the UI.

- **Display (3.5rem - 2.25rem):** Reserved for high-level regime titles or macro volatility indices.
- **Headline (2rem - 1.5rem):** Used for major panel headers (e.g., "USD/JPY Order Flow").
- **Title (1.375rem - 1rem):** Section headers within data cards.
- **Body (1rem - 0.75rem):** The workhorse for data tables. `body-sm` (0.75rem) is the default for terminal grids.
- **Label (0.75rem - 0.6875rem):** All-caps with +0.05em tracking for table headers and ticker symbols to ensure maximum distinction from data values.

**Hierarchy Strategy:** 
Weight is our primary tool. Use `Inter Bold` (700) for data values and `Inter Regular` (400) for labels. This creates a "Value-First" reading pattern.

---

## 4. Elevation & Depth
In this system, "Elevation" is an oxymoron. We do not use Z-axis depth; we use **Tonal Layering**.

- **Level 0 (Base):** `#0a0a0f` (Background).
- **Level 1 (Modules):** `#0f0f18` (Card Surface).
- **Level 2 (In-Card Elements):** `#131318` (Surface Container Low) — Use this for nested table headers or search input backgrounds within a card.
- **The "No-Blur" Mandate:** Floating elements (Modals, Context Menus) must not use backdrop-blur. They should use a solid `#1b1b20` background with a 1px `#8c909f` (Outline) border to "pop" against the darker base layers.

---

## 5. Components

### Navigation & Ticker
- **Global Nav (52px):** Solid `#0a0a0f`. Top-aligned. Icons must be 20px, stroke-based, and use `#8c909f`.
- **Ticker Strip (36px):** Positioned immediately below the Nav. Continuous scrolling data. Font: `label-sm` (0.6875rem), Monospaced numerals recommended.

### Buttons
- **Primary:** Background `#adc6ff`, Text `#002e6a`. 0px radius. No gradient.
- **Secondary/Ghost:** Border 1px `#1c1c2e`, Text `#e4e1e9`. Background is transparent.
- **State Changes:** Hover states must be a simple 10% opacity overlay. No "lifting" or glowing.

### Data Tables (The Core Component)
- **Density:** Row height fixed at 28px for high-density or 36px for standard.
- **Dividers:** Forbid horizontal lines between every row. Use `surface-container-low` for zebra-striping (every other row) to guide the eye without adding visual clutter.
- **Alignment:** Numbers are always right-aligned (Tabular-nums) to allow for easy decimal comparison. Text is left-aligned.

### Input Fields
- **Default:** Background `#0e0e13`, 1px border `#1c1c2e`.
- **Focus:** 1px border `#3b82f6`.
- **Validation:** Error states use a 1px `#ef4444` border and `label-sm` text below the field.

---

## 6. Do's and Don'ts

### Do:
- **Use Tabular Numerals:** Ensure `font-variant-numeric: tabular-nums` is active for all financial data to prevent "jumping" text.
- **Maintain 0px Radius:** Every element—from buttons to cards to dropdowns—must have a hard 90-degree corner.
- **Vertical Alignment:** Align text to the baseline of adjacent data to maintain a rigid horizontal rhythm.

### Don't:
- **No Gradients:** Never use a color transition. Color must be flat and functional.
- **No Soft Shadows:** If you need to separate a layer, use a high-contrast border (`#8c909f`) or a tonal shift.
- **No "Airy" Whitespace:** While margins are necessary, excessive whitespace is viewed as "wasted pixels" in a terminal context. Prioritize data visibility over "breathing room."
- **No Rounded Icons:** Use sharp-edged, geometric iconography to match the Inter typeface and 0px component corners.