# FX Regime Lab — Information Architecture Document
## Round 2: Lead Information Architect
**Date:** 2026-05-05  
**Status:** Authoritative — governs all subsequent design and development rounds  
**Based on:** Round 1 Synthesis (Creative Director, UX Strategist, Motion Designer, Competitive Analyst)

---

## 0. Design Direction (Inherited)

> **"Bernstein for the open web."**

**Brand essence:** Precision under pressure. Rigorous. Warm. Terminal-native. Quietly confident. Alive.

**Mandate from Round 1:** Elevate **strategy performance** to the primary focus. Make the terminal feel like a Bloomberg Terminal crossed with a quant research desk. Keep it cool, keep it professional, never dull.

**The one hierarchy rule:** The site exists to answer one question: *"Does this system actually make correct calls?"* Every architectural decision must make that answer discoverable in < 3 seconds.

---

## 1. Site Map

### 1.1 Complete Hierarchical Map

```
FX REGIME LAB
│
├── PUBLIC SHELL (Marketing + Trust)
│   ├── /
│   │   └── [Homepage — Performance-first hero + live snapshot + validation trust]
│   ├── /performance
│   │   └── [Track Record — THE credibility page: equity curve, hit rate, ledger]
│   ├── /methodology
│   │   └── [Signal Architecture — Transparency + Expert|Student toggle]
│   ├── /about
│   │   └── [Founder + Philosophy + Pipeline integrity]
│   └── /brief
│       └── [Daily Brief — Today's call with Trader's TL;DR]
│
├── TERMINAL (Tool + Daily Use)
│   ├── /terminal
│   │   └── [Overview — Cross-pair snapshot + strategy strip + performance widget]
│   ├── /terminal/fx-regime
│   │   └── [3×3 Mosaic — G10 Systemic Pulse + regime heatmap]
│   ├── /terminal/fx-regime/[pair]
│   │   ├── eurusd  → [EUR/USD Pair Desk]
│   │   ├── usdjpy  → [USD/JPY Pair Desk]
│   │   └── usdinr  → [USD/INR Pair Desk]
│   ├── /terminal/calendar
│   │   └── [Macro Calendar + Event Risk Matrix]
│   ├── /terminal/memos
│   │   └── [Research Memo Archive — browsable, filterable]
│   └── /terminal/performance
│       └── [Alpha Ledger — Regime-grouped, multi-horizon deep dive]
│
├── AUDIT (Trust + Transparency)
│   └── /audit
│       └── [System Integrity Log — Pipeline heartbeat + chat.md + validation chain]
│
├── CONTENT (Discovery + SEO + Permalinks)
│   ├── /memo/[date]
│   │   └── [Permalinked daily brief / research memo]
│   └── /memos
│       └── [Canonical archive redirect → /terminal/memos]
│
└── API ROUTES (Data + Integrations)
    ├── /api/connect-desk
    │   └── [Pair desk data endpoint — spot, regime, confidence, composite]
    ├── /api/linkedin-alpha-hook
    │   └── [Social sharing OG image generator]
    ├── /api/substack-ingest
    │   └── [Webhook: Substack → brief_log / research_memos]        ← NEW
    ├── /api/validation-export
    │   └── [CSV download of full validation ledger]                ← NEW
    └── /api/regime-snapshot
        └── [JSON: today's calls for external embeds]               ← NEW
```

### 1.2 Route Inventory Table

| Route | Section | Template | Priority | Auth | Notes |
|-------|---------|----------|----------|------|-------|
| `/` | Public Shell | Gateway | P0 | Public | Live data; no hardcoded stats |
| `/performance` | Public Shell | Dashboard | P0 | Public | Equity curve + validation log |
| `/methodology` | Public Shell | Editorial | P0 | Public | Student|Expert toggle |
| `/about` | Public Shell | Gateway | P1 | Public | Newsletter CTA |
| `/brief` | Public Shell | Editorial | P0 | Public | Trader's TL;DR at top |
| `/terminal` | Terminal | Dashboard | P0 | Public | Performance widget embedded |
| `/terminal/fx-regime` | Terminal | Dashboard | P0 | Public | 3×3 mosaic — the "wow" moment |
| `/terminal/fx-regime/[pair]` | Terminal | Desk | P0 | Public | Replay mode + chart embed |
| `/terminal/calendar` | Terminal | Dashboard | P1 | Public | Event risk color-coded |
| `/terminal/memos` | Terminal | Archive | P1 | Public | Substack-bidirectional |
| `/terminal/performance` | Terminal | Dashboard | P1 | Public | Brier scores, T+1/T+3/T+5 |
| `/audit` | Audit | Editorial | P2 | Public | Pipeline provenance |
| `/memo/[date]` | Content | Editorial | P1 | Public | SEO canonical; links to Substack |
| `/memos` | Content | Archive | P1 | Public | 301 → `/terminal/memos` |
| `/api/*` | API | — | P0/P1 | Public | See API section below |

### 1.3 Removed / Consolidated Routes

| Current Route | Disposition | Rationale |
|---------------|-------------|-----------|
| `/calendar` (standalone) | **Remove** | Redirect 301 → `/terminal/calendar`. Redundant with terminal calendar. |
| `/terminal/performance` (as duplicate) | **Redesignate** | Keep route but differentiate from `/performance`. Public `/performance` = allocator narrative. Terminal `/terminal/performance` = quant alpha ledger with Brier, multi-horizon, regime-grouped. |
| `/memo/[date]` (orphaned) | **Integrate** | Keep as canonical permalinks, but surface in `/terminal/memos` archive. Every memo needs a parent. |

---

## 2. Navigation System

### 2.1 Philosophy

Navigation must answer: *"Where am I?"* and *"Where can I go?"* in ≤ 1 second. The terminal is a **place**, not a theme — crossing into `/terminal/*` must feel like a threshold crossing.

### 2.2 Primary Navigation (Global Header)

**Placement:** Fixed top bar, 48px height, `border-bottom: 1px solid var(--color-border)`.

**Composition:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FX REGIME LAB          Performance  Terminal  Methodology  Brief  [About]  │
│  (logo/wordmark)                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Item | Label | Route | Rationale |
|------|-------|-------|-----------|
| Logo | `FX REGIME LAB` | `/` | Wordmark in JetBrains Mono, 11px, UPPER, tracking 0.15em. Always returns home. |
| **Performance** | `PERFORMANCE` | `/performance` | **FIRST** in nav. Answers the primary question immediately. |
| **Terminal** | `TERMINAL` | `/terminal` | **SECOND**. The tool traders need daily. Dropdown on hover reveals sub-items. |
| **Methodology** | `METHODOLOGY` | `/methodology` | **THIRD**. Vetting path for allocators and students. |
| **Brief** | `BRIEF` | `/brief` | **FOURTH**. Today's call. Time-bounded relevance. |
| About | `ABOUT` | `/about` | **FIFTH** (or collapsed into `···` on narrow viewports). Founder credibility. |

**Terminal Dropdown Menu:**
```
TERMINAL ▾
├── Overview          → /terminal
├── FX-Regime Mosaic  → /terminal/fx-regime
├── Pair Desks        → /terminal/fx-regime (with pair submenu)
│   ├── EUR/USD
│   ├── USD/JPY
│   └── USD/INR
├── Calendar          → /terminal/calendar
├── Memos             → /terminal/memos
└── Alpha Ledger      → /terminal/performance
```

**Active State:** Current route gets `color: var(--color-accent)` + 2px bottom border in accent. Terminal routes highlight `TERMINAL` parent when any `/terminal/*` is active.

**Typography:** JetBrains Mono, 10px, UPPER, tracking 0.12em. Labels are scaffolding — they should not compete with data.

### 2.3 Secondary Navigation (Contextual)

**A. Terminal Context Rail (Left Sidebar)**

Already exists as `TerminalContextRail`. Expanded spec:

```
┌──────┬────────────────────────────────────────┐
│  ≡   │  OVERVIEW                              │
│  ◎   │  MOSAIC                                │
│  €   │  EUR/USD                               │
│  ¥   │  USD/JPY                               │
│  ₹   │  USD/INR                               │
│  📅  │  CALENDAR                              │
│  📝  │  MEMOS                                 │
│  α   │  ALPHA LEDGER                          │
└──────┴────────────────────────────────────────┘
Collapsed: 54px    Expanded: 160px
```

- **Persistent** on all `/terminal/*` routes.
- **Collapsible** via hamburger or `Cmd+\` shortcut.
- **Active indicator:** 3px left border in emerald `#7a9e7a`.
- **Keyboard:** `1/2/3` jump to EUR/USD / USD/JPY / USD/INR desks.

**B. Public Shell Sub-Navigation (In-Page Anchors)**

On `/performance`, a sticky sub-nav appears below the hero:

```
EQUITY CURVE  ·  HIT RATE  ·  REGIME BREAKDOWN  ·  VALIDATION LOG  ·  EXPORT
```

Smooth-scrolls to section anchors. Appears after user scrolls past hero. Disappears on mobile (replaced by section headers).

**C. Brief Pagination**

At bottom of `/brief`:
```
← PREVIOUS BRIEF  (2026-05-04)          NEXT BRIEF →  (2026-05-06)
```

### 2.4 Footer Navigation (Global Footer)

**Placement:** Bottom of every page except terminal (terminal uses rail + compact footer).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FX REGIME LAB                                                              │
│  Daily regime calls. On the record.                                         │
│                                                                             │
│  NAVIGATION              TRANSPARENCY           DISTRIBUTION                │
│  ───────────             ───────────            ───────────                 │
│  Performance             Audit                  Substack                    │
│  Terminal                Methodology            LinkedIn                    │
│  Brief                   Validation Log         RSS                         │
│  About                   API Docs                                               │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  © 2026 FX Regime Lab. All calls validated next-day. Data is sacred.        │
│  [Get the brief in your inbox — No spam. Unsubscribe anytime.] [Subscribe]  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Rationale:** Three columns mirror the three user mental models:
- **Navigation** = "I want to go somewhere" (Marcus, daily habit)
- **Transparency** = "I want to verify" (Priya, vetting)
- **Distribution** = "I want to follow" (Diego, community)

**Email capture:** Inline input + button in footer. No modal. No popup. Terminal pages show compact version: just the subscribe strip.

### 2.5 Command Palette Structure (`Cmd+K`)

The command palette is **teleport navigation** — muscle memory for power users.

**Category Groups:**

```
┌────────────────────────────────────────────────────┐
│  > _                                                │
├────────────────────────────────────────────────────┤
│  NAVIGATION                                         │
│  Go to Performance      perf      /performance      │
│  Go to Terminal         term      /terminal         │
│  Go to Methodology      meth      /methodology      │
│  Go to Brief            brief     /brief            │
│  Go to About            about     /about            │
│                                                     │
│  PAIR DESKS                                         │
│  EUR/USD Desk           eurusd    /terminal/...     │
│  USD/JPY Desk           usdjpy    /terminal/...     │
│  USD/INR Desk           usdinr    /terminal/...     │
│                                                     │
│  ACTIONS                                            │
│  Copy today's EUR/USD call          clipboard       │
│  Download validation CSV            download        │
│  Toggle Student Mode                toggle          │
│  Share this page                    share           │
│                                                     │
│  HELP                                               │
│  Keyboard shortcuts         ?                       │
│  Show audit trail           audit                   │
└────────────────────────────────────────────────────┘
```

**Aliases:** `g p` → Performance (Vim-style leader). `g t` → Terminal. `g b` → Brief.
**Selection:** Instant invert to white-on-black. No fade. Terminal UIs do not fade selections.
**Teleport:** 150ms heartbeat pulse → route push.

---

## 3. Page Templates

Five reusable templates govern all 18 routes. Every page must declare its template in code comments.

### 3.1 Gateway Template
**Used by:** `/` (Home), `/about`

**Purpose:** First impression. Trust establishment. Narrative breathing room.

**Structure:**
```
┌─────────────────────────────────────────┐
│ GLOBAL HEADER                           │  48px
├─────────────────────────────────────────┤
│                                         │
│  HERO SECTION                           │  100vh
│  [Manifesto text — large serif]         │
│  [Live snapshot cards — 3 pairs]        │
│  [Scroll indicator]                     │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  VALIDATION TRUST SECTION               │  ~600px
│  [Accuracy strip — 4 metrics]           │
│  [Performance teaser → /performance]    │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  SIGNAL ARCHITECTURE SECTION            │  ~500px
│  [How it works — 3 pillars]             │
│  [→ /methodology]                       │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  SUBSTACK FEED SECTION                  │  ~400px
│  [Latest 3 post titles]                 │
│  [Subscribe CTA]                        │
│                                         │
├─────────────────────────────────────────┤
│ GLOBAL FOOTER                           │
└─────────────────────────────────────────┘
```

**Design rules:**
- Generous whitespace: `py-32` to `py-40` between sections
- Cormorant serif for hero H1 only (the "signature move")
- Scroll-triggered reveals (`useScrollReveal`) on all sections below fold
- No data tables. No terminal density. This is the *surface*.

---

### 3.2 Editorial Template
**Used by:** `/methodology`, `/brief`, `/audit`, `/memo/[date]`

**Purpose:** Long-form reading. Information absorption. Credibility through depth.

**Structure:**
```
┌─────────────────────────────────────────┐
│ GLOBAL HEADER                           │
├─────────────────────────────────────────┤
│                                         │
│  PAGE HEADER                            │
│  [Eyebrow label — MONO, UPPER]          │
│  [H1 — Inter, 28px]                     │
│  [Date / Author / Reading time]         │
│                                         │
├─────────────────────────────────────────┤
│  ┌────────────┐ ┌─────────────────────┐ │
│  │            │ │                     │ │
│  │  STICKY    │ │  MAIN CONTENT       │ │
│  │  TOC /     │ │  [Body text]        │ │
│  │  SIDEBAR   │ │  [Equations]        │ │
│  │            │ │  [Diagrams]         │ │
│  │  240px     │ │  [Pull quotes]      │ │
│  │            │ │                     │ │
│  │            │ │  [CTA / Next page]  │ │
│  │            │ │                     │ │
│  └────────────┘ └─────────────────────┘ │
│                                         │
├─────────────────────────────────────────┤
│ GLOBAL FOOTER                           │
└─────────────────────────────────────────┘
```

**Variants:**
- **Methodology:** Sticky TOC left sidebar. "Expert | Student" toggle top-right. KaTeX equations. Interactive signal-weight cards.
- **Brief:** No TOC. Trader's TL;DR box at top (regime + confidence + driver + invalidation). Body below. "Discuss on Substack" CTA at bottom. Previous/Next pagination.
- **Audit:** No TOC. System integrity log as styled `<pre>` blocks. Pipeline heartbeat status strip at top.
- **Memo/[date]:** Same as Brief but with date in URL. Canonical for SEO. Links back to `/terminal/memos` archive.

**Design rules:**
- Max content width: 680px (reading measure)
- Monospace for inline data references: `EUR/USD 1.0847`
- Body: Inter 15px, line-height 1.65, color `text-primary`
- Labels: JetBrains Mono 9px, UPPER, tracking 0.15em

---

### 3.3 Dashboard Template
**Used by:** `/performance`, `/terminal`, `/terminal/fx-regime`, `/terminal/performance`, `/terminal/calendar`

**Purpose:** Data ingestion. At-a-glance comprehension. Tool-like density.

**Structure:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GLOBAL HEADER (terminal style: thinner border, no background shift)        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PAGE HEADER                                                                │
│  [H1 — Inter 22px + Mono subtitle]                                         │
│  [Last updated: 2026-05-05 06:14 UTC]                                      │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ METRIC STRIP (4–6 cards)                                            │   │
│  │ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │   │
│  │ │ 7D ACC │ │ CUM RET│ │ CALLS  │ │ AVG RET│ │ SHARPE │ │ MAX DD │ │   │
│  │ │ 72.4%  │ │ +4.86% │ │   27   │ │ +0.18% │ │  1.34  │ │ -1.2%  │ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PRIMARY VISUALIZATION (chart / heatmap / mosaic)                    │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ SECONDARY DATA (table / log / calendar grid)                        │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ COMPACT FOOTER (terminal pages only: links + copyright strip)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Variants:**
- **Performance:** Equity curve (large, hero). Metric strip below. Validation log table at bottom. Export CSV button.
- **Terminal Overview:** Cross-pair snapshot cards. Strategy strip. Embedded performance widget (mini). Macro pulse marquee.
- **FX-Regime Mosaic:** 3×3 grid dominates. Pair colors. Regime heatmap. Systemic cluster banner.
- **Terminal Performance (Alpha Ledger):** Brier score trend. Multi-horizon hit rate table (T+1, T+3, T+5). Regime-grouped breakdown.
- **Calendar:** Event risk matrix grid. Date navigation. Impact-level color coding.

**Design rules:**
- Background: `#0c0a09` (void) — no shifts from public shell
- Information density is the product. Whitespace is earned, not given.
- All numbers in JetBrains Mono, tabular-nums, fixed decimal places
- Charts are static on mount — no entrance animation theatre
- Tables: row hover → slight elevation (`#141210` → `#1c1917`). Never stagger rows.

---

### 3.4 Desk Template
**Used by:** `/terminal/fx-regime/[pair]` (EUR/USD, USD/JPY, USD/INR)

**Purpose:** Deep pair analysis. Signal decomposition. Replay mode.

**Structure:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GLOBAL HEADER (terminal style)                                             │
├─────────────────┬───────────────────────────────────────────────────────────┤
│                 │                                                           │
│ CONTEXT RAIL    │  PAIR DESK HEADER                                         │
│                 │  EUR/USD · 1.0847 · MODERATE USD STRENGTH · CONF 0.62    │
│                 │  [Timestamp] [Sync status] [Invalidation banner]         │
│                 │                                                           │
│                 ├───────────────────────────────────────────────────────────┤
│                 │                                                           │
│                 │  TOP STRIP (4 columns)                                    │
│                 │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│                 │  │ SPOT     │ │ REGIME   │ │ CONFIDENCE│ │ COMPOSITE│     │
│                 │  │ 1.0847   │ │ MOD STR  │ │ [████░░] │ │ RATE 0.72│     │
│                 │  │ +0.12%   │ │ 3 days   │ │ 62%      │ │ COT 0.58 │     │
│                 │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
│                 │                                                           │
│                 ├───────────────────────────────────────────────────────────┤
│                 │                                                           │
│                 │  MAIN PANEL (2-column layout)                             │
│                 │  ┌─────────────────────────┐ ┌─────────────────────────┐  │
│                 │  │                         │ │                         │  │
│                 │  │  CHART / SPARKLINE      │ │  SIGNAL DECOMPOSITION   │  │
│                 │  │  [TradingView embed     │ │  ┌────┐ ┌────┐ ┌────┐  │  │
│                 │  │   with regime bands]    │ │  │RATE│ │COT │ │VOL │  │  │
│                 │  │                         │ │  └────┘ └────┘ └────┘  │  │
│                 │  │  [7-day regime history] │ │  [Signal chips]         │  │
│                 │  │                         │ │  [Primary driver text]  │  │
│                 │  │  [Replay mode controls] │ │  [Invalidation level]   │  │
│                 │  │                         │ │                         │  │
│                 │  └─────────────────────────┘ └─────────────────────────┘  │
│                 │                                                           │
│                 ├───────────────────────────────────────────────────────────┤
│                 │                                                           │
│                 │  OTHER DESKS SIDEBAR (right, 200px)                       │
│                 │  ┌─────────────────────────┐                              │
│                 │  │ USD/JPY · NEUTRAL       │                              │
│                 │  │ USD/INR · MOD DEP       │                              │
│                 │  │ [Click to switch]       │                              │
│                 │  └─────────────────────────┘                              │
│                 │                                                           │
├─────────────────┴───────────────────────────────────────────────────────────┤
│ COMPACT FOOTER                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Design rules:**
- Threshold crossing: entering a desk feels like "descending" — border colors deepen, typography shifts to monospace dominance
- Replay mode: date picker overlays chart; shows historical call + next-day outcome
- Signal chips: color-coded by family (Rate = blue-tinted, COT = amber-tinted, Vol = grey-tinted)
- No scroll hijacking. No parallax. Data must be scannable.

---

### 3.5 Archive Template
**Used by:** `/terminal/memos`, `/performance` (validation log section), `/audit`

**Purpose:** Browsable history. Searchable corpus. Audit trail.

**Structure:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GLOBAL HEADER                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PAGE HEADER                                                                │
│  [H1 + record count + filter controls]                                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ FILTER BAR                                                          │   │
│  │ [Search ___] [Pair ▾] [Regime ▾] [Date range ▾] [Sort ▾] [Export]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ITEM LIST / TABLE                                                   │   │
│  │                                                                     │   │
│  │  MAY 2026                                                           │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │ 2026-05-05  EUR/USD  MOD STR  ✓ CORRECT  +0.18%  [View]    │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │ 2026-05-04  USD/JPY  NEUTRAL  ✗ INCORRECT -0.05%  [View]   │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  APRIL 2026                                                         │   │
│  │  ...                                                                │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [Load more] or Pagination                                                │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ FOOTER                                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Variants:**
- **Memos:** Card-based list (not table). Date, title, excerpt, pair tags. Click → `/memo/[date]`.
- **Validation Log:** Table-based. Sortable columns. Filter by pair/regime/outcome. Row click → brief for that date.
- **Audit:** Styled log output. `<pre>` blocks. Collapsible sections. Timestamp-aligned.

**Design rules:**
- Month dividers in Mono, UPPER, muted color — temporal wayfinding
- Row/card hover reveals secondary actions (view, share, link)
- Pagination preferred over infinite scroll (terminal must feel bounded)
- Export/download button in filter bar for data-heavy archives

---

## 4. URL Structure

### 4.1 Canonical URL Map

| Page | Current URL | Proposed URL | Change |
|------|-------------|--------------|--------|
| Home | `/` | `/` | — |
| Performance | `/performance` | `/performance` | — |
| Methodology | `/methodology` | `/methodology` | — |
| About | `/about` | `/about` | — |
| Brief | `/brief` | `/brief` | — |
| Terminal Overview | `/terminal` | `/terminal` | — |
| FX-Regime Mosaic | `/terminal/fx-regime` | `/terminal/fx-regime` | — |
| Pair Desk | `/terminal/fx-regime/[pair]` | `/terminal/fx-regime/[pair]` | — |
| Terminal Calendar | `/terminal/calendar` | `/terminal/calendar` | — |
| Terminal Memos | `/terminal/memos` | `/terminal/memos` | **New page** |
| Terminal Performance | `/terminal/performance` | `/terminal/performance` | **Redesignated** |
| Audit | `/audit` | `/audit` | — |
| Memo Permalink | `/memo/[date]` | `/memo/[date]` | **Integrated** |
| Standalone Calendar | `/calendar` | → `/terminal/calendar` | **301 Redirect** |
| Memos Archive | (none) | `/memos` | **301 → /terminal/memos** |

### 4.2 Query Parameters

| Parameter | Applied To | Purpose |
|-----------|------------|---------|
| `?date=YYYY-MM-DD` | `/brief`, `/terminal/fx-regime/[pair]` | Historical view (replay mode) |
| `?pair=eurusd` | `/performance` | Filter validation log by pair |
| `?regime=moderate-strength` | `/performance` | Filter by regime |
| `?horizon=t5` | `/terminal/performance` | Switch T+1 / T+3 / T+5 view |
| `?mode=student` | `/methodology` | Default to student explanations |

### 4.3 API Routes

| Route | Method | Purpose | Response |
|-------|--------|---------|----------|
| `/api/connect-desk` | GET | Pair desk data | JSON: spot, regime, confidence, composite, signals |
| `/api/linkedin-alpha-hook` | GET/POST | OG image generation | PNG: shareable performance card |
| `/api/substack-ingest` | POST | Webhook from Substack | 200 OK on successful ingest |
| `/api/validation-export` | GET | CSV export | `text/csv`: full validation ledger |
| `/api/regime-snapshot` | GET | Today's calls | JSON: all pairs, regimes, confidences |

---

## 5. Content Hierarchy Per Page

### 5.1 Homepage (`/`)

**Primary audience:** Priya (first visit), Diego (discovery)

```
1. HERO (immediate, above fold)
   └── Live snapshot cards (EUR/USD, USD/JPY, USD/INR)
       ├── Spot price
       ├── Regime label
       ├── Confidence %
       └── Timestamp + "Next validation" countdown

2. VALIDATION TRUST (scroll 1)
   └── 4-metric strip: 7D ACC / AVG RET / CUM RET / CALLS
       └── CTA → /performance

3. SIGNAL ARCHITECTURE (scroll 2)
   └── 3 pillars: Rate / COT / Vol
       └── CTA → /methodology

4. SUBSTACK FEED (scroll 3)
   └── Latest 3 posts + subscribe CTA

5. FOOTER
   └── Navigation + email capture
```

**Rationale:** Priya decides in < 3 seconds. The live snapshot cards + metric strip must be visible without scrolling on a 1080p display. The manifesto text (previously dominating) becomes a *secondary* layer that dissolves on scroll — it sets tone but does not block proof.

---

### 5.2 Performance (`/performance`)

**Primary audience:** Priya (vetting), Marcus (context)

```
1. EQUITY CURVE (hero, full width)
   └── Cumulative return over time
       ├── Time range selector: 7D / 30D / 90D / ALL
       └── Drawdown periods highlighted honestly

2. METRIC STRIP (below curve)
   └── 7D ACC / CUM RET / CALLS / AVG RET / SHARPE / MAX DD

3. REGIME-SPECIFIC BREAKDOWN (scroll 1)
   └── Table: Regime | Calls | Hit Rate | Avg Return | Max DD
       └── "Where edge lives (and where it doesn't)"

4. PER-PAIR ACCURACY (scroll 2)
   └── EUR/USD: 68% | USD/JPY: 75% | USD/INR: 61%
       └── Mini sparklines per pair

5. HIT RATE BY HORIZON (scroll 3)
   └── T+1 | T+3 | T+5 columns
       └── Leverages strategy_ledger data

6. VALIDATION LOG (scroll 4)
   └── Full table: Date · Pair · Regime · Outcome · Return · [View Brief]
       └── Filterable, sortable, paginated
       └── Export CSV button

7. FOOTER
```

**Rationale:** This is THE credibility page. The equity curve is non-negotiable — it answers "does this work?" visually in 1 second. Everything below is for allocators who want to stress-test. The validation log is the audit chain; every row links to its source brief.

---

### 5.3 Terminal Overview (`/terminal`)

**Primary audience:** Marcus (daily habit)

```
1. CROSS-PAIR SNAPSHOT (top)
   └── 3 cards: EUR/USD | USD/JPY | USD/INR
       ├── Regime + confidence
       ├── 24h change
       └── Click → pair desk

2. STRATEGY STRIP (below)
   └── Active signal families + primary driver summary

3. PERFORMANCE WIDGET (right or below)
   └── Mini: 7D ACC / CUM RET / CALLS
       └── Links to /performance and /terminal/performance

4. MACRO PULSE MARQUEE (bottom)
   └── Live macro data ticker

5. MEMO PREVIEW (optional, bottom)
   └── Latest memo title + excerpt
       └── Link → /terminal/memos
```

**Rationale:** Marcus opens this pre-market. He needs today's calls immediately. The cross-pair snapshot is the answer. Performance widget bridges public shell → terminal, so he doesn't have to leave his workflow to check track record.

---

### 5.4 Pair Desk (`/terminal/fx-regime/[pair]`)

**Primary audience:** Marcus (execution), Diego (learning)

```
1. PAIR HEADER (sticky)
   └── Pair name · Spot · Regime · Confidence · Timestamp

2. TOP STRIP (4 columns)
   └── SPOT | REGIME | CONFIDENCE | COMPOSITE

3. TRADER'S CONTEXT BOX (new)
   └── "This call is driven by [RATE]. Watch [US 2Y yield].
        Invalidation: spot closes below [1.0780]."

4. CHART PANEL (left/main)
   └── TradingView embed with regime-change vertical markers
       └── Replay mode: date picker + historical overlay

5. SIGNAL DECOMPOSITION (right)
   └── RATE / COT / VOL / IV chips
       └── Weights + percentile ranks
       └── Primary driver text

6. 7-DAY REGIME HISTORY (below chart)
   └── Sparkline of regime states + confidence trend

7. OTHER DESKS SIDEBAR (right)
   └── Quick switch to other pairs

8. RELATED MEMOS (bottom)
   └── Memos mentioning this pair
```

**Rationale:** The desk is where Marcus decides whether to use the call as a bias filter. The Trader's Context box is the TL;DR of the TL;DR — it tells him *what to watch* and *what would prove him wrong*. Replay mode lets Diego learn by tracing historical calls.

---

### 5.5 Brief (`/brief`)

**Primary audience:** Marcus (signal), Diego (narrative)

```
1. TRADER'S TL;DR BOX (new, top)
   └── ┌────────────────────────────────────────┐
       │ TODAY'S CALL: MODERATE USD STRENGTH    │
       │ Confidence: 62% | Primary: Rate Diff   │
       │ Invalidation: Close below 1.0780       │
       │ Driver: US 2Y yield expanding vs DE    │
       └────────────────────────────────────────┘

2. BRIEF HEADER
   └── Date · Title · Reading time

3. BRIEF BODY
   └── Markdown-rendered prose
       └── Auto-linked pair mentions → pair desks
       └── Auto-linked regime mentions → methodology

4. DISCUSS ON SUBSTACK CTA (bottom)
   └── "Continue reading / discuss on Substack"
       └── Comment count if available

5. PAGINATION
   └── ← Previous Brief | Next Brief →
```

**Rationale:** Marcus does not read prose before the open. The TL;DR box gives him what he needs in 3 seconds. If he wants narrative context, he reads below. Diego gets the full story. The Substack CTA closes the bidirectional loop.

---

### 5.6 Methodology (`/methodology`)

**Primary audience:** Priya (vetting), Diego (learning)

```
1. PAGE HEADER
   └── "Signal Architecture" + Expert|Student toggle

2. THE SETUP (narrative intro)
   └── "We combine 4 signals into 1 score..."

3. SIGNAL FAMILY CARDS
   └── RATE (~40%) | COT (~30%) | VOL (~20%) | IV (~10%)
       └── Weight · Explanation · "Why this matters" callout

4. THE EQUATION
   └── S = w_r·R + w_c·C + w_v·V + w_o·O
       └── Student mode: plain English expander

5. REGIME THRESHOLD TABLE
   └── Score ranges → regime labels

6. CONFIDENCE DERIVATION
   └── How confidence is computed
       └── Tooltip glossary for jargon

7. HOW TO READ THE TERMINAL
   └── 3×3 mosaic explained
       └── Link → /terminal/fx-regime

8. DOWNLOAD PDF CTA
   └── Full methodology as printable document
```

**Rationale:** Priya needs to verify there's no black box. Diego needs to learn. The toggle serves both without diluting the expert experience. Every equation has a "Why this matters" callout — no math without context.

---

### 5.7 Terminal Memos (`/terminal/memos`)

**Primary audience:** Diego (deep dives), Priya (research quality)

```
1. PAGE HEADER
   └── "Research Memos" + count + filter bar

2. FILTER BAR
   └── Search | Pair tag | Date range | Sort

3. MEMO LIST (card-based)
   └── Month divider
       └── Card: Date · Title · Excerpt · Pair tags · Reading time
           └── Click → /memo/[date]
           └── "Read on Substack" link

4. PAGINATION
   └── 20 per page
```

**Rationale:** The memo archive transforms ephemeral briefs into a research corpus. Month dividers create temporal wayfinding. Pair tags let Marcus find EUR/USD-specific research. The Substack link maintains the bidirectional flow.

---

### 5.8 Audit (`/audit`)

**Primary audience:** Priya (deep skepticism), technical visitors

```
1. PAGE HEADER
   └── "System Integrity Log"

2. PIPELINE HEARTBEAT STATUS
   └── Ingest → Classify → Validate → Publish
       └── Timestamp per stage
       └── Green/amber/red per pipeline health

3. CHAT.MD TRANSPARENCY
   └── "This site was built with AI assistance."
       └── Link to chat.md file

4. VALIDATION CHAIN
   └── "Every call is timestamped before market open."
       └── Example: brief publish time → call time → validation time

5. DATA PROVENANCE
   └── Sources: CFTC COT, Bloomberg, Refinitiv, etc.
       └── Last ingest timestamp per source
```

**Rationale:** The audit page is for the deeply skeptical. It must not feel like a developer joke. Pipeline heartbeat transforms it into a living system monitor. Every data point gets provenance.

---

## 6. Cross-Linking Strategy

### 6.1 The Trust Network

Pages do not exist in isolation. They form a **trust network** where every claim is verifiable in ≤ 2 clicks.

```
                    ┌─────────────┐
                    │   HOMEPAGE  │
                    │   (/ )      │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   ┌─────────┐      ┌────────────┐      ┌──────────┐
   │PERFORMANCE│     │  TERMINAL  │      │ METHODOLOGY│
   │(/performance)│   │  (/terminal)│     │ (/methodology)│
   └────┬────┘      └─────┬──────┘      └────┬─────┘
        │                 │                  │
        │    ┌────────────┼────────────┐     │
        │    │            │            │     │
        ▼    ▼            ▼            ▼     ▼
   ┌────────┐      ┌──────────┐   ┌──────────┐
   │VALIDATION│    │PAIR DESKS │   │  BRIEF   │
   │   LOG    │    │(/terminal │   │ (/brief) │
   │          │    │/fx-regime │   └────┬─────┘
   └──────────┘    │/[pair])   │        │
                   └───────────┘        │
                           │            │
                           ▼            ▼
                      ┌─────────────────────┐
                      │   MEMO PERMALINK    │
                      │    (/memo/[date])   │
                      └─────────────────────┘
```

### 6.2 Mandatory Cross-Links

| From | To | Anchor Text | Context |
|------|----|-------------|---------|
| Homepage → Performance | `/performance` | "View full ledger" | Below metric strip |
| Homepage → Terminal | `/terminal` | "Open Terminal" | Below live snapshot cards |
| Performance → Brief | `/brief?date=YYYY-MM-DD` | "View call" | Per validation row |
| Performance → Audit | `/audit` | "Verify pipeline integrity" | Bottom of page |
| Terminal → Performance | `/performance` | "Track record" | Performance widget |
| Pair Desk → Methodology | `/methodology` | "How this signal works" | Signal decomposition panel |
| Pair Desk → Brief | `/brief` | "Today's brief" | If pair mentioned in today's brief |
| Brief → Pair Desk | `/terminal/fx-regime/[pair]` | "EUR/USD desk" | Auto-linked pair mentions |
| Brief → Methodology | `/methodology` | "Regime classification" | Auto-linked regime mentions |
| Brief → Substack | (external) | "Discuss on Substack" | Bottom CTA |
| Methodology → Terminal | `/terminal/fx-regime` | "See it live" | "How to read the terminal" section |
| Memo → Pair Desk | `/terminal/fx-regime/[pair]` | Pair name | In pair tags |
| Memo → Substack | (external) | "Read on Substack" | Top and bottom of memo |
| Audit → Performance | `/performance` | "Validation log" | Audit chain section |
| Footer (all pages) | `/about` | "About" | Persistent |
| Footer (all pages) | Substack | "Substack" | Persistent |

### 6.3 Auto-Linking Rules (Content Layer)

When rendering briefs and memos, auto-link:
- **Pair mentions** (`EUR/USD`, `USD/JPY`, `USD/INR`) → respective pair desk
- **Regime labels** (`NEUTRAL`, `MODERATE USD STRENGTH`, etc.) → methodology threshold table
- **Signal families** (`COT`, `Rate Differentials`, `Vol`) → methodology signal cards
- **Dates** (`2026-05-05`) → `/memo/2026-05-05` if exists

**Rationale:** This builds a knowledge graph that Substack writers create manually. FXRL's integrated architecture can do it automatically.

---

## 7. Mobile Architecture

### 7.1 Philosophy

Terminal-native does not mean desktop-only. Marcus checks pre-market on his iPhone. Diego reads on the commute. The mobile experience must compress elegantly — monospace data must reflow, tables must become cards.

### 7.2 Breakpoints

| Name | Width | Usage |
|------|-------|-------|
| `xs` | < 480px | Single column. Full collapse. |
| `sm` | 480–768px | Stacked cards. Drawer nav. |
| `md` | 768–1024px | 2-column where possible. Rail collapses. |
| `lg` | 1024–1280px | Full desktop layout. Rail expanded default. |
| `xl` | > 1280px | Full desktop + sidebar expansions. |

### 7.3 Global Header (Mobile)

```
┌─────────────────────────────────────┐
│ ≡  FX REGIME LAB         [⌘K]  🔍  │
└─────────────────────────────────────┘
```

- **Hamburger menu (≡):** Opens full-screen drawer from left
  - Contains all primary nav items + terminal sub-items
  - Terminal section labeled "TERMINAL" with indented children
  - Active item highlighted
- **Search icon (🔍):** Opens command palette (same as `Cmd+K`)
- **No dropdowns on mobile** — drawers only

### 7.4 Template-Specific Mobile Behavior

#### Gateway Template (`/`, `/about`)

| Element | Mobile Behavior |
|---------|-----------------|
| Hero manifesto | Font size reduces to `clamp(28px, 8vw, 48px)`. Stays centered. |
| Live snapshot cards | Stack vertically (3 → 1 column). Full-width cards. |
| Metric strip | Horizontal scroll OR 2×2 grid. |
| Section padding | Reduces from `py-32` to `py-16`. |
| Substack feed | Stack vertically. Title + date only (no excerpt). |

#### Dashboard Template (`/performance`, `/terminal/*`)

| Element | Mobile Behavior |
|---------|-----------------|
| Metric strip | Horizontal scroll container (swipeable). 4+ metrics don't wrap. |
| Equity curve | Full width, height reduces to 240px. Touch to tooltip. |
| Tables | Transform to card list. Each row becomes a card. Sort/filter in sheet drawer. |
| 3×3 mosaic | Stack to single column. Each cell full-width. Regime label + sparkline. |
| Filter bar | Collapses to "Filters" button → bottom sheet with filter controls. |
| Export CSV | Moves to filter sheet. |

#### Desk Template (`/terminal/fx-regime/[pair]`)

| Element | Mobile Behavior |
|---------|-----------------|
| Context rail | **Completely hidden**. Replaced by hamburger drawer nav. |
| Pair header | Stays sticky. Font sizes reduce. |
| Top strip (4 columns) | 2×2 grid or vertical stack. |
| Trader's Context box | Full-width, stays near top. |
| Chart + Signals layout | Stack vertically. Chart first (full-width), signals below. |
| Other Desks sidebar | Horizontal scroll strip below main content. |
| Replay mode | Date picker becomes native `<input type="date">`. |

#### Editorial Template (`/methodology`, `/brief`, `/memo/[date]`)

| Element | Mobile Behavior |
|---------|-----------------|
| Sticky TOC | **Collapses to floating "Sections" button** → bottom sheet with TOC. |
| Body text | Full width, comfortable measure (padding 16px). |
| Equations | Horizontal scroll if overflow. |
| Trader's TL;DR box | Full-width, prominent. |
| Expert/Student toggle | Stays accessible, moves to top-right of content area. |

### 7.5 Touch Interactions

| Pattern | Desktop | Mobile |
|---------|---------|--------|
| Hover reveals | Secondary data on hover | Tap to expand / long-press |
| Row hover | Background elevation | Tap feedback (ripple-less, 80ms opacity shift) |
| Chart tooltips | Hover | Tap + hold |
| Command palette | `Cmd+K` | Search icon tap |
| Rail expand | Hover / `Cmd+\` | N/A (drawer replaces) |

### 7.6 Performance Budget (Mobile)

- **LCP ≤ 1.5s** on 4G
- **No animation on tables** (they become cards — cards can entrance-animate)
- **BinaryResolve disabled** on mobile for background cards (only primary spot price resolves)
- **Images:** No images on terminal pages. Charts are SVG/canvas. Zero image weight.

---

## 8. IA Decisions Log

### 8.1 Decision: Performance as Primary Navigation Item

**Decision:** `PERFORMANCE` is first in primary nav, before `TERMINAL`.

**Rationale:**
- Round 1 synthesis: "Performance is the primary content."
- UX Strategist: "Users land on a beautiful homepage, but they have no immediate path to answering: 'Does this thing actually make correct calls?'"
- Priya (Verifying Allocator) needs performance data in < 90 seconds. She does not care about the terminal first — she cares about proof.

**Rejected alternative:** Terminal first. Marcus (Active Trader) uses the terminal daily, but he is already a believer. The site must convert skeptics first.

---

### 8.2 Decision: Two Performance Pages (`/performance` + `/terminal/performance`)

**Decision:** Keep both routes but differentiate them sharply, rather than merging.

| | `/performance` | `/terminal/performance` |
|---|---|---|
| **Audience** | Priya (allocators) | Marcus (quants) |
| **Tone** | Narrative, story of discipline | Raw, quant alpha ledger |
| **Hero** | Equity curve (large, beautiful) | Brier score trend |
| **Key data** | Cumulative return, Sharpe, drawdown | T+1/T+3/T+5 hit rates, Brier |
| **Table** | Validation log with "View Brief" links | Regime-grouped alpha ledger |
| **Template** | Dashboard | Dashboard |

**Rationale:**
- UX Strategist identified redundancy but noted terminal performance has Brier scores and multi-horizon data that would overwhelm public visitors.
- Priya wants "does it work?" Marcus wants "how does it work at T+5 in NEUTRAL regimes?"
- Merging would either dilute the quant depth or intimidate allocators.

---

### 8.3 Decision: Consolidate Calendar to Terminal-Only

**Decision:** Remove standalone `/calendar`. Redirect 301 → `/terminal/calendar`.

**Rationale:**
- Competitive Analyst: "Calendar feels like a template not a tool."
- Calendar is inherently contextual — it matters when paired with regime calls and event risk.
- Maintaining two calendar implementations creates drift (already observed in codebase).
- Marcus checks calendar *while* in terminal workflow, not as a standalone destination.

**Rejected alternative:** Keep both with shared component. Creates URL confusion and SEO cannibalization.

---

### 8.4 Decision: `/memos` → `/terminal/memos` Redirect

**Decision:** Create `/terminal/memos` as canonical memo archive. `/memos` 301 redirects.

**Rationale:**
- UX Strategist: "Archive is invisible. Memos exist at `/memo/[date]` but there's no browseable index."
- Substack users expect `/memos` or `/archive`. We support that expectation but redirect to the terminal context where the archive is most useful.
- Terminal context rail provides persistent navigation once inside the archive.
- `/memo/[date]` permalinks remain unchanged for SEO and external links.

---

### 8.5 Decision: Trader's TL;DR Box on `/brief`

**Decision:** Add a prominent signal-summary box at the very top of every brief, above the prose.

**Rationale:**
- Marcus (Active Trader): "Brief is prose-heavy; wants signal snapshot at top."
- UX Strategist: "Add 'Trader's TL;DR' box at top of brief: regime + confidence + primary driver + invalidation level."
- Diego (Student) can skip the box and read the narrative below. It does not harm the student experience.
- This is the equivalent of an executive summary in a research note — standard practice at Bernstein, Goldman, etc.

---

### 8.6 Decision: Expert | Student Toggle on `/methodology`

**Decision:** Add a toggle on the methodology page that switches between full mathematical view and plain-English annotations.

**Rationale:**
- Diego (Student): "Equations are intimidating without context."
- UX Strategist: "Add a 'Student Mode' that explains jargon inline."
- Current methodology page is "excellent for experts. Do not dilute it. Add a toggle."
- This expands addressable audience without alienating core quant users.

**Rejected alternative:** Separate `/methodology/simple` page. Fragments SEO and creates maintenance burden. Toggle keeps all content on one canonical URL.

---

### 8.7 Decision: Auto-Linking in Briefs/Memos

**Decision:** Automatically hyperlink pair mentions, regime labels, signal families, and dates in brief/memo content.

**Rationale:**
- Competitive Analyst (Substack section): "Substack posts interlink to build rabbit holes. FXRL briefs are islands."
- This creates a knowledge graph that increases time-on-site and reduces bounce.
- Zero authoring friction — the system does it, not the writer.
- SEO benefit: internal linking structure signals content relationships to search engines.

---

### 8.8 Decision: No Infinite Scroll Anywhere

**Decision:** Use pagination or "Load more" buttons for all archive/table views. Never infinite scroll.

**Rationale:**
- Creative Director: "No infinite scroll. Pagination or 'Load more.' The terminal must feel bounded and navigable. Infinite scroll creates anxiety in a data-dense interface."
- Marcus needs to know where he is in a dataset. Infinite scroll removes that sense of boundedness.
- Priya wants to see "there are 27 calls" — pagination makes volume tangible.
- Footer (with email capture) must remain accessible.

---

### 8.9 Decision: Context Rail Hidden on Mobile

**Decision:** The terminal context rail is completely hidden on mobile. Navigation moves to hamburger drawer.

**Rationale:**
- Screen real estate on mobile is ~375px wide. A 54px rail consumes 14% of width permanently.
- Touch targets on a collapsed rail are too small for reliable interaction.
- Bloomberg Terminal does not exist on mobile for a reason — the paradigm breaks down. We adapt, not translate literally.
- Drawer navigation is a proven mobile pattern that preserves all route access.

---

### 8.10 Decision: Tables → Cards on Mobile

**Decision:** All data tables transform to card-based lists on viewports < 768px.

**Rationale:**
- Competitive Analyst: "Mobile experience is second-class. The terminal pair page grid collapses to single column but loses context."
- Horizontal table scrolling is cognitively expensive on mobile.
- Cards allow vertical scanning (natural thumb motion) and can entrance-animate without creating "theatre" on data.
- Filter/sort moves to a bottom sheet — accessible without crowding the view.

---

### 8.11 Decision: Substack as Distribution, Not Design

**Decision:** Substack integration is a distribution channel, not a design system. We borrow their subscribe/archive patterns but never their aesthetic.

**Rationale:**
- Creative Director: "Substack sites look like Substack. FXRL should not. The RSS integration is a distribution channel, not a design system."
- Competitive Analyst: "Never let Substack's generic aesthetic override FXRL's warm stone palette."
- We mirror content (briefs, memos) for SEO and utility, but Substack is for *engagement* (comments, restacks). Bidirectional linking preserves both.

---

### 8.12 Decision: Audit Page Kept but Deprioritized

**Decision:** `/audit` remains in the architecture but is P2 priority. It is linked from `/performance` footer, not primary nav.

**Rationale:**
- UX Strategist: "Audit is extremely niche; valuable for the deeply skeptical."
- Competitive Analyst rated Audit 4/10: "visually disconnected, often shows fallback text."
- Priya (the deeply skeptical allocator) will find it via the performance page's "Verify pipeline integrity" link.
- Keeping it proves transparency. Promoting it would confuse the 90% of users who don't need it.

---

### 8.13 Decision: No Light Mode, No Rounded Corners > 4px, No Drop Shadows

**Decision:** Inherited from Round 1 consensus. Enforced at IA level.

**Rationale:**
- Round 1 Synthesis: "No light mode, no rounded corners above 4px, no drop shadows, no loading spinners, no generic stock photography, no delight-for-delight's-sake animations, no blur/backdrop-filter."
- These are brand-defining constraints, not aesthetic preferences. The Obsidian Stone palette is a competitive advantage.
- At IA level, this means: no modal popups (inline CTAs only), no skeleton theatre (structural skeletons only), no glassmorphism in navigation.

---

### 8.14 Decision: Command Palette as Tier-1 Navigation

**Decision:** The command palette (`Cmd+K`) is not a power-user extra — it is a primary navigation mechanism, equally important as the header nav.

**Rationale:**
- Competitive Analyst (Bloomberg section): "Command-driven navigation... Expand it to support ticker jumping, route teleporting, quick queries."
- Marcus (Active Trader): "Terminal access that feels like a real tool, not a blog."
- Bloomberg's `<GO>` keys are iconic because they make navigation *faster* than pointing. The command palette is FXRL's `<GO>`.
- It also solves mobile navigation elegantly — the search icon opens the same interface.

---

### 8.15 Decision: Email Capture in Footer, Never as Modal

**Decision:** Email subscription capture appears only in the global footer and inline on `/brief` and `/about`. Never as a modal, popup, or interstitial.

**Rationale:**
- UX Strategist: "Do NOT use intrusive popups — this audience is sophisticated and hates them."
- Competitive Analyst: "Every Substack publication leads with email capture. FXRL should too, but inline."
- Priya and Marcus are institutional-adjacent users. Popups signal consumer-grade marketing. Inline CTAs signal respect.
- The footer is persistent but unobtrusive. The brief page CTA is contextual: "Get the morning brief in your inbox."

---

## Appendix A: Implementation Checklist

### URL Changes
- [ ] Create `/terminal/memos` page (Archive template)
- [ ] Create `/memos` → `/terminal/memos` 301 redirect
- [ ] Remove `/calendar` standalone page; 301 → `/terminal/calendar`
- [ ] Create `/api/substack-ingest` webhook route
- [ ] Create `/api/validation-export` CSV route
- [ ] Create `/api/regime-snapshot` JSON route

### Navigation
- [ ] Reorder primary nav: PERFORMANCE, TERMINAL, METHODOLOGY, BRIEF, ABOUT
- [ ] Add terminal dropdown with all sub-routes
- [ ] Implement footer with three-column structure + email capture
- [ ] Expand command palette: pair desks, actions, help categories

### Templates
- [ ] Refactor `/` to Gateway template with performance-first hierarchy
- [ ] Refactor `/performance` to Dashboard template with equity curve hero
- [ ] Refactor `/methodology` to Editorial template with Expert|Student toggle
- [ ] Refactor `/brief` to Editorial template with Trader's TL;DR box
- [ ] Refactor `/terminal/fx-regime/[pair]` to Desk template with Replay mode
- [ ] Create `/terminal/memos` as Archive template

### Cross-Linking
- [ ] Auto-link pairs in briefs → pair desks
- [ ] Auto-link regimes in briefs → methodology
- [ ] Link validation rows → `/brief?date=YYYY-MM-DD`
- [ ] Add "Discuss on Substack" CTA to all briefs/memos
- [ ] Add "How this signal works" links in signal decomposition

### Mobile
- [ ] Implement table→card transformation on < 768px
- [ ] Hide context rail on mobile; use drawer nav
- [ ] Implement filter bottom sheets
- [ ] Reduce animation scope on mobile (no BinaryResolve on background cards)

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Public Shell** | Marketing-layer pages (`/`, `/about`, `/methodology`, `/brief`, `/performance`) — generous whitespace, editorial typography |
| **Terminal** | Tool-layer pages (`/terminal/*`) — dense data, monospace dominance, threshold crossing |
| **Pair Desk** | Individual pair analysis page (`/terminal/fx-regime/[pair]`) — signal decomposition + chart |
| **Alpha Ledger** | Terminal performance view with Brier scores, multi-horizon hit rates |
| **Validation Log** | Public table of every call, every outcome, every return |
| **Replay Mode** | Date picker on pair desk to view historical calls + next-day outcomes |
| **Trader's TL;DR** | Signal-summary box at top of brief: regime + confidence + driver + invalidation |
| **Threshold Crossing** | The perceptual shift when entering `/terminal/*` — darker borders, monospace dominance |

---

*Document owner: Lead Information Architect*  
*Next review: After template implementation completion*  
*Dependencies: Round 1 Synthesis (locked), Creative Vision (locked), UX Strategy (locked), Motion Design System (locked)*
