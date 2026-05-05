# Frontend QA Report — FX Regime Lab

**Auditor:** Frontend QA Lead  
**Date:** 2026-05-05  
**Scope:** `fx-regime-lab/web/src/app/*`, `components/shell/*`, `components/ui/*`, `hooks/*`  
**Files Audited:** 11

---

## 1. Accessibility Audit

### 1.1 Color Contrast Ratios

| Color Token | Hex | Background | Calculated Ratio | WCAG AA Normal | Used For |
|-------------|-----|------------|------------------|----------------|----------|
| `--color-text-muted` | `#78716c` | `#0c0a09` (void) | **~4.2:1** | ❌ FAIL | Labels, captions, meta text |
| `--color-text-dim` | `#57534e` | `#0c0a09` (void) | **~2.7:1** | ❌ FAIL | Axis labels, disabled states |
| `--color-text-dim` | `#57534e` | `#1c1917` (elevated) | **~2.4:1** | ❌ FAIL | Terminal axis labels |
| `--color-text-secondary` | `#a8a29e` | `#0c0a09` (void) | **~8.6:1** | ✅ PASS | Body text, descriptions |
| `--color-text` | `#f5f5f4` | `#0c0a09` (void) | **~18.5:1** | ✅ PASS | Primary headings |
| `#8a8a8a` (hardcoded SVG) | `#8a8a8a` | `#000000` | **~6.7:1** | ✅ PASS | SVG axis labels |

**Findings:**
- `fx-regime-lab/web/src/app/globals.css:16` — `--color-text-muted: #78716c` fails WCAG AA normal text (needs 4.5:1). This token is used extensively for section labels (`SectionLabel` component), table headers, and timestamps.
- `fx-regime-lab/web/src/app/globals.css:17` — `--color-text-dim: #57534e` fails WCAG AA for both normal and large text. Used for axis labels, stale badges, and terminal metadata.
- **Recommendation:** Lighten `--color-text-muted` to at least `#9f9894` and `--color-text-dim` to at least `#8a837d` to hit 4.5:1.

### 1.2 Focus Indicators

- `fx-regime-lab/web/src/components/shell/Footer.tsx:88-95` — Email input uses `outline-none` and replaces focus with a 1px border color change (`focus:border-[var(--color-accent)]`). The difference between `--color-border` (`#2a2725`) and `--color-accent` (`#d6d3d1`) is high contrast, but on a 1px border this may be too subtle for low-vision users.
- `fx-regime-lab/web/src/components/shell/Nav.tsx:58-72` — Nav links have **no visible focus styles** whatsoever. No `focus:`, `focus-visible:`, or ring utilities applied. Keyboard users cannot track focus position.
- `fx-regime-lab/web/src/app/page.tsx:62-73` — Hero CTA links have no focus styles.
- `fx-regime-lab/web/src/app/performance/page.tsx` — Table rows have `hover:bg-[var(--color-elevated)]` but no `:focus-within` or row-level focus indicator.
- **No global `:focus-visible` styles** defined in `globals.css`. Tailwind's default `outline-none` is used aggressively without replacement.

### 1.3 Semantic HTML & Landmarks

**Positives:**
- `fx-regime-lab/web/src/components/shell/Nav.tsx:42` — Uses `<header>` landmark.
- `fx-regime-lab/web/src/components/shell/Footer.tsx:15` — Uses `<footer>` landmark.
- `fx-regime-lab/web/src/app/page.tsx:396` — Uses `<main>` landmark.
- `fx-regime-lab/web/src/app/page.tsx:46` — Proper `<h1>` present in Hero.
- `fx-regime-lab/web/src/app/performance/page.tsx:351` — Proper `<h1>` present.
- `fx-regime-lab/web/src/app/performance/page.tsx:528` — Tables use `<thead>`, `<th>`, `<tbody>`, `<tr>`, `<td>` correctly.

**Negatives:**
- `fx-regime-lab/web/src/app/page.tsx:15-21` — `SectionLabel` renders as `<p>`, not a heading. Semantically these are section subtitles/pre-headers; consider `<span>` or connect them to headings via `aria-describedby`.
- `fx-regime-lab/web/src/app/page.tsx:255` — `SignalArchitecture` signal cards use `<h3>` for labels inside a grid with no parent `<h2>` in that section. The `<SectionTitle>` renders an `<h2>`, so hierarchy is actually correct (h2 → h3).
- `fx-regime-lab/web/src/app/performance/page.tsx` — Tables lack `<caption>` elements or `aria-label` attributes. Screen-reader users cannot determine table purpose without entering them.
- `fx-regime-lab/web/src/app/terminal/fx-regime/[pair]/page.tsx:432` — Signals table `<th>` elements lack `scope="col"`.
- **No skip-to-content link** anywhere in the layout. Keyboard users must tab through the entire nav on every page load.

### 1.4 ARIA Labels

- `fx-regime-lab/web/src/app/performance/page.tsx:105-180` — `EquityCurveSVG` renders an `<svg>` with **no `role="img"`**, **no `aria-label`**, and no `<title>` element. Screen readers announce nothing or raw path data. The chart is completely inaccessible to blind users.
- `fx-regime-lab/web/src/app/terminal/fx-regime/[pair]/page.tsx:538` — `Sparkline` component is imported; if it follows the same pattern as `EquityCurveSVG`, it likely lacks accessible name too.
- `fx-regime-lab/web/src/components/shell/Nav.tsx:89` — "Terminal" dropdown trigger lacks `aria-expanded`, `aria-haspopup`, `aria-controls`, and the dropdown panel lacks `role="menu"`.
- `fx-regime-lab/web/src/components/shell/Footer.tsx:70-77` — External Substack link lacks `aria-label` to warn users it opens in a new tab.
- `fx-regime-lab/web/src/components/ui/Skeleton.tsx:20-27` — Skeleton loader has **no `aria-hidden="true"`**, `role="status"`, or `aria-live` region. Screen readers may announce empty divs or silence loaded content unexpectedly.
- `fx-regime-lab/web/src/app/page.tsx:79-84` — Scroll hint is purely decorative but not hidden from AT (`aria-hidden="true"` missing).

### 1.5 prefers-reduced-motion Support

**Positives:**
- `fx-regime-lab/web/src/app/globals.css:342-357` — Global `@media (prefers-reduced-motion: reduce)` block forces `animation-duration: 0.01ms`, `transition-duration: 0.01ms`, and `scroll-behavior: auto`. Also overrides `.reveal` to `opacity: 1` instantly.
- `fx-regime-lab/web/src/hooks/useReducedMotion.ts` — Clean, SSR-safe hook with event listener cleanup.
- `fx-regime-lab/web/src/components/ui/AnimatedNumber.tsx:27-29` — Respects reduced motion by jumping directly to final value.
- `fx-regime-lab/web/src/components/ui/Skeleton.tsx:24` — Removes `animate-pulse` when reduced motion is preferred.
- `fx-regime-lab/web/src/hooks/useScrollReveal.ts:10-15` — Immediately reveals all `.reveal` elements when reduced motion is active.

**Negatives:**
- `fx-regime-lab/web/src/app/globals.css:74` — `scroll-behavior: smooth` is set unconditionally on `<html>`. The reduced-motion media query overrides this, but the declaration sits outside any motion preference block. This is fine because the media query overrides it, but it would be cleaner to gate it.

### 1.6 Keyboard Navigability

- `fx-regime-lab/web/src/components/shell/Nav.tsx:76-114` — Terminal dropdown is **mouse-only**. It uses `onMouseEnter` / `onMouseLeave` with no `onFocus`/`onBlur` equivalents. Keyboard users cannot open the dropdown or access its items.
- `fx-regime-lab/web/src/components/shell/Nav.tsx` — No `Escape` key handler to close the dropdown.
- `fx-regime-lab/web/src/app/terminal/fx-regime/[pair]/page.tsx:560-585` — Regime timeline dots use `title` attribute and CSS `group-hover:block` tooltips. Neither is keyboard-accessible. Keyboard users cannot access date/regime information.
- `fx-regime-lab/web/src/app/terminal/fx-regime/[pair]/page.tsx:309-319` — Signal architecture stacked bars use `title` for tooltips — same keyboard issue.
- `fx-regime-lab/web/src/app/performance/page.tsx` — Tables are scrollable via `overflow-x-auto`, but there is no keyboard-focusable container or tabindex to allow keyboard users to scroll horizontally.
- `fx-regime-lab/web/src/components/shell/Footer.tsx:80-103` — Newsletter form submits to a no-op handler with zero feedback. After pressing Enter, focus remains on the input and nothing is announced to screen readers.

---

## 2. Performance Audit

### 2.1 Unnecessary Re-renders

- `fx-regime-lab/web/src/components/ui/AnimatedNumber.tsx:34-48` — `requestAnimationFrame` loop calls `setDisplayValue` on every frame. For a 1200ms animation at 60fps, this triggers **~72 React re-renders**. The component is small, but at scale this is wasteful. **Recommendation:** Use a `ref` to the `<span>` and update `textContent` directly inside the rAF loop, bypassing React's render cycle entirely.
- `fx-regime-lab/web/src/components/shell/Nav.tsx:19` — `useScrollReveal()` is called with default selector `.reveal`, but `Nav` contains **no `.reveal` elements**. This causes an unnecessary `useEffect` + `IntersectionObserver` setup on every page that mounts the nav.
- `fx-regime-lab/web/src/hooks/useScrollReveal.ts:30` — The hook queries `document.querySelectorAll(selector)` globally. If multiple instances run, they compete for the same DOM elements. The observer is also not re-evaluated if DOM nodes are added dynamically after mount.

### 2.2 Image Optimization

- **No images** present in any of the audited files. The project uses SVG charts rendered inline (server-side), which is optimal for data viz. No `<img>` or `next/image` usage to critique in this scope.

### 2.3 Font Loading Strategy

- `fx-regime-lab/web/src/app/layout.tsx:7-21` — Uses `next/font/google` for Inter, JetBrains Mono, and Cormorant. This is the **gold standard**: fonts are self-hosted, subset to `latin`, and loaded with CSS variables. No layout shift from webfont loading.
- `fx-regime-lab/web/src/app/layout.tsx:17-21` — `Cormorant` loads only weight `300`. Good restraint.
- **Minor:** No `display: swap` specified, but `next/font` defaults to `swap` internally.

### 2.4 CSS Bloat

- `fx-regime-lab/web/src/app/globals.css:320-328` — `@layer base` selector `[data-fxrl-terminal] p, [data-fxrl-terminal] span, [data-fxrl-terminal] div` is **extremely over-broad**. It forces `font-family: var(--font-mono)` on every `p`, `span`, and `div` inside terminal pages. This overrides component-level typography choices and increases specificity wars. **Recommendation:** Scope to a `.font-mono` utility class instead of element selectors.
- `fx-regime-lab/web/src/app/globals.css:166-317` — Utility layer contains many one-off animations. Most are justified, but `omega-gutter`, `omega-haptic`, `omega-depress`, `omega-heartbeat` appear to be dead code in the audited pages. Verify usage or tree-shake.
- `fx-regime-lab/web/src/app/globals.css:95-113` — Scrollbar styling uses `::-webkit-scrollbar` (WebKit only) plus `scrollbar-width: thin` (Firefox). The 4px width is very thin. Not bloat, but worth noting for usability.

### 2.5 JavaScript Bundle Concerns

- `fx-regime-lab/web/src/app/page.tsx:377` — Home page is an `async` Server Component. Data fetching happens server-side; zero client JS shipped for the page shell. Excellent.
- `fx-regime-lab/web/src/app/performance/page.tsx:185` — Performance page is also a Server Component. The `EquityCurveSVG` is computed server-side and shipped as static SVG markup.
- `fx-regime-lab/web/src/app/terminal/fx-regime/[pair]/page.tsx:119` — Pair desk page is a Server Component.
- **Client Components audited:** `Nav`, `Footer`, `AnimatedNumber`, `Skeleton`, `useReducedMotion`, `useScrollReveal`. These are small and focused. No heavy third-party libraries visible in audited files.
- `fx-regime-lab/web/src/app/layout.tsx:5` — `CommandPalette` is imported. Without auditing its source, cannot assess bundle impact.

---

## 3. Code Quality

### 3.1 TypeScript Strictness

- **No `any` types** found in any audited file. Strong typing throughout.
- `fx-regime-lab/web/src/app/terminal/fx-regime/[pair]/page.tsx:393` — `color as string` and similar assertions are present after a `.filter(([, dir]) => dir)` call. The assertion is technically safe but could be eliminated by typing the tuple array more precisely.
- `fx-regime-lab/web/src/app/performance/page.tsx:189-202` — Redundant explicit type annotations on reduce callbacks (`s: number, r: ValidationRow`). TypeScript already infers these from the `validation` array type.
- `fx-regime-lab/web/src/app/layout.tsx:28-31` — Uses `Readonly<{ children: React.ReactNode }>` — good practice.
- `fx-regime-lab/web/src/components/ui/Skeleton.tsx:14` — Uses `React.CSSProperties` correctly for inline styles.

### 3.2 Unused Imports / Variables

- `fx-regime-lab/web/src/app/performance/page.tsx:1` — `notFound` is imported but **never used** in this file. Should be removed.
- `fx-regime-lab/web/src/app/terminal/fx-regime/[pair]/page.tsx:156` — `confidenceHistory` is defined but only used at line 539 inside a `.slice(-14)`. The slice of a slice is slightly confusing but not a bug.

### 3.3 Consistent Patterns

- **Font size mixing:** The codebase uses Tailwind arbitrary values (`text-[10px]`, `text-[9px]`, `text-[8px]`) extensively. This is consistent *within* the terminal aesthetic, but the 8px/9px sizes are extremely small. Recommend establishing named text tokens (e.g., `text-2xs`) to reduce magic numbers.
- **Color access:** Mostly uses CSS custom properties via `var(--color-*)`, which is excellent for theming. However, hardcoded hexes appear in SVGs (`#000000`, `#111111`, `#8a8a8a`).
- **Event handler naming:** `handleSubscribe`, `onScroll` — consistent camelCase.
- **File naming:** Mixed casing (`useReducedMotion.ts`, `AnimatedNumber.tsx`, `page.tsx`). All use PascalCase for components and camelCase for hooks — consistent with React conventions.

### 3.4 Error Handling

- `fx-regime-lab/web/src/app/page.tsx:386-388` — Supabase count query has no error handling. If the query fails, `count` is `null` and the page silently shows `0` calls.
- `fx-regime-lab/web/src/app/performance/page.tsx:186` — `getValidationLog` has no try/catch. An error would bubble to the Next.js error boundary (acceptable, but consider graceful degradation).
- `fx-regime-lab/web/src/components/shell/Footer.tsx:9-13` — Newsletter form handler is a no-op TODO. No loading state, no error state, no success feedback.
- `fx-regime-lab/web/src/app/terminal/fx-regime/[pair]/page.tsx:120-122` — `notFound()` is correctly used for invalid slugs.

### 3.5 Security

- **No exposed API keys, secrets, or tokens** in any audited file.
- `fx-regime-lab/web/src/components/shell/Footer.tsx:70-77` — External link uses `rel="noopener noreferrer"` correctly.
- `fx-regime-lab/web/src/app/terminal/fx-regime/[pair]/page.tsx:419` — `new Date().toISOString()` in render output. Not a security issue, but could leak server timezone in SSR context.

---

## 4. Mobile Responsiveness

### 4.1 Breakpoint Usage

- **Home page (`page.tsx`):** Excellent responsive patterns. Uses `md:grid-cols-3`, `md:grid-cols-2`, `md:grid-cols-[1fr_2fr]`, and `clamp()` for fluid typography.
- **Performance page (`performance/page.tsx`):** Uses `md:grid-cols-4`, `md:h-[320px]`, `lg:h-[400px]`. Tables wrapped in `overflow-x-auto`. Good.
- **Terminal pair page (`terminal/fx-regime/[pair]/page.tsx`):** **Critical failure**. The top strip at line 174 uses inline style `gridTemplateColumns: "repeat(4, 1fr)"` with **no responsive breakpoint**. On a 375px viewport, 4 columns containing `text-[28px]` and `text-[32px]` numbers will overflow horizontally or be unreadable.
- **Nav (`Nav.tsx`):** No responsive breakpoint. The nav is a single row of inline links. On screens below ~640px, links will either wrap awkwardly or be clipped. **No hamburger menu or collapsible pattern exists.**

### 4.2 Touch Targets

| Element | File | Approx. Size | WCAG 2.5.8 (AA 24×24) | WCAG 2.5.5 (AAA 44×44) |
|---------|------|--------------|----------------------|----------------------|
| Nav links | `Nav.tsx:62` | ~54×29px | ❌ FAIL height | ❌ FAIL |
| Footer links | `Footer.tsx:34` | ~auto×21px | ❌ FAIL | ❌ FAIL |
| Terminal dropdown items | `Nav.tsx:102` | ~180×37px | ❌ FAIL height | ❌ FAIL |
| Subscribe button | `Footer.tsx:97` | ~auto×36px | ❌ FAIL height | ❌ FAIL |
| Regime timeline dots | `[pair]/page.tsx:570` | 7×7px | ❌ FAIL | ❌ FAIL |
| Signal chips | `[pair]/page.tsx:396` | ~auto×29px | ❌ FAIL | ❌ FAIL |
| Hero CTA | `page.tsx:62` | ~auto×42px | ✅ PASS | ❌ FAIL (close) |

- **Recommendation:** Add at least `min-h-[44px]` or `py-2.5`/`py-3` to all interactive elements. The terminal aesthetic should not sacrifice usability.

### 4.3 Horizontal Scroll Issues

- `fx-regime-lab/web/src/app/globals.css:77-78,85-87` — `html` and `body` both declare `overflow-x: hidden`. This **prevents natural overflow behavior** and can clip content. On the terminal pair page, the 4-column grid will likely be clipped rather than scrollable.
- `fx-regime-lab/web/src/app/performance/page.tsx:527,619` — Tables correctly use `overflow-x-auto` on wrappers, allowing horizontal scroll. This is the correct pattern.
- `fx-regime-lab/web/src/app/terminal/fx-regime/[pair]/page.tsx:174` — Top strip 4-column grid has no `overflow-x` wrapper. Content will be clipped by the global `overflow-x: hidden`.

### 4.4 Font Size on Mobile

- `text-[8px]` and `text-[9px]` are used extensively in the terminal UI (`[pair]/page.tsx`). While the aesthetic is "terminal dense", iOS Safari will **not auto-zoom** on inputs below 16px, but reading 8px text on a phone is impractical.
- `fx-regime-lab/web/src/app/performance/page.tsx:151` — SVG axis labels use `fontSize={10}`. On a 375px screen, a 1000px viewBox SVG scaled down makes 10px SVG text effectively ~3–4px. Essentially illegible.
- **Recommendation:** Use `min-width` media queries or clamp minimums. Consider a "dense" vs "readable" mode for mobile terminal views.

---

## 5. Issues List

### 🔴 CRITICAL

| # | Issue | File(s) | Line(s) | Impact |
|---|-------|---------|---------|--------|
| C1 | **Nav dropdown is mouse-only, not keyboard accessible** | `Nav.tsx` | 76–114 | Keyboard and screen-reader users cannot access Terminal sub-pages |
| C2 | **Top strip uses 4 fixed columns with no responsive fallback** | `[pair]/page.tsx` | 174 | Severe layout breakage on all phones (< 640px) |
| C3 | **EquityCurveSVG has no accessible name** | `performance/page.tsx` | 105–180 | Blind users receive zero information from the chart |
| C4 | `--color-text-muted` (#78716c) fails WCAG AA contrast on dark bg | `globals.css` | 16 | Low-vision users cannot read labels, timestamps, captions |
| C5 | `--color-text-dim` (#57534e) fails WCAG AA contrast on all dark surfaces | `globals.css` | 17 | Axis labels and metadata are illegible for low-vision users |
| C6 | **No skip-to-content link** | `layout.tsx`, `Nav.tsx` | — | Keyboard users must tab through entire nav on every page |
| C7 | `overflow-x: hidden` on `html`/`body` clips content and prevents pinch-zoom recovery | `globals.css` | 77, 85 | Mobile users cannot access overflowed content |

### 🟡 WARNING

| # | Issue | File(s) | Line(s) | Impact |
|---|-------|---------|---------|--------|
| W1 | Nav links have **no visible focus indicators** | `Nav.tsx` | 58–93 | Keyboard users lose track of focus position |
| W2 | `AnimatedNumber` re-renders ~72 times per animation via `setState` in rAF | `AnimatedNumber.tsx` | 34–48 | Unnecessary React churn; should mutate DOM ref directly |
| W3 | Skeleton lacks `aria-hidden` or loading status | `Skeleton.tsx` | 20–27 | Screen readers may announce empty blocks |
| W4 | Terminal timeline dots rely on `title` and hover tooltips (no keyboard access) | `[pair]/page.tsx` | 560–585 | Keyboard users cannot read date/regime tooltips |
| W5 | Newsletter form is a no-op with zero feedback | `Footer.tsx` | 9–13, 80–103 | Users believe submission succeeded; no AT feedback |
| W6 | `useScrollReveal` called in `Nav` despite no `.reveal` elements | `Nav.tsx` | 19 | Unnecessary IntersectionObserver overhead on every page |
| W7 | `@layer base` terminal selector forces monospace on all p/span/div | `globals.css` | 321–328 | Overrides component typography; hard to maintain |
| W8 | Hardcoded `new Date()` in render causes potential hydration mismatch | `[pair]/page.tsx` | 419 | React hydration warnings; date may differ SSR vs CSR |
| W9 | Tables lack captions or `aria-label` | `performance/page.tsx` | 528, 620 | Screen-reader users don't know table purpose until inside |
| W10 | Footer input uses `outline-none` with only border-color focus | `Footer.tsx` | 94–95 | Focus indicator may be too subtle for low-vision users |
| W11 | `notFound` imported but unused | `performance/page.tsx` | 1 | Dead code; slight bundle noise |
| W12 | Terminal nav has no hamburger/collapsible pattern for mobile | `Nav.tsx` | 41–117 | Links wrap or overflow on narrow viewports |

### 🟢 NICE-TO-HAVE

| # | Issue | File(s) | Line(s) | Impact |
|---|-------|---------|---------|--------|
| N1 | Add `scope="col"` to all table headers | `[pair]/page.tsx` | 435–446 | Improves screen-reader table navigation |
| N2 | Add `aria-current="page"` to active nav links | `Nav.tsx` | 58–93 | Helps AT identify current location |
| N3 | Add `aria-label="Opens in new tab"` to external Substack link | `Footer.tsx` | 70–77 | Warns screen-reader users before navigation |
| N4 | Replace magic-number font sizes (`text-[9px]`, `text-[8px]`) with design tokens | Multiple | — | Improves maintainability |
| N5 | Hardcoded hex colors in SVGs (`#000000`, `#8a8a8a`) should use CSS vars | `performance/page.tsx` | 112, 125, 154 | Ensures theming consistency |
| N6 | `omega-*` utility classes may be dead code | `globals.css` | 281–317 | Verify usage; remove if unused |
| N7 | Add `prefers-reduced-motion` gating to `scroll-behavior: smooth` | `globals.css` | 74 | Cleaner separation of motion concerns |
| N8 | Use `min-height`/`min-width` for touch targets rather than arbitrary padding | Multiple | — | More robust responsive behavior |
| N9 | Consider `aria-live="polite"` region for data freshness indicators | `performance/page.tsx` | 361–369 | Announce stale data to screen-reader users |
| N10 | Add `role="img"` and `aria-label` to Sparkline if not already present | `[pair]/page.tsx` | 538 | Ensure consistency with chart a11y |

---

## Summary

The FX Regime Lab codebase demonstrates **strong architectural choices**: Server Components for data-heavy pages, excellent font-loading strategy via `next/font`, robust `prefers-reduced-motion` support, and consistent use of CSS custom properties for theming.

However, **accessibility and mobile responsiveness are the two weakest areas**:

1. **Accessibility gaps** — Missing focus indicators, mouse-only dropdowns, unnamed SVG charts, and insufficient color contrast on muted text tokens are the most severe issues.
2. **Mobile breakpoints** — The navigation and terminal pair page lack mobile-first responsive design. The 4-column terminal top strip and ultra-small touch targets will make the app unusable on phones.
3. **Performance nit** — `AnimatedNumber`'s frame-by-frame re-renders are an easy win via direct DOM manipulation.

**Priority order for remediation:**
1. Fix color contrast (C4, C5) — one-line CSS changes.
2. Add keyboard support to Nav dropdown (C1) and skip-link (C6).
3. Make terminal pair page responsive (C2, C7, W12).
4. Label SVG charts (C3).
5. Optimize `AnimatedNumber` (W2) and clean up dead code (W6, W11).
