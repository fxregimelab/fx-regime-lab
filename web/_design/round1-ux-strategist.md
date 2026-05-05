# FX Regime Lab — UX Strategy Document

**Version:** Round 1  
**Date:** 2026-05-05  
**Scope:** Next.js 15 App | 18 Pages | Obsidian Stone Dark Theme  
**Author:** Lead UX Strategist  

---

## 0. Executive Summary

FX Regime Lab is a discretionary macro research platform with a defensible core: **daily regime calls published before market open, validated next-day, publicly auditable.** The site currently operates in two modes — a marketing shell (Home, About, Brief, Methodology, Performance) and a dense terminal interface (Terminal, FX-Regime Mosaic, Pair Desks, Calendar, Memos). 

**The primary strategic tension:** The terminal is visually arresting and technically impressive, but the *performance narrative* — the proof that this system works — is under-indexed. Users land on a beautiful homepage, but they have no immediate path to answering the only question that matters: *"Does this thing actually make correct calls?"*

**Our mandate:** Elevate **strategy performance** to the primary focus. Make the terminal feel like a Bloomberg Terminal crossed with a quant research desk. Keep it cool, keep it professional, never dull.

---

## 1. User Personas

### Persona A: "The Verifying Allocator" — Priya, 38
**Role:** Emerging markets allocator at a $400M family office  
**Goal:** Evaluate whether FX Regime Lab's calls have edge before allocating research budget or personal capital  
**Pain Points:**
- Cannot easily distinguish signal from noise in macro research
- Has been burned by "gurus" who backfit narratives
- Needs *auditable* track record, not marketing claims
- Time-constrained; wants the answer in < 90 seconds

**What they want from the site:**
1. A single screen that screams "this is real" — cumulative P&L, hit rate, max drawdown
2. Ability to verify that calls were made *before* the move (timestamp audit)
3. Understanding of *how* the signal is generated (methodology transparency)
4. No paywalls, no "contact us for performance" — the data must be naked

**Device:** Desktop (primary), iPad Pro (secondary)  
**Frequency:** Visits 2-3x/week, deeply when considering a new research vendor

---

### Persona B: "The Active Trader" — Marcus, 31
**Role:** FX trader at a prop desk; trades EUR/USD and USD/JPY intraday  
**Goal:** Use regime calls as a directional bias filter for his own trade construction  
**Pain Points:**
- Current free macro research is too vague ("cautiously constructive")
- Needs specific regime labels with confidence intervals
- Wants to know *why* the system is calling what it's calling
- Frustrated by research that disappears after a bad run

**What they want from the site:**
1. Today's call for his pairs — immediately, above the fold
2. The composite breakdown (which signal family is driving the call)
3. Historical regime transitions for context ("how long do USD strength regimes last?")
4. Calendar of macro events that could invalidate the call
5. Terminal access that feels like a real tool, not a blog

**Device:** Desktop (3 monitors), iPhone (checking pre-market)  
**Frequency:** Daily, often during market hours

---

### Persona C: "The Learning Student" — Diego, 22
**Role:** Final-year finance student in Mumbai; wants to learn FX macro  
**Goal:** Understand how discretionary macro research actually works by studying a live, validated system  
**Pain Points:**
- Textbooks teach theory; this is live application
- Intimidated by dense terminal interfaces
- Wants to trace a call from signal → classification → validation → outcome
- Needs explanations of terms (COT, risk reversals, percentile ranks)

**What they want from the site:**
1. A "beginner mode" that explains jargon inline
2. The ability to replay historical calls day-by-day
3. Clear methodology that bridges textbook theory to live practice
4. Sense of community / newsletter to learn alongside others

**Device:** Laptop (primary), Phone (commute reading)  
**Frequency:** Weekly deep dives, newsletter reader

---

## 2. User Journey Maps

### Journey A: The Verifying Allocator (Priya)

| Stage | Touchpoint | Emotional State | Friction | Opportunity |
|-------|-----------|-----------------|----------|-------------|
| **Discovery** | LinkedIn post or word-of-mouth | Skeptical | "Another macro research site" | Homepage hero must lead with performance, not philosophy |
| **First Visit** | Lands on `/` | Curious but guarded | Scrolls through philosophy before seeing proof | **Move ValidationTrust section to immediately below hero** |
| **Vetting** | Clicks to `/performance` | Analytical | Sees accuracy % but not cumulative return curve | Add equity curve chart. Add "verify this call" deep links to daily entries |
| **Deep Dive** | Checks `/methodology` | Evaluative | Math is present but not contextualized | Add "Why this matters" callouts next to each equation |
| **Trust Test** | Clicks specific date in validation log | Suspicious | Wants to verify call was pre-market | Add timestamp metadata + link to archived brief for that date |
| **Conversion** | Bookmark site / share with PM | Convinced | — | Make shareable performance cards (OG images with stats) |
| **Ongoing** | Returns weekly for updates | Satisfied | Has to navigate to performance each time | **Add performance widget to terminal overview** |

### Journey B: The Active Trader (Marcus)

| Stage | Touchpoint | Emotional State | Friction | Opportunity |
|-------|-----------|-----------------|----------|-------------|
| **Discovery** | Colleague mentions "this public regime tracker" | Interested | — | — |
| **Daily Habit** | Opens `/terminal` pre-market | Expectant | Terminal loads with overview; needs one more click to see pair detail | **Default terminal to the FX-Regime mosaic or make pair detail immediately accessible** |
| **Decision Support** | Reads today's brief | Urgent | Brief is prose-heavy; wants signal snapshot at top | Add "Trader's TL;DR" box at top of brief: regime + confidence + primary driver + invalidation level |
| **Execution** | Checks pair desk for EUR/USD | Focused | Signal chips are good but lack actionable levels | Add invalidation price / key technical level if available |
| **Validation** | Reviews yesterday's outcome | Accountability-minded | Has to go to performance page; not in terminal | **Add yesterday's validation strip to terminal header** |
| **Ongoing** | Uses as bias filter | Dependent | Wants alerts when regime changes | Phase 2: Webhook / email alerts for regime shifts |

### Journey C: The Learning Student (Diego)

| Stage | Touchpoint | Emotional State | Friction | Opportunity |
|-------|-----------|-----------------|----------|-------------|
| **Discovery** | Finds via search: "how does FX regime classification work" | Excited | — | SEO on methodology page should be strong |
| **First Visit** | Reads `/methodology` | Curious | Equations are intimidating without context | Add expandable "Plain English" annotations |
| **Exploration** | Plays with `/terminal` | Overwhelmed | Too much data, no guide | Add a "Guided Tour" tooltip walkthrough (first visit only) |
| **Learning** | Replays a historical call | Engaged | No clear way to see "what happened next" | **Add a "Replay Mode" on pair desk: date picker + call + next-day outcome** |
| **Community** | Reads Substack | Connected | Wants to ask questions | Add comment engagement on Substack; link prominently |
| **Ongoing** | Weekly newsletter reader | Loyal | Wants to share with classmates | Make referral-friendly: "Share this week's call" cards |

---

## 3. Content Strategy

### Primary Goal Hierarchy

The site has ONE primary goal: **demonstrate that the regime classification system has predictive edge.** Everything else serves this.

```
PRIMARY GOAL
└── "This system makes correct calls, publicly, consistently"
    ├── PROOF LAYER (must be visible in < 3 seconds)
    │   ├── Live today's call (regime + confidence + timestamp)
    │   ├── Cumulative accuracy / hit rate
    │   ├── Number of validated calls (social proof via volume)
    │   └── Equity curve (visual proof of edge)
    ├── TRANSPARENCY LAYER (must be reachable in 1 click)
    │   ├── Full validation log (every call, every outcome)
    │   ├── Methodology (how it works, no black boxes)
    │   ├── Signal decomposition (what's driving today's call)
    │   └── Audit trail (chat.md, pipeline integrity)
    └── CONTEXT LAYER (for engaged users)
        ├── Historical regime transitions
        ├── Macro calendar
        ├── Research memos / deep dives
        └── Newsletter / Substack
```

### Content Pillar: Performance as Narrative

Do not present performance as a static table. Present it as a **story of discipline:**

1. **The Setup** (Methodology) — "Here's how we generate the signal"
2. **The Call** (Daily Brief + Terminal) — "Here's what we said before market open"
3. **The Validation** (Performance Ledger) — "Here's what actually happened"
4. **The Audit** (Audit Page) — "You can verify we didn't edit this"

This narrative arc should be visually explicit. Consider a horizontal timeline component on the homepage that shows: *Yesterday's Call → Current Regime → Next Validation*.

### Content Pillar: Terminal as Credential

The terminal is not just a tool — it is **proof of seriousness.** A student project doesn't have a correlation matrix. A marketing site doesn't have a systemic cluster banner. The terminal says: *"This operator thinks like a quant."*

- Terminal access should be **prominent** in navigation
- Terminal should be **demo-ready** without login (all public data)
- Terminal visuals should be **shareable** (OG images for each pair desk)

---

## 4. Information Architecture Recommendations

### Current State Audit

The site has 18 routes but redundancy and unclear hierarchy:

| Route | Purpose | Issue |
|-------|---------|-------|
| `/` | Marketing home | Performance too low on page |
| `/about` | Bio + philosophy | Good, but could integrate validation stats |
| `/brief` | Daily brief | Good; needs trader TL;DR |
| `/methodology` | Math + architecture | Excellent; needs plain-English mode |
| `/performance` | Public validation | **Underpowered** — needs equity curve, sharable cards |
| `/terminal` | Terminal overview | Fine; should surface performance summary |
| `/terminal/fx-regime` | 3×3 mosaic | Excellent; the "wow" moment |
| `/terminal/fx-regime/[pair]` | Pair desk | Good; needs replay mode |
| `/terminal/calendar` | Macro calendar | Verify utility; integrate with brief |
| `/terminal/memos` | Research memos | Good for depth; needs discovery |
| `/terminal/performance` | Terminal performance | **Redundant with `/performance`?** Unify or differentiate |
| `/audit` | System integrity log | Niche; keep but don't prioritize |
| `/memo/[date]` | Historical memo | Good for SEO; needs linking |
| `/calendar` | Redirects to terminal | Fine |

### Recommended IA Restructure

```
FX REGIME LAB
├── PUBLIC SHELL (Marketing + Trust)
│   ├── /                    [Home: Performance-first hero]
│   ├── /performance         [Track Record: THE credibility page]
│   ├── /methodology         [Signal Architecture: Transparency]
│   ├── /about               [Founder + Philosophy]
│   └── /brief               [Daily Brief: Today's call]
│
├── TERMINAL (Tool + Daily Use)
│   ├── /terminal            [Overview: Cross-pair snapshot + strategy strip]
│   ├── /terminal/fx-regime  [3×3 Mosaic: G10 Systemic Pulse]
│   ├── /terminal/fx-regime/eurusd  [Pair Desk: EUR/USD]
│   ├── /terminal/fx-regime/usdjpy  [Pair Desk: USD/JPY]
│   ├── /terminal/fx-regime/usdinr  [Pair Desk: USD/INR]
│   ├── /terminal/calendar   [Macro Calendar + Event Risk]
│   ├── /terminal/memos      [Research Memo Archive]
│   └── /terminal/performance [Alpha Ledger: Regime-grouped track record]
│
├── AUDIT (Trust + Transparency)
│   └── /audit               [System Integrity Log]
│
└── CONTENT (Discovery + SEO)
    └── /memo/[date]         [Permalinked research memos]
```

### Essential vs. Nice-to-Have

**Essential (P0):**
- `/` — But restructured with performance above the fold
- `/performance` — The single most important page for allocators
- `/terminal` and `/terminal/fx-regime/[pair]` — The tool traders need
- `/brief` — Daily content that drives repeat visits
- `/methodology` — Required for credibility vetting

**Important (P1):**
- `/about` — Founder credibility matters in this space
- `/terminal/calendar` — Event risk is part of the thesis
- `/terminal/memos` — Deep dives for engaged users
- `/terminal/performance` — Alpha Ledger view (differentiated from public performance)

**Nice-to-Have (P2):**
- `/audit` — Extremely niche; valuable for the deeply skeptical
- `/memo/[date]` — Good for SEO and permalinking; low traffic

---

## 5. Key User Flows

### Flow 1: "Check Today's Call" (Marcus — Daily Habit)

**Current Path:** Home → Terminal → Pair detail (3 clicks)  
**Target Path:** Home → Call visible immediately (0 clicks) OR Terminal → Call visible (1 click)

```
[Entry: Home or /terminal]
    │
    ▼
┌─────────────────────────────────────────┐
│ TODAY'S REGIME CALLS (hero section)     │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│ │ EUR/USD │ │ USD/JPY │ │ USD/INR │    │
│ │ 1.0847  │ │ 147.32  │ │ 83.42   │    │
│ │ MOD STR │ │ NEUTRAL │ │ MOD DEP │    │
│ │ CONF 62%│ │ CONF 48%│ │ CONF 71%│    │
│ └─────────┘ └─────────┘ └─────────┘    │
│         [Open Terminal →]               │
└─────────────────────────────────────────┘
    │
    ▼ (if user clicks a card)
┌─────────────────────────────────────────┐
│ PAIR DESK — EUR/USD                     │
│ Spot · Regime · Confidence · Composite  │
│ Signal chips (RATE, COT, VOL, IV)       │
│ Primary driver + invalidation context   │
│ 7-day regime history + confidence trend │
└─────────────────────────────────────────┘
```

**Key Design Principles:**
- The homepage live snapshot cards are good. **Keep them.** But add a "Last updated" timestamp and a "Next validation" countdown to reinforce the pre-market discipline.
- Each card should be the full click target, not just the "Open terminal" link.
- On the pair desk, add a **"Trader's Context"** strip: "This call is driven by rate differentials. Watch US 2Y yield. Invalidation: spot closes below 1.0780."

---

### Flow 2: "Verify Track Record" (Priya — Vetting)

**Current Path:** Home → Performance → Scroll through table  
**Target Path:** Home → Performance → See equity curve + hit rate + full log in one view

```
[Entry: Home → "View full ledger"]
    │
    ▼
┌─────────────────────────────────────────┐
│ PERFORMANCE — TRACK RECORD              │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ EQUITY CURVE (cumulative return)    │ │  ← NEW
│ │ [line chart showing edge over time] │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│ │7D ACC│ │AVG RET│ │CUM RET│ │CALLS │   │
│ │72.4% │ │+0.18%│ │+4.86%│ │  27  │   │
│ └──────┘ └──────┘ └──────┘ └──────┘   │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ PER-PAIR ACCURACY + HIT RATE        │ │
│ │ EUR/USD: 68%  USD/JPY: 75% ...      │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [Validation Log — full table]           │
│ Date · Pair · Regime · Outcome · Return │
│ [each row links to archived brief]      │
└─────────────────────────────────────────┘
```

**Key Design Principles:**
- **The equity curve is non-negotiable.** A table of numbers doesn't build trust like a chart showing consistent positive drift.
- Each validation row must link to the `/brief` for that date — this is the *audit chain*.
- Add filtering: by pair, by regime, by date range. Let allocators stress-test the data.
- Consider a "Download CSV" button — serious allocators want to run their own analysis.

---

### Flow 3: "Understand Methodology" (Diego — Learning)

**Current Path:** Home → Methodology → Reads math  
**Target Path:** Home → Methodology → Chooses "Student Mode" → Plain English explanations

```
[Entry: Home → Methodology]
    │
    ▼
┌─────────────────────────────────────────┐
│ METHODOLOGY — SIGNAL ARCHITECTURE       │
│                                         │
│ [Toggle: Expert | Student]              │  ← NEW
│                                         │
│ Expert view:                            │
│   S = w_r·R + w_c·C + w_v·V + w_o·O   │
│                                         │
│ Student view (expanded):                │
│   "We combine 4 signals into 1 score.   │
│    Rate differentials (yield spreads)   │
│    matter most (~40%). Think of it as:  │
│    if US yields rise vs Europe, the     │
│    dollar usually strengthens."         │
│                                         │
│ [Signal family cards with weights]      │
│ [Regime threshold table]                │
│ [Confidence derivation with tooltip]    │
└─────────────────────────────────────────┘
```

**Key Design Principles:**
- The current methodology page is excellent for experts. **Do not dilute it.** Add a toggle.
- Use inline tooltips for jargon: "COT Positioning → [?]" expands to "Commitments of Traders: weekly report showing how speculators are positioned."
- Add a "How to read the terminal" section — the 3×3 mosaic is powerful but opaque to newcomers.

---

## 6. Analytics & Performance Focus

### The Trust Equation

For allocators, trust = (Transparency × Consistency) / Time. The site must optimize for all three variables.

### Recommended Performance Visualization Hierarchy

#### Tier 1: The "At a Glance" Strip (Homepage + Terminal)
- **7-day rolling accuracy** — most responsive to recent edge
- **Total validated calls** — volume = seriousness
- **Pairs tracked** — scope signal
- **Average next-day return** — magnitude of edge
- **Last validated date** — freshness signal

*Current implementation is good. Add: sparkline of last 30 days accuracy.*

#### Tier 2: The "Convince Me" Dashboard (`/performance`)
This page needs to be completely rebuilt as a **credibility engine:**

1. **Equity Curve** (NEW — priority P0)
   - Cumulative return of directional calls
   - Benchmark: flat line at zero (no edge)
   - Highlight drawdown periods (honesty builds trust)
   - Time range selector: 7D / 30D / 90D / All

2. **Regime-Specific Performance** (NEW — priority P1)
   - How does the system perform in "MODERATE USD STRENGTH" vs "NEUTRAL"?
   - Some regimes may be harder to predict — show this honestly
   - Table: Regime | Calls | Hit Rate | Avg Return | Max Drawdown

3. **Hit Rate by Horizon** (NEW — priority P1)
   - T+1 (current), T+3, T+5 from strategy_ledger
   - Shows the system is validated at multiple horizons
   - Builds confidence that it's not just next-day noise

4. **Brier Score Trend** (Leverage existing alpha-ledger.tsx)
   - Already implemented in terminal performance
   - Bring to public performance or unify the two pages

5. **Validation Log Table** (Current — keep, enhance)
   - Add filtering by pair, regime, outcome
   - Add "View Brief" link for each row
   - Add "Share" button for individual rows (OG image generation)

#### Tier 3: The "Deep Audit" (`/audit` + terminal performance)
- Alpha Ledger (regime-grouped, multi-horizon)
- System integrity log
- Pipeline heartbeat status

### Data Presentation Principles

| Principle | Application |
|-----------|-------------|
| **Show, don't tell** | Equity curve > "we have edge" |
| **Be honest about drawdowns** | Hiding losses destroys credibility faster than admitting them |
| **Make it inspectable** | Every stat must have a drill-down path |
| **Update automatically** | Manual updates create suspicion; pipeline-driven timestamps build trust |
| **Use monospace for numbers** | Tabular nums, consistent decimal places — precision signals rigor |

---

## 7. Substack Integration Strategy

### Current State
- SubstackFeed component exists
- Newsletter is a key channel for Diego (students) and casual followers
- But the integration is likely a simple embed or RSS feed

### Strategic Role of Substack

Substack serves **three distinct purposes:**
1. **Acquisition channel** — SEO + social discovery for new users
2. **Retention mechanism** — Weekly rhythm keeps the site top-of-mind
3. **Depth layer** — Long-form research that doesn't fit the terminal's density

### Integration Architecture

```
SUBSTACK (Primary Content Origin)
│
├── Daily Brief (cross-posted to /brief)
│   └── Auto-ingest into brief_log table
│
├── Weekly Deep Dive (cross-posted to /terminal/memos)
│   └── Auto-ingest into research_memos table
│
└── Ad-hoc Research Notes
    └── Linked from /terminal/memos, not fully mirrored

MAIN SITE (Canonical Experience)
│
├── /brief — Today's brief (from brief_log)
│   └── "Originally published on Substack" + link to comment
│
├── /terminal/memos — Research archive
│   └── "Read on Substack" + comment CTA
│
└── Homepage — Substack feed widget
    └── Last 3 posts, linking to Substack for full read
```

### Recommended UX Integration

1. **Bidirectional Linking**
   - Every `/brief` page should have a prominent "Discuss on Substack" link
   - Every Substack post should link back to the relevant terminal page

2. **Embed Strategy**
   - Homepage: Show latest 3 Substack post titles + dates (not full text — drive to Substack for engagement)
   - `/about`: "Follow the newsletter" CTA with subscriber count if available

3. **Content Mirroring**
   - Daily brief: Mirror fully on site (users need it for trading)
   - Weekly deep dive: Mirror fully on site (SEO value)
   - Ad-hoc notes: Title + summary on site, full text on Substack

4. **Subscriber Conversion**
   - Add a subtle "Get the brief in your inbox" banner in `/brief` and `/terminal`
   - Do NOT use intrusive popups — this audience is sophisticated and hates them
   - Consider a footer CTA: "Weekly synthesis. No spam. Unsubscribe anytime."

### Substack Widget Placement

| Page | Widget | Purpose |
|------|--------|---------|
| Home | Latest 3 post titles | Discovery |
| `/brief` | "Subscribe for daily briefs" | Conversion |
| `/about` | Subscriber count + subscribe | Social proof |
| `/terminal/memos` | Full memo list + Substack links | Archive |
| Footer (global) | "FX Regime Lab on Substack" | Persistent CTA |

---

## 8. Priority Matrix

### P0 — Launch Blockers (Do Now)

| Feature | Rationale | Effort | Owner |
|---------|-----------|--------|-------|
| **Performance equity curve** | Single most impactful trust signal | Medium | Frontend + Data |
| **Unify `/performance` and `/terminal/performance`** | Currently confusing duplication; decide on differentiation or merge | Low | Design |
| **Trader's TL;DR on `/brief`** | Marcus needs signal, not prose | Low | Frontend |
| **Timestamp + "next validation" on live snapshot cards** | Reinforces pre-market discipline | Low | Frontend |
| **Validation log row → archived brief deep link** | Completes the audit chain | Low | Frontend |

### P1 — High Impact (Next Sprint)

| Feature | Rationale | Effort | Owner |
|---------|-----------|--------|-------|
| **Regime-specific performance breakdown** | Shows where edge exists (and where it doesn't) | Medium | Frontend + Data |
| **Hit rate by horizon (T+1, T+3, T+5)** | Leverages existing strategy_ledger data | Medium | Frontend |
| **Methodology "Student Mode" toggle** | Expands audience to learners | Low | Frontend |
| **Terminal guided tour (first visit)** | Reduces intimidation for new users | Medium | Frontend |
| **Pair desk "Replay Mode" (date picker)** | Powerful learning + audit tool | Medium | Frontend + Data |
| **Shareable performance cards (OG images)** | Organic acquisition via social | Medium | Frontend |
| **Substack integration refinement** | Better bidirectional linking | Low | Frontend |

### P2 — Polish & Depth (Backlog)

| Feature | Rationale | Effort | Owner |
|---------|-----------|--------|-------|
| **Download CSV from performance page** | Serious allocators want raw data | Low | Frontend |
| **Advanced filtering on validation log** | Date range, regime, pair | Medium | Frontend |
| **Macro calendar event risk matrices** | Leverages existing event_risk_matrices table | High | Frontend + Data |
| **Webhook / email alerts for regime shifts** | Retention mechanism for traders | High | Backend |
| **Mobile-optimized terminal view** | Current terminal is desktop-first | High | Frontend |
| **Search across memos + briefs** | Discovery at scale | Medium | Frontend |
| **Multi-language support (Hindi, Japanese)** | USD/INR and USD/JPY audiences | High | Frontend |

---

## 9. Design Principles (Obsidian Stone Evolution)

The current palette is excellent: warm blacks, muted accents, monospace precision. To meet the "cool but professional" mandate:

### Preserve
- **Warm blacks** (`#0c0a09`, `#141210`) — never go pure #000, it feels cheap
- **Monospace for data** — the terminal aesthetic is a core differentiator
- **Restrained color** — pair colors are subtle, not neon
- **Generous whitespace** — the public shell breathes; the terminal is dense by design

### Evolve
- **Motion with purpose** — The GhostResolve and BinaryResolve components are brilliant. Extend this language: numbers should "resolve" on update, not just appear.
- **Performance color coding** — Use the existing up/down semantic colors for validation outcomes (green = correct, red = incorrect) consistently across both public and terminal views.
- **Micro-interactions** — Hover states on validation rows should reveal the archived brief link. Clicking a regime in the transition matrix should filter the validation log.
- **Terminal-public bridge** — The terminal feels like a different product. Add subtle bridges: the validation strip on the homepage should use terminal-style typography; the public performance page should feel like a "report" extracted from the terminal.

### Avoid
- **Dashboard clutter** — More charts ≠ more credibility. Every visual must answer a specific question.
- **Marketing speak** — No "unlock alpha" or "revolutionize your trading." This audience is allergic to it.
- **Modal popups** — Especially for newsletter signup. Use inline CTAs only.
- **Light mode** — The dark theme is a brand asset. Maintain it exclusively.

---

## 10. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Homepage → Performance conversion | > 40% of new sessions | Nav click or scroll depth |
| Terminal daily active users | > 30% of total visitors | `/terminal/*` pageviews |
| Validation log avg. time on page | > 90 seconds | Scroll depth + row interaction |
| Brief → Terminal cross-nav | > 50% | Click-through rate |
| Substack subscriber growth | +15% MoM | Substack analytics |
| Social shares of performance cards | > 10/week | OG image endpoint hits |
| "Student mode" toggle usage | > 20% of methodology visitors | Event tracking |

---

## 11. Appendix: Quick Wins (This Week)

1. **Move ValidationTrust section up on homepage** — It's currently below SignalArchitecture. Swap them.
2. **Add equity curve to `/performance`** — Even a simple sparkline using historical_prices data dramatically upgrades credibility.
3. **Link validation rows to briefs** — Add a `/brief?date=YYYY-MM-DD` route or use existing `/memo/[date]`.
4. **Add "Discuss on Substack" to `/brief`** — One link, immediate engagement lift.
5. **Add timestamp to live snapshot cards** — "As of 2026-05-05 09:14 UTC" in monospace, small.

---

*Document status: Final. Ready for design handoff.*
