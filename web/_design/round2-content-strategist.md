# FX Regime Lab — Content Strategy Document

**Version:** Round 2  
**Date:** 2026-05-05  
**Author:** Lead Content Strategist  
**Status:** Design handoff ready  

---

## 0. Executive Summary

This document defines every word, label, and narrative pattern for FX Regime Lab. The brand voice is **"precision under pressure"** — rigorous, warm, terminal-native, quietly confident, alive. We are "Bernstein for the open web."

**The golden rule:** If a line of copy would feel out of place in a research note from a top-tier macro hedge fund, delete it.

**What we are NOT:** A SaaS product, a fintech startup, a newsletter factory, or a guru blog. We are a living research ledger. The copy must reflect that.

---

## 1. Content Pillars

### Pillar 1: PERFORMANCE AS PROOF
*"Show, don't tell. The equity curve is the homepage."*

Everything orbits around one question: **Does this system make correct calls?** Performance data is not a feature — it is the primary content. Every page must reinforce this narrative.

- Homepage: live snapshot + validation stats above the fold
- Performance page: equity curve, hit rates, drawdown honesty
- Terminal: yesterday's validation strip in header
- Brief: Trader's TL;DR with confidence and invalidation

### Pillar 2: TRANSPARENCY AS TRUST
*"The validation table IS the social proof."*

We do not use testimonials, star ratings, or "trusted by" logos. We use auditable data. Every claim must be inspectable. Every call must link to its provenance.

- Methodology: full math, no black boxes
- Audit trail: timestamped, linkable, immutable
- Validation log: every call, every outcome, every brief
- Drawdowns: shown, not hidden

### Pillar 3: TERMINAL AS CREDENTIAL
*"A student project doesn't have a correlation matrix."*

The terminal is proof of seriousness. It says: *"This operator thinks like a quant."* The copy must feel like a Bloomberg Terminal — telegraphese, dense, purposeful.

- Labels: `CONF 0.62` not `Confidence: 62%`
- Status: `ACTIVE`, `SYNCED`, `STALE`
- Navigation: keyboard shortcuts, command palette, muscle-memory paths

### Pillar 4: DISCIPLINE AS NARRATIVE
*"The story is the repetition."*

The daily rhythm — ingest, composite, classify, publish, validate — is the story. We do not chase virality. We chase consistency. The copy must reflect calendar discipline.

- Daily brief: published before market open, every day
- Validation: next-day, no exceptions
- Memos: deep dives, not hot takes
- Substack: distribution, not content strategy

---

## 2. Page-by-Page Content Spec

### `/` — Homepage

**Primary message:**  
> FX Regime Lab generates daily G10 FX regime calls before market open and validates them publicly the next day.

**Secondary messages:**
- Three pairs. Four signal families. One composite.
- Every call is dated, logged, and auditable.
- The terminal is open. The data is naked.

**Calls to action:**
| Priority | CTA | Destination | Pattern |
|----------|-----|-------------|---------|
| Primary | `Read today's brief` | `/brief` | Filled button, `--color-text` bg |
| Secondary | `Open terminal →` | `/terminal` | Underlined text link |
| Tertiary | `View full ledger →` | `/performance` | Inline link below validation strip |

**Evidence/support:**
- Live snapshot cards (spot + regime + confidence)
- Validation trust strip (calls logged, 7D accuracy, pairs tracked)
- Signal architecture grid (the "how")

**Microcopy tone:**
```
Hero label:    Live · G10 FX · Daily Calls
Hero H1:       Daily regime calls. On the record.
Hero body:     G10 FX regime classification across EUR/USD, USD/JPY, 
               and USD/INR. Composite signal from rate differentials, 
               COT positioning, realized volatility, and open interest. 
               Every call public before market open. Every outcome validated.
Scroll hint:   Scroll
Section label: Live Snapshot
Section title: Today's regime calls
```

**Required additions (P0):**
- Add timestamp to live snapshot cards: `As of 2026-05-05 09:14 UTC`
- Add "Next validation" countdown: `Validates in 4h 23m`
- Move `ValidationTrust` section above `SignalArchitecture`
- Add Substack email capture below validation strip

---

### `/performance` — Track Record

**Primary message:**  
> Here is the complete, unedited record of every call and every outcome.

**Secondary messages:**
- The equity curve shows edge over time — including drawdowns.
- Regime-specific breakdowns show where the system works and where it doesn't.
- Every row links to the brief that generated the call.

**Calls to action:**
| Priority | CTA | Destination |
|----------|-----|-------------|
| Primary | `Download CSV` | API endpoint |
| Secondary | `View brief for this call` | `/brief?date=YYYY-MM-DD` per row |
| Tertiary | `Discuss on Substack` | Substack comment thread |

**Evidence/support:**
- Equity curve (cumulative return, P0)
- 7D / 30D / 90D / All time range selector
- Regime-specific performance table
- Hit rate by horizon (T+1, T+3, T+5)
- Validation log (full table, filterable)
- Per-pair accuracy with progress bars

**Microcopy tone:**
```
Page label:    Track Record
Page H1:       Performance
Subtitle:      Next-day directional validation. Updated daily after market close.

Metrics:
  7D ACCURACY          → 72.4%          (14/19 correct)
  AVG NEXT-DAY RET     → +0.18%         Per call directional
  CUMULATIVE RET       → +4.86%         Since Apr 2026
  CALLS VALIDATED      → 27             3 pairs

Section label: Rolling 7-Day Accuracy
Section label: Validation Log — All Calls
Section label: Regime-Specific Performance
Section label: Hit Rate by Horizon

Table header:  DATE · PAIR · REGIME · OUTCOME · RETURN · BRIEF

Footer:        NEXT-DAY DIRECTIONAL OUTCOME. RETURN % IS NEXT-DAY 
               CLOSE-TO-CLOSE SPOT MOVE IN DIRECTION OF CALL. 
               RESEARCH ONLY — NOT INVESTMENT ADVICE.
```

**Required additions (P0):**
- Equity curve chart (non-negotiable)
- "View brief" link per validation row
- Filter controls: by pair, by regime, by date range
- Regime-specific breakdown table
- Time range selector for equity curve

---

### `/brief` — Daily Brief

**Primary message:**  
> This is what we said before the market opened.

**Secondary messages:**
- The call is timestamped and immutable.
- The TL;DR gives traders what they need in 10 seconds.
- The full brief gives context for the call.

**Calls to action:**
| Priority | CTA | Destination |
|----------|-----|-------------|
| Primary | `Open terminal →` | `/terminal` |
| Secondary | `Discuss on Substack` | Substack post URL |
| Tertiary | `Previous brief / Next brief` | Date pagination |

**Evidence/support:**
- Date stamp + "Morning Brief" label
- Regime snapshot cards for all pairs
- Trader's TL;DR box (NEW, P0)

**Microcopy tone:**
```
Header label:  MORNING BRIEF
Date:          2026-05-05
H1:            Daily Brief — 2026-05-05

TL;DR box (NEW):
  ┌─────────────────────────────────────────┐
  │ TRADER'S TL;DR                          │
  │ EUR/USD: MODERATE USD STRENGTH          │
  │ Confidence: 62%                         │
  │ Primary driver: Rate differentials      │
  │ Invalidation: Spot closes below 1.0780  │
  └─────────────────────────────────────────┘

Regime snapshot label: Regime Snapshot

Empty state:   No brief available for today.
               The pipeline runs at 06:00 UTC. Check back shortly.

Footer:        RESEARCH AND LEARNING ONLY. NOT INVESTMENT ADVICE. 
               ALL CALLS LOGGED PRIOR TO MARKET OPEN. 
               OUTCOMES VALIDATED NEXT TRADING DAY.
```

**Required additions (P0):**
- Trader's TL;DR box at top of brief
- "Discuss on Substack" link
- Previous / Next brief pagination
- Archive navigation (`/memos` link)

---

### `/terminal` — Terminal Overview

**Primary message:**  
> Live cross-pair snapshot. One glance, full context.

**Secondary messages:**
- All three pairs, spot, regime, confidence, day change.
- Active strategy strip with pipeline heartbeat.
- Click any pair to enter the desk.

**Calls to action:**
| Priority | CTA | Destination |
|----------|-----|-------------|
| Primary | Pair card (full click target) | `/terminal/fx-regime/[pair]` |
| Secondary | `FX-REGIME` strategy strip | `/terminal/fx-regime` |

**Evidence/support:**
- Live spot prices with day change %
- Regime labels with confidence bars
- Pipeline timestamp

**Microcopy tone:**
```
Section label: Live Cross-Pair Overview
Pair label:    EUR/USD (in pair color)
Spot:          1.0847
Day change:    +0.12%  (green if >= 0, red if < 0)
Regime:        MODERATE USD STRENGTH
Confidence:    CONF 62% (with bar)

Strategy label: Strategies
Strategy badge: ACTIVE
Strategy name:  FX-REGIME
Strategy CTA:   Open →

Pair desk strip:
  EUR/USD    MODERATE USD STRENGTH    CONF 62%    COMP +0.84
  USD/JPY    NEUTRAL                  CONF 48%    COMP +0.12
  USD/INR    MODERATE DEPRECIATION    CONF 71%    COMP -0.67

Pipeline:      ● Pipeline: 2026-05-05 (green pulse dot)

Placeholder:   MORE STRATEGIES — PHASE 2+
```

---

### `/terminal/fx-regime/[pair]` — Pair Desk

**Primary message:**  
> This pair's full signal decomposition, regime history, and invalidation context.

**Secondary messages:**
- The composite is driven by four families — see the breakdown.
- Regime history shows how we got here.
- Invalidation levels tell you when the call is wrong.

**Calls to action:**
| Priority | CTA | Destination |
|----------|-----|-------------|
| Primary | `Read brief` | `/brief` |
| Secondary | `View performance` | `/performance?pair=EURUSD` |
| Tertiary | `Other desks` (sidebar) | `/terminal/fx-regime/[other]` |

**Evidence/support:**
- Spot price with BinaryResolve animation
- Regime label + confidence bar
- Signal decomposition table (RATE, COT, VOL, OI)
- 7-day regime history
- Invalidation context strip
- TradingView chart embed with regime bands (P1)

**Microcopy tone:**
```
Header:        EUR/USD PAIR DESK
Spot:          1.0847 (BinaryResolve flicker on update)
Regime:        MODERATE USD STRENGTH
Confidence:    CONF 0.62
Composite:     COMP +0.84

Signal table header:
  FAMILY    VALUE    WEIGHT    CONTRIBUTION
  RATE      0.72     ~40%      +0.29
  COT       0.61     ~30%      +0.18
  VOL       0.45     ~20%      +0.09
  OI        0.58     ~10%      +0.06

Invalidation strip:
  WATCH: US 2Y yield
  INVALIDATION: Spot closes below 1.0780
  LAST REGIME SHIFT: 2026-04-28 (7 days ago)

Other desks sidebar:
  OTHER DESKS
  USD/JPY   NEUTRAL              →
  USD/INR   MODERATE DEPREC      →
```

---

### `/methodology` — Signal Architecture

**Primary message:**  
> Here is exactly how the signal is generated. No black boxes.

**Secondary messages:**
- Four families, normalized, weighted, thresholded.
- Confidence is internal consistency, not probability.
- Student mode explains the math in plain English.

**Calls to action:**
| Priority | CTA | Destination |
|----------|-----|-------------|
| Primary | `Toggle: Expert / Student` | In-page toggle (NEW, P1) |
| Secondary | `Download PDF` | `/methodology.pdf` (P2) |

**Evidence/support:**
- Composite score equation (KaTeX)
- Normalization formula
- Regime threshold table
- Confidence derivation formula
- Signal family cards with metadata

**Microcopy tone:**
```
Page label:    Methodology
Page H1:       Signal Architecture
Subtitle:      The math behind the composite score and regime classification.

Student mode (NEW):
  "We combine 4 signals into 1 score. Rate differentials 
   (yield spreads) matter most (~40%). Think of it as: 
   if US yields rise vs Europe, the dollar usually strengthens."

Tooltip example:
  COT Positioning [?]
  → "Commitments of Traders: weekly report showing 
     how speculators are positioned in futures markets."

Section labels:
  Composite Score
  Normalization
  Regime Thresholds
  Confidence Derivation
```

---

### `/about` — Founder + Philosophy

**Primary message:**  
> This is a discretionary macro research system that happens to be public.

**Secondary messages:**
- Not a student project. Not a SaaS. A research ledger.
- Credibility compounds through discipline, not marketing.
- The pipeline is transparent. The validation is public.

**Calls to action:**
| Priority | CTA | Destination |
|----------|-----|-------------|
| Primary | `Today's brief →` | `/brief` |
| Secondary | `Open terminal →` | `/terminal` |
| Tertiary | `Track record →` | `/performance` |

**Evidence/support:**
- "This is / This is not" grid
- Pipeline stage overview
- Validation stats
- Substack subscriber count (if available)

**Microcopy tone:**
```
Page H1:       A research system. Public by design.
Name:          Shreyash Sakhare
Title:         EE Undergrad · Discretionary Macro Research

Bio:           EE undergrad. Studying how G10 FX regimes form and break 
               using rate differentials, COT positioning, and volatility. 
               This is not a learning journal or a student project in 
               disguise. It is a discretionary macro research system 
               that happens to be public.

This is:
  + Daily regime calls for G10 pairs
  + Public validation trail
  + Composite signal from 4 families
  + Morning brief before market open
  + Terminal for dense monitoring

This is not:
  — A SaaS or subscription product
  — Investment advice
  — An automated trading system
  — Generic macro commentary
```

---

### `/terminal/memos` — Research Memo Archive

**Primary message:**  
> The full research corpus. Every brief, every deep dive, every note.

**Secondary messages:**
- Browse by date, pair, or regime.
- Cross-linked to terminal desks and validation log.
- Originally published on Substack — discuss there.

**Calls to action:**
| Priority | CTA | Destination |
|----------|-----|-------------|
| Primary | `Read on Substack` | Substack post URL |
| Secondary | `View in terminal` | Relevant pair desk |

**Microcopy tone:**
```
Page label:    Research
Page H1:       Memo Archive
Subtitle:      All briefs and research notes. Reverse chronological.

List item:
  2026-05-05    Daily Brief — EUR/USD shifts to MODERATE USD STRENGTH
  2026-05-04    Daily Brief — Neutral bias holds across G10
  2026-05-03    Deep Dive: Why rate differentials dominate in Q2

Month divider: APRIL 2026
Empty state:   No memos found for this filter.
```

---

## 3. Copy Framework

### 3.1 Section Labels

Section labels are **monospace, uppercase, tracked out, 9–10px**. They are the "room signs" of the interface.

```
✓ LIVE SNAPSHOT
✓ SIGNAL ARCHITECTURE
✓ VALIDATION
✓ TRACK RECORD
✓ MORNING BRIEF
✓ REGIME SNAPSHOT
✓ TRADER'S TL;DR
✓ METHODOLOGY
✓ RESEARCH

✗ Live Snapshot
✗ Signal Architecture
✗ Today's Calls
```

### 3.2 Button Text Patterns

| Pattern | Use | Example |
|---------|-----|---------|
| Action + destination | Primary CTA | `Read today's brief` |
| Action + arrow | Secondary CTA | `Open terminal →` |
| Destination + arrow | Tertiary link | `Track record →` |
| Noun phrase + arrow | Navigation | `Full ledger →` |
| Verb + object | Form submit | `Download CSV` |

**Rules:**
- No "Get started" — this is not onboarding.
- No "Learn more" — every link tells you where it goes.
- No "Discover" — the user discovers; we present.

### 3.3 Empty States

Empty states must be **honest, not apologetic**. They explain *why* something is empty and *when* it will not be.

```
No brief available for today.
The pipeline runs at 06:00 UTC. Check back shortly.

No calls yet for this pair.
Validation begins after the first trading day.

No memos found for this filter.
Try broadening your date range or clearing pair filters.

No data for the selected period.
The strategy began tracking on 2026-04-01.
```

### 3.4 Error States

Error states must be **calm and specific**. No alarms. No exclamation marks. State what failed, what it means, and what to do.

```
Data stale.
Last successful sync: 2026-05-04 18:32 UTC.
The pipeline will retry automatically.

Failed to load validation log.
Refresh the page or check the audit trail for system status.

Brief not found.
The requested date (2026-04-15) has no logged brief.
Browse the archive for available dates.

Terminal connection interrupted.
Displaying last known state. Reconnecting...
```

### 3.5 Loading States

No spinners. Use **skeleton screens** that match final layout dimensions. Terminal uses "pending" language.

```
Skeleton:      [████░░░░░░]  (block matching final text width)

Terminal:      SYNCING...
               INGESTING DATA...
               COMPUTING COMPOSITE...

Brief:         Loading today's brief...
               (skeleton paragraphs)

Performance:   Loading validation log...
               (skeleton table rows)
```

### 3.6 Timestamp Formats

| Context | Format | Example |
|---------|--------|---------|
| Brief date | `YYYY-MM-DD` | `2026-05-05` |
| Brief header | `YYYY-MM-DD` inline | `MORNING BRIEF · 2026-05-05` |
| Pipeline timestamp | `YYYY-MM-DD HH:MM UTC` | `Ingested 06:14 UTC · Validated 14:32 UTC` |
| Relative time | `Xh Ym` or `X days ago` | `Validates in 4h 23m` · `3 days ago` |
| Validation log | `YYYY-MM-DD` | `2026-05-05` |
| Chart tooltip | `MMM DD, YYYY` | `May 05, 2026` |

---

## 4. Substack Integration Content Plan

### 4.1 Content Ownership Model

```
SUBSTACK (Primary Distribution + Community)
│
├── Daily Brief (cross-posted to /brief)
│   └── Full text mirror on site
│   └── "Discuss on Substack" CTA
│
├── Weekly Deep Dive (cross-posted to /terminal/memos)
│   └── Full text mirror on site
│   └── "Read on Substack" CTA for comments
│
└── Ad-hoc Research Notes
    └── Title + summary on site
    └── Full text on Substack only

MAIN SITE (Canonical Experience + Tool)
│
├── /brief — Today's brief (canonical, from brief_log)
│   └── "Originally published on Substack" + comment link
│
├── /terminal/memos — Research archive (canonical)
│   └── "Read on Substack" + comment CTA
│
└── Homepage — Latest 3 post titles (discovery, not full text)
```

### 4.2 What Lives Where?

| Content Type | Primary Home | Mirror | Rationale |
|-------------|--------------|--------|-----------|
| Daily brief | Main site (`/brief`) | Substack | Traders need it for trading; site is faster |
| Weekly deep dive | Main site (`/terminal/memos`) | Substack | SEO value; long-form belongs in archive |
| Ad-hoc notes | Substack | Title + summary on site | Community engagement lives on Substack |
| Comments / discussion | Substack | Linked from site | Substack owns community |
| Newsletter signup | Substack | Embedded on site | Substack manages deliverability |

### 4.3 Brief Sync Strategy

**Flow:**
1. Brief is written in Substack (author's preferred editor)
2. Substack webhook triggers ingestion to `brief_log` table
3. Site renders from `brief_log` (canonical)
4. Substack post URL stored in `brief_log.substack_url`
5. `/brief` page displays: "Originally published on Substack · Discuss →"

**Failure mode:** If webhook fails, site shows last available brief with stale indicator.

### 4.4 Archive Structure on Main Site

**New page:** `/memos` (reverse-chronological, browseable)

```
MEMO ARCHIVE

May 2026
  2026-05-05  Daily Brief — EUR/USD shifts to MODERATE USD STRENGTH
  2026-05-04  Daily Brief — Neutral bias holds across G10
  2026-05-03  Deep Dive: Why rate differentials dominate in Q2

April 2026
  2026-04-30  Daily Brief — Month-end regime summary
  2026-04-29  Daily Brief — USD/JPY volatility expansion
  ...

Filters: [All pairs] [All regimes] [Daily Brief] [Deep Dive]
```

### 4.5 Newsletter Signup Flow Copy

**Placement:** Homepage (below ValidationTrust), Brief page (below footer), About page (sidebar)

**Copy:**
```
Get the morning brief in your inbox.
One email per trading day. No spam. Unsubscribe anytime.

[Email input          ] [Subscribe]

Footer variant:
FX Regime Lab on Substack — Subscribe for daily briefs
```

**Post-subscribe:**
```
Subscribed. Check your inbox for confirmation.
```

**DO NOT:** Use popups, interstitials, or "unlock premium content" gating. This audience is sophisticated and hates them.

### 4.6 Bidirectional Link Strategy

**From site to Substack:**
- Every `/brief` → "Discuss on Substack" link
- Every `/terminal/memos` entry → "Read on Substack" link
- Footer → "FX Regime Lab on Substack"

**From Substack to site:**
- Every brief → link to `/terminal` for live data
- Every regime mention → link to relevant pair desk
- Every performance claim → link to `/performance`
- Footer → "Live terminal → fxregimelab.com/terminal"

**Auto-linking rule (P1):** When a brief mentions a regime or pair, auto-link to the relevant terminal desk or methodology section. Build a knowledge graph.

---

## 5. Performance Content Strategy

### 5.1 The Trust Equation

For allocators: **Trust = (Transparency × Consistency) / Time**

The performance narrative must optimize all three variables. Do not present performance as a static table. Present it as a **story of discipline**:

1. **The Setup** (Methodology) — "Here's how we generate the signal"
2. **The Call** (Daily Brief + Terminal) — "Here's what we said before market open"
3. **The Validation** (Performance Ledger) — "Here's what actually happened"
4. **The Audit** (Audit Page) — "You can verify we didn't edit this"

### 5.2 Equity Curve Narrative

The equity curve is **the single most impactful trust signal**. It must tell a story:

```
CUMULATIVE RETURN
+5.2% ┤                              ╭─
+4.0% ┤                    ╭────────╯
+2.5% ┤           ╭───────╯
+1.0% ┤    ╭─────╯
 0.0% ┼────┴────────────────────────────
      Apr    Apr    May    May    May
      01     15     01     15     31

Time range: [7D] [30D] [90D] [All]
```

**Copy around the curve:**
```
Chart label:   Cumulative Return of Directional Calls
Benchmark:     Flat line at zero (no edge)
Annotation:    "Drawdown: -1.2% (Apr 12–14). System held NEUTRAL 
               across all pairs during NFP volatility."
```

### 5.3 Regime-Specific Stories

Some regimes are easier to predict than others. **Show this honestly.**

```
REGIME-SPECIFIC PERFORMANCE

Regime                    Calls   Hit Rate   Avg Return   Max DD
─────────────────────────────────────────────────────────────────
STRONG USD STRENGTH       4       75.0%      +0.34%       -0.12%
MODERATE USD STRENGTH     11      72.7%      +0.21%       -0.18%
NEUTRAL                   8       50.0%      +0.02%       -0.08%
MODERATE USD WEAKNESS     3       66.7%      +0.15%       -0.22%
VOL_EXPANDING             1       —          —            —

Note: NEUTRAL regimes have lower hit rates by design — 
directional calls are inherently harder when the composite 
sits near zero. This is expected and honest.
```

### 5.4 Drawdown Honesty

**Never hide losses.** Hiding losses destroys credibility faster than admitting them.

```
CURRENT DRAWDOWN: -0.8% from peak (Apr 28)
PEAK-TO-TROUGH:   -1.2% (Apr 12–14)
RECOVERY:         3 trading days
CONTEXT:          All three pairs held NEUTRAL during 
                  NFP week. No directional exposure.
```

### 5.5 Validation Log as Story

The validation log is not "our record" — it is **"your audit."** The user is the buy-side client. The site is the analyst.

```
Table header:  YOUR AUDIT — ALL CALLS

Row example:
  DATE       PAIR      REGIME                  OUTCOME    RETURN   
  2026-05-05 EUR/USD   MODERATE USD STRENGTH   —          —        [Brief]
  2026-05-04 EUR/USD   MODERATE USD STRENGTH   ✓ Correct  +0.18%   [Brief]
  2026-05-03 EUR/USD   NEUTRAL                 ✗ Wrong    -0.05%   [Brief]

Filter:       [All pairs] [EUR/USD] [USD/JPY] [USD/INR]
              [All regimes] [All outcomes] [Date range]
```

---

## 6. Terminal Content Strategy

### 6.1 Information Density Model

The terminal serves **two audiences simultaneously**. The content must support both without cluttering either.

```
┌─────────────────────────────────────────┐
│ DENSITY SPECTRUM                        │
├─────────────────────────────────────────┤
│ TL;DR        → Marcus (trader)          │
│              → 10 seconds, 4 data points │
├─────────────────────────────────────────┤
│ Signal Breakdown → Priya (allocator)    │
│              → 90 seconds, full context  │
├─────────────────────────────────────────┤
│ Full Audit   → Diego (student)          │
│              → Unlimited, every detail   │
└─────────────────────────────────────────┘
```

### 6.2 TL;DR Format for Traders

```
┌─────────────────────────────────────────┐
│ TRADER'S TL;DR — EUR/USD                │
├─────────────────────────────────────────┤
│ REGIME:      MODERATE USD STRENGTH      │
│ CONFIDENCE:  62%                        │
│ DRIVER:      Rate differentials (+0.29) │
│ INVALIDATION: Spot < 1.0780             │
│ LAST SHIFT:  2026-04-28 (7 days)        │
└─────────────────────────────────────────┘
```

**Rules:**
- Exactly 5 lines. No scrolling.
- Driver shows the largest contributor.
- Invalidation is a specific level or event.
- "Last shift" gives regime duration context.

### 6.3 Full Signal Breakdown for Researchers

```
SIGNAL DECOMPOSITION — EUR/USD

FAMILY          RAW      PCTILE   WEIGHT    CONTRIBUTION    TREND
─────────────────────────────────────────────────────────────────
RATE DIFF       0.84     P72      ~40%      +0.29           ↗
COT POSITION    0.61     P61      ~30%      +0.18           →
REALIZED VOL    0.45     P45      ~20%      +0.09           ↘
OI / RISK REV   0.58     P58      ~10%      +0.06           →
─────────────────────────────────────────────────────────────────
COMPOSITE                          +0.84   → MODERATE STR

CONFIDENCE: 62% (distance to boundary: 0.36, signal dispersion: low)
```

### 6.4 Invalidation Context

Invalidation must be **specific and actionable**:

```
INVALIDATION CONTEXT

Technical:    Spot closes below 1.0780 (previous regime low)
Macro:        US 2Y yield drops below 3.85% (rate driver fade)
Event:        ECB rate decision (May 15) — watch for dovish shift
Duration:     Regime has persisted 7 days. Average: 5.2 days.
              Extended regimes face mean-reversion pressure.
```

### 6.5 Confidence Explanation

Confidence is the most misunderstood metric. The copy must clarify:

```
CONFIDENCE: 62%

What this means:
  The composite sits 0.36 units above the NEUTRAL boundary.
  Signal families agree (low dispersion).
  This is NOT the probability of being correct. It is the 
  system's internal consistency metric.

How it changes:
  ↑ If rate differentials strengthen and vol compresses
  ↓ If COT and OI send conflicting signals
  → If composite drifts toward boundary
```

---

## 7. SEO & Meta Content

### 7.1 Title Patterns

```
Homepage:       FX Regime Lab | Daily G10 FX Regime Calls, Validated
Brief:          Daily Brief — 2026-05-05 | FX Regime Lab
Performance:    Track Record | FX Regime Lab
Methodology:    Signal Architecture | FX Regime Lab
Terminal:       Terminal | FX Regime Lab
Pair desk:      EUR/USD Pair Desk | FX Regime Lab
About:          About | FX Regime Lab
Memo:           Deep Dive: [Title] | FX Regime Lab
Memos archive:  Research Memo Archive | FX Regime Lab
```

**Rules:**
- Site name suffixes every title after a pipe.
- Date in brief title for SEO freshness.
- Pair names in pair desk titles for searchability.

### 7.2 Description Patterns

```
Homepage:
  Daily G10 FX regime classification for EUR/USD, USD/JPY, and 
  USD/INR. Composite signal from rate differentials, COT positioning, 
  realized volatility, and open interest. Every call published before 
  market open. Every outcome validated publicly.

Performance:
  Complete validation log for FX Regime Lab's daily directional calls. 
  27 calls logged since April 2026. Next-day close-to-close validation. 
  No ex-post edits. Download CSV.

Brief:
  Morning brief for 2026-05-05: EUR/USD MODERATE USD STRENGTH (62%), 
  USD/JPY NEUTRAL (48%), USD/INR MODERATE DEPRECIATION (71%). 
  Published before market open.

Methodology:
  The complete signal architecture behind FX Regime Lab's regime 
  classification system. Four normalized signal families, weighted 
  composite, threshold mapping, and confidence derivation. Full math.
```

### 7.3 OG Image Strategy

**Dynamic OG images for:**
- `/brief` — Daily regime snapshot card (pair + regime + confidence + date)
- `/terminal/fx-regime/[pair]` — Pair desk snapshot (spot + regime + day change)
- `/performance` — Performance summary card (accuracy + cumulative return + calls)

**Static OG image for:**
- Homepage, About, Methodology, Memos

**OG image copy patterns:**
```
Brief OG:
  FX REGIME LAB — MORNING BRIEF
  2026-05-05
  EUR/USD · MODERATE USD STRENGTH · CONF 62%

Performance OG:
  FX REGIME LAB — TRACK RECORD
  72.4% 7D ACCURACY · +4.86% CUMULATIVE · 27 CALLS

Pair OG:
  EUR/USD PAIR DESK
  1.0847 · MODERATE USD STRENGTH · CONF 62%
```

---

## 8. Content Governance

### 8.1 Roles & Responsibilities

| Role | Owner | Updates | Frequency | Approval |
|------|-------|---------|-----------|----------|
| Daily Brief | Shreyash | Substack → auto-ingest | Daily (pre-market) | None (single author) |
| Terminal Data | Pipeline | Supabase tables | Real-time | Automated |
| Validation Log | Pipeline | `strategy_ledger` table | Daily (post-close) | Automated |
| Performance Page | Frontend | Equity curve, metrics | On page load | Data-driven |
| Methodology | Shreyash | Text, equations, examples | As needed | None |
| About | Shreyash | Bio, pipeline description | Quarterly | None |
| Memos Archive | Auto | From `brief_log` + `research_memos` | Daily | None |
| SEO / Meta | Frontend | Title, description, OG | On deploy | Design lead |

### 8.2 Update Cadence

```
DAILY (automated)
  ├── 06:00 UTC — Pipeline ingests data, generates composite
  ├── 06:30 UTC — Brief published, regime calls live
  ├── 14:30 UTC — Market close, outcome data available
  ├── 15:00 UTC — Validation log updated with T+1 outcomes
  └── 15:05 UTC — Performance metrics recalculated

WEEKLY (manual)
  ├── Monday — Review previous week's validation accuracy
  └── Friday — Weekly deep dive memo (if applicable)

MONTHLY (manual)
  ├── Regime-specific performance review
  ├── Signal weight calibration check
  └── Substack subscriber analytics review

QUARTERLY (manual)
  ├── Methodology review and updates
  ├── "Regime Outlook" long-form report
  └── Performance narrative refresh
```

### 8.3 Quality Checklist

Before any content goes live:

- [ ] Does it answer "What is the call?" or "Why should I believe it?"
- [ ] Are all numbers tabular-nums with consistent decimal places?
- [ ] Are all timestamps in UTC?
- [ ] Does every claim have a drill-down path?
- [ ] Are drawdowns shown, not hidden?
- [ ] Is the tone precise, not hype-driven?
- [ ] Are there no exclamation marks?
- [ ] Does the copy pass the hedge fund research note test?
- [ ] Are all links functional (no 404s to briefs)?
- [ ] Is the Substack cross-link present?

### 8.4 Content Migration Plan

**From static to live (P0):**
1. Replace hardcoded homepage stats with live API data
2. Replace hardcoded transition matrix with computed data
3. Link validation rows to archived briefs
4. Add stale-data indicators when API is down

**From isolated to integrated (P1):**
1. Bidirectional linking between briefs and terminal desks
2. Substack comment CTAs on all briefs
3. Performance widget in terminal header
4. Memo archive with full browseability

---

## 9. Quick Reference: Voice & Tone

### The Voice Test

> If a line of copy would feel out of place in a research note from a top-tier macro hedge fund, delete it.

### We Are / We Are Not

| We ARE | We are NOT |
|--------|-----------|
| Precise and direct | Cute or conversational |
| Confident but never arrogant | Hype-driven |
| Warm but formal | Cold or robotic |
| Data-first, narrative-second | Storytelling for engagement |
| Transparent about uncertainty | Overpromising |
| Disciplined and repetitive | Chasing trends |

### Punctuation Rules

- No exclamation marks. Ever.
- Periods end every sentence, even in labels.
- Em-dashes (—) for asides, not parentheses.
- Monospace for all data, labels, and timestamps.
- Sans-serif for narrative body.
- Serif (Cormorant) for editorial moments only.

### Number Rules

- Tabular nums always.
- Percentages to one decimal place.
- Spot prices: 4 decimals for EUR/USD, 2 for USD/JPY, 2 for USD/INR.
- No rounding theater ("~72%" not "almost three-quarters").
- Negative numbers: prefix with `−` (minus sign), not hyphen.

---

## 10. Appendix: Copy Examples by Component

### Hero Manifesto (Homepage)
```
Live · G10 FX · Daily Calls

Daily regime calls. On the record.

G10 FX regime classification across EUR/USD, USD/JPY, and USD/INR. 
Composite signal from rate differentials, COT positioning, realized 
volatility, and open interest. Every call public before market open. 
Every outcome validated.

[Read today's brief]  [Open terminal →]
```

### Validation Trust Strip
```
Validation
Every call validated. No ex-post edits.

3          27         72.4%      4
Pairs      Calls      7-day      Signal
Tracked    Logged     Accuracy   Families

Outcomes measured against next-day spot with a 5bps dead-band. 
Brier scores computed for directional calls.

[View full ledger →]
```

### Performance Metrics
```
Track Record
Performance

Next-day directional validation. Updated daily after market close.

72.4%      +0.18%     +4.86%     27
7D ACC     AVG RET    CUM RET    CALLS
           NEXT-DAY              VALIDATED
```

### Terminal Pair Desk
```
EUR/USD PAIR DESK

1.0847                    MODERATE USD STRENGTH
Spot                      Regime

CONF 0.62                 COMP +0.84
Confidence                Composite

SIGNAL DECOMPOSITION
FAMILY    VALUE    WEIGHT    CONTRIBUTION
RATE      0.72     ~40%      +0.29
COT       0.61     ~30%      +0.18
VOL       0.45     ~20%      +0.09
OI        0.58     ~10%      +0.06

WATCH: US 2Y yield
INVALIDATION: Spot closes below 1.0780
```

### Footer (Global)
```
FX Regime Lab
Daily G10 FX regime research. Every call logged. Every outcome 
public. No narrative added after the fact.

Research          Info
Daily Brief       About
Methodology       Performance
Terminal

Research and learning only. Not investment advice.
Shreyash Sakhare — Discretionary Macro Research
```

---

*Document status: Final. Ready for design and engineering handoff.*
