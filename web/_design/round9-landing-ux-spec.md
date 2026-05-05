# FX Regime Lab — Homepage UX Specification
## Round 9: Landing Information Architecture
**Date:** 2026-05-05  
**Author:** Lead UX Architect  
**Status:** Design Specification — Ready for Implementation  
**Scope:** `fx-regime-lab/web/src/app/page.tsx` (homepage)

---

## 0. Design Thesis

> **"The homepage is a research desk, not a product page. The visitor should understand what we do, what we said today, and why they can trust us — in that order."**

This document re-architects the homepage information hierarchy around **three trust beats**:  
1. *Identity* (Hero — who we are)  
2. *Proof of life* (Validation Ticker — we are actively validating)  
3. *Product* (Live Snapshot — today's calls)  
4. *Philosophy* (Manifesto — why this matters)  
5. *Method* (Signal Architecture — how it works)  
6. *Evidence* (Validation Trust — the numbers)  
7. *Provenance* (About — who is behind this)

---

## 1. Section Map

| # | Section | Purpose | Data Requirements | Source |
|---|---------|---------|-------------------|--------|
| 1 | **Hero** | Establish identity, tone, and primary CTA. Asymmetric layout creates tension and editorial confidence. | None (static) | — |
| 2 | **Validation Ticker** | Prove the system is alive and accountable. A scrolling ledger of recent outcomes creates immediate trust through sheer visibility. | `ValidationRow[]` (last 20 validated calls) | `getValidationLog` |
| 3 | **Live Snapshot** | Show today's regime calls. The product surface. Three pair cards with spot, regime, confidence. | `RegimeCallMap`, `SignalMap` | `getLatestRegimeCalls`, `getLatestSignals` |
| 4 | **Manifesto** | Editorial pause. A large serif statement that explains the ethical commitment — no black boxes, no ex-post edits. | None (static) | — |
| 5 | **Signal Architecture** | Explain the engine. Four signal families in a 2×2 grid. Evidence that this is quant work, not opinion. | None (static, hardcoded weights) | — |
| 6 | **Validation Trust** | Aggregate credibility. Monumental stat cards that feel like museum plinths. | `accuracy`, `totalCalls` | `getValidationLog` + `regime_calls.count` |
| 7 | **About Snippet** | Human provenance. Who runs this, and why. | None (static) | — |

**Section order rationale:**  
The old homepage ended with stats. Stats before the product felt like marketing. The new order leads with identity, proves life with the ticker, shows the product, then builds trust through philosophy → method → evidence → human. The Manifesto acts as a **breath** between data-dense sections.

---

## 2. Hero Section Spec

### 2.1 Layout Grid

```
┌─────────────────────────────────────────────────────────────────────┐
│  max-w-[1152px] mx-auto px-6                                        │
│                                                                     │
│  ┌─────────────────────────────┐  ┌────────────────────────────┐   │
│  │                             │  │                            │   │
│  │  ● LIVE · G10 FX · DAILY   │  │      2026-05-05            │   │
│  │                             │  │      05:47 UTC             │   │
│  │  Daily regime              │  │                            │   │
│  │  calls. On the             │  │      ┃                     │   │
│  │  record.                   │  │      ┃ MARKET OPEN         │   │
│  │                             │  │      ┃ LONDON / NEW YORK   │   │
│  │  G10 FX regime classi-     │  │      ┃                    │   │
│  │  fication across EUR/USD,  │  │      ┃                    │   │
│  │  USD/JPY, and USD/INR...   │  │                            │   │
│  │                             │  │                            │   │
│  │  [Read today's brief]      │  │                            │   │
│  │  [Open terminal →]         │  │                            │   │
│  │                             │  │                            │   │
│  └─────────────────────────────┘  └────────────────────────────┘   │
│                                                                     │
│                         Scroll                                      │
│                           │                                         │
└─────────────────────────────────────────────────────────────────────┘
```

**Grid:** `grid grid-cols-1 lg:grid-cols-[5fr_3fr] gap-12 lg:gap-16 items-start`

**Container:** `max-w-[1152px] mx-auto px-6 min-h-[92vh] flex flex-col justify-center relative`

**Left column (5fr):**
- Content anchored top-left, no internal centering
- `max-w-[640px]` on the text block itself for measure control
- All text left-aligned

**Right column (3fr):**
- Hidden below `lg` breakpoint (`hidden lg:flex`)
- Content: vertical status strip aligned to the right edge
- Contains: UTC date/time, market status, thin vertical rule
- The vertical rule is `1px` wide, `h-full`, `bg-[var(--color-border)]`, with a small green dot at top

### 2.2 Element Specs

| Element | Classes | Notes |
|---------|---------|-------|
| Live dot | `w-2 h-2 rounded-full bg-[var(--color-up)] animate-gentle-pulse` | No radius change (2px is max allowed) |
| Hero label | `font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase` | "Live · G10 FX · Daily Calls" |
| H1 | `font-sans font-semibold text-[clamp(40px,6vw,72px)] text-[var(--color-text)] leading-[1.08] tracking-tight` | Three lines max. Soft-break after "regime" and "the" |
| Body | `font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[440px]` | 15px is the canonical body size per Round 1 |
| Primary CTA | `px-6 py-2.5 bg-[var(--color-text)] text-[var(--color-void)] font-sans text-[13px] tracking-wide transition-all duration-300 hover:bg-[var(--color-accent-hover)]` | Filled button, sharp corners |
| Secondary CTA | `font-sans text-[13px] text-[var(--color-text-muted)] underline decoration-[var(--color-border)] underline-offset-4 transition-colors duration-300 hover:text-[var(--color-text)]` | Text link with underline |
| Right column time | `font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase text-right` | Current UTC timestamp |
| Right column status | `font-mono text-[9px] tracking-[0.12em] text-[var(--color-up)] uppercase text-right` | "Market Open" or "Market Closed" |
| Vertical rule | `w-px h-[180px] bg-[var(--color-border)] ml-auto relative` | Decorative separator. On load, animates as line-grow from top |
| Scroll hint | `absolute bottom-8 left-1/2 -translate-x-1/2` | Same as current. Label + 1px gradient line |

### 2.3 Animation Sequence on Load

All animations use `animation-fill-mode: forwards` and `opacity: 0` in initial state (or rely on keyframe from-to).

| # | Element | Animation | Duration | Delay | Easing |
|---|---------|-----------|----------|-------|--------|
| 1 | Live dot | `fade-in` + `gentle-pulse` | 0.4s | 0ms | `ease-out` |
| 2 | Hero label | `fade-in` | 0.5s | 80ms | `var(--ease-institutional)` |
| 3 | H1 | `slide-in-left` | 0.7s | 180ms | `var(--ease-institutional)` |
| 4 | Body paragraph | `fade-up` | 0.6s | 320ms | `var(--ease-institutional)` |
| 5 | CTA group | `fade-up` | 0.5s | 460ms | `var(--ease-institutional)` |
| 6 | Right column vertical rule | `line-grow` (scaleX → scaleY variant) | 0.8s | 600ms | `var(--ease-institutional)` |
| 7 | Right column text | `fade-in` | 0.5s | 700ms | `ease-out` |
| 8 | Scroll hint | `fade-in` | 0.5s | 900ms | `ease-out` |

**Implementation note:** Use inline `animation-delay` via Tailwind delay utilities (`delay-100`, `delay-200`, etc.) or inline styles. The existing `.delay-*` classes in `globals.css` are already defined. The H1 should use `animate-slide-in-left` (already defined in globals.css) rather than `fade-up` to reinforce the left-anchored asymmetry.

### 2.4 Responsive Behavior

| Breakpoint | Behavior |
|-----------|----------|
| `≥ 1024px` (`lg`) | Full 5fr/3fr asymmetric grid. Right column visible. |
| `768–1023px` (`md`) | Single column. Right column hidden. H1 scales to `clamp(36px,7vw,56px)`. Max-width of text block stays at `640px`. |
| `< 768px` (`sm`) | Single column. H1: `clamp(32px,8vw,48px)`. Body: `text-[14px]`. CTAs stack vertically, full width. Scroll hint hidden. Vertical padding increases to compensate for lost right column: `pt-24 pb-16`. |

**Mobile CTA stack:**
```
flex flex-col gap-3
```
Primary CTA: `w-full text-center`  
Secondary CTA: `w-full text-center` (underline removed on mobile for tap-target clarity; keep color transition)

---

## 3. Validation Ticker

### 3.1 Purpose
A full-width, horizontally scrolling strip that displays the last 20 validated calls. It answers the visitor's subconscious question: *"Is this thing actually running, or is it a static demo?"* before they even scroll.

### 3.2 Layout & Container

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  border-t border-b border-[var(--color-border)] bg-[var(--color-surface)]  │
│  overflow-hidden h-[48px] flex items-center                                 │
│                                                                             │
│  ←  2026-05-04  EUR/USD  MODERATE USD STRENGTH  ✓ CORRECT  +0.18%  │  ...  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Container classes:** `w-full border-t border-b border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden h-[48px] flex items-center`

**Position in DOM:** Immediately after `<Hero />`, before `<LiveSnapshot />`.

### 3.3 Item Format

Each ticker item is a flex row of atomic spans, separated by a diamond divider:

```
DATE        PAIR       REGIME                  OUTCOME       RETURN
2026-05-04  EUR/USD    MODERATE USD STRENGTH   ✓ CORRECT     +0.18%
```

**Item wrapper classes:** `inline-flex items-center gap-4 px-6 shrink-0`

**Divider between items:** `<span className="text-[var(--color-border)] font-mono text-[11px]">◆</span>`

**Field specs:**

| Field | Classes | Color Logic |
|-------|---------|-------------|
| Date | `font-mono text-[11px] tabular-nums text-[var(--color-text-muted)]` | Always muted |
| Pair | `font-mono text-[11px] font-medium tracking-wide uppercase` | Pair color (`--color-pair-eurusd`, etc.) |
| Regime | `font-mono text-[11px] text-[var(--color-text-secondary)] tracking-wide` | Always secondary |
| Outcome | `font-mono text-[11px] font-medium tracking-wide uppercase` | `var(--color-up)` for correct, `var(--color-down)` for incorrect |
| Return | `font-mono text-[11px] font-medium tabular-nums` | `var(--color-up)` if ≥ 0, `var(--color-down)` if < 0. Always show sign. |

### 3.4 Scroll Behavior

**Technique:** CSS `translateX` animation (marquee). Content duplicated once for seamless loop.

**Wrapper:**
```
<div className="flex animate-pulse-marquee hover:[animation-play-state:paused]">
  {/* original items */}
  {/* duplicated items */}
</div>
```

Use the existing `.animate-pulse-marquee` keyframe from `globals.css`, but add a **faster variant** for this ticker:

```css
@keyframes ticker-marquee {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}
.animate-ticker-marquee {
  animation: ticker-marquee 40s linear infinite;
  will-change: transform;
}
.animate-ticker-marquee:hover {
  animation-play-state: paused;
}
```

| Property | Value |
|----------|-------|
| Speed | `40s` per full loop (slower than the macro pulse ticker — this is text, not indicators) |
| Direction | Right to left (`translateX(0) → translateX(-50%)`) |
| Pause on hover | Yes (`animation-play-state: paused`) |
| Easing | `linear` (constant speed, no acceleration) |

### 3.5 Data Source

```typescript
interface ValidationRow {
  date: string;        // "2026-05-04"
  pair: string;        // "EUR/USD"
  regime: string;      // "MODERATE USD STRENGTH"
  outcome: "correct" | "incorrect";
  return_pct: number;  // +0.18
}
```

**Server Component fetch:**
```typescript
const validation = await getValidationLog(supabase);
const tickerRows = validation
  .filter((r) => r.outcome !== null && r.outcome !== "pending")
  .slice(0, 20);
```

**Empty state:** If fewer than 5 validated calls exist, hide the ticker entirely. Do not show a "no data" message — the strip is proof of life, and absence of life should not draw attention.

### 3.6 Accessibility

- `prefers-reduced-motion: reduce` → animation duration becomes `0.01ms` (handled globally in `globals.css`). The strip will show the first ~3 items statically, overflow hidden.
- Ensure text contrast meets WCAG AA against `var(--color-surface)`.

---

## 4. Manifesto Section

### 4.1 Purpose
An editorial pause between the product (Live Snapshot) and the method (Signal Architecture). The Manifesto establishes the ethical framework of the project — immutability, pre-market publication, no ex-post edits. It is the only place on the homepage where we use the serif voice.

### 4.2 Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  bg-[var(--color-elevated)] py-32                                           │
│                                                                             │
│                    max-w-[720px] mx-auto px-6                               │
│                                                                             │
│       "Every call is published before the market opens.                     │
│        Every outcome is measured the next trading day.                      │
│        No edits. No excuses. The record is the product."                    │
│                                                                             │
│                              — FX Regime Lab · Since 2026                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Container:** `bg-[var(--color-elevated)] py-32` (desktop), `py-20` (mobile)

**Inner wrapper:** `max-w-[720px] mx-auto px-6`

### 4.3 Typography

| Element | Font | Size | Weight | Line Height | Color |
|---------|------|------|--------|-------------|-------|
| Quote | `font-serif` | `clamp(24px, 3.5vw, 42px)` | `300` (light) | `1.35` | `var(--color-text-secondary)` |
| Attribution | `font-mono` | `11px` | `400` | `1.6` | `var(--color-text-muted)` |

**Quote classes:** `font-serif font-light text-[clamp(24px,3.5vw,42px)] text-[var(--color-text-secondary)] leading-[1.35] italic tracking-normal`

**Attribution classes:** `mt-8 font-mono text-[11px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase`

**Opening mark:** A large decorative `"` in `font-serif`, `text-[64px]`, `text-[var(--color-border)]`, `leading-none`, `float-left mr-4 -mt-4`. This is the one allowed ornamental element on the page.

### 4.4 Scroll Animation

The quote text uses a **word-by-word fade-in** on scroll reveal. Not character-by-character (too theatrical) — word-by-word creates a "reading pace" without feeling like a typewriter.

**Technique:** Split text into `<span>` words. Each word starts at `opacity: 0.2` and transitions to `opacity: 1` as the user scrolls, or use a simple staggered fade-up on reveal.

For simplicity and performance (Server Component + minimal JS), use the existing `.reveal` class pattern:

```
.reveal { opacity: 0; transform: translateY(20px); ... }
.reveal.revealed { opacity: 1; transform: translateY(0); }
```

Stagger the quote lines:  
- Line 1: `transition-delay: 0ms`  
- Line 2: `transition-delay: 100ms`  
- Line 3: `transition-delay: 200ms`  
- Attribution: `transition-delay: 400ms`

**Reduced motion:** All lines appear simultaneously at full opacity.

---

## 5. Live Snapshot Refinement

The existing three-card grid is functionally correct but visually flat. These changes elevate it from "dashboard card" to "instrument panel."

### 5.1 Premium Treatments (Suggestions)

1. **Pair-colored top border**
   - Each card gets a `1px` top border in its pair color.
   - Classes: `border-t border-[var(--color-pair-eurusd)]` (etc.)
   - This is the only color accent on the card surface — everything else remains monochrome.

2. **Increased internal padding**
   - From `p-6` to `p-8`.
   - More negative space signals confidence and reduces density fatigue.

3. **Timestamp micro-line**
   - Below the pair label, add: `font-mono text-[9px] text-[var(--color-text-dim)] tracking-wide`
   - Content: `As of 2026-05-05 09:14 UTC`
   - This answers "how fresh is this?" immediately.

4. **Confidence bar refinement**
   - Track: `bg-[var(--color-border)]`, height `3px` (was `2px`)
   - Fill: `bg-[var(--color-accent)]` (warm silver, not green — confidence is not "good", it is magnitude)
   - Animation on reveal: `width` animates from `0%` to final over `0.8s` `var(--ease-institutional)`, staggered `150ms` per card

5. **Spot price in pair color (subtle)**
   - `text-[var(--color-pair-eurusd)]` at `80%` opacity.
   - Use `opacity-80` utility or `color-mix` in CSS.
   - This creates instant visual identification without adding UI chrome.

6. **Hover state: restrained lift + border glow**
   - `transition: transform 0.3s var(--ease-institutional), border-color 0.3s var(--ease-institutional)`
   - Hover: `transform: translateY(-1px)` (was `-2px`; more subtle), `border-color: var(--color-accent)` at `20%` opacity
   - No shadow. Never shadow.

7. **"Next validation" countdown (optional P1)**
   - Below the confidence bar, a single line: `font-mono text-[9px] text-[var(--color-text-dim)]`
   - Content: `Validates in 4h 23m`
   - Computed from market close time (14:30 UTC for FX) minus current UTC.

### 5.2 Grid Spec (unchanged)

`grid grid-cols-1 md:grid-cols-3 gap-4`

Card container: `border border-[var(--color-border)] bg-[var(--color-surface)]`

---

## 6. Validation Trust Refinement

The current stats strip is a `grid-cols-4 gap-px bg-[var(--color-border)]` with `p-6` cells. It feels like a table. We want it to feel like **monumental architecture** — the numbers are the content, not decorations inside boxes.

### 6.1 Monumental Treatments

1. **Enlarged number typography**
   - From `clamp(24px,3vw,32px)` to `clamp(36px,5vw,56px)`
   - Weight: `500` (medium)
   - Tracking: `tighter` (slightly more compressed for impact)
   - Color: `var(--color-text)` (full brightness — these are the heroes of this section)

2. **Vertical divider lines instead of grid gaps**
   - Remove the `gap-px` + `bg-[var(--color-border)]` trick.
   - Use `border-l border-[var(--color-border)]` on each cell except the first.
   - This creates classical columnar architecture — think bank facade, not spreadsheet.

3. **Increased cell padding**
   - `py-12 px-8` (desktop)
   - `py-8 px-6` (mobile)
   - The vertical space gives the numbers room to "land."

4. **Background elevation**
   - Section background: `bg-[var(--color-elevated)]`
   - Cell backgrounds: transparent (no `bg-[var(--color-surface)]` on individual cells)
   - The numbers float directly on the elevated surface.

5. **Label refinement**
   - Current: `font-mono text-[9px] tracking-[0.12em]`
   - New: `font-mono text-[9px] tracking-[0.2em] uppercase mt-4`
   - Increased tracking creates more air between letters, making labels feel like captions in a museum.

6. **Mini trend indicator (optional P1)**
   - Next to the "Accuracy" number, a small `↑` or `↓` arrow in `var(--color-up)` or `var(--color-down)`.
   - Compares current 7D accuracy to previous 7D window.
   - `font-mono text-[13px] ml-2 align-middle`

7. **Full-bleed top border**
   - A single `1px` line in `var(--color-border)` spans the full viewport width above the section.
   - Creates a threshold — crossing into evidence.

### 6.2 Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  border-t border-[var(--color-border)] bg-[var(--color-elevated)]          │
│                                                                             │
│  max-w-[1152px] mx-auto px-6 py-24                                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ VALIDATION                                                          │   │
│  │ Every call validated. No ex-post edits.                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐             │
│  │     3        │     27       │    72.4%     │      4       │             │
│  │  ↑           │              │              │              │             │
│  │ PAIRS        │ CALLS SINCE  │ 7D ACCURACY  │ SIGNAL       │             │
│  │ TRACKED      │ APRIL 2026   │              │ FAMILIES     │             │
│  └──────────────┴──────────────┴──────────────┴──────────────┘             │
│                                                                             │
│  ───────────────────────────────────────────────────────────────────────   │
│  Outcomes measured against next-day spot...           [View full ledger →] │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Stats grid:** `grid grid-cols-2 md:grid-cols-4`  
**Cell borders:** `first:border-l-0 border-l border-[var(--color-border)]`

### 6.3 Responsive

| Breakpoint | Grid | Padding |
|-----------|------|---------|
| `≥ 768px` | 4 columns, horizontal | `py-12 px-8` per cell |
| `< 768px` | 2×2 grid | `py-8 px-4` per cell. Bottom border added: `border-b border-[var(--color-border)]` on first two cells. |

---

## 7. Scroll Behavior

### 7.1 Reveal Strategy

All sections below the Hero use **intersection-observer-triggered reveals**. The Hero animates on load; everything else animates on scroll.

**Trigger:** `IntersectionObserver` with `threshold: 0.15` (15% of element visible) and `rootMargin: "0px 0px -40px 0px"`.

**Technique:** Add class `revealed` when intersecting. CSS handles the transition.

```css
.reveal {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);
}
.reveal.revealed {
  opacity: 1;
  transform: translateY(0);
}
```

This already exists in `globals.css`.

### 7.2 Per-Section Animation Rules

| Section | What Animates | What Does NOT Animate | Stagger |
|---------|---------------|----------------------|---------|
| **Hero** | All text elements + right column rule | — | See §2.3 |
| **Validation Ticker** | Entire strip fades in (`fade-in`, 0.5s) | Individual items | None |
| **Live Snapshot** | Section label + title fade up. Cards stagger in. | Spot prices, confidence bars (bars grow via CSS width transition, NOT translate) | 100ms per card |
| **Manifesto** | Quote lines stagger fade up. Opening mark fades in. | — | 100ms per line |
| **Signal Architecture** | Section header fades up. Grid cells stagger. | Signal weights, descriptions | 100ms per cell |
| **Validation Trust** | Section header fades up. Stat numbers count up (optional) or fade in. Divider lines grow. | — | 100ms per stat |
| **About Snippet** | Left and right columns fade up independently. | Bio text (static) | 150ms between columns |

### 7.3 What Must NOT Animate

- **Spot prices** — instant update. Any motion on a number that changes frequently creates visual noise.
- **Tables and data grids** — render immediately. Never stagger table rows.
- **Confidence bar on data refresh** — if the bar width changes due to new data, it may transition smoothly (`transition: width 0.3s`), but on initial render it should not have an entrance animation.
- **Validation Ticker items** — the strip moves, individual items do not fade in.
- **Navigation** — static.

### 7.4 Reduced Motion Fallback

The existing `@media (prefers-reduced-motion: reduce)` block in `globals.css` is comprehensive:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  .reveal {
    opacity: 1 !important;
    transform: none !important;
    transition: none !important;
  }
}
```

**Additional rule for this page:** The Validation Ticker should respect reduced motion by displaying the first 4 items statically (no marquee) with a `...` indicator. Implementation: add a `.reduce-motion` class to the ticker wrapper when `prefers-reduced-motion: reduce` is detected, which overrides `animation` and caps width.

---

## 8. Mobile Adaptation

### 8.1 Asymmetric Hero on Mobile

The asymmetric grid collapses to a single column. The right-column vertical status strip is **hidden** (`hidden lg:flex`). The asymmetry is preserved through typography scale and spacing, not layout.

**Mobile hero layout:**
```
flex flex-col justify-center min-h-[85vh] pt-24 pb-16 px-6
```

**Key changes:**
- H1: `text-[clamp(32px,8vw,48px)]` — still large, but within mobile safe zones
- Body: `text-[14px] leading-[1.65]` — slightly tighter for small screens
- CTAs: Stack vertically, full width (`w-full`)
- Primary CTA: `text-center`
- Secondary CTA: `text-center`, remove underline (tap targets need clear bounding boxes)
- Scroll hint: **Hidden** on mobile (`hidden md:flex`). Mobile users know to scroll.

### 8.2 Validation Ticker on Mobile

- Height: `40px` (slightly smaller)
- Font: `text-[10px]`
- Speed: `50s` (slower — less horizontal real estate means more loops)
- Touch: No hover pause (no hover on touch). Instead, on tap, pause the animation and show a tooltip-like expansion. **Simpler approach:** Just let it run. Tapping an item could link to `/performance`.

### 8.3 Live Snapshot on Mobile

- Single column: `grid-cols-1`
- Cards: full width
- Internal padding: `p-6` (reduced from `p-8`)
- Spot price: `text-[28px]` (down from `32px`)

### 8.4 Manifesto on Mobile

- Padding: `py-20`
- Quote: `text-[clamp(20px,6vw,28px)]`
- Opening mark: `text-[48px]`
- Attribution: `text-[10px]`

### 8.5 Validation Trust on Mobile

- Grid: `grid-cols-2` with `border-b` on the first row
- Numbers: `text-[clamp(28px,8vw,40px)]`
- Labels: `text-[9px] tracking-[0.15em]`
- Cell padding: `py-8 px-4`

### 8.6 Signal Architecture on Mobile

- Grid: `grid-cols-1` (stack the 2×2)
- Each signal cell: full width, `p-6`
- Signal number (`01`, `02`, etc.): `text-[10px]`

### 8.7 Touch Target Minimums

| Element | Min Size |
|---------|----------|
| CTA buttons | `44px` height |
| Snapshot cards | Full width |
| Links in footer | `44px` height |
| Ticker items | Do not require individual taps — strip is decorative, not interactive |

---

## 9. Server Component Data Flow

```typescript
// page.tsx (Server Component)
export default async function HomePage() {
  const supabase = await createClient();

  const [calls, signals, validation] = await Promise.all([
    getLatestRegimeCalls(supabase),
    getLatestSignals(supabase),
    getValidationLog(supabase),
  ]);

  const { count } = await supabase
    .from("regime_calls")
    .select("*", { count: "exact", head: true });

  const correctCount = validation.filter((r) => r.outcome === "correct").length;
  const accuracy = validation.length > 0 ? (correctCount / validation.length) * 100 : 0;

  // Ticker data: last 20 validated calls
  const tickerRows = validation
    .filter((r) => r.outcome === "correct" || r.outcome === "incorrect")
    .slice(0, 20);

  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <main id="main-content">
        <Hero />
        <ValidationTicker rows={tickerRows} />
        <LiveSnapshot calls={calls} signals={signals} />
        <Manifesto />
        <SignalArchitecture />
        <ValidationTrust accuracy={accuracy} totalCalls={count ?? 0} />
        <AboutSnippet />
      </main>
      <Footer />
    </div>
  );
}
```

**Key rule:** All data fetching happens in the Server Component. Child components (Hero, Manifesto, SignalArchitecture) receive data via props. No client-side data fetching on the homepage except for intersection observer logic (which is purely presentational).

---

## 10. CSS Custom Properties Reference

All values below are already defined in `globals.css`. This spec uses them exclusively.

| Token | Value | Usage in this spec |
|-------|-------|-------------------|
| `--color-void` | `#0c0a09` | Page background |
| `--color-surface` | `#141210` | Card backgrounds, ticker background |
| `--color-elevated` | `#1c1917` | Manifesto section, Validation Trust section |
| `--color-panel` | `#242220` | Hit-rate tracks, inactive states |
| `--color-border` | `#2a2725` | All borders, dividers |
| `--color-text` | `#f5f5f4` | Hero H1, stat numbers, primary data |
| `--color-text-secondary` | `#a8a29e` | Body text, manifesto quote |
| `--color-text-muted` | `#9f9894` | Labels, timestamps, metadata |
| `--color-text-dim` | `#8a837d` | Tertiary info, countdowns |
| `--color-accent` | `#d6d3d1` | Confidence bar fill, active borders |
| `--color-accent-hover` | `#e7e5e4` | CTA hover state |
| `--color-up` | `#7a9e7a` | Correct calls, live dot, positive returns |
| `--color-down` | `#b87a7a` | Incorrect calls, negative returns |
| `--color-warn` | `#a8947a` | Stale badges, neutral states |
| `--color-pair-eurusd` | `#8fa8bc` | EUR/USD card accent |
| `--color-pair-usdjpy` | `#b8a67a` | USD/JPY card accent |
| `--color-pair-usdinr` | `#b08080` | USD/INR card accent |
| `--ease-institutional` | `cubic-bezier(0.16, 1, 0.3, 1)` | All scroll reveals, hero animations |
| `--ease-crisp` | `cubic-bezier(0.25, 0.1, 0.25, 1)` | Hover states, micro-interactions |
| `--duration-emphasis` | `600ms` | Confidence bar grow, section reveals |

---

## 11. Implementation Checklist

- [ ] Rewrite `Hero` with asymmetric `lg:grid-cols-[5fr_3fr]` layout
- [ ] Add `ValidationTicker` component (new file)
- [ ] Add `@keyframes ticker-marquee` and `.animate-ticker-marquee` to `globals.css`
- [ ] Add `Manifesto` component (new file)
- [ ] Refine `SnapshotCard` with pair-colored top border, `p-8`, timestamp micro-line
- [ ] Refine `ValidationTrust` with monumental typography, vertical dividers, `bg-[var(--color-elevated)]`
- [ ] Wire up `IntersectionObserver` reveal logic for all `.reveal` elements below Hero
- [ ] Ensure `prefers-reduced-motion` hides ticker marquee and shows static items
- [ ] Mobile audit: all grids collapse, touch targets ≥ 44px, no layout overflow
- [ ] Verify all colors use custom properties, no hardcoded hex exceptions
- [ ] Verify no border-radius above `2px` on any element in new sections

---

*End of Round 9 Landing UX Specification*  
*Next step: Engineering review → Component implementation → Visual QA*