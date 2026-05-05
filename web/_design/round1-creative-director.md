# FX Regime Lab — Creative Vision Document
## Round 1: Creative Director's Brief
**Date:** 2026-05-05  
**Project:** FX Regime Lab (Next.js 15, Obsidian Stone Theme)  
**Status:** Foundation locked. Polish, motion, and coherence phase.

---

## 1. Brand Essence

**"Precision under pressure."**

Or, in five words: **Rigorous. Warm. Terminal-native. Quietly confident. Alive.**

FX Regime Lab is not a fintech startup. It is not a dashboard. It is a **living research ledger** — a single author's public trace of discretionary macro calls, validated in real-time. The visual personality must communicate that this is serious work done by a serious mind, but without the cold corporate sterility of a bank terminal. There is warmth in the precision. There is craft in the code.

The user should feel like they have walked into a private research desk — not a product page.

---

## 2. Design Principles

### Principle 1: Darkness is the canvas, not the absence of light
The void (#0c0a09) is not "dark mode." It is the default state of focus. Every element that floats above it — a card, a chart, a line of monospace — earns its place. Light is information. Darkness is rest. We do not fight the void; we sculpt within it.

### Principle 2: Every pixel must justify its existence
No decorative gradients that do not encode data. No borders that do not separate meaning. No margin that does not create breathing room. If an element can be removed without losing clarity, it is removed. The interface is **editorial**, not ornamental.

### Principle 3: Motion is information, not entertainment
Animations do not say "look at me." They say "this just arrived," or "this is connected to that," or "this surface responded to your touch." Transitions are fast (200–400ms), eased with `cubic-bezier(0.16, 1, 0.3, 1)`, and always purposeful. No bounce. No spring physics. No "delight" for delight's sake.

### Principle 4: The terminal is a place, not a theme
The terminal routes (`/terminal/*`) are not "dark pages." They are a **spatial context shift** — a descent into the engine room. The transition from marketing surfaces to terminal surfaces must feel like crossing a threshold. Typography shifts to monospace. Borders get thinner. Information density increases. The user should feel the pressure change.

### Principle 5: Performance is the primary content
Strategies, signals, validation logs, accuracy metrics — these are not "features." They are the **reason the site exists.** Every design decision must make the performance data more legible, more trustworthy, and more immediately graspable. The design serves the alpha. Never the reverse.

---

## 3. Mood Board Description

### The Aesthetic: *Bloomberg Terminal × Aesop × Stripe Press*

Imagine a space where these three worlds collide:

**From Bloomberg Terminal:**  
The relentless information density. The grid logic. The way numbers sit in monospace columns and command attention without shouting. The sense that this screen is connected to live markets, that data is flowing in from somewhere real. The terminal is a *tool*, not a *presentation*.

**From Aesop:**  
The warm, material darkness. The sense that every surface has weight and texture. The restraint — Aesop never uses two words where one will do, never uses two ingredients where one is sufficient. The warm stone palette (our Obsidian Stone) feels like a laboratory bench, not a server room. The typography breathes. The whitespace is confident.

**From Stripe Press:**  
The editorial confidence. The way complex ideas are made approachable through typography hierarchy alone. The understated polish — the sense that someone spent three hours adjusting the kerning on a single heading. The belief that **good information design is a form of respect** for the reader. The subtle animations that make the interface feel alive but never playful.

### The Feeling We Chase
- Walking into a private research library at 5:47 AM.
- The hush of a dealing room before the open.
- The warmth of a single desk lamp on cold stone.
- The satisfaction of a perfectly aligned grid.

### Texture & Material Language
- **Surfaces:** Warm matte stone, brushed metal, smoked glass.
- **Light:** Single-source, warm, directional. No ambient glow. No halos.
- **Edges:** Sharp, not rounded. A radius of 0px or 2px maximum. This is not a consumer app.
- **Typography:** Inter for readability, JetBrains Mono for data, Cormorant for moments of editorial voice.

---

## 4. Tone of Voice

### How the interface speaks

The interface is a **research assistant** — not a salesperson, not a chatbot, not a cheerleader.

| We are | We are NOT |
|--------|-----------|
| Precise and direct | Cute or conversational |
| Confident but never arrogant | Hype-driven |
| Warm but formal | Cold or robotic |
| Data-first, narrative-second | Storytelling for engagement |
| Transparent about uncertainty | Overpromising |

### Microcopy rules
- **Headings:** Declarative. No verbs needed. "Daily regime calls. On the record." Not "Discover our daily regime calls."
- **Labels:** Monospace, uppercase, tracked out. `LIVE SNAPSHOT` not `Live Snapshot`.
- **Numbers:** Tabular-nums always. Percentages to one decimal place. No rounding theater.
- **CTAs:** Direct action. "Read today's brief" not "Get started" or "Learn more."
- **Empty states:** Honest. "No calls yet for this pair." Not "Oops, nothing here!"
- **Terminal copy:** Telegraphese. `CONF 0.62` not `Confidence: 62%`.

### The one voice test
If a line of copy would feel out of place in a research note from a top-tier macro hedge fund, delete it.

---

## 5. Visual Hierarchy Rules

### The Z-axis of attention
We guide the eye through **density, not contrast.** In a dark interface, the brightest thing wins — so we must be disciplined about what we allow to glow.

#### Layer 0: The Void
`#0c0a09` — the background. Passive. Receptive. Never competes.

#### Layer 1: Surfaces
`#141210` (surface) and `#1c1917` (elevated) — containers for information. Cards, panels, table rows. These are the "paper" of our interface. They rise slightly above the void through subtle border definition, not drop shadows.

#### Layer 2: Structural Text
`#a8a29e` (secondary) and `#78716c` (muted) — labels, metadata, timestamps, table headers. The scaffolding. Most of the text lives here.

#### Layer 3: Primary Information
`#f5f5f4` (text) — the data that matters. Spot prices. Regime labels. Accuracy percentages. Used sparingly. When everything is bright, nothing is bright.

#### Layer 4: Accent
`#d6d3d1` (accent) — reserved for: the active nav item, the primary CTA fill, the focused input border, the confidence bar fill. This is our "spotlight color." It must never appear in more than 10% of the viewport at once.

#### Layer 5: Functional Color
- `#7a9e7a` (up/bullish) — positive moves, correct calls, live indicators.
- `#b87a7a` (down/bearish) — negative moves, incorrect calls, tail-risk pulses.
- `#a8947a` (warn) — vol expanding, caution states.

These encode meaning. They are not decorative. A green number is not "good" — it is "up."

### Spacing system
- **Base unit:** 4px.
- **Section padding:** 96px (py-24) vertical. Never less between major sections.
- **Container:** max-w-[1152px] centered. The grid is the spine of the layout.
- **Gap rhythm:** 4px, 8px, 16px, 24px, 32px, 48px, 64px. No arbitrary values.

### Typography scale
| Role | Font | Size | Weight | Tracking | Case |
|------|------|------|--------|----------|------|
| Hero | Inter | clamp(40px,6vw,72px) | 600 | tight | Sentence |
| H2 | Inter | 28px | 600 | tight | Sentence |
| H3 | Inter | 22px | 600 | tight | Sentence |
| Body | Inter | 15px | 400 | normal | Sentence |
| Label | JetBrains Mono | 9–10px | 400/500 | 0.12–0.2em | UPPER |
| Data | JetBrains Mono | 24–32px | 500 | tight | UPPER/num |
| Terminal | JetBrains Mono | 10–11px | 400/700 | 0.1em | UPPER |
| Editorial | Cormorant | 22–32px | 300 | normal | Sentence |

Cormorant (our serif) is used **only** for moments of editorial voice — a pull quote, an about section heading, a methodology preamble. It is the only "soft" thing in the interface. Use it like salt.

---

## 6. What NOT to Do

### Anti-patterns (non-negotiable)

**1. No rounded corners above 4px**  
This is not a SaaS dashboard. Sharp edges signal precision. Rounded cards feel like consumer apps. Our radius budget: 0px for most elements, 2px for small tags/pills, 4px max for interactive elements.

**2. No drop shadows on cards**  
Depth is communicated through borders (`#2a2725`, `#1f1d1b`) and subtle background shifts (surface → elevated). Shadows are lazy depth. In a dark interface, they read as smudges.

**3. No generic stock photography**  
No photos of cities at night. No abstract 3D glass shapes. No crypto-adjacent imagery. The only "images" are data visualizations, charts, and the occasional diagram. The interface itself is the visual.

**4. No loading spinners**  
Skeleton screens that match the final layout. Or, better, stale-while-revalidate with graceful decay. A spinner says "we are not ready." A skeleton says "the structure is here, the data is arriving."

**5. No "delight" animations**  
No confetti on correct calls. No bounce on button presses. No parallax scroll hijacking. Motion is information. If the animation does not encode state change, it is cut.

**6. No light mode**  
The Obsidian Stone palette is the identity. A light mode would fracture the brand. Users who want light mode are not our users.

**7. No infinite scroll**  
Pagination or "Load more." The terminal must feel bounded and navigable. Infinite scroll creates anxiety in a data-dense interface.

**8. No blur/backdrop-filter**  
Glassmorphism is dead. It adds render cost, reduces legibility, and contradicts our material language of warm stone and solid surfaces.

**9. No more than two typefaces per viewport**  
Inter + Mono, or Inter + Cormorant, or Mono + Cormorant. Never all three competing on the same screen.

**10. No social proof widgets**  
No "trusted by" logos. No star ratings. No testimonial carousels. The validation table IS the social proof.

---

## 7. Success Metrics

How do we know the design works? Not by "it looks good." By these signals:

### Quantitative
1. **Time-to-first-insight ≤ 3 seconds**  
   A new visitor should understand what FX Regime Lab is, what today's calls are, and what the track record is within 3 seconds of landing. Measured via scroll depth and CTA click-through on the hero.

2. **Terminal route engagement ≥ 40% of sessions**  
   The terminal is the product. If users are not entering it, the gateway pages are failing to communicate value.

3. **Validation table scroll depth ≥ 60%**  
   The validation log is the trust anchor. If users are not scrolling through it, it is not legible enough or not findable enough.

4. **Page load ≤ 1.5s (LCP)**  
   A research tool must be fast. No excuse for slow. The dark theme helps — no heavy images, minimal JS.

5. **Mobile usability score ≥ 95**  
   Terminal-native does not mean desktop-only. The terminal must compress elegantly. Monospace data must reflow. Tables must become cards.

### Qualitative
6. **"I trust this" test**  
   Show a macro trader the performance page for 10 seconds, then ask: "Would you follow these calls?" If the answer is not immediately positive, the data presentation is failing.

7. **"I know where I am" test**  
   Drop a user on any page blindfolded (metaphorically). They should know within 1 second whether they are in the marketing layer or the terminal layer. The threshold must be felt.

8. **No cognitive fatigue after 5 minutes**  
   A user should be able to spend 5 minutes in the terminal without feeling visually exhausted. This means contrast discipline, spacing discipline, and animation restraint.

### Technical
9. **Zero layout shift on data hydration**  
   Numbers loading in should not push content. Skeletons must match final dimensions exactly. Tabular nums prevent jitter.

10. **Accessibility: WCAG 2.1 AA minimum**  
    All functional colors must meet contrast ratios. Focus states must be visible. The interface must be navigable by keyboard. Dark mode is not an excuse for poor accessibility.

---

## 8. Priority Matrix: What We Build Next

### P0 — The Foundation (locked, do not break)
- Obsidian Stone palette
- Three-typeface system (Inter, JetBrains Mono, Cormorant)
- 1152px max-width container
- Terminal/native page distinction
- Existing animation primitives (`fade-up`, `reveal`, `hover-lift`)

### P1 — Coherence Pass (this round)
- Unify border colors across all 18 pages (some drift exists)
- Standardize all label typography to the hierarchy table above
- Audit every page for "orphan" animations that do not use the shared primitives
- Ensure terminal pages enforce monospace via `data-fxrl-terminal` consistently

### P2 — Motion & Transitions (next round)
- Page transition: a subtle fade + 8px Y shift, 250ms. Not a full-screen wipe.
- Threshold transition: entering `/terminal/*` triggers a 300ms "descent" — border colors darken slightly, typography shifts, a thin line animates across the top.
- Live data updates: numbers should **count** or **cross-fade**, not snap. A spot price updating should feel like a heartbeat, not a glitch.
- Strategy cards: on hover, the confidence bar should animate to full width and back (a "breath"), indicating interactivity without screaming it.

### P3 — Terminal Depth (future)
- Command palette (`Cmd+K`) polish: visual feedback on selection, category grouping.
- Substack integration: embed the latest memo with a "read on Substack" threshold link — the transition out to Substack should feel like opening a window, not leaving the building.
- Pair-specific pages (`/terminal/fx-regime/[pair]`): regime history sparklines, signal decomposition visualizations.

---

## 9. Final Notes for the Team

This is a **research platform with a point of view.** The point of view is: *macro forecasting should be transparent, validated, and beautiful in the way a proof is beautiful — not in the way an advertisement is beautiful.*

Every design decision is a signal to the user about the rigor of the work inside. If the interface is sloppy, the user will assume the models are sloppy. If the interface is precise, warm, and quietly confident, the user will assume the same of the research.

We are not designing for everyone. We are designing for the person who wakes up at 5 AM to read the CFTC report. Make them feel at home.

---

*Document owner: Creative Director*  
*Next review: After P1 coherence pass completion*
