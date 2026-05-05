# FX Regime Lab — Motion Design System v1.0

**Project:** FX Regime Lab — Macro Research Terminal  
**Theme:** Obsidian Stone (dark)  
**Stack:** Next.js 15, React 19, Tailwind CSS v4, Framer Motion 12.38+  
**Date:** 2026-05-05  
**Author:** Lead Motion Designer  

---

## 1. Motion Philosophy

> **"Data reveals itself like a live terminal."**

Every animation in FX Regime Lab serves a single purpose: to make abstract financial data feel **observable, alive, and trustworthy**. The terminal is not a dashboard — it is a **command station** where regime states materialize from noise, validate in real-time, and settle into permanence.

**Core principles:**

1. **Reveal, don't announce.** Animations should feel like the system is *thinking*, not like a slide deck transitioning. Values flicker through hex noise before resolving. Cards lift into view with weight and inertia.
2. **Institutional gravity over consumer bounce.** No spring physics, no overshoot, no playful elastic easings. Motion is deliberate, calibrated, and slightly overdamped — like a Bloomberg terminal waking up.
3. **Live surface, archived depth.** The current state pulses. Historical data is static and scannable. Loading states must never feel broken — they feel *pending*.
4. **Minimal, focused, professional, not dull.** Every motion has a job. If removing an animation doesn't make the UI feel broken, remove it.

---

## 2. Animation Taxonomy

| Category | Purpose | Mental Model | Primary Mechanism |
|----------|---------|--------------|-------------------|
| **Page Transitions** | Orient user in information hierarchy | "Depth change" | Framer Motion `AnimatePresence` + scale/opacity |
| **Scroll-Triggered Reveals** | Progressive disclosure of content below fold | "Surface emerging" | CSS `reveal` class + `useScrollReveal` hook |
| **Hover Micro-Interactions** | Confirm interactivity, show secondary data | "Instrument response" | CSS transitions + `omega-haptic` class |
| **Data Updates / Live Indicators** | Signal freshness and system activity | "Terminal flicker" | `BinaryResolve`, `GhostResolve`, pulse keyframes |
| **Loading States** | Maintain trust during async gaps | "System handshake" | Skeleton + `animate-pulse` + vault handshake |
| **Error States** | Communicate failure without alarm | "Degraded mode" | Static red accent, persistent but calm |

---

## 3. Timing & Easing Standards

### 3.1 The Easing Family

All motion in the system derives from **two canonical cubic-beziers**. Never introduce a third without design approval.

| Name | Value | Use Case | Feel |
|------|-------|----------|------|
| **Institutional Settle** | `cubic-bezier(0.16, 1, 0.3, 1)` | Page ingress, gateway blur dissolve, rail slide, hero card mount | Heavy initial velocity, graceful long tail. Like a vault door closing. |
| **Crisp Ease** | `cubic-bezier(0.25, 0.1, 0.25, 1)` | Route transitions, math inspector expand/collapse, rail label fade | Fast, precise, slightly mechanical. Like a terminal tab switch. |

**Framer Motion array equivalents:**
```ts
const INSTITUTIONAL_SETTLE = [0.16, 1, 0.3, 1] as const;
const CRISP_EASE = [0.25, 0.1, 0.25, 1] as const;
```

### 3.2 Duration Scale

| Token | Duration | Use Case |
|-------|----------|----------|
| `duration-instant` | `80ms` | Active state depression (`omega-haptic:active`), toggle switches |
| `duration-fast` | `150–200ms` | Rail width expand, hover color transitions, teleport handshake start |
| `duration-standard` | `220ms` | Route transitions (`TerminalRouteTransition`), math inspector accordion |
| `duration-reveal` | `450ms` | Gateway blur dissolve, vault handshake visibility |
| `duration-ingress` | `700–880ms` | Hero card mount, major section fade-up, desk card hero entrance |
| `duration-ambient` | `1.4–3s` | Live indicator pulse, ghost resolve flicker, marquee scroll |
| `duration-infinite` | — | Tail-risk pulse (`2.2s`), macro drift outlier blink (`1.4s`), heartbeat (`0.8s`) |

### 3.3 Stagger Patterns

| Pattern | Delay | Use Case |
|---------|-------|----------|
| `stagger-dense` | `50ms` | Terminal pair grid items (3 cards), command palette list |
| `stagger-standard` | `100ms` | Section children, form fields, list items |
| `stagger-dramatic` | `200ms` | Hero elements, major section reveals |

**Framer Motion variants:**
```ts
const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }, // dense
  },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2, ease: 'easeOut' },
  },
};
```

---

## 4. Terminal-Specific Animations

The Bloomberg-like terminal has its own motion dialect. These patterns make the terminal feel **alive without being distracting**.

### 4.1 Value Resolution (BinaryResolve)

When a numeric value first appears or updates, it resolves through hex noise.

| Property | Spec |
|----------|------|
| Flicker duration | `300ms` (`DEFAULT_FLICKER_MS`) |
| Tick interval | `45ms` (`DEFAULT_TICK_MS`) |
| Resolved length | `max(4, stringLength)` |
| Character set | `0123456789ABCDEF` |
| Resolve flash | Brief `text-white` snap for `200ms` (disable with `resolveFlash={false}`) |
| Paused state | Skip flicker, show immediately (used for background cards) |

**Behavior on update:** The `resolveKey` prop changes → full re-flicker runs. This gives every data refresh a "terminal tick" feel.

**Usage matrix:**
- **Primary spot prices:** Full flicker + flash
- **Secondary telemetry:** Full flicker, no flash (`resolveFlash={false}`)
- **Background/mosaic cards:** `paused={true}` — instant, no motion

### 4.2 Ghost Whispers (GhostResolve)

Muted, slower variant for atmospheric text (subaudible traces, correlation whispers).

| Property | Spec |
|----------|------|
| Flicker duration | `600ms` |
| Tick interval | `80ms` |
| Resolved color | `text-[#888] opacity-60` |
| Flicker color | `text-[#555] opacity-50` |
| Trigger | `active={true}` + hover state (hero always active) |

**Design rule:** Ghost text must feel like it's *behind* the glass — present but not demanding attention.

### 4.3 Live Indicators

| Indicator | Animation | Duration | Color |
|-----------|-----------|----------|-------|
| **Sync dot** | Static | — | Bullish `#7a9e7a` (synced), Bearish `#b87a7a` (error), Grey `#737373` (loading) |
| **Tail-risk ring** | `tail-risk-pulse` | `2.2s ease-in-out infinite` | `rgba(184, 122, 122, 0.3)` → `0.1` |
| **Omega heartbeat** | `omega-heartbeat` | `0.8s ease-in-out infinite` | Opacity `1 → 0.3` |
| **Macro drift outlier** | Framer Motion `opacity: [1, 0.35, 1]` | `1.4s repeat: Infinity` | White |
| **Marquee pulse** | `pulse-marquee` | `30s linear infinite` | Scrolls macro data horizontally |

### 4.4 Command Palette Teleport

The command palette is not a modal — it is a **teleport interface**.

| Phase | Duration | Behavior |
|-------|----------|----------|
| **Open** | `0ms` (instant) | Overlay appears, input focused via `requestAnimationFrame` |
| **Navigation** | Instant | `↑↓` keys move selection without animation; bg color snaps to `#ffffff` on active item |
| **Teleport** | `150ms` (`TELEPORT_MS`) | Selection triggers `omega-heartbeat` text → `CALCULATING_INGRESS_VECTOR...` → route push |
| **Close** | `0ms` | Palette unmounts immediately on route change |

**Critical detail:** The active item inverts to white-on-black instantly. No fade. Terminal UIs do not fade selections.

### 4.5 Vault Handshake (Gateway Ingress)

When the user clicks "Access Terminal", the gateway performs a **protocol handshake**.

| Step | Duration | Behavior |
|------|----------|----------|
| 1. Overlay fade | `350ms` | Gateway overlay opacity `1 → 0` with `INSTITUTIONAL_SETTLE` |
| 2. Content reveal | `450ms` | Terminal content blur `20px → 0`, scale `1.05 → 1`, opacity `0 → 1` |
| 3. Handshake text | `90ms` interval for `450ms` | `[ INITIALIZING G10_SESSION... ]` ↔ `[ DECRYPTING_VAULT_KEYS... ]` toggles |

**Easing:** `INSTITUTIONAL_SETTLE` for both overlay and content.

---

## 5. Performance Chart Animations

### 5.1 Philosophy

Charts in FX Regime Lab are **not animated for entertainment**. They animate to:
1. Show data *arriving* (lines draw, bars grow)
2. Show *state changes* (regime switches, confidence shifts)
3. Maintain **spatial stability** (scales do not bounce)

### 5.2 Sparkline & Mini-Chart Specs

| Property | Spec |
|----------|------|
| **Stroke draw** | Static (no entrance animation) — sparklines are always pre-loaded |
| **Area fill** | Static, `fillOpacity: 0.1` |
| **Color logic** | Up = `#7a9e7a`, Down = `#b87a7a` (derived from first vs last data point) |
| **Stroke width** | `1.5px` |
| **Line cap** | `round` |

**Exception:** When a sparkline first mounts inside a card that is itself animating in, the sparkline is static — the *container* carries the motion.

### 5.3 Confidence Bar

| Property | Spec |
|----------|------|
| **Track** | `background: #1e1e1e`, height `3px` |
| **Fill** | `width: ${pct}%` |
| **Transition** | `width 0.5s ease` |

**Design note:** The confidence bar uses CSS `transition`, not Framer Motion. It is a passive, ambient indicator. On data update, the bar *glides* to the new position.

### 5.4 Brier Sparkline (Alpha Ledger)

| Property | Spec |
|----------|------|
| **Baseline** | Dashed line at `y = 0.75` (Brier = 0.25), `#333` |
| **Single point** | `circle` with `r=1.5` |
| **Multi-point** | `polyline`, stroke width `1.5` |
| **Color** | `< 0.25` = `#10b981`, `> 0.5` = `#ef4444`, else `#666` |
| **Animation** | None — static render on mount |

### 5.5 Macro Drift Engine Sparkline

| Property | Spec |
|----------|------|
| **Path** | `M` + `L` segments, no curves |
| **Stroke** | `currentColor` (`emerald-500/80`), width `0.8` |
| **Vector effect** | `non-scaling-stroke` (crisp at all sizes) |
| **Animation** | None — path updates instantly on data change |

### 5.6 Regime Heatmap

The heatmap cells should **stagger in** on first mount:

| Property | Spec |
|----------|------|
| **Stagger** | `30ms` per cell, row-major order |
| **Cell entrance** | `opacity: 0 → 1`, `scale: 0.95 → 1` |
| **Duration** | `200ms` per cell |
| **Easing** | `CRISP_EASE` |
| **Hover** | `brightness(1.1)` transition `150ms` |

---

## 6. Scroll Behaviors

### 6.1 Global Scroll

| Property | Spec |
|----------|------|
| **Behavior** | `scroll-behavior: smooth` on `html` |
| **Scrollbar** | `4px` wide, `rgba(255,255,255,0.1)` thumb, transparent track |
| **Horizontal overflow** | Hidden globally (`overflow-x: hidden` on html/body) |

### 6.2 Scroll-Triggered Reveals (`useScrollReveal`)

The existing `useScrollReveal` hook uses `IntersectionObserver` with these exact parameters:

```ts
const observer = new IntersectionObserver(
  (entries) => { /* add 'revealed' class */ },
  { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
);
```

| Property | Spec |
|----------|------|
| **Threshold** | `0.1` (10% visibility triggers reveal) |
| **Root margin** | `0px 0px -40px 0px` (slightly early trigger) |
| **Initial state** | `opacity: 0; transform: translateY(20px)` |
| **Revealed state** | `opacity: 1; transform: translateY(0)` |
| **Transition** | `0.7s cubic-bezier(0.16, 1, 0.3, 1)` for both opacity and transform |
| **Fire once** | `observer.unobserve(entry.target)` after reveal |

**CSS class pattern:**
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

### 6.3 Parallax & Scroll-Linked Motion

**Gateway Manifesto Section:**

The hero manifesto uses Framer Motion's `useScroll` + `useTransform` for a **scroll-linked dissolve**.

| Property | Range | Effect |
|----------|-------|--------|
| `opacity` | `[0, 100, 350]` → `[1, 1, 0]` | Hold crisp through 100px, then evaporate |
| `y` | `[0, 100, 350]` → `[0, 0, -60]` | Gentle upward drift as it fades |
| `blur` | `[0, 100, 350]` → `[0, 0, 12]` | Softens as it leaves viewport |

**Reveal Section (below manifesto):**

| Property | Range | Effect |
|----------|-------|--------|
| `opacity` | `[0, 100, 280]` → `[0.55, 0.55, 1]` | Dim until user scrolls past reading beat |
| `y` | `[0, 100, 300]` → `[56, 56, 0]` | Slides up as manifesto fades |

**Performance note:** Both use `will-change: transform, opacity, filter` and `useMotionTemplate` for the blur filter. This is GPU-accelerated.

### 6.4 No Parallax Elsewhere

**Rule:** Do not add parallax to terminal pages, ledger tables, or data-dense views. Parallax is reserved for the **gateway landing** only — it is a narrative device, not a data device.

---

## 7. Technical Implementation Plan

### 7.1 Library Stack

| Library | Version | Role | Rationale |
|---------|---------|------|-----------|
| **Framer Motion** | `^12.38.0` | Layout animations, AnimatePresence, scroll-linked transforms, variants | Already installed. Best-in-class React integration. `AnimatePresence` handles route transitions flawlessly. |
| **CSS Keyframes** | Native | Ambient loops, simple entrances, hover states | Zero JS overhead. Use for anything that doesn't need React state. |
| **IntersectionObserver** | Native | Scroll-triggered reveals | Already implemented in `useScrollReveal`. No library needed. |

**Do not add:**
- **GSAP** — overkill for this system. Framer Motion handles all requirements.
- **React Spring** — redundant with Framer Motion.
- **Lottie** — no vector character animations needed.

### 7.2 Architecture Patterns

**Pattern A: CSS-first for ambient, Framer for interactive**
```tsx
// Good: CSS keyframe for infinite pulse
<span className="animate-tail-risk-ring" />

// Good: Framer Motion for mount/unmount
<AnimatePresence>
  {mathOpen && (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.22, ease: CRISP_EASE }}
    />
  )}
</AnimatePresence>
```

**Pattern B: Variants for staggered lists**
```tsx
const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};
const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' } },
};

<motion.div variants={container} initial="hidden" animate="show">
  {items.map(i => <motion.div key={i.id} variants={item} />)}
</motion.div>
```

**Pattern C: `will-change` discipline**
- Apply `will-change: transform, opacity` **only** to actively animating elements
- Remove after animation completes (Framer Motion does this automatically)
- Never apply `will-change` to static containers

### 7.3 File Locations

| File | Responsibility |
|------|----------------|
| `src/hooks/useScrollReveal.ts` | IntersectionObserver-based reveal hook |
| `src/components/layout/terminal-route-transition.tsx` | Route-level `AnimatePresence` wrapper |
| `src/components/ui/BinaryResolve.tsx` | Hex-flicker value resolution |
| `src/components/ui/GhostResolve.tsx` | Muted hex-flicker for whispers |
| `src/app/globals.css` | Keyframes, utilities, reveal classes |

---

## 8. Animation Specs by Component

### 8.1 `TerminalRouteTransition`

```tsx
<AnimatePresence mode="wait">
  <motion.div
    key={pathname}
    initial={{ scale: 0.98, opacity: 0 }}
    animate={{ scale: 1, opacity: 1 }}
    exit={{ scale: 1.02, opacity: 0 }}
    transition={{ duration: 0.22, ease: [0.25, 0.1, 0.25, 1] }}
  />
</AnimatePresence>
```

| Property | Value |
|----------|-------|
| Mode | `wait` (exit completes before enter) |
| Scale range | `0.98 → 1 → 1.02` |
| Duration | `220ms` |
| Easing | `CRISP_EASE` |

**Why scale + opacity:** Scale creates depth (zooming into a terminal tab). Opacity prevents flash. The `1.02` exit scale makes the outgoing page feel like it's *receding* slightly.

### 8.2 `TerminalContextRail`

| State | Property | Value |
|-------|----------|-------|
| **Collapsed** | Width | `54px` |
| **Expanded** | Width | `160px` |
| **Transition** | Duration | `220ms` (width), `180ms` (label opacity/maxWidth) |
| **Ingress** | X slide | `-54px → 0` over `450ms` with `INSTITUTIONAL_SETTLE` |
| **Active indicator** | Left bar | `3px` emerald, static |

**Label animation:**
```tsx
<motion.span
  initial={false}
  animate={{ opacity: expanded ? 1 : 0, maxWidth: expanded ? 120 : 0 }}
  transition={{ duration: 0.18, ease: [0.25, 0.1, 0.25, 1] }}
/>
```

### 8.3 `DeskCard` (Hero + Standard)

| Element | Animation | Spec |
|---------|-----------|------|
| **Card mount (hero)** | `opacity + y` | `0 → 1`, `y: 64 → 0`, `duration: 0.88s`, `INSTITUTIONAL_SETTLE` |
| **Math inspector** | `height + opacity` | `0 → auto`, `0 → 1`, `duration: 0.22s`, `CRISP_EASE` |
| **Omega haptic** | `transform + box-shadow` | `0.1s` transitions, active: `translateY(0.5px) scale(0.995)` |
| **Ghost whisper** | `GhostResolve` | `600ms` flicker, `80ms` ticks, triggered on hover (hero always on) |
| **Spot price** | `BinaryResolve` | `300ms` flicker, `45ms` ticks, flash on resolve |
| **LinkedIn button** | State machine | `idle → loading (pulse) → success (green border) → idle` |

**Crisis state:** When `invalidationTriggered` is true, the top border animates to `#f59e0b` (static, no pulse). The regime text gets `line-through`.

### 8.4 `DeskCardTelemetryRow`

| Element | Animation | Spec |
|---------|-----------|------|
| **Spot price** | `BinaryResolve` with `paused` toggle | Paused when card is in background mosaic |
| **Model instability badge** | Static | No animation — it must be immediately readable |

### 8.5 `HomeGatewayShell`

| Phase | Element | Animation | Spec |
|-------|---------|-----------|------|
| **Overlay** | Gateway | `opacity` exit | `1 → 0`, `350ms`, `INSTITUTIONAL_SETTLE` |
| **Content** | Terminal | `opacity + scale + blur` | `0 → 1`, `1.05 → 1`, `20px → 0`, `450ms` |
| **Handshake** | Text | Toggle interval | `90ms` for `450ms` total |

### 8.6 `CommandPalette`

| Element | Animation | Spec |
|---------|-----------|------|
| **Overlay** | Backdrop | Static `bg-black/80` (no fade — instant for responsiveness) |
| **Input** | Focus | `requestAnimationFrame` autofocus |
| **Selection** | Background | Instant snap to `bg-[#ffffff] text-[#000000]` |
| **Teleport** | Text | `omega-heartbeat` (`0.8s` opacity pulse) |

### 8.7 `MacroPulseBar`

| Element | Animation | Spec |
|---------|-----------|------|
| **Marquee** | `translateX` | `30s linear infinite`, `will-change: transform` |
| **Hover** | Pause | `animation-play-state: paused` |
| **Loading** | Skeleton | `animate-pulse` on text |

### 8.8 `MacroDriftEngine`

| Element | Animation | Spec |
|---------|-----------|------|
| **Outlier text** | `opacity` loop | `[1, 0.35, 1]`, `1.4s`, `easeInOut`, `repeat: Infinity` |
| **Sparkline** | Path update | Instant on data change (no morph) |
| **Loading** | Skeleton | `animate-pulse` on container |

### 8.9 `ConfidenceBar`

| Property | Value |
|----------|-------|
| **Fill transition** | `width 0.5s ease` |
| **Track** | `#1e1e1e` |
| **Height (dark)** | `3px` |
| **Height (light)** | `2px` |

### 8.10 `ValidationTable` / `AlphaLedger`

| Element | Animation | Spec |
|---------|-----------|------|
| **Table mount** | None | Static render — tables must be scannable immediately |
| **Row hover** | Background | `transition-colors` `150ms` to slightly elevated surface |
| **Brier sparkline** | None | Static SVG |
| **Skeleton loading** | `animate-pulse` | `bg-[#111]` block |

**Design rule:** Never stagger table rows. Data tables are for scanning, not theatre.

### 8.11 `RegimeHeatmap`

| Element | Animation | Spec |
|---------|-----------|------|
| **Cell entrance** | `opacity + scale` | Stagger `30ms` per cell, `200ms` duration, `CRISP_EASE` |
| **Cell hover** | Brightness | `filter: brightness(1.1)`, `150ms` transition |

---

## 9. Accessibility

### 9.1 `prefers-reduced-motion`

All motion must respect `prefers-reduced-motion: reduce`. Implement via a global CSS override and a React context hook.

**Step 1: CSS override in `globals.css`**
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }

  .animate-pulse-marquee {
    animation: none !important;
  }

  .reveal {
    opacity: 1 !important;
    transform: none !important;
  }
}
```

**Step 2: React hook (`src/hooks/useReducedMotion.ts`) — ADD THIS FILE**
```ts
"use client";

import { useEffect, useState } from "react";

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mql.matches);
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return reduced;
}
```

**Step 3: Component-level gating for JS-driven animations**

For `BinaryResolve`, `GhostResolve`, and Framer Motion components, gate animation logic:

```tsx
import { useReducedMotion } from "@/hooks/useReducedMotion";

function MyComponent() {
  const reduced = useReducedMotion();
  
  return (
    <motion.div
      initial={reduced ? false : { opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={reduced ? { duration: 0 } : { duration: 0.7, ease: INSTITUTIONAL_SETTLE }}
    />
  );
}
```

**BinaryResolve / GhostResolve gating:**
```tsx
// Inside BinaryResolve:
const reduced = useReducedMotion();
// If reduced, skip flicker entirely — show resolved value immediately
```

### 9.2 Focus Management

| Component | Focus Behavior |
|-----------|----------------|
| **Command palette** | `autoFocus` on input, `Escape` closes and returns focus |
| **Math inspector toggle** | Button retains focus, expanded content is `aria-expanded` |
| **Rail entries** | Links are native `<Link>` — keyboard navigable |
| **Desk cards** | `motion.button` for pair grid — receives focus, Enter/Space navigates |

### 9.3 Aria Live Regions

| Element | Region | Message |
|---------|--------|---------|
| **Vault handshake** | `aria-live="polite"` | `[ INITIALIZING G10_SESSION... ]` |
| **Sync status** | Visual only (no live region) | Avoid chatter |
| **LinkedIn copy** | `aria-live="polite"` | `[ COPIED! ✓ ]` |

### 9.4 Vestibular Safety

- **No zoom-scrolling** (scaling the viewport on scroll)
- **No blur-on-scroll except gateway manifesto** (and it fades out quickly)
- **No rotation** anywhere in the system
- **No rapid flashing** — fastest pulse is `0.8s` (omega heartbeat), well below seizure risk thresholds

---

## Appendix A: Token Quick Reference

```ts
// Easing
const INSTITUTIONAL_SETTLE = [0.16, 1, 0.3, 1] as const;
const CRISP_EASE           = [0.25, 0.1, 0.25, 1] as const;

// Durations (seconds for Framer Motion, ms for CSS)
const DURATION_INSTANT     = 0.08;
const DURATION_FAST        = 0.15;
const DURATION_STANDARD    = 0.22;
const DURATION_REVEAL      = 0.45;
const DURATION_INGRESS     = 0.70;
const DURATION_HERO_MOUNT  = 0.88;

// Stagger
const STAGGER_DENSE        = 0.05;
const STAGGER_STANDARD     = 0.10;
const STAGGER_DRAMATIC     = 0.20;

// BinaryResolve
const FLICKER_MS           = 300;
const TICK_MS              = 45;
const GHOST_FLICKER_MS     = 600;
const GHOST_TICK_MS        = 80;

// Command palette
const TELEPORT_MS          = 150;

// Gateway
const INGRESS_DURATION_S   = 0.45;
```

---

## Appendix B: Checklist for New Components

Before shipping any new animated component:

- [ ] Does it use one of the two canonical easings?
- [ ] Does its duration fit the scale (`instant` → `ingress`)?
- [ ] Is `will-change` applied only during active animation?
- [ ] Does it respect `prefers-reduced-motion`?
- [ ] Is the animation *revealing* something (good) or *decorating* something (bad)?
- [ ] Does it maintain `60fps` on a mid-range laptop? (Test with Chrome DevTools Performance panel)
- [ ] Does it work without JS? (CSS fallbacks for keyframes)

---

*End of Motion Design System v1.0*
