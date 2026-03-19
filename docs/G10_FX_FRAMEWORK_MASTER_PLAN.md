# G10 FX REGIME DETECTION FRAMEWORK
## Master Implementation Plan — March 2026
### Shreyash Sakhare | Personal Research & Practice Project

---

## SECTION 0 — PROJECT IDENTITY AND PURPOSE

This is a personal FX research framework built to understand and practice
institutional-grade FX analysis. The goal is to build something that
functions the way a real desk tool functions — not a tutorial, not a demo,
but a working analytical pipeline that produces genuine signals and
renders them in a way a practitioner would actually read.

The framework detects FX regimes for EUR/USD, USD/JPY, and USD/INR by
layering rate differentials, speculative positioning, volatility, and
commodity/macro signal layers. Every signal added must earn its place —
it must be analytically meaningful, not decorative.

This document is the master context file. It exists so that any AI
coding assistant (Claude Code or otherwise) can understand the full
architecture, design philosophy, column naming conventions, layout rules,
and implementation plan without needing to re-establish context from
scratch. Keep this file updated as phases complete.

---

## SECTION 1 — CURRENT STATE (AS OF MARCH 2026)

### What Is Live And Working
- EUR/USD, USD/JPY, USD/INR pair cards with three-tab navigation
  (FUNDAMENTALS / POSITIONING / VOL & CORRELATION)
- Rate differentials: US-DE 10Y, US-DE 2Y, US-JP 10Y, US-JP 2Y,
  US-IN 10Y, US-IN Policy Spread
- COT positioning: Leveraged Money + Asset Manager for EUR and JPY
  with 3-year percentile rank
- 30D realized volatility with 3-year percentile for EUR and JPY
- 60D regime correlation (spread changes vs FX price changes)
- Plotly interactive charts — 7 total, embedded in brief via tab system
  - EUR/USD: fundamentals (price + spreads), positioning (2 subplots),
    vol & correlation (vol + corr subplots)
  - USD/JPY: same three charts
  - USD/INR: fundamentals only (no positioning, no vol — data gaps)
- Dark theme HTML brief deployed to GitHub Pages
- Status bar: DXY, Brent, Gold, COT date, Next COT date, timestamps
- Refactored project structure: core/, charts/, reports/, config.py,
  paths.py, run.py with argparse flags
- Key levels S3/S2/S1/R1/R2/R3 displayed as text per pair

### What Is Confirmed Fixed
- Plotly vertical line rendering bug (removed `matches: 'x2'` from xaxis)
- Timestamp serialization (Pandas Timestamps now converted to YYYY-MM-DD
  strings before passing to Plotly traces)
- Container measurement bug (explicit width/height via default_width /
  default_height in pio.to_html)
- Tab visibility (switched from display:none/block to
  visibility:hidden/visible + position:absolute/relative)

### What Is Confirmed Fixed (Phase Pre-1)
- Brent and Gold fetching added to pipeline.py (yfinance BZ=F / GC=F)
- Brent, Gold, and all chg_* columns now live in latest_with_cot.csv
- Commodity prices shown in morning summary terminal output

### Known Gaps
- USD/INR has no commodity or macro signal layers
- FPI flow data unavailable (SEBI JS-rendered, Playwright deferred)
- No composite regime score per pair
- Key levels are text-only, not drawn on Plotly price chart
- No 200D moving average on price panels
- No commodity correlation signals (oil, gold, DXY decomp) — data ready, pipeline pending
- No BTP-Bund spread (eurozone fragmentation signal)
- No macro calendar awareness
- HTML brief data rows not auto-refreshed from CSV (left column numbers are from prior HTML template)

---

## SECTION 2 — PROJECT FILE STRUCTURE

```
fx_regime/
├── run.py                       ← pipeline orchestration, argparse --only/--skip
├── config.py                    ← TODAY, PAIRS registry, CB_EVENTS calendar
├── core/
│   ├── utils.py                 ← shared formatters: ordinal, fmt_pct, color_class
│   └── paths.py                 ← DATA_DIR, BRIEFS_DIR, brief_html(), etc.
├── charts/
│   ├── base.py                  ← _load_and_filter, _base_layout, _style_axes
│   ├── registry.py              ← CHART_REGISTRY dict
│   └── create_charts_plotly.py  ← build_fundamentals_chart,
│                                   build_positioning_chart,
│                                   build_vol_correlation_chart
├── data/
│   └── latest_with_cot.csv      ← master data file, never edit manually
├── briefs/
│   └── brief_YYYYMMDD.html      ← daily output
├── pipeline.py                  ← Layer 1: yields, spreads, vol, correlations
├── cot_pipeline.py              ← Layer 2: CFTC COT disaggregated data
├── inr_pipeline.py              ← USD/INR specific: IN yields, RBI, FPI
├── create_html_brief.py         ← HTML brief assembly and chart injection
└── deploy.py                    ← GitHub Pages push
```

### File Ownership Rules
- `pipeline.py` — add new price-based signals, correlations, commodity data
- `inr_pipeline.py` — all India-specific data (RBI, FPI, IN yields)
- `create_charts_plotly.py` — add new chart functions or modify existing
- `create_html_brief.py` — layout, display rows, text formatting
- `config.py` — add new pairs, update CB_EVENTS calendar each quarter
- `data/latest_with_cot.csv` — READ ONLY, never modify manually
- Never add a new file without a clear reason

---

## SECTION 3 — COLUMN REGISTRY (MASTER REFERENCE)

### Confirmed Existing Columns in latest_with_cot.csv
```
FX prices:    EURUSD, USDJPY, DXY, USDINR
Yields:       US_2Y, US_10Y, DE_2Y, DE_10Y, JP_2Y, JP_10Y
              IN_10Y (FBIL daily; FRED monthly fallback), IN_repo_proxy
Spreads:      US_DE_10Y_spread, US_DE_2Y_spread
              US_JP_10Y_spread, US_JP_2Y_spread
              US_IN_10Y_spread, US_IN_policy_spread
              US_curve (US10Y - US2Y)
COT Lev:      EUR_net_pos, EUR_net_pct_oi, EUR_percentile
              EUR_lev_long, EUR_lev_short
              JPY_net_pos, JPY_net_pct_oi, JPY_percentile
              JPY_lev_long, JPY_lev_short
COT AM:       EUR_assetmgr_net, EUR_assetmgr_pct_oi, EUR_assetmgr_percentile
              EUR_assetmgr_long, EUR_assetmgr_short
              JPY_assetmgr_net, JPY_assetmgr_pct_oi, JPY_assetmgr_percentile
              JPY_assetmgr_long, JPY_assetmgr_short
Vol:          EURUSD_vol30, USDJPY_vol30, USDINR_vol30
              EURUSD_vol_pct, USDJPY_vol_pct, USDINR_vol_pct
Correlation:  EURUSD_spread_corr_60d, USDJPY_spread_corr_60d
              EURUSD_corr_percentile, USDJPY_corr_percentile
FX changes:   EURUSD_chg_1D, EURUSD_chg_1W, EURUSD_chg_1M, EURUSD_chg_12M
              (same pattern for USDJPY, DXY, USDINR)
Commodity:    Brent, Gold
              Brent_chg_1D, Brent_chg_1W, Brent_chg_1M, Brent_chg_3M, Brent_chg_12M
              Gold_chg_1D, Gold_chg_1W, Gold_chg_1M, Gold_chg_3M, Gold_chg_12M
              (fetched via yfinance: BZ=F for Brent, GC=F for Gold)
```

### Columns To Be Added By Phase (exact names, case-sensitive)
```
Phase 1:  oil_eurusd_corr_60d, oil_usdjpy_corr_60d, oil_inr_corr_60d
Phase 2:  dxy_eurusd_corr_60d, dxy_usdjpy_corr_60d, dxy_inr_corr_60d
Phase 3:  EURUSD_corr_20d, USDJPY_corr_20d
Phase 4:  gold_usdjpy_corr_60d, gold_inr_corr_60d, gold_seasonal_flag
Phase 5:  rbi_reserve_chg_1w, rbi_intervention_flag
Phase 6:  fpi_net_weekly_cr, fpi_net_4w_cr, fpi_flow_flag
Phase 9:  IT_10Y, BTP_Bund_spread, BTP_Bund_flag
```

---

## SECTION 4 — LAYOUT ARCHITECTURE AND VISUAL DESIGN

### Design Philosophy
The brief is practitioner-first. Every layout decision serves information
density and readability. The reader scans the left column for numbers,
uses the right column charts for context and pattern, reads the regime
section last for synthesis. The layout must support that reading pattern
without requiring navigation or explanation.

Dark theme is fixed throughout:
```
Page background:    #0a0a0a
Card background:    #111111
Card border:        #1e1e1e
Grid lines:         #1e1e1e
Label text:         #888888
Value text:         #ffffff
Positive change:    #00d4aa  (teal)
Negative change:    #ff4444  (red)
```
These values do not change. All additions must work within this palette.

### Current Brief Structure (Top To Bottom)
```
┌─────────────────────────────────────────────────────────────────────┐
│  STATUS BAR — DXY | Brent | Gold | COT: date | Next COT: date | ts  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  G10 FX REGIME DETECTION FRAMEWORK                                  │
│  Morning Brief — Weekday, DD Month YYYY          data as of: ...    │
│                                                  pipeline run: ...  │
└─────────────────────────────────────────────────────────────────────┘

[optional: MACRO EVENT STRIP — only when CB event within 7 days]

┌─────────────────────────────────────────────────────────────────────┐
│  PAIR CARD — EUR/USD                                                │
│ ┌────────────────────────┐  ┌──────────────────────────────────────┐│
│ │  EUR/USD  1.1697        │  │ FUNDAMENTALS | POSITIONING | VOL&COR ││
│ │  -0.90%  12M: +10.82%  │  │                                      ││
│ │                         │  │  [ACTIVE PLOTLY CHART — 400px tall]  ││
│ │  RATE DIFFERENTIALS     │  │                                      ││
│ │  US-DE 10Y  0.71%  -1.24│  │                                      ││
│ │  US-DE 2Y   1.44%  -0.74│  │                                      ││
│ │                         │  │                                      ││
│ │  POSITIONING (COT)      │  │                                      ││
│ │  Lev Money  +36,797  94th│  │                                      ││
│ │  Asset Mgr  +395,311  79th│  │                                      ││
│ │                         │  │                                      ││
│ │  VOLATILITY & CORRELATION│  │                                      ││
│ │  30D Vol    8.7%    64th │  │                                      ││
│ │  60D Corr  -0.205  BRKN  │  │                                      ││
│ │                         │  │                                      ││
│ │  REGIME READ            │  │                                      ││
│ │  [3-4 sentence text]    │  │                                      ││
│ └────────────────────────┘  └──────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘

[PAIR CARD — USD/JPY]   (same structure)
[PAIR CARD — USD/INR]   (same structure, fewer signal rows)

[FOOTER]
```

### Column Layout Proportions
Left column: 38% width — all text metrics, section headers, regime read.
Right column: 62% width — tabbed chart area.
This ratio is calibrated. Do not change it. New signal rows always go
into the left column following existing row format.

### Left Column Row Format (Strict Pattern)
Every data row follows this exact visual pattern:
```
[SECTION LABEL]                        ← uppercase, #444444, small tracking
[METRIC LABEL]    [VALUE]    [CHANGE]  [BADGE]
```

Metric label: `#888888`, small, uppercase tracking
Value: `#ffffff`, medium weight
Change: teal `#00d4aa` if positive-directional, red `#ff4444` if negative
Badge: pill, see badge color system below

All new signal rows added in Phases 1-9 must match this pattern exactly.
Do not introduce new row formats without explicit layout discussion.

### Badge Color System (Fixed)
```
CROWDED LONG      bg #2a1a00   text #f0a500   (amber)
CROWDED SHORT     bg #2a0000   text #e05c5c   (red)
NEUTRAL           bg #1a1a1a   text #666666   (gray)
BROKEN            bg #2a0000   text #ff4444   (red)
INTACT            bg #002a1a   text #00d4aa   (teal)
ELEVATED          bg #2a1a00   text #f0a500   (amber)
EXTREME           bg #2a0000   text #ff4444   (red)
NORMAL            bg #1a1a1a   text #888888   (gray)
DOLLAR REGIME     bg #1a1a2a   text #4da6ff   (blue)
EUR SPECIFIC      bg #1a2a1a   text #00d4aa   (teal)
YEN SPECIFIC      bg #1a2a1a   text #00d4aa   (teal)
INDIA SPECIFIC    bg #1a2a1a   text #00d4aa   (teal)
MIXED             bg #1a1a1a   text #888888   (gray)
ACTIVE SUPPORT    bg #002a1a   text #00d4aa   (teal)
ACTIVE CAPPING    bg #2a1a00   text #f0a500   (amber)
SUSTAINED INFLOW  bg #002a1a   text #00d4aa   (teal)
SUSTAINED OUTFLOW bg #2a0000   text #ff4444   (red)
OIL DIVERGENCE    bg #2a1a00   text #f0a500   (amber)
REGIME TRANSITION bg #2a1a00   text #f0a500   (amber)
DEPRECIATION PRESSURE  bg #2a0000  text #ff4444
APPRECIATION PRESSURE  bg #002a1a  text #00d4aa
```

### Section Header Format In Left Column
```
font-size: 0.65rem
color: #444444
letter-spacing: 0.08em
text-transform: uppercase
margin-top: 8px
margin-bottom: 4px
```
New sections follow this exactly: COMMODITY SIGNALS, CENTRAL BANK
ACTIVITY, INR COMPOSITE are the new section headers being added.

### Tab Bar Design
```
Tab bar background:   transparent
Tab padding:          8px 16px
Active tab:           color #ffffff, border-bottom 2px solid #ffffff
Inactive tab:         color #555555, no border
Font:                 uppercase, 0.7rem, letter-spacing 0.08em
Transition:           color 0.15s ease
```

Tab pane switching uses `visibility:hidden + position:absolute` for
hidden panes and `visibility:visible + position:relative` for active.
Never use `display:none`. This is a confirmed fix — do not revert.

### Pair Color Identity (Fixed)
```
EUR/USD    #4da6ff    (blue)
USD/JPY    #ff9944    (orange)
USD/INR    #e74c3c    (red)
```
Used for: price trace line, pair ticker label text, pair-specific
annotations. Not used for any other purpose within the same card.

---

## SECTION 5 — CHART ARCHITECTURE

### Chart Functions In create_charts_plotly.py

**build_fundamentals_chart(pair)**
```
Subplots:    2 rows, row_heights=[0.55, 0.45]
Row 1:       FX price as line, pair color, 2px
             Annotation: current price value on right side, pair color
Row 2:       10Y spread as line, #2980b9 (blue), 1.5px
             2Y spread as line, #e67e22 (orange), 1.5px
             Both labeled on right side
X-axis:      type='date', range explicit YYYY-MM-DD strings
             No 'matches' key — confirmed causes rendering collapse
Y-axis row1: explicit range [min*0.92, max*1.08] from filtered data
Y-axis row2: explicit range with 15% padding each side
Height:      400px (G10 pairs), 360px (USD/INR)
```

**build_positioning_chart(pair)**
```
Subplots:    2 rows, each with secondary y-axis for percentile
Row 1:       Leveraged Money — bar chart (green if > 0, red if < 0)
             Percentile as line on secondary y-axis, range [0, 100]
             Horizontal dashed lines at 25th and 75th percentile
             Regime badge annotation (CROWDED LONG / NEUTRAL / SHORT)
Row 2:       Asset Manager — same structure
Bar width:   3.5 days in milliseconds (3.5 * 24 * 3600 * 1000)
Bar borders: line_width=0.5, line_color='#0d0d0d'
Height:      480px
```

**build_vol_correlation_chart(pair)**
```
Subplots:    2 rows, row_heights=[0.65, 0.35]
Row 1:       Vol as filled area (pair color, opacity 0.15)
             Vol as line on top (white, 1.5px)
             Percentile on secondary y-axis [0, 100]
             Threshold zones: 75th amber dashed, 90th red dashed
             Annotation: current value and percentile on right
Row 2:       Correlation as single line
             Color: > 0.6 = #00d4aa, 0.3-0.6 = #888888, < 0.3 = #ff4444
             Threshold lines: 0.6 teal dashed, 0.3 red dashed
             Annotation: current value and INTACT/BROKEN label
Height:      420px
```

### Chart Construction Rules (Critical — Do Not Violate)
1. All x-axis values must be `YYYY-MM-DD` strings. Convert in
   `_load_and_filter()`: `d.index = d.index.strftime('%Y-%m-%d')`
2. Never pass raw Pandas Timestamps to Plotly traces
3. Never use `matches: 'x2'` in any xaxis definition
4. Y-axis ranges always set explicitly from data with padding
5. `scrollZoom=True, displayModeBar=False, responsive=True`
6. Layout paper_bgcolor and plot_bgcolor: `#0a0a0a`
7. Grid: color `#1e1e1e`, width 1
8. Tick font: size 10, color `#666666`

### Embedding In Brief
`pio.to_html()` called with:
```python
full_html=False,
include_plotlyjs=False,   # Plotly.js loaded once in HTML head
config=plotly_config,
default_width='100%',
default_height=f'{height}px'
```
Plotly.js CDN: `https://cdn.plot.ly/plotly-2.27.0.min.js`
Never load Plotly.js twice. Never use include_plotlyjs=True in embedded divs.

### Data Filter
12-month window applied in `_load_and_filter()` in `charts/base.py`.
After filter: `d.index = d.index.strftime('%Y-%m-%d')`
USD/INR: outlier removal via quantile filter (0.01, 0.99) on price.

---

## SECTION 6 — PLANNED LAYOUT CHANGES BY PHASE

### After Phase 1 — Oil Correlation Rows
Added to each pair's VOLATILITY & CORRELATION section, below 60D Corr:
```
Oil corr (60D)    -0.43    [MODERATE]         ← EUR/USD example
Oil corr (60D)    +0.61    [HIGH]             ← USD/JPY example
Oil corr (60D)    +0.71    [HIGH]             ← USD/INR example
```
When correlation sign diverges from expected direction:
```
Oil corr (60D)    +0.21    [OIL DIVERGENCE]   ← unexpected sign
```
No separate section. These rows sit inside existing VOLATILITY &
CORRELATION section. Compact, one row per pair.

### After Phase 2 — DXY Decomposition Rows
Added to same section, below Oil corr row:
```
DXY corr (60D)    -0.71    [DOLLAR REGIME]    ← EUR/USD
DXY corr (60D)    +0.54    [MIXED]            ← USD/JPY
DXY corr (60D)    +0.83    [DOLLAR REGIME]    ← USD/INR
```
Badge tells the story — no additional text needed.

### After Phase 3 — Dual Window Correlation
Replace existing single 60D Corr row with two rows:
```
Corr 60D    -0.205    [BROKEN]
Corr 20D    +0.124    [WEAKENING]
```
When 20D and 60D diverge by more than 0.3, add small amber inline text
below both rows: `REGIME TRANSITION — 20D diverging from 60D`
Chart: add 20D correlation as dashed line, same color, opacity 0.5,
on the correlation subplot of build_vol_correlation_chart().

### After Phase 4 — Gold Rows
USD/JPY — inside VOLATILITY & CORRELATION section:
```
Gold corr (60D)    -0.38    [MODERATE]
```
USD/INR — same section:
```
Gold corr (60D)    +0.51    [MODERATE]
Seasonal window    ACTIVE   [WEDDING SEASON]   ← only when flag=True
```
Seasonal row is absent entirely when off-season. No empty row shown.

### After Phase 5 — RBI Intervention
USD/INR card only. New section header between POSITIONING (COT) and
VOLATILITY & CORRELATION: CENTRAL BANK ACTIVITY
```
CENTRAL BANK ACTIVITY
RBI Reserves    -$4.2B 1W    [ACTIVE SUPPORT]
```
Secondary text in small gray below value: `defending floor`
Color on value: teal for ACTIVE SUPPORT, amber for ACTIVE CAPPING.

### After Phase 6 — FPI Equity Flow
USD/INR card, same CENTRAL BANK ACTIVITY section, below RBI row:
```
FPI Flow (4W)    -₹18,432 cr    [SUSTAINED OUTFLOW]
```
Use ₹ symbol. Values in crores. No decimal places.
Badge: SUSTAINED INFLOW teal, SUSTAINED OUTFLOW red, NEUTRAL gray.

### After Phase 7 — INR Composite Score
USD/INR card. New block above REGIME READ, below all signal rows.
New section header: INR COMPOSITE
```
INR COMPOSITE
REGIME SCORE    +67    [DEPRECIATION PRESSURE]

[thin score bar — 4px height, 100% width, filled proportionally]
  red fill for positive score, teal fill for negative score

  Oil          +18    Brent rising, corr 0.71
  Dollar       +14    DXY broad strength
  FPI          +20    3-week outflow streak
  RBI          -8     Active support absorbing
  Rate diff    +7     Differential widening
```
Component rows use small font `#666666`. Values use their directional
color (red if adding depreciation pressure, teal if reducing it).

### After Phase 9 — BTP-Bund Spread
EUR/USD card only. Bottom of RATE DIFFERENTIALS section:
```
BTP-Bund    1.32%    +0.08pp    [NORMAL]
```
When flag is ELEVATED or STRESS, add full-width warning strip at top
of EUR/USD card (above pair ticker row):
```
⚠  BTP-Bund at stress levels — eurozone fragmentation risk elevated
```
Background `#1a0a00`, text `#f0a500`. Strip absent when flag = NORMAL.

### After Phase 10 — Macro Calendar Flag
Global strip between brief header and first pair card.
Absent when no event within 7 days — no empty space.
When event within 3-7 days:
```
⚠  Fed FOMC in 5 days — positioning signals may shift pre-decision
```
Background `#1a1500`, text `#f0a500`.
When event within 1-2 days:
```
🔴  ECB Meeting tomorrow — positioning data unreliable until post-decision
```
Background `#1a0000`, text `#ff4444`.

### After Phase 11 — Chart Enhancements

Key levels on price chart:
- S1/R1: solid `#333333`, 1px horizontal line with right label
- S2/R2: dotted `#2a2a2a`, 1px with right label
- S3/R3: dotted `#222222`, 0.5px, no label (too far from price)
- Only draw levels that fall within current 12-month y-range
- Label format: `S1 1.0834` or `R1 1.1920`, small font `#555555`

200D MA on price panel:
- Dashed `#444444`, 1px, labeled `200D MA` on right
- Calculated from full unfiltered data, displayed in 12-month window
- Ensures MA accuracy even at start of display window

Yield curve inversion shading:
- vrect during US_curve < 0 periods on price panel only
- fillcolor `rgba(255, 80, 0, 0.04)` — extremely subtle
- layer='below', no border
- Small legend entry: `US curve inverted`, gray text

---

## SECTION 7 — PHASE 1: OIL CORRELATION LAYER

### Signal Logic Per Pair

EUR/USD: Eurozone is net energy importer. Oil up = trade deficit widens =
EUR selling pressure. Expected correlation sign: negative.
Divergence (positive sign) = EUR-specific strength overriding energy headwind.

USD/JPY: Japan imports ~100% of energy needs. Oil up = wider trade deficit =
yen weakens. Expected sign: positive.
Divergence (negative sign) = safe haven or BoJ factor dominating.

USD/INR: India imports 85% of crude. Oil up = direct USD demand for
oil payment = INR weakens. Expected sign: positive.
Divergence (negative sign) = RBI intervention absorbing oil signal.
This RBI absorption case is itself analytically informative.

### Calculation
```python
# In pipeline.py, add after existing correlation calculations
brent_ret  = df['Brent'].pct_change()
eurusd_ret = df['EURUSD'].pct_change()
usdjpy_ret = df['USDJPY'].pct_change()
usdinr_ret = df['USDINR'].pct_change()

df['oil_eurusd_corr_60d'] = brent_ret.rolling(60).corr(eurusd_ret)
df['oil_usdjpy_corr_60d'] = brent_ret.rolling(60).corr(usdjpy_ret)
df['oil_inr_corr_60d']    = brent_ret.rolling(60).corr(usdinr_ret)
```

### Divergence Flag Thresholds
```
EUR/USD: correlation > +0.20  → OIL DIVERGENCE
USD/JPY: correlation < -0.20  → OIL DIVERGENCE
USD/INR: correlation < -0.20  → OIL DIVERGENCE (likely RBI absorbing)
```

---

## SECTION 8 — PHASE 2: DXY DECOMPOSITION LAYER

### Signal Logic Per Pair

EUR/USD: EUR is 57.6% of DXY. Expected: strongly negative. When correlation
weakens toward zero = EUR-specific factors dominating (ECB hawkishness,
fiscal expansion, positioning unwind). High correlation = dollar regime.

USD/JPY: JPY is 13.6% of DXY. Expected: positive but weaker than EUR.
When drops = BoJ, carry unwind, or safe haven driving yen specifically.

USD/INR: INR not in DXY but tracks EM basket. Expected: positive.
When drops = India-specific factor: RBI, FPI, domestic event.

### Calculation
```python
dxy_ret = df['DXY'].pct_change()

df['dxy_eurusd_corr_60d'] = dxy_ret.rolling(60).corr(eurusd_ret)
df['dxy_usdjpy_corr_60d'] = dxy_ret.rolling(60).corr(usdjpy_ret)
df['dxy_inr_corr_60d']    = dxy_ret.rolling(60).corr(usdinr_ret)
```

### Regime Label Logic
```
EUR/USD:
  corr < -0.60              → DOLLAR REGIME
  corr -0.60 to -0.30       → MIXED
  corr > -0.30              → EUR SPECIFIC

USD/JPY:
  corr > +0.60              → DOLLAR REGIME
  corr +0.30 to +0.60       → MIXED
  corr < +0.30              → YEN SPECIFIC

USD/INR:
  corr > +0.60              → DOLLAR REGIME
  corr +0.30 to +0.60       → MIXED
  corr < +0.30              → INDIA SPECIFIC
```

---

## SECTION 9 — PHASE 3: DUAL WINDOW CORRELATION (20D + 60D)

### Why
60D is medium-term regime read. 20D is early warning. When 20D diverges
from 60D, a regime transition is beginning before the 60D confirms it.
Most actionable timing signal in the framework.

### Calculation
```python
spread_de_chg = df['US_DE_10Y_spread'].diff()
spread_jp_chg = df['US_JP_10Y_spread'].diff()

df['EURUSD_corr_20d'] = spread_de_chg.rolling(20).corr(eurusd_ret)
df['USDJPY_corr_20d'] = spread_jp_chg.rolling(20).corr(usdjpy_ret)
```

### Regime Logic
```
Both > 0.6                     → REGIME INTACT
Both < 0.3                     → REGIME BROKEN
20D < 0.3 while 60D > 0.6      → BREAKING — early warning
20D > 0.6 while 60D < 0.3      → REBUILDING — recovery signal
```

---

## SECTION 10 — PHASE 4: GOLD LAYER

### Pairs: USD/JPY and USD/INR only
EUR/USD excluded — EUR/gold relationship is structurally unstable.

### USD/JPY Logic
Yen and gold are both safe-haven assets. Risk-off events cause both
to strengthen simultaneously. Expected: negative (gold up = USD/JPY down).
Break to positive = carry or growth factors overriding safe haven flow.

### USD/INR Logic
India is world's second largest gold consumer. Physical import demand
creates direct USD buying = INR selling. Seasonal demand windows amplify:
- October-November: Diwali and Dhanteras
- November-February: wedding season (peak bridal gold)
- April-May: Akshaya Tritiya
During these windows, rising gold price = amplified INR pressure because
volume and price both work against INR simultaneously.

### Calculation
```python
gold_ret = df['Gold'].pct_change()

df['gold_usdjpy_corr_60d'] = gold_ret.rolling(60).corr(usdjpy_ret)
df['gold_inr_corr_60d']    = gold_ret.rolling(60).corr(usdinr_ret)

def is_gold_season(date):
    m = pd.Timestamp(date).month
    return m in [10, 11, 12, 1, 2, 5]

df['gold_seasonal_flag'] = df.index.map(is_gold_season)
```

### Seasonal Labels By Month
```
10, 11     → DIWALI SEASON
12, 1, 2   → WEDDING SEASON
4, 5       → AKSHAYA TRITIYA
else       → flag = False, row not displayed
```

---

## SECTION 11 — PHASE 5: RBI INTERVENTION DETECTION

### Why This Layer Is Critical For INR
INR is a managed float. The RBI intervenes regularly. Without knowing
RBI activity, all other INR signals are incomplete. Oil spike may
predict INR weakness but if RBI is spending $5B defending a level,
USDINR may barely move. The brief must surface this to make the
other signals interpretable.

### Data Source
FRED series: `RBUKRESERVES` — RBI total FX reserves, USD billions.
Weekly frequency. ~1 week lag. No new API key needed.

### Calculation
```python
rbi = fred.get_series('RBUKRESERVES')
df_rbi = rbi.to_frame('rbi_reserves').resample('D').ffill()
df['rbi_reserve_chg_1w'] = df_rbi['rbi_reserves'].diff(7)

def rbi_flag(chg):
    if pd.isna(chg):   return 'UNKNOWN'
    if chg < -3.0:     return 'ACTIVE SUPPORT'
    if chg > 3.0:      return 'ACTIVE CAPPING'
    return 'NEUTRAL'

df['rbi_intervention_flag'] = df['rbi_reserve_chg_1w'].apply(rbi_flag)
```

### Threshold Note
$3B weekly = ~0.7% of India's ~$620B reserves. Adjust quarterly
if reserve level changes materially.

---

## SECTION 12 — PHASE 6: FPI EQUITY FLOW

### Why
FPI flow is the closest equivalent to COT positioning for INR. It measures
actual capital movement. Large sustained outflows = forced USD buying as
foreign funds repatriate = structural INR selling that persists until the
outflow reverses. Distinct from oil or DXY which are price signals.

### Data Source Priority Order
Option A — NSE India API:
  `https://www.nseindia.com/api/fiidiiTradeReact`
  Requires browser session headers via requests.Session().
  Load NSE homepage first to get session cookies, then call API.

Option B — Stooq alternative:
  Test if Indian FPI data available without session requirement.
  Less reliable but simpler.

Option C — Playwright (last resort):
  SEBI FPI page is JavaScript-rendered. Playwright async scrape.
  Highest reliability but highest implementation complexity.

Before writing any code: test Option A manually in browser.
If blocked, test Option B. Only escalate to Option C if both fail.

### Calculation
```python
df['fpi_net_weekly_cr'] = fpi_daily['net_cr'].rolling(5).sum()
df['fpi_net_4w_cr']     = fpi_daily['net_cr'].rolling(20).sum()

def fpi_flag(val):
    if pd.isna(val):    return 'UNAVAILABLE'
    if val > 10000:     return 'SUSTAINED INFLOW'
    if val < -10000:    return 'SUSTAINED OUTFLOW'
    return 'NEUTRAL'

df['fpi_flow_flag'] = df['fpi_net_4w_cr'].apply(fpi_flag)
```

Threshold: ₹10,000 crore ≈ USD 1.2B. Meaningful vs typical USDINR
daily turnover. Review quarterly.

---

## SECTION 13 — PHASE 7: INR COMPOSITE REGIME SCORE

### Prerequisites
Phases 1-6 live and confirmed accurate. Do not synthesize broken inputs.

### Score Construction
```python
def compute_inr_composite(row):
    oil  = row.get('oil_inr_corr_60d', 0) * np.sign(
               row.get('Brent', 0) - row.get('Brent_prev', 0))
    dxy  = row.get('dxy_inr_corr_60d', 0) * np.sign(
               row.get('DXY', 0) - row.get('DXY_prev', 0))
    fpi_raw = row.get('fpi_net_4w_cr', 0)
    fpi  = -np.clip(fpi_raw / 20000, -1, 1)
    rbi_map = {
        'ACTIVE SUPPORT': -0.3,
        'ACTIVE CAPPING': 0.2,
        'NEUTRAL': 0,
        'UNKNOWN': 0
    }
    rbi  = rbi_map.get(row.get('rbi_intervention_flag', 'NEUTRAL'), 0)
    rate = -np.sign(row.get('US_IN_10Y_spread', 0))

    score = (
        oil  * 0.25 +
        dxy  * 0.20 +
        fpi  * 0.25 +
        rbi  * 0.20 +
        rate * 0.10
    ) * 100
    return float(np.clip(score, -100, 100))
```

### Score Labels
```
> 60    → STRONG DEPRECIATION PRESSURE
30-60   → MODERATE DEPRECIATION PRESSURE
-30-30  → NEUTRAL
-60--30 → MODERATE APPRECIATION PRESSURE
< -60   → STRONG APPRECIATION PRESSURE
```

### Decomposition Is The Feature
Each component shown separately with directional color. A composite
that hides its inputs is a black box. A composite with transparent
decomposition shows the analytical chain and invites understanding.

---

## SECTION 14 — PHASE 8: EUR/USD AND USD/JPY COMPOSITE SCORES

### Only After INR Composite Proven
INR is more complex (managed float, more signal types). Build and
validate there first. Then extend to G10 pairs.

### EUR/USD Composite Weights
```
Rate differential direction    0.30
Lev Money percentile           0.20
Asset Manager percentile       0.10
Vol percentile (quality filter) 0.10
60D regime correlation         0.15
Oil correlation signal         0.08
DXY decomposition signal       0.07
```

### USD/JPY Composite Weights
```
Rate differential direction    0.25
Lev Money percentile           0.20
Asset Manager percentile       0.10
Vol percentile (quality filter) 0.10
60D regime correlation         0.15
Oil correlation signal         0.10
Gold safe-haven signal         0.05
DXY decomposition signal       0.05
```

---

## SECTION 15 — PHASE 9: BTP-BUND SPREAD

### Signal
BTP-Bund spread gauges eurozone fragmentation risk. Widening spread =
investors demanding premium for Italian vs German debt = EUR structural
stress. No other signal in the current framework captures this risk.

### Data Source
ECB Statistical Data Warehouse.
Italian 10Y: `YC/B.IT.EUR.4F.G_N_A.SV_C_YM.SR_10Y`
German 10Y: already fetched. Same ECB SDW endpoint, no new infrastructure.

### Calculation
```python
df['IT_10Y']          = ecb_fetch('YC/B.IT.EUR.4F.G_N_A.SV_C_YM.SR_10Y')
df['BTP_Bund_spread'] = df['IT_10Y'] - df['DE_10Y']
df['BTP_Bund_flag']   = df['BTP_Bund_spread'].apply(
    lambda x: 'STRESS' if x > 2.5 else 'ELEVATED' if x > 1.8 else 'NORMAL'
)
```

---

## SECTION 16 — PHASE 10: MACRO CALENDAR FLAG

### Stage 1 — Hardcoded (Immediate)
Dict in `config.py`, updated manually each quarter:
```python
CB_EVENTS = {
    '2026-03-19': 'Fed FOMC',
    '2026-04-07': 'ECB Meeting',
    '2026-03-19': 'BoJ Policy Review',
}
```

### Flag Function
```python
def get_upcoming_event(today, window_days=7):
    for date_str, name in sorted(CB_EVENTS.items()):
        days_away = (pd.Timestamp(date_str) - pd.Timestamp(today)).days
        if 0 <= days_away <= window_days:
            return {'event': name, 'date': date_str, 'days_away': days_away}
    return None
```

### Stage 2 — Automated (Future)
Automate fetch from CME FedWatch and ECB website calendar.
Update quarterly instead of manually. Do not build until Stage 1
is running for at least one quarter.

---

## SECTION 17 — PHASE 11: PLOTLY CHART ENHANCEMENTS

### Key Levels On Price Chart
```python
for label, level, style in [
    ('S1', s1, 'solid'), ('R1', r1, 'solid'),
    ('S2', s2, 'dot'),   ('R2', r2, 'dot')
]:
    if y_min <= level <= y_max:   # only draw if in visible range
        fig.add_hline(
            y=level, row=1, col=1,
            line=dict(
                color='#333333' if 'solid' else '#2a2a2a',
                width=1, dash=style
            ),
            annotation_text=f'{label} {level:.4f}',
            annotation_position='right',
            annotation_font=dict(size=9, color='#555555')
        )
```

### 200D Moving Average
```python
# Calculate from full unfiltered data
ma200 = df_full[price_col].rolling(200).mean()
# Trim to 12-month display window
ma200_display = ma200[ma200.index.isin(d.index)]

fig.add_trace(
    go.Scatter(
        x=ma200_display.index, y=ma200_display.values,
        name='200D MA', mode='lines',
        line=dict(color='#444444', width=1, dash='dash')
    ),
    row=1, col=1
)
```

### Yield Curve Inversion Shading
```python
inversion_mask = df_display['US_curve'] < 0
# Find contiguous inversion periods
for start, end in get_contiguous_periods(inversion_mask):
    fig.add_vrect(
        x0=start, x1=end, row=1, col=1,
        fillcolor='rgba(255, 80, 0, 0.04)',
        layer='below', line_width=0
    )
```

---

## SECTION 18 — PHASE 12: FLASK DASHBOARD

### Decision Gate
Only build if static GitHub Pages brief is insufficient for the use case.
Do not add infrastructure without a concrete need.

### Architecture If Building
```
app.py          — Flask routes, single index serving latest brief
/refresh        — endpoint triggering python run.py via subprocess
Procfile        — Railway.app / Render.com deployment
requirements.txt — add Flask
```
No Plotly Dash. Flask serving the static HTML is simpler and sufficient.

---

## SECTION 19 — PHASE 13: AI SYNTHESIS LAYER

### Architecture
```
ai_brief.py         — reads latest CSV row, calls Anthropic API, writes JSON
data/ai_regime_read.json — output consumed by create_html_brief.py
```
Called by `run.py` after `create_html_brief.py`.
Fallback: if JSON missing or API fails, use hardcoded regime read text.
Brief must never break because AI failed.

### API Details
Model: `claude-haiku-4-5-20251001`
Three calls per run (one per pair).
Estimated daily cost: < $0.01.

### System Prompt
```
You are an FX analyst writing the regime read section of a morning
brief. You will receive structured data for one FX pair as JSON.
Write 3-4 sentences synthesizing rate differential, positioning, and
volatility signals into a coherent regime read. Be direct and specific.
Use numbers. Do not hedge excessively. No markdown, no lists.
Target reader: experienced FX market participant.
```

### Output Format
```json
{
  "eurusd_regime_read": "...",
  "usdjpy_regime_read": "...",
  "usdinr_regime_read": "..."
}
```

---

## SECTION 20 — EXECUTION TIMELINE

```
WEEK 0 — COMPLETE:
  ✅ Plotly vertical line fix
  ✅ Timestamp serialization fix
  ✅ Tab visibility fix
  ✅ Explicit chart dimensions
  ✅ Project restructure
  ✅ Charts rendering correctly in brief

WEEK 1 (PRE-PHASE 1 FIX — COMPLETE):
  ✅ Brent (BZ=F) and Gold (GC=F) added to pipeline.py fetch
  ✅ Brent, Gold, and chg_* columns confirmed in latest_with_cot.csv
  ✅ Section 3 column names corrected (corr + AM COT names)

WEEK 1 (PHASES 1 & 2 — COMPLETE):
  ✅ Phase 1: Oil correlation all 3 pairs
    ✅ oil_eurusd_corr_60d — pipeline.py calculate_oil_correlation()
    ✅ oil_usdjpy_corr_60d — pipeline.py calculate_oil_correlation()
    ✅ oil_inr_corr_60d   — inr_pipeline.py build_and_save()
    ✅ _oil_corr_label() + OIL CORRELATION section in morning_brief.py
    ✅ All 3 pairs show live values in text brief
  ✅ Phase 2: DXY decomposition all 3 pairs
    ✅ dxy_eurusd_corr_60d — pipeline.py calculate_dxy_correlation()
    ✅ dxy_usdjpy_corr_60d — pipeline.py calculate_dxy_correlation()
    ✅ dxy_inr_corr_60d   — inr_pipeline.py build_and_save()
    ✅ _dxy_corr_label() + DXY DECOMPOSITION section in morning_brief.py
    ✅ All 3 pairs show live values: EUR/USD MIXED, USD/JPY MIXED, USD/INR INDIA SPECIFIC

WEEK 2:
  → Phase 3: Dual window correlation 20D+60D
  → Phase 4: Gold layer USD/JPY and USD/INR
  → Phase 5: RBI intervention via FRED RBUKRESERVES

WEEK 3:
  → Phase 6: FPI equity flow
  → Phase 9: BTP-Bund spread
  → Phase 10: Macro calendar flag

WEEK 4:
  → Phase 7: INR composite regime score
  → Phase 11: Key levels + 200D MA on charts

MONTH 2:
  → Phase 8: EUR/USD and USD/JPY composite scores
  → Phase 11: Yield curve inversion shading
  → Phase 12: Flask dashboard (only if needed)

MONTH 3:
  → Phase 13: AI synthesis layer
  → GBP/USD extension (if scope expands)
```

---

## SECTION 21 — RULES FOR CODING AGENTS READING THIS FILE

1. `data/latest_with_cot.csv` is READ ONLY. Never modify it directly.
   It is the output of pipeline.py and cot_pipeline.py.

2. Before adding any column, check Section 3 for the exact column name.
   Case-sensitive mismatches between pipeline output and chart/brief
   consumption are the most common failure mode in this project.

3. All Plotly x-axis values must be `YYYY-MM-DD` strings. Conversion
   happens in `_load_and_filter()` in `charts/base.py`. Never pass raw
   Pandas Timestamps to Plotly traces.

4. Never use `matches: 'x2'` in any xaxis definition. Confirmed to cause
   x-axis collapse for EUR/USD fundamentals chart.

5. Never use `display:none` for hiding chart panes. Use
   `visibility:hidden + position:absolute` for hidden panes,
   `visibility:visible + position:relative` for active pane.

6. When adding a new display row to the brief, match the exact row format
   from Section 4 (label / value / change / badge pattern).

7. When adding a new badge type, add it to the badge color system in
   Section 4 first. Never use arbitrary colors inline.

8. Test commands after any change:
   - Data change:  `python run.py --only pipeline`
   - Chart change: `python run.py --only charts` then verify proto HTML
   - Brief change: `python run.py --only html` then open in browser
   - Full run:     `python run.py`

9. One change at a time. Never span two files in one edit session
   without verifying the first change works correctly.

10. This file is the source of truth for architecture, column names,
    layout rules, badge system, and phase sequence. Read it before
    writing code, not after something breaks.

---

*Framework version: Phases 1 & 2 complete (Oil Correlation + DXY Decomposition) — entering Week 2 (Phases 3–5)*
*Last updated: March 2026*
*Live brief: https://shreyash3007.github.io/G10-FX-Regime-Detection-Framework/*
