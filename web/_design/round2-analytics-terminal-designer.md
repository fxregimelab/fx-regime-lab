# Analytics & Terminal Design Specification
## FX Regime Lab — Round 2 Design Document

**Author:** Lead Analytics & Terminal Designer  
**Date:** 2026-05-05  
**Status:** Design Specification — Ready for Implementation  
**Classification:** Round 2 Deliverable

---

## 0. Design Thesis

> **"The terminal is not a dashboard. It is a Bloomberg Terminal crossed with a quant research desk — warm, rigorous, and never dull."**

This document specifies the redesign of three critical surfaces:
1. **`/performance`** — The credibility engine (currently 6/10)
2. **`/terminal`** — The cross-pair command station (currently 7/10)
3. **`/terminal/fx-regime/[pair]`** — The pair desk (currently 7/10)

All specifications derive from Round 1 consensus: Obsidian Stone palette, motion-as-information, monospace data discipline, and "Bernstein for the open web."

---

## 1. Performance Dashboard Spec (`/performance`)

### 1.1 Page Architecture

```
PERFORMANCE PAGE
├── Header (title + subtitle + last-updated timestamp)
├── Equity Curve Panel           ← NEW — P0
├── Metrics Strip (4 cards)
├── Hit Rate by Horizon          ← NEW — P1
├── Regime Performance Breakdown ← NEW — P1
├── Drawdown + Sharpe Panel      ← NEW — P1
├── Streak Indicator             ← NEW — P1
├── Validation Log Table         ← ENHANCED
└── Footer (disclaimer)
```

**Container:** `max-w-[1152px] mx-auto px-6 pt-28 pb-20`  
**Background:** `var(--color-void)`  
**Section gap:** `mb-10` between major panels  
**Border rule:** All panels use `border border-[var(--color-border)]` with `bg-[var(--color-surface)]`

---

### 1.2 Equity Curve Component

**Position:** First visual element below header. This is the single most important trust signal on the site.

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ EQUITY CURVE — CUMULATIVE DIRECTIONAL RETURN                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │  [ line chart with regime bands + drawdown shading ]   │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│ [7D] [30D] [90D] [ALL]              Max DD: -2.4%  │  Vol: 8.2% │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
| Property | Value |
|----------|-------|
| **Chart height** | `320px` (desktop), `240px` (mobile) |
| **Chart library** | Lightweight Charts by TradingView (already installed) |
| **Background** | `#000000` (pure black inside chart pane for contrast) |
| **Grid** | `vertLines: #111111`, `horzLines: #111111` |
| **Line color** | Pair-agnostic `#d6d3d1` (warm silver) — this is aggregate performance |
| **Line width** | `2px` |
| **Area fill** | `topColor: rgba(214,211,209,0.08)`, `bottomColor: rgba(214,211,209,0.01)` |
| **Crosshair** | LargeDashed, `#555`, label visible |
| **Price scale** | Right side, `minimumWidth: 80`, formatted to 2 decimal places |

#### Data Requirements
```typescript
// From validation_log + signals (chronological)
interface EquityCurvePoint {
  time: string;           // ISO date
  value: number;          // Cumulative return % from directional calls
  drawdown: number;       // Current drawdown from peak
  pair?: string;          // Optional: for per-pair overlay
}

// Calculation logic (server-side preferred):
// 1. Filter validation_log rows where correct_1d !== null
// 2. Sort by date ascending
// 3. Cumsum of actual_return_1d (directional sign applied)
// 4. Track running peak; drawdown = (current / peak) - 1
```

#### Regime Band Overlay
Same technique as `TradingViewChart.tsx` — segment price data by regime and render transparent `AreaSeries` behind the equity line:

| Regime | Band Color |
|--------|-----------|
| STRONG USD STRENGTH | `rgba(30,58,95,0.12)` |
| MODERATE USD STRENGTH | `rgba(45,90,142,0.10)` |
| NEUTRAL | `rgba(58,58,58,0.08)` |
| MODERATE USD WEAKNESS | `rgba(122,63,31,0.10)` |
| VOL_EXPANDING | `rgba(122,92,0,0.10)` |

#### Drawdown Shading
When equity is below running peak, fill area between line and peak with `rgba(184,122,122,0.06)` — subtle red haze. **Do not hide drawdowns.**

#### Time Range Selector
- Buttons: `[ 7D ] [ 30D ] [ 90D ] [ ALL ]`
- Style: `font-mono text-[10px] tracking-widest`, border `#333`, bg `#000000`
- Active: `text-white`, Inactive: `text-[#888]`
- Default: `90D`

#### Bottom Stats Row (inside panel)
- `Max Drawdown: -2.4%` in `--color-down` if negative
- `Volatility (ann): 8.2%`
- `Best Month: +4.1%`
- `Worst Month: -1.8%`
- All in `font-mono text-[10px] text-[var(--color-text-muted)]`

#### Animation
- **Line draw:** On mount, line draws left-to-right over `1.2s` with `INSTITUTIONAL_SETTLE`
- **Area fade:** Fill opacity `0 → 1` over `0.6s`, delayed `0.4s`
- **Range switch:** Crossfade `0.22s` `CRISP_EASE` — no jarring snap
- **Skeleton:** Exact-match skeleton with `animate-pulse bg-[#111]` on chart pane before data loads

---

### 1.3 Metrics Strip

**Current implementation is good. Enhance with live data integrity.**

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ 7D ACCURACY │ AVG NEXT-DAY│ CUMULATIVE  │ CALLS       │
│    72.4%    │   +0.18%    │   +4.86%    │    27       │
│  19/27 cor  │ per call    │ since Apr   │  3 pairs    │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

#### Changes from Current
| Change | Detail |
|--------|--------|
| **Cumulative Return** | Computed from actual equity curve, not `avgReturn * total`. Currently wrong. |
| **Timestamp** | Add `font-mono text-[9px] text-[var(--color-text-dim)]` below strip: `UPDATED 2026-05-05 14:32 UTC` |
| **Stale indicator** | If data > 24h old, strip gets `opacity-50` and a `[ STALE ]` badge in `--color-warn` |
| **Mini sparkline** | Add 30-day accuracy sparkline (30px high) inside the 7D Accuracy card |

#### Data Requirements
```typescript
// From validation_log
{
  accuracy7d: number;      // correct_1d / total in last 7 days
  avgReturn: number;       // mean(actual_return_1d)
  cumulativeReturn: number;// cumsum(actual_return_1d) — NOT avg * count
  totalCalls: number;      // count of validated calls
  lastUpdated: string;     // max(created_at) from validation_log
}
```

---

### 1.4 Hit Rate by Horizon (T+1 / T+5 / T+20)

**New component. Leverages existing `strategy_ledger` data.**

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ HIT RATE BY HORIZON                                         │
│                                                             │
│  T+1 (next day)    ████████████████████░░░░  68.2%  (19/27) │
│  T+5 (1 week)      ████████████████░░░░░░░░  58.3%  (14/24) │
│  T+20 (1 month)    ██████████░░░░░░░░░░░░░░  41.7%  (10/24) │
│                                                             │
│  [ hover: show confidence interval ]                        │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Bars:** Horizontal, track height `4px`, fill height `4px`
- **Track color:** `var(--color-panel)` (`#242220`)
- **Fill color:** Gradient from `var(--color-up)` (left) to `var(--color-warn)` (right) — but use solid colors:
  - `≥ 60%` → `var(--color-up)`
  - `40–60%` → `var(--color-warn)`
  - `< 40%` → `var(--color-down)`
- **Bar width:** `max(120px, 40%)` of panel
- **Numbers:** `font-mono text-[13px] tabular-nums`, label + fraction right-aligned
- **Labels:** `font-mono text-[10px] tracking-[0.15em] uppercase`

#### Data Requirements
```typescript
// From strategy_ledger
interface HorizonHitRate {
  horizon: 'T+1' | 'T+5' | 'T+20';
  hitRate: number;      // t1_hit, t5_hit aggregated (exclude nulls)
  hits: number;
  trials: number;
}
// Note: T+20 may have fewer trials — show honest count, not inflated percentages
```

#### Animation
- Bars grow from `width: 0` on scroll-reveal
- Duration: `0.7s`, easing: `INSTITUTIONAL_SETTLE`
- Stagger: `150ms` between horizons

---

### 1.5 Regime-Specific Performance Breakdown

**New component. Shows where edge exists and where it doesn't.**

#### Layout
```
┌──────────────────────────────────────────────────────────────────┐
│ REGIME PERFORMANCE                                               │
│                                                                  │
│  REGIME                    CALLS  HIT%  AVG RET  MAX DD  STREAK │
│  ─────────────────────────────────────────────────────────────── │
│  STRONG USD STRENGTH         4    75%   +0.42%   -0.8%   W2     │
│  MODERATE USD STRENGTH      11    64%   +0.21%   -1.2%   W1     │
│  NEUTRAL                     6    50%   +0.03%   -0.4%   L1     │
│  MODERATE USD WEAKNESS       4    50%   -0.08%   -1.5%   L2     │
│  VOL_EXPANDING               2    50%   +0.15%   -0.3%   W1     │
│                                                                  │
│  [ click regime → filter validation log below ]                  │
└──────────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Table style:** Same as existing ValidationTable — monospace, striped rows, no rounded corners
- **Header:** `font-mono text-[9px] tracking-[0.15em] uppercase`, bg `var(--color-elevated)`
- **Hit% column:** Color-coded: `≥ 60%` green, `40–60%` amber, `< 40%` red
- **Avg Ret:** Green for positive, red for negative, always show sign
- **Max DD:** Always red — losses are not shameful, they are data
- **Streak:** `W2` in green, `L2` in red. No streak = `—`
- **Row hover:** `bg-[var(--color-elevated)]`, cursor pointer, filters validation log on click

#### Data Requirements
```typescript
// From strategy_ledger + validation_log (joined by date+pair)
interface RegimePerformance {
  regime: string;
  calls: number;
  hitRate: number;       // t1_hit mean
  avgReturn: number;     // mean actual_return
  maxDrawdown: number;   // worst single-day return in this regime
  currentStreak: { type: 'W' | 'L'; count: number } | null;
}
```

---

### 1.6 Brier Score Trend

**Already exists in `AlphaLedger`. Extract and elevate.**

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ BRIER SCORE TREND (LOWER = BETTER CALIBRATION)              │
│                                                             │
│  1.0 ┤                                          ╭─╮        │
│  0.8 ┤                              ╭─╮        ╭╯ ╰╮       │
│  0.6 ┤            ╭─╮              ╭╯ ╰╮      ╭╯   │       │
│  0.4 ┤  ╭─╮      ╭╯ ╰╮    ╭─╮     ╭╯   ╰────╭╯    │       │
│  0.2 ┤──╯ ╰──────╯   ╰────╯ ╰─────╯           ╰────╯       │
│  0.0 ┼────────────────────────────────────────────────────  │
│       └────┬────┬────┬────┬────┬────┬────┬────┬────┬──→   │
│      30D trailing window · updated daily                   │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Chart type:** Lightweight Charts `LineSeries`, no area fill
- **Baseline:** Dashed line at `y = 0.25` ("well-calibrated" threshold), `#333`
- **Line color:** Dynamic by latest value:
  - `< 0.25` → `#7a9e7a` (green, well calibrated)
  - `0.25–0.5` → `#a8947a` (amber, acceptable)
  - `> 0.5` → `#b87a7a` (red, poorly calibrated)
- **Height:** `120px`
- **No price scale label** — this is a secondary metric

#### Data Requirements
```typescript
// From strategy_ledger.brier_score_t5
// 30-day rolling average, plotted daily
interface BrierPoint {
  time: string;
  value: number;  // avg brier_score_t5 over trailing 30 days
}
```

---

### 1.7 Drawdown Display + Sharpe-Like Ratio

#### Layout (side-by-side cards, 2-col grid)
```
┌────────────────────────────┐  ┌────────────────────────────┐
│ MAX DRAWDOWN               │  │ SHARPE-LIKE RATIO          │
│                            │  │                            │
│      -3.8%                 │  │       1.24                 │
│                            │  │                            │
│  3 days to recover         │  │  (return / vol, 90d)       │
│  Longest: -5.2% (12d)      │  │  Sortino: 1.87             │
└────────────────────────────┘  └────────────────────────────┘
```

#### Visual Spec
- **Max Drawdown:** Large number in `var(--color-down)`, always honest
- **Recovery time:** Days from trough back to peak
- **Longest drawdown:** Historical worst, with duration
- **Sharpe-like:** `(mean return / std dev) * sqrt(252)` — label it "Sharpe-Like" to avoid claiming true Sharpe
- **Sortino:** Same but downside deviation only
- **Both ratios:** Green if `> 1.0`, amber if `0.5–1.0`, red if `< 0.5`

#### Data Requirements
```typescript
// Computed from equity curve series
interface DrawdownStats {
  currentDrawdown: number;     // % from peak
  maxDrawdown: number;         // historical worst
  maxDrawdownDuration: number; // days
  recoveryTime: number | null; // days to recover from current (null if still underwater)
}

interface RiskRatios {
  sharpeLike: number;    // annualized, 90-day lookback
  sortino: number;       // annualized, downside dev only
  calmar: number;        // ann return / max DD
}
```

---

### 1.8 Win Streak / Loss Streak Indicator

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ STREAK                                                      │
│                                                             │
│  CURRENT:  [ W I N  S T R E A K ]  3 calls                  │
│                                                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  longest W: 5     │
│  ━━━━━━━━━━━━━━━━╺━━━━━━━━━━━━━━━━━━━━━━━  longest L: 3     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Current streak:** Large text. Green glow for win, red for loss.
- **Streak bars:** Horizontal bars showing proportion of longest streak
  - Bar color: `var(--color-up)` for wins, `var(--color-down)` for losses
- **Typography:** `font-mono text-[11px] tracking-[0.15em]`

#### Data Requirements
```typescript
// From validation_log, sequential by date
interface StreakStats {
  currentStreak: { type: 'W' | 'L'; count: number };
  longestWinStreak: number;
  longestLossStreak: number;
  totalWinningDays: number;
  totalLosingDays: number;
}
```

---

### 1.9 Monthly Performance Table

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ MONTHLY BREAKDOWN                                             │
│                                                             │
│  MONTH      CALLS  HITS  MISS  HIT%  AVG RET  CUM RET       │
│  ───────────────────────────────────────────────────────────│
│  2026-04      12     8     4   67%   +0.22%   +2.64%       │
│  2026-03       9     5     4   56%   +0.11%   +1.62%       │
│  2026-02       6     4     2   67%   +0.31%   +1.24%       │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Table:** Same styling as ValidationTable
- **Month:** `YYYY-MM` format
- **Hit%:** Color-coded green/amber/red
- **Avg Ret:** Color-coded by sign
- **Cum Ret:** Running cumulative, always shown
- **Row hover:** Highlight row, show tooltip with best/worst single call of month

#### Data Requirements
```typescript
// From validation_log, grouped by month
interface MonthlyRow {
  month: string;       // "2026-04"
  calls: number;
  hits: number;
  misses: number;
  hitRate: number;
  avgReturn: number;
  cumulativeReturn: number;  // running from inception
}
```

---

### 1.10 Validation Log Table — Enhanced

**Current table is good. Add these enhancements:**

| Enhancement | Spec |
|-------------|------|
| **Link to brief** | Each row gets a "VIEW" link → `/brief?date=YYYY-MM-DD` or `/memo/[date]` |
| **Filter chips** | Above table: `[ All ] [ EUR/USD ] [ USD/JPY ] [ USD/INR ] [ STRONG STR ] [ NEUTRAL ]` |
| **Pair color** | Pair name in its pair color (EUR/USD in `#8fa8bc`, etc.) |
| **Return sparkline** | Mini 5-day return sparkline per row (if data available) |
| **Outcome badge** | `✓ CORRECT` in green, `✗ INCORRECT` in red — bold |
| **Date sort** | Click header to sort asc/desc |
| **Pagination** | 50 rows per page, not infinite scroll |

---

## 2. Terminal Index Spec (`/terminal`)

### 2.1 Page Architecture

```
TERMINAL INDEX
├── Ticker Header (3 pairs, always visible)
├── Live Indicators Strip
├── Strategy Cards
│   ├── FX-REGIME (active)
│   ├── PHASE 2+ placeholder
│   └── Future strategies...
├── Quick Actions Row
└── Performance Summary Widget  ← NEW
```

**Background:** `#000000` (pure black for terminal context shift)  
**Padding:** `px-6 md:px-8`, top offset for nav: `pt-[calc(var(--terminal-nav-h)+24px)]`

---

### 2.2 Cross-Pair Ticker Layout

**Current implementation is close. Refine for density and actionability.**

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ LIVE CROSS-PAIR OVERVIEW · UPDATED 14:32 UTC                │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  EUR/USD    │  │  USD/JPY    │  │  USD/INR    │         │
│  │   1.0847    │  │   147.32    │  │   83.42     │         │
│  │  +0.12%     │  │  -0.08%     │  │  +0.04%     │         │
│  │             │  │             │  │             │         │
│  │ MOD STR     │  │ NEUTRAL     │  │ MOD DEP     │         │
│  │ CONF 62%    │  │ CONF 48%    │  │ CONF 71%    │         │
│  │ ████████░░  │  │ ██████░░░░  │  │ █████████░  │         │
│  │             │  │             │  │             │         │
│  │ [ OPEN → ]  │  │ [ OPEN → ]  │  │ [ OPEN → ]  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Grid:** `grid-template-columns: repeat(3, 1fr)`, gap `1px`, bg `var(--color-border)`
- **Cell bg:** `var(--color-surface)`, hover: `var(--color-elevated)`
- **Pair label:** `font-mono text-[10px] font-bold tracking-wider`, pair color
- **Spot price:** `font-mono text-[28px] font-medium tracking-tight tabular-nums`
- **Day change:** `font-mono text-[10px] font-medium`, green/red by sign
- **Regime:** `font-mono text-[10px] font-medium tracking-wider`
- **Confidence:** `font-mono text-[9px]`, + ConfidenceBar component
- **Click target:** Entire cell is clickable to pair desk

#### Live Timestamp
Below ticker grid:
```
<span className="font-mono text-[9px] text-[var(--color-text-dim)] tracking-wider">
  PIPELINE INGESTED 2026-05-05 06:14 UTC · VALIDATED 14:32 UTC
</span>
```

---

### 2.3 Live Indicators Strip

**New component. Shows system health at a glance.**

```
┌─────────────────────────────────────────────────────────────┐
│ ● SYNCED  │  COT AGE: 2D  │  VIX: 18.4  │  DXY: 104.2      │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Height:** `28px` (same as global pulse)
- **Background:** `var(--color-surface)`
- **Border:** `border-t border-b border-[var(--color-border)]`
- **Items:** Inline flex, separated by `│` divider in `var(--color-text-dim)`
- **Sync dot:** `w-[5px] h-[5px] rounded-full`
  - Green `#7a9e7a` = synced (data < 2h old)
  - Amber `#a8947a` = stale (2–24h old)
  - Red `#b87a7a` = interrupted (> 24h old)
- **Text:** `font-mono text-[9px] tracking-wider`

#### Data Requirements
```typescript
// From useCrossAssetPulse + useLastPipelineRun
interface LiveIndicators {
  syncStatus: 'synced' | 'stale' | 'interrupted';
  cotAgeDays: number;      // days since last COT release
  vix: number | null;
  dxy: number | null;
  lastPipelineRun: string; // ISO timestamp
}
```

---

### 2.4 Strategy Cards

**Current implementation is good. Enhance active card with performance preview.**

#### FX-REGIME Active Card Enhancement
Add a performance strip inside the card, below pair summaries:

```
┌─────────────────────────────────────────────────────────────┐
│ ACTIVE  FX-REGIME                                    Open → │
├─────────────────────────────────────────────────────────────┤
│ [pair summaries — existing]                                 │
├─────────────────────────────────────────────────────────────┤
│  7D HIT RATE: 72%  │  30D: 68%  │  T+5: 58%  │  BRIER: 0.18│
│  [ mini sparkline of 30d accuracy ]                         │
├─────────────────────────────────────────────────────────────┤
│  ● Pipeline: 2026-05-05                                     │
└─────────────────────────────────────────────────────────────┘
```

#### Data Refresh Rules
| Data | Refresh |
|------|---------|
| Strategy card hit rates | Daily after validation (06:00–07:00 UTC typical) |
| Sparkline | On page load + every 5 minutes |
| Pipeline timestamp | Static from SSR, no polling |

---

### 2.5 Quick Actions Row

**New component. Keyboard-shortcut-aware action strip.**

```
┌─────────────────────────────────────────────────────────────┐
│ QUICK ACTIONS                                               │
│                                                             │
│  [ View Mosaic ]  [ View Ledger ]  [ Today's Brief ]        │
│  [ ⌘K Command ]  [ ? Shortcuts ]                            │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Buttons:** `font-mono text-[10px] tracking-widest`, border `#222`, bg `#000000`
- **Hover:** `bg-[#080808] text-white`
- **Shortcuts hint:** `?` opens shortcut modal (existing Command Palette)

---

## 3. Pair Desk Spec (`/terminal/fx-regime/[pair]`)

### 3.1 Page Architecture

```
PAIR DESK (e.g., EUR/USD)
├── Top Data Strip (4 metrics)
├── Signal Architecture Visualization  ← NEW
├── TradingView Chart + Regime Bands   ← NEW (embed existing)
├── Historical Regime Timeline         ← ENHANCED
├── Trader's Context Strip             ← NEW
├── Confidence Sparkline               ← ENHANCED
├── Signal Table                       ← ENHANCED
├── Invalidation Level Display         ← NEW
├── Related Pairs Sidebar              ← ENHANCED
└── Primary Driver Display             ← ENHANCED
```

---

### 3.2 Top Data Strip Layout

**Current 4-column grid is correct. Reorder for scan priority.**

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ SPOT PRICE   │ REGIME       │ CONFIDENCE   │ COMPOSITE    │
│ 1.0847       │ MOD STR      │ 62%          │ +0.84        │
│ +0.12% today │ PRIMARY: RATE│ ████████░░   │ [====|====] │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

#### Metric Order & Priority
| Position | Metric | Why |
|----------|--------|-----|
| 1 | **Spot Price** | Immediate market context |
| 2 | **Regime** | The call itself |
| 3 | **Confidence** | How sure the system is |
| 4 | **Composite** | Signal strength magnitude |

#### Changes from Current
- **Add primary driver below regime:** `font-mono text-[9px] text-[var(--color-text-muted)] truncate`
- **Add day change below spot:** Keep existing
- **Confidence bar:** Use pair color for fill (existing)
- **Composite bar:** Center marker at 0, green right, red left (existing)

---

### 3.3 Signal Architecture Visualization

**New component. Shows the 4 signal families and their contribution to today's composite.**

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ SIGNAL ARCHITECTURE · COMPOSITE: +0.84                      │
│                                                             │
│  RATE DIFF    ████████████████████████████  40%  BULLISH   │
│  COT POSITION ██████████████████░░░░░░░░░░  30%  NEUTRAL   │
│  VOL REGIME   ████████████░░░░░░░░░░░░░░░░  20%  NORMAL    │
│  RISK REV     ██████░░░░░░░░░░░░░░░░░░░░░░  10%  ─        │
│                                                             │
│  [ hover row → show raw value and z-score ]                 │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Container:** `border border-[var(--color-border)] bg-[var(--color-surface)]`
- **Rows:** 4 rows, one per signal family
- **Bar track:** `bg-[var(--color-panel)]`, height `4px`
- **Bar fill:** Pair color at `80% opacity`
- **Weight label:** `font-mono text-[9px] text-[var(--color-text-muted)]` (fixed: 40/30/20/10)
- **Signal value:** `font-mono text-[11px]`
  - `BULLISH` / `BEARISH` / `NEUTRAL` / `ELEVATED` / `NORMAL`
  - Color-coded: green for bullish, red for bearish, muted for neutral
- **Row hover:** `bg-[var(--color-elevated)]`, tooltip shows raw signal value

#### Data Requirements
```typescript
// From regime_calls row + signals row
interface SignalArchitecture {
  rate: { weight: 0.40; signal: 'BULLISH' | 'BEARISH' | 'NEUTRAL'; raw: number | null; zscore: number | null };
  cot:  { weight: 0.30; signal: 'BULLISH' | 'BEARISH' | 'NEUTRAL'; raw: number | null; percentile: number | null };
  vol:  { weight: 0.20; signal: 'ELEVATED' | 'NORMAL' | 'CONTRACTING'; raw: number | null };
  rr:   { weight: 0.10; signal: string | null; raw: number | null };
}
```

#### Animation
- Bars stagger in on mount: `50ms` delay per row
- Duration: `0.5s`, easing: `INSTITUTIONAL_SETTLE`

---

### 3.4 TradingView Chart + Regime Bands

**Embed existing `TradingViewChart` component. Add regime-change markers.**

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ PRICE · YIELD SPREAD · COT POSITION                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [ Lightweight Charts: 3-pane synced layout ]        │   │
│  │                                                     │   │
│  │  Price pane (280px) with regime band overlay       │   │
│  │  ─────────────────────────────────────────────────  │   │
│  │  Yield pane (120px)                                │   │
│  │  ─────────────────────────────────────────────────  │   │
│  │  COT pane (120px)                                  │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│  [ 1M ] [ 1Y ] [ MAX ]                                      │
└─────────────────────────────────────────────────────────────┘
```

#### Enhancements to Existing Chart
1. **Regime-change markers:** Vertical dashed lines on price pane where regime changed
   - Line: `1px dashed rgba(214,211,209,0.2)`
   - Label at top: `font-mono text-[8px] text-[var(--color-text-dim)]`
2. **Current regime highlight:** Right edge of chart shows current regime label
3. **Spot price color:** Use pair color instead of generic blue

#### Data Requirements
```typescript
// Already provided by TradingViewChart props
// regimeData: Array<{ date: string; regime: string }>
// From getHistoricalRegimeCalls(supabase, pair, 90)
```

---

### 3.5 Historical Regime Timeline

**Current implementation shows 7 days. Expand to 30 days with visual encoding.**

#### Layout
```
┌─────────────────────────────────────────────────────────────┐
│ REGIME HISTORY (30D)                                        │
│                                                             │
│  Apr 05  ████  MOD STR   62%  [═] correct  +0.12%          │
│  Apr 04  ████  MOD STR   58%  [═] correct  +0.08%          │
│  Apr 03  ████  NEUTRAL   48%  [═] ─        +0.02%          │
│  Apr 02  ████  MOD STR   61%  [═] correct  +0.15%          │
│  ...                                                        │
│                                                             │
│  [══] = validated outcome  ·  click row → replay mode       │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Rows:** Expand from 7 to 30 days, scrollable container `max-h-[400px]`
- **Date:** `font-mono text-[10px] text-[var(--color-text-muted)]`
- **Regime color block:** `w-8 h-3` filled with regime color from `REGIME_HEATMAP_COLORS`
- **Regime text:** `font-mono text-[10px] text-[var(--color-text)]`
- **Confidence:** `font-mono text-[10px]`, pair color
- **Outcome indicator:** Small square
  - Green fill = correct
  - Red fill = incorrect
  - Grey outline = pending validation
- **Return:** `font-mono text-[10px]`, color by sign

#### Data Requirements
```typescript
// Join regime_calls + validation_log by date+pair
interface RegimeHistoryRow {
  date: string;
  regime: string;
  confidence: number;
  outcome: 'correct' | 'incorrect' | 'pending';
  returnPct: number | null;
  spot: number | null;
}
```

---

### 3.6 Trader's Context Strip

**New component. The "TL;DR" Marcus needs.**

```
┌─────────────────────────────────────────────────────────────┐
│ TRADER'S CONTEXT                                            │
│                                                             │
│  BIAS:        Moderate USD Strength (EUR/USD bearish)       │
│  DRIVER:      Rate differential widening (US 2Y +12bp)      │
│  INVALIDATION: Spot closes above 1.0920 (confidence < 50%)  │
│  WATCH:       US 2Y yield, ECB speakers, NFP Fri            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Container:** `border-l-2 border-[var(--color-warn)] bg-[var(--color-elevated)]`
- **Labels:** `font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase`
- **Values:** `font-mono text-[11px] text-[var(--color-text-secondary)]`
- **Invalidation:** If triggered, border turns `var(--color-down)`, text gets `line-through`

#### Data Requirements
```typescript
// From desk_open_cards
interface TraderContext {
  bias: string;              // structural_regime translated to directional bias
  driver: string;            // primary_driver
  invalidationLevel: number | null;  // computed or from telemetry
  watchlist: string[];       // derived from event_risk_matrices
}
```

---

### 3.7 Confidence Sparkline

**Current sparkline is good. Enhance with annotations.**

#### Enhancements
1. **Add horizontal threshold line at 50%:** `1px dashed #333`
2. **Color gradient:** Below 50% = faded pair color; above 50% = full pair color
3. **Current value dot:** `r=3` circle at latest point, pair color
4. **Labels at ends:** Start date left, end date right, `font-mono text-[9px] text-[var(--color-text-dim)]`
5. **Height:** Increase from `50px` to `70px`

---

### 3.8 Signal Table

**Current table is functional but raw. Add visual encoding.**

#### Enhanced Layout
```
┌─────────────────────────────────────────────────────────────┐
│ SIGNALS TABLE                                               │
├─────────────────────────────────────────────────────────────┤
│ METRIC                    VALUE          Z-SCORE   TREND    │
├─────────────────────────────────────────────────────────────┤
│ Rate differential 2Y      +1.24%         +1.8      ↑        │
│ COT net position pctile   72             +0.6      →        │
│ Realized vol 20d          8.2%           +0.4      →        │
│ Realized vol 5d           7.8%           +0.2      →        │
│ Implied vol 30d           9.1%           +0.8      ↑        │
│ Signal composite          +0.84          +1.2      ↑        │
│ Spot                      1.0847         —         →        │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Encoding
- **Z-SCORE column:** Color-coded
  - `|z| > 2` → bold, pair color
  - `|z| > 1` → normal weight
  - `|z| < 1` → muted
- **TREND column:** Mini arrow sparkline (3-day)
  - `↑` = rising, `→` = flat, `↓` = falling
  - Color: green for rising, red for falling
- **Row zebra:** Alternate `var(--color-void)` / `var(--color-surface)`

---

### 3.9 Invalidation Level Display

**New component. Shows when the call is no longer valid.**

```
┌─────────────────────────────────────────────────────────────┐
│ INVALIDATION                                                │
│                                                             │
│  LEVEL:     1.0780 (spot below = regime shift risk)         │
│  STATUS:    ● ACTIVE                                        │
│  DISTANCE:  -0.62% from spot                                │
│                                                             │
│  [████████████░░░░░░░░] 62% to invalidation                 │
└─────────────────────────────────────────────────────────────┘
```

#### Visual Spec
- **Status dot:** Green `#7a9e7a` = active, Red `#b87a7a` = triggered
- **Distance bar:** Track `var(--color-panel)`, fill `var(--color-warn)`
- **Triggered state:** Entire panel gets `border-color: var(--color-down)`, regime text struck through

#### Data Requirements
```typescript
// From desk_open_cards.telemetry_audit or computed
interface InvalidationData {
  level: number | null;
  status: 'active' | 'triggered';
  distancePct: number;       // (spot - level) / level * 100
}
```

---

### 3.10 Related Pairs Sidebar

**Current "Other Desks" is cramped. Expand and add correlation signal.**

#### Enhanced Layout
```
┌─────────────────────────────────┐
│ OTHER DESKS                     │
├─────────────────────────────────┤
│ USD/JPY                         │
│ 147.32  NEUTRAL  CONF 48%       │
│ [══] weakly correlated (+0.32)  │
├─────────────────────────────────┤
│ USD/INR                         │
│ 83.42   MOD DEP  CONF 71%       │
│ [══] uncorrelated (-0.08)       │
└─────────────────────────────────┘
```

#### Visual Encoding
- **Correlation line:** `[══]` length = strength, color = sign (green positive, red negative)
- **Regime card:** Existing `RegimeCard` component, but with more breathing room (`p-4` instead of `p-3`)
- **Click:** Navigates to pair desk

---

## 4. Charting Strategy

### 4.1 Chart Type Decision Matrix

| Visualization | Chart Type | Library | Rationale |
|---------------|-----------|---------|-----------|
| **Equity Curve** | Line + Area + Band overlay | Lightweight Charts | Time-series, needs crosshair, regime bands |
| **Hit Rate Bars** | Horizontal bar (custom DOM) | None (CSS) | Simple comparison, no interactivity needed |
| **Regime Heatmap** | Custom grid of divs | None (DOM) | Categorical x time, needs tooltips |
| **Confidence Trend** | Sparkline (SVG) | Custom `Sparkline` | Already exists, enhance |
| **Brier Trend** | Line | Lightweight Charts | Time-series, needs baseline |
| **Signal Architecture** | Horizontal stacked bar (custom DOM) | None (CSS) | Static weights, visual comparison |
| **Price + Yield + COT** | Multi-pane synced | Lightweight Charts | Already implemented |
| **Monthly Performance** | Table + mini bar | None (DOM) | Precision first, chart secondary |

### 4.2 Library Recommendation: Lightweight Charts by TradingView

**Primary rationale:** Already installed. Already used in `TradingViewChart.tsx`. Purpose-built for financial time-series.

#### Why Not Recharts?
- Recharts is React-native but heavier. Lightweight Charts is canvas-based = smoother at high data density.
- Financial formatting (price scales, time axes) is built-in.

#### Why Not D3?
- D3 is overkill for this scope. We need 4 chart surfaces, not 40.
- Maintenance burden is higher.

#### Why Not TradingView Widget Embed?
- Widget is good for `/terminal/fx-regime/[pair]` price context (already exists as fallback).
- But it cannot show regime bands, equity curves, or Brier scores.
- Use widget for "market price" chart; use Lightweight Charts for "system analytics" charts.

### 4.3 Color Coding for Charts (Dark Background)

| Semantic | Hex | Usage |
|----------|-----|-------|
| **Up / Bullish / Correct** | `#7a9e7a` | Positive returns, correct calls, rising trends |
| **Down / Bearish / Incorrect** | `#b87a7a` | Negative returns, incorrect calls, falling trends |
| **Neutral / Warning** | `#a8947a` | Neutral regime, stale data, mid-range values |
| **Primary line** | `#d6d3d1` | Equity curve, main signal line |
| **Grid** | `#111111` | Chart grid lines |
| **Crosshair** | `#555555` | Hover indicator |
| **Text** | `#8a8a8a` | Axis labels |
| **Background** | `#000000` | Chart pane (pure black for contrast) |
| **Regime bands** | See 1.2 | Transparent fills behind price |

### 4.4 Animation Strategy for Chart Entry

| Chart | Entrance | Duration | Easing |
|-------|----------|----------|--------|
| Equity curve | Line draws L→R | `1.2s` | `INSTITUTIONAL_SETTLE` |
| Area fill | Opacity `0 → 1` | `0.6s` | `ease-out`, delay `0.4s` |
| Regime bands | Fade in with line | `0.8s` | `ease-out`, delay `0.6s` |
| Hit rate bars | `width: 0 → final` | `0.7s` | `INSTITUTIONAL_SETTLE` |
| Brier sparkline | Static render | `0s` | No animation (scanned, not watched) |
| Confidence sparkline | Static render | `0s` | Container fades in |

**Rule:** Charts animate once on mount. Data updates crossfade; lines do not redraw.

### 4.5 Responsive Chart Behavior

| Breakpoint | Behavior |
|------------|----------|
| `≥ 1024px` (desktop) | Full height, all panes visible |
| `768–1023px` (tablet) | Reduce chart height by 20%, stack sidebars below |
| `< 768px` (mobile) | Single column, charts scroll horizontally if needed, hide COT pane behind toggle |

**Chart resize:** Use `autoSize: true` in Lightweight Charts. Listen to container resize via ResizeObserver.

### 4.6 Exact Chart Specs Summary

#### Equity Curve
```typescript
const equityChartOptions = {
  layout: {
    background: { type: ColorType.Solid, color: '#000000' },
    textColor: '#8a8a8a',
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 10,
  },
  grid: { vertLines: { color: '#111111' }, horzLines: { color: '#111111' } },
  crosshair: {
    vertLine: { color: '#555', style: LineStyle.LargeDashed, width: 1, labelVisible: true },
    horzLine: { color: '#555', style: LineStyle.LargeDashed, width: 1, labelVisible: true },
  },
  rightPriceScale: { minimumWidth: 80, borderColor: '#111111' },
  timeScale: { borderColor: '#111111', timeVisible: false },
  autoSize: true,
};

const equitySeriesOptions = {
  color: '#d6d3d1',
  lineWidth: 2,
  priceLineVisible: false,
  lastValueVisible: true,
};

const areaSeriesOptions = {
  topColor: 'rgba(214,211,209,0.08)',
  bottomColor: 'rgba(214,211,209,0.01)',
  lineColor: 'transparent',
  lastValueVisible: false,
};
```

#### Hit Rate Bars (CSS)
```css
.hit-rate-track {
  background: #242220;
  height: 4px;
  width: 100%;
}
.hit-rate-fill {
  height: 100%;
  transition: width 0.7s cubic-bezier(0.16, 1, 0.3, 1);
}
.hit-rate-fill.good { background: #7a9e7a; }
.hit-rate-fill.mid { background: #a8947a; }
.hit-rate-fill.poor { background: #b87a7a; }
```

#### Regime Heatmap (DOM)
```typescript
// Cell: w-3.5 h-7 (desktop), w-3 h-6 (mobile)
// Gap: 2px
// Color: REGIME_HEATMAP_COLORS[regime]
// Tooltip: native title attribute with date + regime
// Animation: stagger 30ms per cell, opacity 0→1, scale 0.95→1, 200ms, CRISP_EASE
```

---

## 5. Data Visualization Principles

### 5.1 Numbers vs Charts vs Tables

| Question Type | Best Format | Example |
|---------------|-------------|---------|
| "What's the trend?" | **Chart** | Equity curve, Brier trend |
| "What's the exact value?" | **Number** | Spot price, confidence % |
| "How does X compare to Y?" | **Bar chart** | Hit rate by horizon, regime performance |
| "What happened on date D?" | **Table** | Validation log, monthly breakdown |
| "What's the distribution?" | **Heatmap** | Regime history, correlation matrix |
| "Is this abnormal?" | **Sparkline + number** | Z-score with trend arrow |

**Rule:** If a user needs to copy-paste the value, use a table or number. If they need to see shape, use a chart. Never put a chart where a number is faster.

### 5.2 Color Usage for Data

| Color | Meaning | Never Use For |
|-------|---------|---------------|
| `#7a9e7a` (green) | Up, correct, bullish, synced, active | Decorative elements, neutral data |
| `#b87a7a` (red) | Down, incorrect, bearish, error, loss | Warnings (use amber), neutral data |
| `#a8947a` (amber) | Warning, stale, neutral, mid-range | Success states, errors |
| `#d6d3d1` (silver) | Primary accent, active nav, focused input | Body text, backgrounds |
| `#f5f5f4` (white) | Primary text, important numbers | Labels, metadata |
| `#a8a29e` (grey) | Secondary text, headers | Primary data |
| `#78716c` (muted) | Timestamps, labels, disabled | Active data |

**Critical rule:** Green always means "up/correct." Red always means "down/incorrect." Amber is the only escape hatch for "neither."

### 5.3 Monospace for All Numbers Rule

**Every numeric display must use `font-mono` with `tabular-nums`.** This includes:
- Spot prices
- Percentages
- Dates (`YYYY-MM-DD`)
- Timestamps
- Confidence values
- Table cells
- Chart axis labels

**Why:** Tabular figures prevent layout shift on update. A number changing from `1.08` to `1.09` should not move surrounding text.

**Exception:** Editorial text (about page, methodology preamble) may use proportional nums in body copy. Data never does.

### 5.4 Significant Figures Rule

| Data Type | Format | Example |
|-----------|--------|---------|
| Spot (EUR/USD, GBP/USD) | 4 decimal places | `1.0847` |
| Spot (USD/JPY) | 2 decimal places | `147.32` |
| Percentage return | 2 decimal places, always show sign | `+0.18%`, `-1.24%` |
| Percentage (hit rate) | 1 decimal place | `72.4%` |
| Confidence | Integer percent | `62%` |
| Z-score | 1 decimal place | `+1.8` |
| Brier score | 2 decimal places | `0.18` |
| Date | `YYYY-MM-DD` | `2026-05-05` |
| Timestamp | `YYYY-MM-DD HH:mm UTC` | `2026-05-05 14:32 UTC` |

**Rule:** No rounding theater. `72.4%` not `~72%`. Precision signals rigor.

### 5.5 Empty State for Missing Data

| Scenario | Display |
|----------|---------|
| No equity curve data yet | Flat line at 0 with label: `INSUFFICIENT DATA (N < 5)` |
| No validation for a regime | Row shows `—` for all columns |
| Missing spot price | `—` (em dash), not `0` or `N/A` |
| Missing confidence | Bar at 0%, text `—` |
| Stale data (> 24h) | `opacity-50` + `[ STALE ]` badge |
| Failed fetch | `DATA UNAVAILABLE` in red, retry button |
| Loading | Skeleton matching final dimensions exactly |

**Skeleton spec:**
- Use `animate-pulse bg-[#111]` (not generic skeleton colors)
- Match exact final width/height of data element
- Never use generic loading spinners

---

## 6. Live Data Strategy

### 6.1 What Updates in Real-Time?

**Nothing updates faster than 60 seconds.** This is a daily research system, not a trading platform.

| Data | Refresh Rate | Source | Rationale |
|------|-------------|--------|-----------|
| Spot prices | Every 60s | Supabase `signals` | Intraday context, not critical |
| Day change % | Every 60s | Supabase `signals` | Derived from spot |
| Live indicators | Every 60s | Supabase `signals` | VIX, DXY, etc. |
| Sync status | Every 60s | Supabase `regime_calls` | Pipeline health |

### 6.2 What Updates Daily?

| Data | Refresh Time | Source |
|------|-------------|--------|
| Regime calls | ~06:00–07:00 UTC | Pipeline batch |
| Validation outcomes | ~14:00–15:00 UTC | Post-market close |
| Strategy ledger | ~14:00–15:00 UTC | Post-validation |
| Brief | ~06:00–07:00 UTC | Pipeline batch |
| COT data | Weekly (Fri) | CFTC release |

### 6.3 What Is Static?

| Data | Loaded |
|------|--------|
| Historical prices (MAX) | On demand, cached indefinitely |
| Methodology | Build-time |
| About page | Build-time |
| Regime transition matrix | Compute weekly, cache |

### 6.4 Loading State for Async Data

| Component | Loading State |
|-----------|---------------|
| Equity curve | Skeleton pane `320x100%`, `animate-pulse bg-[#111]` |
| Metrics strip | Skeleton boxes matching 4-card grid |
| Hit rate bars | Track bars visible at 0% fill, labels show `—` |
| Validation table | Skeleton rows (10), exact row height match |
| Chart panes | Text: `Loading Historical Archive...` (existing pattern) |
| Pair desk | Top strip shows `—`, panels show skeletons |

### 6.5 Stale Data Indicator

```
┌─────────────────────────────────┐
│ [ STALE ] · LAST UPDATE 24H AGO │
└─────────────────────────────────┘
```

- **Trigger:** Data timestamp > 24 hours old
- **Style:** `font-mono text-[9px] tracking-widest`, border `var(--color-warn)`, text `var(--color-warn)`
- **Placement:** Top of affected panel, inline with title
- **Affected panels:** Gray out with `opacity-50`, no `pointer-events`

### 6.6 Error State for Failed Fetches

```
┌─────────────────────────────────────────────────────────────┐
│ [ DATA_FLOW_INTERRUPTED ]                                   │
│                                                             │
│  Could not load strategy ledger.                            │
│                                                             │
│  [ RETRY ]                                                  │
└─────────────────────────────────────────────────────────────┘
```

- **Style:** `font-mono text-[11px] text-[#ef4444]` (red, but calm)
- **Button:** `border border-[#333] bg-[#000000] font-mono text-[10px]`
- **Behavior:** Retry with exponential backoff (2s, 4s, 8s)
- **No alerts:** Error is inline, never a modal or toast

---

## 7. Mobile Analytics

### 7.1 Philosophy

> **"Dense data dashboards do not shrink — they restructure."**

The terminal on mobile is not a "smaller desktop." It is a **priority-ordered data stream** where the most actionable information appears first, and secondary data is one tap away.

### 7.2 Performance Page — Mobile

| Section | Mobile Treatment |
|---------|-----------------|
| **Equity curve** | Full width, `240px` height, range selector below |
| **Metrics strip** | 2×2 grid instead of 4×1 |
| **Hit rate bars** | Stack vertically, full width |
| **Regime breakdown** | Horizontal scroll table, sticky header |
| **Brier sparkline** | Full width, `100px` height |
| **Drawdown + Sharpe** | Stack vertically |
| **Streak** | Full width, large text |
| **Monthly table** | Horizontal scroll, first 3 columns sticky |
| **Validation log** | Card-based list (not table), 10 per page |

#### Validation Log — Mobile Card Format
```
┌─────────────────────────────┐
│ 2026-05-04    EUR/USD       │
│ MOD STR          ✓ correct  │
│ +0.12%                      │
│ [ View Brief → ]            │
└─────────────────────────────┘
```

### 7.3 Terminal Index — Mobile

| Element | Mobile Treatment |
|---------|-----------------|
| **Ticker grid** | Horizontal swipe carousel, 1 pair per viewport width |
| **Live indicators** | Marquee scroll (existing `MacroPulseBar`) |
| **Strategy cards** | Full width, collapsed by default, tap to expand |
| **Quick actions** | Bottom sticky bar (existing `TerminalMobileBottomNav`) |

### 7.4 Pair Desk — Mobile

| Element | Mobile Treatment |
|---------|-----------------|
| **Top strip** | 2×2 grid instead of 4×1 |
| **Signal architecture** | Full width, tap row to expand raw values |
| **TradingView chart** | Single pane (price only), toggle for yield/COT |
| **Regime timeline** | Horizontal scrollable timeline (not vertical list) |
| **Trader's context** | Full width, always expanded |
| **Signal table** | Accordion: tap metric to expand detail |
| **Related pairs** | Horizontal swipe cards |
| **Confidence sparkline** | Full width, `50px` height |

#### Mobile Horizontal Regime Timeline
```
◀ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ▶
  │ May │ │ May │ │ May │ │ May │
  │  02 │ │  03 │ │  04 │ │  05 │
  │MOD  │ │NEU  │ │MOD  │ │MOD  │
  │ 61% │ │ 48% │ │ 58% │ │ 62% │
  └─────┘ └─────┘ └─────┘ └─────┘
```

### 7.5 Touch Targets

| Element | Minimum Size |
|---------|-------------|
| Buttons | `44×44px` |
| Table rows | `48px` height |
| Cards | Full width tap target |
| Chart crosshair | Disabled on touch (show on tap instead) |

### 7.6 Mobile-Specific Motion

- **Reduce motion:** On mobile, halve all animation durations (equity curve draw: `0.6s` instead of `1.2s`)
- **No parallax:** Already banned, but especially on mobile
- **Swipe gestures:** Enable horizontal swipe between pair desks (EUR/USD → USD/JPY → USD/INR)

---

## 8. Component Inventory

### 8.1 New Components to Build

| Component | File | Reuses |
|-----------|------|--------|
| `EquityCurveChart` | `components/charts/equity-curve-chart.tsx` | Lightweight Charts, `useEquityCurve` |
| `HitRateHorizon` | `components/charts/hit-rate-horizon.tsx` | CSS bars only |
| `RegimePerformanceTable` | `components/charts/regime-performance-table.tsx` | ValidationTable styling |
| `BrierSparklineChart` | `components/charts/brier-sparkline-chart.tsx` | Lightweight Charts |
| `DrawdownPanel` | `components/charts/drawdown-panel.tsx` | Numbers only |
| `StreakIndicator` | `components/charts/streak-indicator.tsx` | CSS bars |
| `MonthlyTable` | `components/charts/monthly-table.tsx` | ValidationTable styling |
| `SignalArchitecture` | `components/charts/signal-architecture.tsx` | CSS bars |
| `TradersContextStrip` | `components/charts/traders-context-strip.tsx` | Static layout |
| `InvalidationDisplay` | `components/charts/invalidation-display.tsx` | CSS bar |
| `LiveIndicatorsStrip` | `components/charts/live-indicators-strip.tsx` | `useCrossAssetPulse` |
| `MobileRegimeTimeline` | `components/charts/mobile-regime-timeline.tsx` | Horizontal scroll |

### 8.2 Existing Components to Enhance

| Component | Enhancement |
|-----------|-------------|
| `Sparkline` | Add threshold line, end-dot, date labels |
| `ValidationTable` | Add filters, pair colors, brief links, pagination |
| `ConfidenceBar` | No changes needed |
| `TradingViewChart` | Add regime-change markers, pair-colored spot line |
| `RegimeHeatmap` | Rewrite for dark theme (currently light-only) |
| `PerformanceLedgerPageContent` | Merge into unified `/performance` |

### 8.3 Hooks / Queries to Add

```typescript
// lib/queries.ts additions:

export function usePerformanceMetrics() {
  // Aggregates: accuracy7d, avgReturn, cumulativeReturn, totalCalls, lastUpdated
}

export function useHorizonHitRates() {
  // From strategy_ledger: t1_hit, t5_hit aggregated
}

export function useRegimePerformance() {
  // Grouped by regime with streaks, max drawdown per regime
}

export function useBrierTrend() {
  // 30-day rolling Brier from strategy_ledger
}

export function useDrawdownStats() {
  // From equity curve: max DD, recovery time, current DD
}

export function useStreakStats() {
  // Sequential analysis of validation_log
}

export function useMonthlyBreakdown() {
  // validation_log grouped by YYYY-MM
}
```

---

## 9. Implementation Priority

### P0 — Must Ship (blocks credibility)
1. **Equity curve on `/performance`** — Single most impactful change
2. **Fix cumulative return calculation** — Current math is wrong
3. **Add timestamp + stale indicator** — Honesty about data freshness
4. **Regime heatmap dark theme rewrite** — Currently light-only, jarring in terminal

### P1 — High Impact (next sprint)
5. Hit rate by horizon
6. Regime-specific performance breakdown
7. Signal architecture visualization on pair desk
8. Trader's context strip
9. Enhanced validation table (filters, links, pagination)
10. Mobile regime timeline

### P2 — Depth (polish)
11. Brier score trend chart
12. Drawdown + Sharpe panel
13. Streak indicator
14. Monthly performance table
15. Invalidation level display
16. Download CSV from performance

---

## 10. Success Criteria

| Criterion | Target | How to Measure |
|-----------|--------|---------------|
| Time-to-equity-curve | ≤ 2 seconds from landing `/performance` | LCP on equity pane |
| Mobile validation log usability | Can verify a call in 3 taps | User flow test |
| Data accuracy | Zero hardcoded financial data | Code audit |
| Stale data transparency | 100% of panels show timestamp | Visual audit |
| Terminal engagement | ≥ 40% of sessions enter `/terminal/*` | Analytics |
| Performance page engagement | ≥ 60% scroll to validation log | Scroll depth |

---

*End of Analytics & Terminal Design Specification*
*Next step: Engineering review → Component breakdown → Implementation sprint*
