# Round 9: Hero Redesign — Creative Brief

**Date:** 2026-05-05  
**Author:** Creative Director  
**Status:** Ready for design handoff  
**Scope:** Homepage hero section only. Full redesign. No iteration.

---

## 1. The Problem

The current hero fails on three counts:

- **It reads like a product pitch, not a research desk.** "Daily regime calls. On the record." could be the tagline for any SaaS analytics tool. It does not announce that a single mind is operating here, making judgments under uncertainty, publishing before the open, and standing by the outcome.
- **It explains too much and declares too little.** Four signal families, three pairs, validation logic — this is methodology copy, not hero copy. The fold is being used to educate when it should be used to *impress*. Education belongs below the fold or on `/methodology`.
- **The dual-CTA layout splits intent.** Two buttons of near-equal visual weight create hesitation. A visitor does not know whether to read or to enter. A research desk does not ask visitors what they want to do. It presents the door.

The user is right: it feels noob and basic. It sounds like it was written by a landing-page template, not by someone who wakes up at 5 AM to read the CFTC report.

---

## 2. The Concept

**The hero is a single, immovable statement of identity: "This is my desk, these are my calls, and the record is open."**

The emotional goal is not conversion. It is **recognition** — the visitor, within two seconds, must understand that they have found a discretionary macro research operation run by one person who publishes on the record, daily, before the market opens. The feeling should be: *I have walked into someone's working space, not clicked on a product.*

---

## 3. The Copy

### H1 (Manifesto)

> **I call regimes before the open. The record is public.**

- Two sentences. First declares the act. Second declares the stakes.
- "I" — singular author. Non-negotiable. This is not a team, not a platform, not a startup.
- "Call regimes" — the core verb. Active, specific, not "analyze" or "track."
- "Before the open" — the time constraint that creates pressure. This is what separates commentary from forecasting.
- "The record is public" — transparency as a challenge, not a feature. It implies courage, not marketing.

### Manifesto Paragraph

> Every morning, I publish a directional view on EUR/USD, USD/JPY, and USD/INR before the first London print. The call is timestamped, the math is open, and the next-day validation is automatic. I am an EE undergrad running a discretionary macro research system that happens to be public — not the other way around.

- **Sentence 1:** The ritual. "Every morning" creates calendar discipline. "Before the first London print" is precise and trader-native. "Directional view" is honest — we are picking sides, not describing weather.
- **Sentence 2:** The three pillars in one breath — timestamped (immutable), math open (transparent), validation automatic (rigorous). No buzzwords. No "AI-powered" or "data-driven."
- **Sentence 3:** The identity twist. "EE undergrad" is credential-adjacent but honest. "Discretionary macro research system that happens to be public" directly quotes the `/about` positioning. "Not the other way around" kills the "student project" assumption before it forms.

### System Status Strip

A single horizontal band below the manifesto, monospace, live-updating. Four data points:

```
LATEST CALL    2026-05-05 06:14 UTC    ·    PAIRS TRACKED    3    ·    CALLS VALIDATED    27    ·    7D ACCURACY    72.4%
```

- **LATEST CALL** — proves recency. Not "last updated." A call is a discrete event.
- **PAIRS TRACKED** — scope. Three is small and focused, not "50+ assets."
- **CALLS VALIDATED** — cumulative proof of discipline. The number grows. It is the ledger.
- **7D ACCURACY** — the only performance number above the fold. Short horizon, recent, honest.

Rules for the strip:
- JetBrains Mono, 11px, uppercase, tracking `0.12em`, color `#78716c`.
- Values in `#f5f5f4`, tabular-nums.
- Separated by centered dots (`·`), not pipes or slashes.
- No labels like "System Status" or "Live Metrics." The data speaks.

### Single CTA

> **Open the terminal**

- One action. One door. No second button, no underline link beside it.
- "Open" is physical — like opening a door, a book, a desk.
- "The terminal" is the product name and the spatial metaphor. It is where the work lives.
- No arrow. No em dash. The button itself is the affordance.

Button spec:
- Background: `#f5f5f4` (text color inverted). Text: `#0c0a09` (void).
- Font: Inter, 14px, weight 500, tracking `0.02em`.
- Padding: 14px 28px. No border-radius (0px).
- Hover: background shifts to `#d6d3d1` (accent), 200ms ease.

---

## 4. Visual Direction

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  [NAV — minimal, 48px height]                                │
│                                                              │
│                                                              │
│  FX REGIME LAB                                               │
│  ────────────────────────────────────────────────────────    │
│                                                              │
│  I call regimes before the open.                             │
│  The record is public.                                       │
│                                                              │
│  Every morning, I publish a directional view on EUR/USD,     │
│  USD/JPY, and USD/INR before the first London print.         │
│  The call is timestamped, the math is open, and the          │
│  next-day validation is automatic. I am an EE undergrad      │
│  running a discretionary macro research system that          │
│  happens to be public — not the other way around.            │
│                                                              │
│  LATEST CALL  2026-05-05 06:14 UTC  ·  PAIRS TRACKED  3  ·   │
│  CALLS VALIDATED  27  ·  7D ACCURACY  72.4%                  │
│                                                              │
│  [ OPEN THE TERMINAL ]                                       │
│                                                              │
│                                                              │
│  ────────────────────────────────────────────────────────    │
│  SCROLL                                                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

- **Vertical rhythm:** The H1 starts at ~20% from the top of the viewport. Not centered. Research desks do not center their mission statements. They pin them to the upper-left quadrant and leave the lower-right empty — room for thought.
- **Horizontal alignment:** Left-aligned to the 1152px container. No centering of any text block.
- **Scroll hint:** A single line of monospace text, 10px, `#78716c`, at the bottom center: `SCROLL`. Not an arrow icon. Not an animated chevron. A word.

### Typography Scale

| Element | Font | Size | Weight | Line Height | Color |
|---------|------|------|--------|-------------|-------|
| Brand mark | JetBrains Mono | 10px | 500 | 1.2 | `#78716c` |
| Rule line | — | 1px | — | — | `#2a2725` |
| H1 (line 1) | Inter | clamp(44px, 5.5vw, 72px) | 600 | 1.05 | `#f5f5f4` |
| H1 (line 2) | Inter | clamp(44px, 5.5vw, 72px) | 600 | 1.05 | `#f5f5f4` |
| Manifesto | Inter | 17px | 400 | 1.6 | `#a8a29e` |
| Status strip | JetBrains Mono | 11px | 400 | 1.4 | `#78716c` values: `#f5f5f4` |
| CTA | Inter | 14px | 500 | 1 | `#0c0a09` on `#f5f5f4` |

- **H1 treatment:** The two lines must break after "open." If viewport forces a rewrap, the break must stay semantic — never split "regimes" from "before," never split "The record" from "is public." Use `&nbsp;` or `white-space: nowrap` on critical pairs.
- **Manifesto max-width:** 560px. This is a narrow column of text, not a full-bleed paragraph. Narrow columns signal editorial confidence.

### Color Usage

- **Background:** Pure void `#0c0a09`. No gradient. No texture. No subtle noise overlay.
- **Rule line:** A single 1px horizontal rule above the H1, color `#2a2725`, width 96px (not full-bleed). This is the only decorative line on the page. It signals: *something serious follows.*
- **No accent color in the text.** The only warm color is the CTA fill. The H1 is `#f5f5f4`, not accent. We do not use `#d6d3d1` for text — it is reserved for interactive states and the CTA hover.
- **No green or red in the status strip.** Accuracy is a number, not a judgment. The 7D accuracy is `#f5f5f4`, not `#7a9e7a`.

### Background Element Ideas (Exploratory)

**Option A: The Void (Recommended)**
Nothing. Pure `#0c0a09`. The absence of visual noise is the statement. This is the Aesop move: the product (the copy) is the interface.

**Option B: Faint Composite Trace**
A single, extremely faint (opacity 0.03–0.05) line chart of the cumulative composite score over the last 90 days, positioned in the lower-right quadrant, behind the text. It is barely visible — a ghost of the work. Color: `#a8a29e`. No axes, no labels, no grid. It must be invisible at first glance and discoverable on second look.

**Option C: Terminal Blink**
A single monospace cursor (`_`) blinking at the end of the status strip, or after the brand mark. Blink rate: 1.2s, opacity 0→1. Color: `#78716c`. This is the only animation on the hero. It says: *the system is live, the operator is present.*

**Decision:** Start with Option A. Add Option C (the blink) if the page feels static after implementation. Reject Option B unless Shreyash specifically requests a visual anchor — the composite trace risks looking like decorative chart junk.

---

## 5. What to Remove

These elements from the current hero must not appear in the new design:

1. **The label "Live · G10 FX · Daily Calls"** — Removed entirely. The brand mark is now `FX REGIME LAB` in monospace above the rule. The old label was a category tag. We do not categorize ourselves.
2. **The body paragraph describing signal families** — Removed entirely. Rate differentials, COT, vol, OI — this lives on `/methodology`. The hero is identity, not explanation.
3. **The secondary CTA "Read today's brief"** — Removed. The brief is accessible from the terminal. The brief is a daily artifact. The terminal is the system. We lead with the system.
4. **Any visual of a chart, card, or data widget in the hero** — Removed. No live snapshot cards above the fold. No sparklines. No regime badges. The hero is text and a single button. The data appears on scroll.
5. **The "Two CTAs" pattern** — Non-negotiable removal. One CTA. One path. No choice architecture.

---

## 6. Personality Check

| Line of Copy | How It Reflects Shreyash's Voice |
|--------------|----------------------------------|
| **"I call regimes before the open."** | First-person singular. Active verb. Time-bound constraint. This is a trader's sentence, not a marketer's. It admits ego without arrogance — "I call" is a claim of authorship, not infallibility. |
| **"The record is public."** | Defiant and transparent. It says: you can check me. This reflects the "transparency as trust" pillar. No hedge fund writes this on their homepage. That is the point. |
| **"Before the first London print."** | Jargon used correctly. "London print" is not performative finance-speak; it is the actual market event that matters for G10 FX. This signals domain fluency. |
| **"EE undergrad running a discretionary macro research system"** | Self-aware credentialing. He does not hide his background, nor does he lean on it. The sentence structure mirrors how a confident but honest researcher introduces themselves at a dinner table. |
| **"That happens to be public — not the other way around."** | The twist. This is the line that kills the "student project" assumption. It reframes publicness as a side effect of rigor, not the purpose of the work. It is warm but firm. |
| **"Open the terminal"** | Physical, direct, unapologetic. Not "Explore our platform." Not "Get started." You open a terminal the way you open a door. |

---

## 7. Implementation Notes

### Responsive Behavior

- **Desktop (>1024px):** Full layout as specified. H1 at max size. Manifesto at 560px width. Status strip on one line.
- **Tablet (768–1024px):** H1 scales down via clamp. Manifesto max-width 480px. Status strip may wrap to two lines after the second dot. CTA remains same size.
- **Mobile (<768px):** H1 breaks naturally but maintains semantic breaks. Manifesto becomes full-width with 16px side padding. Status strip stacks vertically with 8px gaps, no dots. CTA becomes full-width (max 320px). Rule line remains 96px, not full-width.

### Animation Spec

- **Page load sequence:**
  1. Brand mark fades in (opacity 0→1, 300ms, delay 0ms).
  2. Rule line draws from left (scaleX 0→1, 400ms, delay 150ms, transform-origin left).
  3. H1 line 1 fades up (opacity 0→1, translateY 12px→0, 500ms, delay 300ms).
  4. H1 line 2 fades up (same, delay 450ms).
  5. Manifesto fades up (same, delay 600ms).
  6. Status strip fades in (opacity 0→1, 400ms, delay 800ms).
  7. CTA fades up (opacity 0→1, translateY 8px→0, 300ms, delay 950ms).
- **Easing:** `cubic-bezier(0.16, 1, 0.3, 1)` for all.
- **No parallax. No scroll-triggered re-animation.** The hero animates once on load.

### Accessibility

- H1 must be a single `<h1>` with a `<span>` or `<br>` for the line break.
- The status strip should be a `<dl>` or a series of `<span>` with `aria-label` describing each metric for screen readers.
- CTA must have visible focus state: 2px outline offset 2px, color `#d6d3d1`.
- All text meets WCAG 2.1 AA contrast ratios against `#0c0a09`.

---

*This brief is a directive, not a suggestion. The hero is the first and last impression. Make it count.*

*Document owner: Creative Director*  
*Next review: After implementation and user feedback*
