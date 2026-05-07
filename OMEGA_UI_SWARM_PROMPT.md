# OMEGA UI SWARM PROMPT
## FX Regime Lab — Complete Frontend Rebuild Specification

> **Version:** 2026-05-07  
> **Scope:** Complete Next.js 15+ frontend rebuild for 3-pair production rig  
> **Pairs:** EUR/USD, USD/JPY, USD/INR only  
> **Status:** AI on hold. Deterministic telemetry only.  
> **Target:** Production-ready, institutional-grade research terminal.

---

## SECTION 0: PROJECT IDENTITY (READ FIRST)

**FX Regime Lab** is a live, public **quantamental macro research rig** — not a SaaS, not a subscription product, not a framework demo, not coursework. It is a disciplined practice environment that happens to be public.

**What it does:**
1. Ingests macro data daily (FRED yields, CFTC COT, FX spot, vol indices, cross-asset)
2. Scores 3 currency pairs using a deterministic 3-Layer Signal Framework
3. Persists immutable regime calls to Supabase
4. Validates calls out-of-sample (T+5, T+20) and accumulates accuracy statistics
5. Publishes daily briefs and weekly macro analysis

**External persona:** Independent institutional research operation.  
**Strictly forbidden in all public files:** "student," "applicant," "NTU," "MFE," "learning journey," "built to learn."

---

## SECTION 1: NON-NEGOTIABLE HARD RULES

### 1.1 Scope Lock
- **ONLY 3 PAIRS:** EUR/USD, USD/JPY, USD/INR
- No references to GBP/USD, AUD/USD, USD/CAD, USD/CHF anywhere in UI code, copy, or navigation
- The `universe` table may still have legacy rows — filter them out in all queries

### 1.2 AI On Hold
- **No AI-generated narrative in the UI.** No LLM-written briefs, no chatbot, no "AI insights" panel
- Desk cards show deterministic telemetry only (regime, pain index, Markov, dominance array)
- `brief_log` table contains placeholder text: "AI brief generation on hold. Regime telemetry available in terminal."
- `macro_events.ai_brief` column may exist but is empty — do not build UI that depends on it

### 1.3 Immutable Track Record
- `regime_calls` and `validation_log` are **append-only**
- Never build edit/delete functionality for these tables
- Performance page must communicate this immutability as a feature, not a limitation

### 1.4 Design Discipline
- **Swiss Monochrome** — Obsidian Stone dark terminal is the PRIMARY surface
- **No rounded corners** above 2px (scrollbars get 2px, live dots get `rounded-full`)
- **1px sharp borders only** — no soft shadows, no drop shadows, no glassmorphism
- **No neon blue/purple "AI dashboard" palettes**
- **No generic SaaS landing tropes** — no gradient heroes, no three-column feature grids with stock icons
- **No loading spinners** — use skeleton pulses or text state changes
- **All financial numbers use `tabular-nums`**
- **No decorative animations** — every motion must carry information

### 1.5 Two-Surface Architecture
| Surface | Routes | Theme | Purpose |
|---------|--------|-------|---------|
| **Shell** | `/`, `/about`, `/brief`, `/performance`, `/methodology` | Light (`#f5f5f0` bg, `#0a0a0a` text) | Public face: landing, methodology, track record |
| **Terminal** | `/terminal/*` | Dark (`#0c0a09` bg, `#f5f5f4` text) | Engine room: live data, pair desks, signals |

There is NO light-mode toggle. The terminal is ALWAYS dark.

---

## SECTION 2: TECHNOLOGY STACK (LOCKED)

```
Framework:     Next.js 15.3.9+ (App Router)
React:         19.0.0
TypeScript:    5.x strict: true
Styling:       Tailwind CSS v4 (@import "tailwindcss" — NO tailwind.config.ts)
PostCSS:       @tailwindcss/postcss
Animation:     Framer Motion (orchestrated reveals), CSS keyframes (ambient)
Data:          TanStack Query v5 (@tanstack/react-query)
Database:      Supabase (@supabase/supabase-js, @supabase/ssr)
Charts:        lightweight-charts v5 (for price charts), SVG (for sparklines/equity curves)
Math:          KaTeX (methodology page only)
Icons:         lucide-react
Lint:          Biome (npm run lint = biome check .)
Fonts:         Inter (UI), JetBrains Mono (data), Cormorant 300 (editorial)
```

**Path alias:** `@/*` → `./src/*`

---

## SECTION 3: DESIGN SYSTEM (DEEP SPEC)

### 3.1 Color Tokens

Define these as CSS custom properties in `globals.css`:

```css
:root {
  /* Dark Terminal (Primary) */
  --color-void: #0c0a09;
  --color-surface: #141210;
  --color-elevated: #1c1917;
  --color-panel: #242220;
  --color-border: #2a2725;
  --color-border-subtle: #1f1d1b;
  --color-text: #f5f5f4;
  --color-text-secondary: #a8a29e;
  --color-text-muted: #78716c;
  --color-text-dim: #57534e;
  --color-accent: #d6d3d1;
  --color-accent-hover: #e7e5e4;
  --color-up: #7a9e7a;
  --color-down: #b87a7a;
  --color-warn: #a8947a;

  /* Pair Colors (Sacred) */
  --color-pair-eurusd: #4BA3E3;
  --color-pair-usdjpy: #F5923A;
  --color-pair-usdinr: #FB923C;

  /* Light Shell (Secondary) */
  --color-shell-bg: #f5f5f0;
  --color-shell-text: #0a0a0a;
  --color-shell-secondary: #525252;
  --color-shell-muted: #737373;
  --color-shell-border: #e5e5e5;

  /* Motion */
  --ease-institutional: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-crisp: cubic-bezier(0.25, 0.1, 0.25, 1);
  --duration-micro: 80ms;
  --duration-default: 300ms;
  --duration-emphasis: 600ms;
}
```

### 3.2 Typography

```css
@theme {
  --font-sans: var(--font-inter), ui-sans-serif, system-ui, sans-serif;
  --font-mono: var(--font-jetbrains-mono), ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  --font-serif: var(--font-playfair), ui-serif, Georgia, Cambria, "Times New Roman", Times, serif;
}
```

| Role | Font | Size | Weight | Tracking | Notes |
|------|------|------|--------|----------|-------|
| Hero H1 | Inter | clamp(40px, 6vw, 72px) | 600 | tight | Shell pages only |
| Body | Inter | 15px | 400 | normal | leading 1.7, max-width 440px |
| Mono labels | JetBrains Mono | 9px–11px | 400 | 0.15em–0.2em | uppercase, tracking-widest |
| Data values | JetBrains Mono | 10px–14px | 400 | normal | tabular-nums MANDATORY |
| Spot prices | JetBrains Mono | 18px–32px | 500 | tight | tabular-nums |
| Editorial | Cormorant | 24px–40px | 300 | normal | Manifesto quotes only |

### 3.3 Spacing & Layout

- **Max content width:** `1152px` (`max-w-[1152px] mx-auto px-6`)
- **Section padding:** `py-32` desktop, `py-20` mobile
- **Terminal nav height:** dynamic `--terminal-nav-h` set by JS (76px base)
- **Macro pulse height:** `28px` fixed
- **Systemic banner height:** `32px` fixed

### 3.4 Border & Surface Conventions

**Standard bevel (OMEGA_BEVEL):**
```css
border-0 border-t-[0.5px] border-t-white/[0.08] border-l-[0.5px] border-l-white/[0.03] bg-[var(--color-surface)]
```

**Crisis bevel:**
```css
border-0 border-t-[0.5px] border-t-[#f59e0b] border-l-[0.5px] border-l-white/[0.03]
```

**Divider:**
```css
border-b-[0.5px] border-b-[#111]
```

**Haptic feedback (buttons/links):**
```css
/* hover-lift: translateY(-2px) + border color transition */
/* omega-haptic:active: translateY(0.5px) scale(0.995) + inset shadow */
```

### 3.5 Scrollbar & Selection

```css
scrollbar-width: thin;
scrollbar-color: rgba(255, 255, 255, 0.08) transparent;

::selection {
  background: rgba(168, 162, 158, 0.25);
  color: var(--color-text);
}
```

---

## SECTION 4: DATA MODEL & API CONTRACT

### 4.1 Core Tables (What the UI Reads)

| Table | Key Columns | UI Usage |
|-------|-------------|----------|
| `signals` | `date`, `pair`, `spot`, `rate_diff_2y`, `cot_percentile`, `realized_vol_5d/20d`, `cross_asset_vix/dxy/oil/us10y/gold`, `day_change_pct`, `oi_delta`, `volume_rvol`, `structural_instability` | Live snapshot cards, signal tables, cross-asset pulse |
| `regime_calls` | `date`, `pair`, `regime`, `confidence`, `signal_composite`, `rate_signal`, `cot_signal`, `vol_signal`, `primary_driver`, `data_quality_score`, `stress_level` | Regime labels, confidence bars, signal chips |
| `validation_log` | `date`, `pair`, `predicted_direction`, `predicted_regime`, `confidence`, `actual_return_1d/5d`, `correct_1d/5d` | Validation tables, accuracy stats, equity curves |
| `brief_log` | `date`, `brief_text`, `dollar_dominance`, `idiosyncratic_outlier`, `sentiment_json` | Daily brief text, dollar dominance bar |
| `desk_open_cards` | `date`, `pair`, `structural_regime`, `dominance_array` (JSONB), `pain_index`, `markov_probabilities`, `ai_brief`, `telemetry_audit`, `global_rank`, `apex_score`, `regime_age`, `invalidation_triggered`, `telemetry_status` | Terminal desk cards, dominance HUD |
| `strategy_ledger` | `date`, `pair`, `regime`, `direction`, `entry_close`, `t1/t3/t5_close`, `t1/t3/t5_hit`, `brier_score_t5`, `max_pain_bps` | Alpha ledger, hit rates |
| `macro_events` | `date`, `event`, `impact` (HIGH/MEDIUM/LOW), `pairs`, `category` | Macro calendar |
| `historical_prices` | `date`, `pair`, `open`, `high`, `low`, `close`, `volume` | Price charts |
| `research_analogs` | `as_of_date`, `pair`, `match_date`, `match_score`, `forward_30d_return` | Historical analogs |
| `universe` | `pair`, `class`, `spot_ticker` | Pair registry |

### 4.2 Critical Rules

1. **`regime_calls.regime` is a FREE STRING, not an enum.** Valid values:
   - `NEUTRAL`, `USD_STRENGTH_MODERATE`, `USD_WEAKNESS_MODERATE`
   - `INR_APPR_MODERATE`, `INR_DEPR_MODERATE`
   - `NEUTRAL__VOL_EXPANDING`
   - `UNKNOWN`
   - Map explicitly for display. Never assume a closed enum.

2. **`confidence`** is float `[0,1]`. Display as `Math.round(confidence * 100) + '%'`.

3. **`spot` formatting:**
   - EUR/USD: `toFixed(4)`
   - USD/JPY: `toFixed(2)`
   - USD/INR: `toFixed(4)`

4. **RLS:** Anon can SELECT public tables. `pipeline_errors` and `ai_usage_log` are NOT readable by anon.

### 4.3 Query Patterns

**Client Components (TanStack Query):**
```typescript
// Always filter universe to canonical 3 pairs
function useUniverse() {
  return useQuery({
    queryKey: ['universe', 'fx_pairs'],
    queryFn: async () => {
      const { data } = await supabase.from('universe').select('pair').eq('class', 'FX');
      const canonical = new Set(['EURUSD', 'USDJPY', 'USDINR']);
      return (data ?? []).map(r => r.pair).filter(p => canonical.has(p));
    },
    staleTime: 60 * 60 * 1000,
  });
}

// Latest data uses sliceLatestCalendarDate (NOT browser today)
function useLatestRegimeCalls() // → Record<string, RegimeCall>
function useLatestSignals() // → Record<string, Signal>
function useLatestDeskOpenCardsSnapshot() // → { asOfDate, cards[], rankJumpByPair }
function useCrossAssetPulse() // → { vix, dxy, oil, us10y } with deltas
function useValidationLog(limit) // → ValidationRow[]
function useEquityCurve() // → EquityPoint[]
function useStrategyLedger(pair) // → StrategyLedgerRow[]
function useUpcomingMacroEvents() // → MacroEventRow[]
function useG10CorrelationMatrix() // → RPC get_g10_correlation_matrix
```

**Server Components:**
```typescript
import { createClient } from '@/lib/supabase/server';
import { getLatestRegimeCalls, getLatestSignals, getValidationLog } from '@/lib/supabase/queries';

export default async function Page() {
  const supabase = await createClient();
  const calls = await getLatestRegimeCalls(supabase);
  const signals = await getLatestSignals(supabase);
  // ...
}
```

---

## SECTION 5: PAGE-BY-PAGE SPECIFICATION

### 5.1 SHELL PAGES (Light Theme)

---

#### PAGE: `/` — Homepage

**Type:** Server Component (async)

**Data fetched:**
- `getLatestRegimeCalls(supabase)` — latest regime per pair
- `getLatestSignals(supabase)` — latest signals per pair
- `getValidationLog(supabase, 500)` — validation rows

**Sections (top to bottom):**

1. **Nav** — Sticky, white bg, border-bottom `#e5e5e5`. Links: Performance, Terminal (dropdown), Methodology, Brief, About. Terminal dropdown: Overview, FX-Regime Mosaic, EUR/USD, USD/JPY, USD/INR, Calendar, Memos, Alpha Ledger.

2. **Hero** — Full viewport height (`min-h-[92vh]`). Left: H1 "FX Regime Lab" + subtitle "Daily regime classification for G10 FX. On the record. Out-of-sample." + CTA "Enter Terminal →". Right: Live snapshot card for EACH of the 3 pairs (EUR/USD, USD/JPY, USD/INR).

3. **Live Snapshot Cards** — 3-column grid (`md:grid-cols-3`). Each card:
   - Pair label (mono, 11px, pair-colored, bold)
   - Spot price (mono, 24px, tabular-nums)
   - Day change % (color-coded: green up, red down)
   - Regime label (mono, 10px, tracking-wide)
   - Confidence bar (3px height, pair-colored fill)
   - Mini signal readout: RATE DIFF, COT PCT, RVOL 20D
   - Left border: 3px solid pair color
   - Surface: `#ffffff`, border `#e5e5e5`
   - Empty state: "Awaiting data" with pulse skeleton

4. **Validation Ticker** — Horizontal scrolling marquee of recent validation outcomes. Each item: `[DATE] PAIR REGIME → OUTCOME (RET%)`. Green for correct, red for incorrect. Speed: 40s loop.

5. **Manifesto** — Editorial section with quote in Cormorant 300 italic: "The only way to survive in macro is to be honest about when you're wrong." Below: 3-column "This is / This is not" grid.

6. **Signal Architecture** — Visual diagram of the 3-Layer Framework:
   - Layer 1: Regime Gate (rate momentum, inflation, spot vol)
   - Layer 2: Directional Signal (COT percentile, crowding, alignment)
   - Layer 3: Timing & Entry (vol rank, RR skew, ADR/MIE)
   - Each layer as a bordered card with icon + description

7. **Validation Trust** — Stats strip:
   - Total regime calls (count from validation_log)
   - 7-day accuracy %
   - Cumulative return %
   - Calls validated since launch
   - Streak (current consecutive correct count)
   - If data >24h old: show "STALE" badge in amber

8. **About Snippet** — 2 paragraphs + "Read full methodology →" link.

9. **Footer** — 3-column: Navigation, Transparency (methodology, audit link removed), Distribution (Substack subscribe form). Substack form: email input + submit → opens Substack in new tab with pre-filled email.

**Animation:**
- Hero: fade-up on load, staggered 100ms
- Live snapshots: fade-up with 150ms stagger
- Validation ticker: CSS marquee, no JS animation
- Below fold: IntersectionObserver-triggered reveals at threshold 0.15

---

#### PAGE: `/about`

**Type:** Client Component

**Sections:**
1. **Nav + Hero** — H1 "About" + subtitle
2. **This is / This is not** — Two-column list
   - This is: Live research, deterministic signals, on-the-record validation, public track record
   - This is not: Investment advice, a fund, a SaaS, a prediction service, black-box ML
3. **Pipeline Methodology** — 5 stages: Ingest → Signal → Regime → Validate → Publish
4. **Signal Weights Sidebar** — Per-pair weight table (RATE, COT, VOL, OI, SPECIAL)
5. **Validation Philosophy** — Brier scores, log returns in bps, causal rolling windows
6. **Footer**

**Animation:** `useScrollReveal` — `.reveal` elements fade-up on viewport entry

---

#### PAGE: `/brief` — Morning Brief

**Type:** Server Component (async)

**Data:** `getLatestBrief(supabase)` — newest `brief_log` row

**Sections:**
1. **Nav**
2. **Header** — Date of brief, "Morning Brief" label
3. **Brief Text** — Render `brief_text` with markdown-like parsing:
   - `## ` → H2
   - `# ` → H1
   - `---` → horizontal rule
   - `**bold**` → bold
   - Plain text → paragraph
4. **Dollar Dominance Index** — Horizontal stacked bar:
   - Width = `dollar_dominance` value (0-100)
   - Color: `#7a9e7a` (strong USD) or `#b87a7a` (weak USD)
   - Label: "Dollar Dominance: XX%"
5. **Per-Pair Regime Snapshot** — 3 cards showing:
   - Pair name
   - Regime label
   - Confidence %
   - Primary driver
   - Empty state if no data
6. **Footer**

**Conditional:** If `brief_text` is null/empty, show: "No brief available for today. Regime telemetry is updated daily in the terminal."

---

#### PAGE: `/performance`

**Type:** Server Component (async)

**Data:** `getValidationLog(supabase, 500)`

**Sections:**
1. **Nav**
2. **Equity Curve** — SVG area chart:
   - X-axis: date
   - Y-axis: cumulative directional return (mean of all pairs per day)
   - Fill: gradient from pair accent to transparent
   - Drawdown shading: red fill below previous peak
   - If data >24h old: dim with "STALE DATA" overlay
3. **Metrics Strip** — 4 stats:
   - 7D Accuracy: `rolling7dAccuracyPct()` + "%"
   - Cumulative Return: `equitySeries.ALL[last].cum * 100` + "%"
   - Calls Validated: `callsValidatedSince(launchDate)`
   - Avg Next-Day Return: `mean(actual_return_1d) * 10000` + "bps"
4. **Hit Rate by Horizon** — 3 bars:
   - T+1 (real data)
   - T+5 (placeholder: "Pending T+5 horizon")
   - T+20 (placeholder: "Pending T+20 horizon")
5. **Per-Pair Accuracy** — 3-column grid:
   - Each pair: accuracy %, total calls, wins, losses
   - Progress bar per pair
6. **Regime Performance Breakdown** — Table:
   - Regime | Calls | Hit % | Avg Ret | Max DD | Streak
7. **Monthly Breakdown** — Table: Month | Calls | Hit % | Avg Ret
8. **Full Validation Log** — `ValidationTable` component (dark tone, striped rows, green/red outcomes)
9. **Footer**

---

#### PAGE: `/methodology`

**Type:** Client Component

**Sections:**
1. **Nav**
2. **Composite Score Formula** — KaTeX-rendered:
   ```
   S = w_r · R + w_c · C + w_v · V + w_o · O + w_s · S
   ```
3. **Normalization** — Percentile math explanation
4. **Regime Threshold Table** — Thresholds for each tier
5. **Confidence Derivation** — Formula + explanation
6. **Sticky Sidebar** — Signal family details (RATE, COT, VOL, OI, SPECIAL)
7. **Footer**

**Conditional:** KaTeX gracefully falls back to raw LaTeX string if render fails.

---

### 5.2 TERMINAL PAGES (Dark Theme)

---

#### PAGE: `/terminal` — Terminal Overview

**Type:** Server Component (async)

**Data:** `getLatestRegimeCalls(supabase)`, `getLatestSignals(supabase)`

**Layout:** TerminalLayout (GlobalMacroPulse + TerminalNav + main content)

**Sections:**
1. **Cross-Pair Overview Grid** — 3 cards (EUR/USD, USD/JPY, USD/INR):
   - Spot price (large mono)
   - Regime label
   - Confidence bar
   - Day change % (color-coded)
   - Signal composite score (bipolar bar: -2 to +2)
2. **Active Strategy Strip** — FX-REGIME strategy card:
   - Status: ACTIVE
   - Last update: timestamp
   - Pairs covered: 3
   - Per-pair regime + confidence
3. **More Strategies** — Placeholder: "Phase 2+ strategies under development"

**Animation:** fade-up stagger on cards

---

#### PAGE: `/terminal/fx-regime` — FX-Regime Mosaic

**Type:** Client Component

**Data hooks:** `useLatestRegimeCalls()`, `useLatestSignals()`, `useLatestDeskOpenCardsSnapshot()`, `useG10CorrelationMatrix()`

**Layout:** Full-screen grid (`h-screen max-h-screen overflow-hidden`)

**Display:** 3×3 spatial grid:
- **Row 1:** Rank 1 (hero DeskCard), Rank 2 (MosaicCell), Rank 3 (MosaicCell)
- **Row 2:** Rank 4 (MosaicCell), Rank 5 (MosaicCell), Rank 6 (MosaicCell)
- **Row 3:** Rank 7 (MosaicCell), CorrelationMatrix, MacroDriftEngine

**MosaicCell:**
- If card exists: pair label, spot, regime, confidence bar
- If empty: invisible empty div (no "RANK · EMPTY" text)

**Hero DeskCard (Rank 1):**
- Full `DeskCard` component with `variant="hero"`
- Spot price with BinaryResolve animation
- Structural regime (large)
- Dominance array grid
- Markov probabilities
- Pain index with asymmetry warning if >80
- AI brief section (deterministic fallback text)
- `[ OPEN DESK → ]` button

**Interactions:**
- Hover on any cell: dims other cells to 30% opacity, grayscale
- Correlation glow: if hovering a pair, its top-correlated peer gets green bg tint
- Ghost whisper strip at bottom of hero card
- Sector-based column luminance dimming

**Loading:** 9 pulse skeleton divs
**Error:** `[ DATA_FLOW_INTERRUPTED ]` banner

---

#### PAGE: `/terminal/fx-regime/[pair]` — Pair Desk

**Type:** Server Component (async)

**Data:** `getLatestRegimeCalls(supabase)`, `getLatestSignals(supabase)`, `getHistoricalRegimeCalls(supabase, pair, 30)`

**Layout:** TerminalLayout

**Sections:**
1. **Top Strip** — Full width:
   - Left: Spot price (32px mono, tabular-nums), day change %
   - Center: Regime label (large, pair-colored if confidence ≥ 0.55 and directional)
   - Right: Confidence % + ConfidenceBar, Composite score (-2 to +2 bipolar bar)

2. **Trader's TL;DR** — Bordered card:
   - Bias: LONG / SHORT / NEUTRAL (from `rate_signal`)
   - Driver: `primary_driver`
   - Invalidation level: "Spot below X.XX"
   - Watchlist tags: 2-3 tags based on signal composition

3. **Signal Architecture Visualization** — Weighted horizontal bar:
   - RATE (40% for EUR/USD, 30% for USD/JPY, 30% for USD/INR)
   - COT (25% / 20% / 10%)
   - VOL (20% / 25% / 20%)
   - OI (10% / 15% / 10%)
   - SPECIAL (5% / 10% / 30%)
   - Each segment pair-colored with label

4. **Signal Chips** — Horizontal row:
   - RATE: `rate_signal` value
   - COT: `cot_percentile` + percentile label
   - VOL: `realized_vol_20d` + "ELEVATED" if >8
   - IV: `implied_vol_30d` vs `realized_vol_20d`
   - Crowding flag if `cot_percentile` >85 or <15

5. **Signals Table** — Table with rows:
   - Signal | Value | Z-Score | Trend
   - Rate Diff 2Y | value | z-score | →
   - COT Percentile | value | — | →
   - Realized Vol 20D | value | — | →
   - Cross-Asset VIX | value | — | →

6. **Sidebar** (right side, sticky):
   - **Other Desks:** RegimeCards for the other 2 pairs
   - **7D Regime History:** Dot grid (7 days, each dot = regime color)
   - **14D Confidence Sparkline:** SVG sparkline
   - **30D Regime Timeline:** Horizontal dot strip with regime labels

**OG Image:** Dynamic 1200×630 PNG with pair display, regime, confidence %

---

#### PAGE: `/terminal/performance` — Alpha Ledger

**Type:** Client Component

**Data hooks:** `useStrategyLedger(pair)`, `useUniverse()`

**Display:** Full-page alpha ledger inside terminal chrome
- Pair selector tabs (EUR/USD, USD/JPY, USD/INR)
- `AlphaLedger` component: regime-grouped grid
- Columns: Date, Regime, Direction, T+1, T+3, T+5, Brier (90d)
- Hit marks: `[ ✓ ]` white bold, `[ ✕ ]` gray, `[ = ]` neutral
- Brier sparkline per row (SVG, 90-day sliding window)
- Empty state: "No ledger rows for this pair."

---

#### PAGE: `/terminal/calendar` — Event Radar

**Type:** Client Component

**Data hooks:** `useEventRiskMatrices(pair)`, `useUpcomingMacroEvents()`, `useLatestSignals()`

**Display:**
- Pair selector (EUR/USD, USD/JPY, USD/INR)
- List of high-impact macro events for selected pair
- Each event row: Date, Event Name, Impact badge (HIGH/MEDIUM), MIE multiplier
- Expandable detail:
  - Sample size, median MIE multiplier
  - Beat/Miss/Inline median T+1 returns
  - Asymmetry ratio badge
  - Volatility profile
  - Execution note (static fallback text)
- Crisis mode: if `invalidation_triggered` for pair, show amber banner "CRISIS MODE — EXPANSION DISABLED"

---

#### PAGE: `/terminal/memos` — Research Memos

**Type:** Client Component

**Data hooks:** `useResearchMemosList()`

**Display:**
- Memo list (title + date)
- Click opens reader overlay modal
- Raw content in Georgia serif font
- Substack subscribe iframe at bottom
- Empty state: "No research memos available."

---

## SECTION 6: COMPONENT LIBRARY SPECIFICATION

### 6.1 Layout Components

#### `Nav` (Shell)
- Sticky, white bg `#ffffff`, border-bottom `#e5e5e5`
- Height: 64px
- Left: Logo + "FX Regime Lab"
- Right: Performance, Terminal (dropdown), Methodology, Brief, About
- Terminal dropdown: Overview, Mosaic, EUR/USD, USD/JPY, USD/INR, Calendar, Memos, Alpha Ledger
- Scroll-aware: adds subtle shadow on scroll
- Accessibility: `aria-expanded`, `aria-haspopup`, Escape key closes dropdown

#### `TerminalNav` (Terminal)
- Fixed, dark bg `#0c0a09`, border-bottom `#2a2725`
- Dynamic height `--terminal-nav-h` set by JS
- Row 1 (optional): Systemic cluster banner (amber) if `Systemic_Cluster` flag true
- Row 2 (optional): Systemic command strip — Ghost whisper, dollar dominance, idiosyncratic outlier, Polymarket top 3
- Row 3: Brand bar — LogoMark, "Terminal" label, PipelineHeartbeatTimer, refresh button, sync status
- Row 4: Breadcrumb + pair quick-jump tabs (with day change %)
- Pair tabs: EUR/USD, USD/JPY, USD/INR — active tab has pair-colored bottom border

#### `GlobalMacroPulse`
- Fixed at viewport top, z-[110]
- Height: 28px, bg `#000000`
- CSS marquee scrolling: DXY, US10Y, VIX, WTI with values and change indicators
- Duplicated content for seamless loop
- Pending: "SYNCING MACRO PULSE…" with pulse animation

#### `Footer` (Shell)
- 3-column grid
- Column 1: Navigation links
- Column 2: Transparency (Methodology, Performance — NO Audit link)
- Column 3: Substack subscribe form
- Substack form: email input → opens `https://fxregimelab.substack.com/?utm_source=website&utm_campaign=footer` with pre-filled email

---

### 6.2 UI Primitives

#### `ConfidenceBar`
```tsx
interface ConfidenceBarProps {
  value?: number; // 0-1
  tone?: 'dark' | 'light';
  color?: string; // pair color or accent
}
```
- Track: `#1e1e1e` (dark) / `#ebebeb` (light)
- Fill width: `value * 100%`
- Height: 3px (dark) / 2px (light)
- Transition: width 600ms

#### `Sparkline`
```tsx
interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fillOpacity?: number;
}
```
- SVG area + line
- Auto-color: `#7a9e7a` if end ≥ start, `#b87a7a` otherwise
- Stroke: 1.5px, round caps
- Fill opacity: 0.1

#### `BinaryResolve`
```tsx
interface BinaryResolveProps {
  value: string;
  resolveKey?: string;
  paused?: boolean;
  flickerMs?: number; // default 300
  tickMs?: number; // default 45
}
```
- On mount/key change: cycles random hex characters every 45ms for 300ms
- Then resolves to actual value with brief white luminance flash
- Font: mono, tabular-nums
- Skips animation if paused or value is "—"/"N/A"

#### `GhostResolve`
- Slower variant of BinaryResolve: 600ms flicker, 80ms ticks
- Final state: `#888` at 60% opacity
- Used for muted labels, correlation matrix headers

#### `TerminalLabel`
```tsx
interface TerminalLabelProps {
  children: string;
  limit?: number; // default 12
  prefix?: string;
  suffix?: string;
}
```
- Mono, 9px, tracking-widest, uppercase, tabular-nums
- Truncates with `…` if over limit
- `title` tooltip shows full text

#### `RegimeCard`
```tsx
interface RegimeCardProps {
  call?: LatestRegimeCallRow;
  signals?: LatestSignalRow;
  pairDisplay?: string;
}
```
- Dark bg `#0e0e0e`, left border 3px solid pair color
- Pair label: 11px mono, pair-colored, bold
- Spot: 18px mono, white
- Regime: 10px mono, bold, tracking-wide
- Confidence bar + CONF label + percentage
- Signal rows: RATE DIFF, COT PCT, RVOL 20D
- Regime accent only if confidence ≥ 0.55 and directional

#### `DeskCard`
```tsx
interface DeskCardProps {
  variant?: 'default' | 'hero';
  pairDisplay: string;
  spot: number | null;
  confidence: number | null;
  structuralRegime: string;
  dominanceArray: DominanceItem[];
  painIndex: number | null;
  markovProbabilities: MarkovPayload | null;
  aiBrief: string | null;
  telemetryAudit: TelemetryAuditPayload | null;
  invalidationTriggered: boolean;
  telemetryStatus: string;
  globalRank: number | null;
  apexScore: number | null;
  regimeAge: number | null;
  pausedBinaryResolve?: boolean;
  whisper?: string;
}
```
- Header: pair label + `[ ∫ ]` math inspector toggle
- Crisis/offline banners (amber/gray)
- Math inspector (collapsible): Rate Z (T), Rate Z (S), Pain Index, Dynamic Beta
- Hero spot price with BinaryResolve
- Structural regime (large, strikethrough if crisis)
- Dominance array grid: rank #1 highlighted, rest muted
- Markov probabilities: continuation % + transition list
- Asymmetry radar: warning if pain index > 80
- AI brief section (deterministic fallback JSON)
- Ghost whisper strip at bottom

#### `ValidationTable`
```tsx
interface ValidationTableProps {
  rows: ValidationTableRow[];
  tone?: 'light' | 'dark';
}
```
- 5 columns: DATE, PAIR, REGIME, OUTCOME, RET %
- Outcome colors: green correct, red incorrect
- Striped rows
- Font: mono for data, sans for headers

#### `AlphaLedger`
```tsx
interface AlphaLedgerProps {
  rows: AlphaLedgerRow[];
}
```
- Grouped by regime cycle
- Grid columns: Date, Regime, Direction, T+1, T+3, T+5, Brier (90d)
- Hit marks: `[ ✓ ]` white bold, `[ ✕ ]` gray, `[ = ]` neutral
- BrierSparkline sub-component: SVG sparkline with 0.25 threshold dashed line

#### `ConvexityRadar`
```tsx
interface ConvexityRadarProps {
  pair: string;
  events: MacroEventRow[];
  matrices: EventRiskMatrixRow[];
}
```
- Event list with expand/collapse
- Each event: date, name, impact badge, MIE multiplier
- Expanded detail:
  - ExhaustionZonesBar: gradient outer (95%), green inner (68%), 0% line
  - Tail risk ring animation on extreme events
  - Asymmetry badge: red border if bearish skew
- Crisis mode: amber banner, disables expansion

#### `CorrelationMatrix`
```tsx
interface CorrelationMatrixProps {
  matrix: G10CorrelationJson | null;
  pending?: boolean;
}
```
- 3×3 grid (only 3 pairs now)
- Green cells for positive correlation, red for negative
- Alpha: 0.12 + 0.55 * |correlation|
- Beveled borders
- GhostResolve for axis labels
- Tooltip on hover: exact correlation value
- Pending: "LOADING_MATRIX…"

#### `MacroDriftEngine`
- Dollar dominance delta with color-coded sign
- 5-day sparkline SVG
- Current dominance value
- Idiosyncratic outlier label with gentle pulse animation
- Pending: "SYNCING_BRIEF_LOG…"

#### `CommandPalette`
- Global `⌘K` / `Ctrl+K` toggle
- Centered modal overlay
- Filtered list of pages + pair desks
- Keyboard: ↑↓ navigate, ↵ teleport, Escape close
- BinaryResolve flickers target path during 150ms teleport delay
- Selected item: inverted colors (white bg, black text)

---

## SECTION 7: ANIMATION & MOTION SPECIFICATION

### 7.1 CSS Keyframes (in globals.css)

```css
@keyframes fade-up {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes gentle-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes ticker-marquee {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

@keyframes pulse-marquee {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

@keyframes tail-risk-pulse {
  0%, 100% { opacity: 0.6; box-shadow: 0 0 0 0 rgba(248, 113, 113, 0.4); }
  50% { opacity: 1; box-shadow: 0 0 0 8px rgba(248, 113, 113, 0); }
}

@keyframes omega-heartbeat {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
```

### 7.2 Animation Classes

| Class | Behavior |
|-------|----------|
| `.animate-fade-up` | 0.7s fade + translateY(24px→0) |
| `.animate-fade-in` | 0.6s fade |
| `.animate-gentle-pulse` | 3s infinite opacity pulse |
| `.animate-ticker-marquee` | 40s linear infinite translateX(-50%) |
| `.animate-pulse-marquee` | 30s linear infinite translateX(-50%) |
| `.animate-tail-risk-ring` | 2.2s infinite tail risk pulse |
| `.reveal` | Scroll-triggered fade-up (IntersectionObserver, threshold 0.15) |
| `.revealed` | Added by IntersectionObserver |
| `.hover-lift` | hover: translateY(-2px) + border transition |
| `.omega-haptic` | active: translateY(0.5px) scale(0.995) + inset shadow |

### 7.3 Framer Motion Patterns

```tsx
// Staggered container
const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } }
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] } }
};

// Sector dimming (terminal mosaic)
<motion.div animate={{ opacity: isFocused ? 1 : 0.3, filter: isFocused ? 'grayscale(0%)' : 'grayscale(100%)' }} />

// Math inspector height animation
<AnimatePresence>
  {open && <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} />}
</AnimatePresence>

// Macro drift outlier pulse
<motion.span animate={{ opacity: [1, 0.35, 1] }} transition={{ duration: 2, repeat: Infinity }} />
```

### 7.4 Motion Rules

- **Hero:** Animates on load with staggered delays (100ms)
- **Below fold:** IntersectionObserver-triggered reveals at threshold 0.15
- **What does NOT animate:** Spot prices (instant update), tables/data grids, navigation, validation ticker items
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` sets all animations to 0.01ms and reveals instantly

---

## SECTION 8: COPY & VOICE GUIDELINES

### 8.1 Tone
- Practitioner-built, not marketing
- High intellectual bar, concrete tone
- Numbers, dates, pairs, calls on the record
- Credibility compounds through calendar discipline and honest validation

### 8.2 Formatting Rules
1. **No Unicode em dashes (U+2014)** — use hyphens or sentence breaks
2. **Use numerals:** `87th percentile`, `5%`, not "eighty-seven"
3. **Timestamp format:** `YYYY-MM-DD` for data, `07:12 UTC` for pipeline runs
4. **Pair display:** `EUR/USD` (with slash), not `EURUSD` in user-facing strings
5. **Disclaimer:** All public pages need "Research and learning only. Not investment advice."

### 8.3 Forbidden Words
Never use in any public-facing file, comment, or copy:
- "student", "applicant", "NTU", "MFE"
- "learning journey", "built to learn", "framework demo"
- "AI-powered insights", "machine learning predictions"
- generic SaaS tropes: "unlock potential", "supercharge", "game-changing"

---

## SECTION 9: AGENT SWARM WORK ASSIGNMENTS

### Team A: Shell Surface (Light Theme)
**Agent A1:** Homepage (`/`) — Hero, Live Snapshot Cards, Validation Ticker, Manifesto, Signal Architecture, Validation Trust  
**Agent A2:** About (`/about`) + Methodology (`/methodology`) — Static content, KaTeX formulas, scroll reveals  
**Agent A3:** Brief (`/brief`) + Performance (`/performance`) — Daily brief rendering, equity curve SVG, validation tables, stats  
**Agent A4:** Shell Layout — Nav, Footer, CommandPalette, global CSS variables for light theme

### Team B: Terminal Surface (Dark Theme)
**Agent B1:** Terminal Layout — TerminalNav, GlobalMacroPulse, error boundaries, dark CSS variables  
**Agent B2:** Terminal Overview (`/terminal`) + FX-Regime Mosaic (`/terminal/fx-regime`) — Cross-pair grid, 3×3 mosaic, DeskCard, CorrelationMatrix, MacroDriftEngine  
**Agent B3:** Pair Desk (`/terminal/fx-regime/[pair]`) — Deep pair view, signal table, sidebar with regime history and sparklines, OG image  
**Agent B4:** Alpha Ledger (`/terminal/performance`) + Calendar (`/terminal/calendar`) + Memos (`/terminal/memos`) — Hit/miss grid, event radar, memo reader

### Team C: Shared Infrastructure
**Agent C1:** UI Primitives — ConfidenceBar, Sparkline, BinaryResolve, GhostResolve, TerminalLabel, RegimeCard, ValidationTable  
**Agent C2:** Data Layer — All TanStack Query hooks in `lib/queries.ts`, server queries in `lib/supabase/queries.ts`, type-safe Supabase client setup  
**Agent C3:** Design System — `globals.css` with all tokens, keyframes, utilities, layout.tsx with fonts, middleware.ts with pair slug rewrites  
**Agent C4:** Integration & QA — Build verification, type checking, dead code elimination, final polish

---

## SECTION 10: ACCEPTANCE CRITERIA

### Build Verification
- [ ] `npm run build` passes with zero errors
- [ ] `npm run lint` (biome check) passes
- [ ] `tsc --noEmit` passes (strict mode)

### Functional Verification
- [ ] Homepage shows exactly 3 pairs (EUR/USD, USD/JPY, USD/INR)
- [ ] Terminal mosaic shows exactly 3 pairs, no empty placeholder text
- [ ] All navigation links work; no 404s on public routes
- [ ] `/memo/[date]` returns 404 (disabled)
- [ ] `/audit` has no link in footer (page exists but unlinked)

### Data Verification
- [ ] `useUniverse()` filters to canonical 3 pairs even if DB has more
- [ ] All Supabase reads use generated types from `database.types.ts`
- [ ] No hand-written DB row interfaces anywhere
- [ ] All financial numbers use `tabular-nums`

### Design Verification
- [ ] Terminal is always dark (`#0c0a09` bg)
- [ ] Shell is light (`#f5f5f0` bg)
- [ ] No rounded corners above 2px
- [ ] 1px sharp borders only
- [ ] All pair accents use sacred colors (EUR/USD `#4BA3E3`, USD/JPY `#F5923A`, USD/INR `#FB923C`)
- [ ] Animations respect `prefers-reduced-motion`

### Copy Verification
- [ ] No forbidden words anywhere
- [ ] Disclaimer present on all public pages
- [ ] All pair displays use slash format (EUR/USD)
- [ ] No AI marketing language

---

## APPENDIX A: FILE STRUCTURE (TARGET)

```
web/src/
├── app/
│   ├── layout.tsx              # Root layout: fonts, providers, command palette
│   ├── page.tsx                # Homepage (shell)
│   ├── about/page.tsx          # About (shell)
│   ├── brief/page.tsx          # Morning Brief (shell)
│   ├── performance/page.tsx    # Performance (shell)
│   ├── methodology/page.tsx    # Methodology (shell)
│   ├── audit/page.tsx          # Audit (shell, unlinked)
│   ├── calendar/page.tsx       # Redirect to terminal/calendar
│   ├── memo/[date]/page.tsx    # Memo viewer (disabled)
│   ├── terminal/
│   │   ├── layout.tsx          # Terminal layout: pulse + nav
│   │   ├── page.tsx            # Terminal overview
│   │   ├── error.tsx           # Error boundary
│   │   ├── fx-regime/page.tsx  # Mosaic
│   │   ├── fx-regime/[pair]/
│   │   │   ├── page.tsx        # Pair desk
│   │   │   ├── layout.tsx      # Pair desk layout
│   │   │   └── opengraph-image.tsx # OG image
│   │   ├── performance/page.tsx # Alpha Ledger
│   │   ├── calendar/page.tsx   # Event Radar
│   │   └── memos/page.tsx      # Research Memos
│   └── api/
│       ├── connect-desk/route.ts
│       └── linkedin-alpha-hook/route.ts
├── components/
│   ├── layout/
│   │   ├── command-palette.tsx
│   │   ├── global-macro-pulse.tsx
│   │   ├── terminal-nav.tsx
│   │   └── ny-pipeline-run.ts
│   ├── shell/
│   │   ├── Nav.tsx
│   │   └── Footer.tsx
│   ├── regime/
│   │   ├── RegimeCard.tsx
│   │   └── ValidationTable.tsx
│   ├── pages/
│   │   ├── convexity-radar-page-content.tsx
│   │   └── performance-ledger-page-content.tsx
│   └── ui/
│       ├── alpha-ledger.tsx
│       ├── confidence-bar.tsx
│       ├── sparkline.tsx
│       ├── BinaryResolve.tsx
│       ├── GhostResolve.tsx
│       ├── desk-card.tsx
│       ├── convexity-radar.tsx
│       ├── correlation-matrix.tsx
│       ├── macro-drift-engine.tsx
│       ├── macro-pulse-bar.tsx
│       ├── memo-sidebar.tsx
│       ├── systemic-cluster-banner.tsx
│       ├── TerminalLabel.tsx
│       ├── logo-mark.tsx
│       └── utils.ts
├── hooks/
│   ├── useLocalSettings.ts
│   ├── useReducedMotion.ts
│   └── useScrollReveal.ts
├── lib/
│   ├── constants.ts            # PAIRS, BRAND, REGIME_HEATMAP_COLORS
│   ├── mockData.ts             # Re-export from constants (backward compat)
│   ├── pairProfiles.ts         # Pair profile metadata
│   ├── g10Correlation.ts       # Correlation matrix helpers
│   ├── queries.ts              # TanStack Query hooks
│   ├── validation-format.ts    # Validation display formatting
│   ├── utils.ts                # General utilities
│   └── supabase/
│       ├── client.ts           # Browser Supabase client
│       ├── server.ts           # Server Component client
│       ├── database.types.ts   # Generated types
│       └── queries.ts          # Server-side query helpers
├── middleware.ts               # Pair slug rewrites
└── app/globals.css             # All design tokens, keyframes, utilities
```

---

## APPENDIX B: QUICK REFERENCE

| Need to build... | See Section... |
|------------------|----------------|
| Light shell page | 5.1 |
| Dark terminal page | 5.2 |
| Layout component | 6.1 |
| UI primitive | 6.2 |
| Data fetching | 4.3 |
| Animation | 7 |
| Copy/voice | 8 |
| Color tokens | 3.1 |
| Typography | 3.2 |
| File structure | Appendix A |

---

*End of specification. Build with discipline.*
