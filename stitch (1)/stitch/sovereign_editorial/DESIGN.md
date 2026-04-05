# Design System Strategy: The Financial Editorial

## 1. Overview & Creative North Star

### The Creative North Star: "The Quant Archive"
This design system rejects the frantic, neon-soaked tropes of retail trading platforms. Instead, it adopts the persona of **The Quant Archive**—a high-end, authoritative financial research publication that balances the heritage of classical typography with the surgical precision of modern data science.

The aesthetic is built on the tension between "Warm Heritage" (the editorial research layer) and "Cold Intelligence" (the live data layer). We break the traditional UI template by using intentional asymmetry, generous negative space, and "Contrast Islands"—dark, immersive modules that house live data visualizations against a serene, parchment-like background.

---

## 2. Colors & Surface Architecture

Our palette is anchored by `Warm White (#F4F5F3)` to reduce eye strain and provide a premium "paper" feel, contrasted against `Primary Navy (#1B3A6B)` for authoritative structure.

### The "No-Line" Rule
**Explicit Instruction:** Traditional 1px solid borders are strictly prohibited for sectioning. We define boundaries through tonal shifts. A `surface-container-low` section sitting on a `background` provides all the separation necessary. Use negative space (following a strict 8px/16px/24px/48px scale) to define the relationship between objects.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers of fine paper:
- **Level 0 (Background):** `surface` (#F9FAF8) – The base "table."
- **Level 1 (Sections):** `surface-container-low` (#F3F4F2) – Large structural areas.
- **Level 2 (Cards):** `surface-container-lowest` (#FFFFFF) – The highest "lift" for light-mode content.
- **The Contrast Island:** `on-primary-fixed` (#001A40) – Specifically for live data cards. These are high-contrast "viewports" into the market, providing a dark-mode experience within a light-mode layout.

### Pair Identities (Semantic Data)
For financial currency pairs, use these tokens to provide instant cognitive recognition:
- **EUR/USD Blue:** `#2563A8`
- **USD/JPY Amber:** `#B86B2A`
- **USD/INR Deep Red:** `#A63030`

---

## 3. Typography: The Editorial Voice

We utilize a tri-font system to separate narrative from utility.

*   **Display & Headlines (Newsreader):** Use for "The Why." These Serif headings convey institutional authority. The high-contrast strokes of Newsreader suggest a curated, researched perspective.
*   **Body & UI (Work Sans):** Use for "The What." A clean, highly legible Sans-Serif that disappears into the background, allowing the user to focus on the content without distraction.
*   **Numerical Data (JetBrains Mono):** Use for "The Value." Numbers must be tabular and monospaced to ensure vertical alignment in data tables and rapid scanning of price action.

| Level | Token | Font | Size | Weight |
| :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-lg` | Newsreader | 3.5rem | Medium |
| **Headline** | `headline-md` | Newsreader | 1.75rem | Semi-Bold |
| **Body Text** | `body-md` | Work Sans | 0.875rem | Regular |
| **Data Point**| `label-md` | JetBrains Mono | 0.75rem | Medium |

---

## 4. Elevation & Depth

### Tonal Layering
Avoid shadows where possible. Instead, stack your surface tiers. 
*Example:* A data visualization should sit on a `surface-container-lowest` (#FFFFFF) card, which itself sits on a `surface-container` (#EDEEEC) section.

### Ambient Shadows & The "Ghost Border"
When a "floating" effect is required (e.g., a dropdown or modal):
- **Ambient Shadow:** Use the `on-surface` color at 6% opacity with a blur of 32px and Y-offset of 16px. It should feel like a soft glow, not a dark smudge.
- **The Ghost Border:** If high-density data requires containment, use `outline-variant` (#C4C6D0) at **15% opacity**. Never use 100% opaque lines.

### Corner Geometry
The "Quant Archive" aesthetic is precise. 
- **Standard Corners:** 0px (Sharp).
- **Interactive Elements:** Maximum 12px. 
- Avoid the "pill" shape entirely unless used for secondary Chips.

---

## 5. Components

### Buttons: The "Ghost Only" Mandate
To maintain an editorial feel, we avoid heavy, solid-fill buttons which can look "app-like."
- **Primary:** `outline` (#747780) Ghost Border (at 20% opacity) with `primary` text. Hover state introduces a `primary-container` (#1B3A6B) background at 5% opacity.
- **Secondary:** Text-only with a subtle underline (2px) using `surface-tint`.

### Data Cards (Contrast Islands)
- **Background:** `#0F1420` (Dark Navy).
- **Text:** `on-primary-fixed` or `primary-fixed` (#D7E2FF) for high legibility.
- **Graph Lines:** Use Pair Identity colors with a 2px stroke width. No fills under lines.

### Inputs & Fields
- **State:** No background fill. Only a bottom-border (2px) using `outline-variant`.
- **Focus:** Transition the bottom-border to `primary` (#002452).

### Additional Component: The Signal Pulse
Since the background features a Canvas-based signal pulse, UI elements that require attention should use a 2px "Pulse Dot" in the corner of a card rather than a traditional notification badge.

---

## 6. Do's and Don'ts

### Do:
- **Do** use asymmetric layouts. Align a headline to the left and body text to a narrow column on the right to mimic high-end magazine spreads.
- **Do** allow numerical data to breathe. Use `JetBrains Mono` with increased letter-spacing (0.05em).
- **Do** use background shifts to indicate "active" states in lists rather than checkboxes.

### Don't:
- **Don't use gradients.** This system relies on flat, sophisticated color blocks.
- **Don't use glassmorphism.** Blur effects feel too "tech-startup." This system is about institutional stability.
- **Don't use rounded corners above 12px.** Sharp edges are preferred to maintain a professional, architectural feel.
- **Don't use divider lines.** Use the spacing scale to separate content blocks. If it feels cluttered, increase the whitespace.