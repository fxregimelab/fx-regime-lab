# G10 FX Regime Detection Framework

An automated daily pipeline that detects FX regimes for EUR/USD and USD/JPY
by combining rate differential analysis with speculative positioning data.

Built by Shreyash Sakhare | First Year Engineering Student | Pune, India
Started: February 2026

---

## What This Does

Most FX analysis looks at either fundamentals or positioning in isolation.
This framework combines both into a regime classification system.

Every morning the pipeline answers two questions:
1. What direction do rate differentials predict for EUR/USD and USD/JPY?
2. Is speculative positioning confirming that direction or creating reversal risk?

The combination classifies the current regime — which determines how much
confidence to place in the directional signal.

---

## Three Regimes

**Regime 1 — Rate Differential Dominant**
Positioning is neutral. Capital flows follow yield differentials cleanly.
The spread signal is reliable.
*Current example: EUR/USD past 12 months — spread compressed 74bp, EUR rose 12%.*

**Regime 2 — Positioning Dominant**
Crowded positioning overrides the fundamental signal temporarily.
Direction may still be correct but timing and magnitude are distorted.
*Current example: EUR/USD today — 97th percentile crowded long, reversal risk.*
*Past example: USD/JPY mid-2025 — carry trade overrode spread compression signal.*

**Regime 3 — Risk Sentiment Dominant**
Volatility spike forces liquidations across all positions.
Fundamental signals break down entirely.
*Example: August 2024 yen carry unwind — USD/JPY fell 15 yen in six weeks.*

---

## Current Findings (as of February 2026)

**EUR/USD — 1.1775**
- US-DE 10Y spread: 0.66% (narrowed 74bp over 12 months)
- US-DE 2Y spread: 1.42% (narrowed 56bp over 12 months)
- EUR Leveraged Money: +43,549 contracts | 97th percentile
- Regime: CROWDED LONG — fundamental direction correct, asymmetric reversal risk

**USD/JPY — 155.88**
- US-JP 10Y spread: 1.28% (narrowed 126bp over 12 months)
- US-JP 2Y spread: 2.21% (narrowed 92bp over 12 months)
- JPY Leveraged Money: -29,321 contracts | 67th percentile
- Regime: NEUTRAL — carry trade partially unwound, spread compression intact

---

## Architecture

For a full directory map, entry points, and deploy behaviour, see **[AGENTS.md](AGENTS.md)** (maintainer and AI context).

```
run.py / run_all.py
├── pipeline.py           # Layer 1: Rate differentials & FX data
├── cot_pipeline.py       # Layer 2: CFTC positioning
├── inr_pipeline.py       # INR-specific metrics
├── morning_brief.py      # Text brief
├── create_html_brief.py  # HTML brief + chart iframes
└── deploy.py             # GitHub Pages (index.html)
```

### pipeline.py — Layer 1
Pulls daily data from three sources and calculates four rate differential spreads.

Data sources:
- FX prices: Yahoo Finance (EUR/USD, USD/JPY, DXY)
- US yields: FRED API — US 2Y (DGS2), US 10Y (DGS10) — daily
- German yields: ECB Statistical Data Warehouse — DE 2Y, DE 10Y — daily
- Japan yields: Ministry of Finance Japan — JP 2Y, JP 10Y — daily

Spreads calculated:
- US 2Y minus DE 10Y (cross-maturity, capital flow signal)
- US 2Y minus DE 2Y (same-maturity, pure policy rate differential)
- US 2Y minus JP 10Y (cross-maturity, capital flow signal)
- US 2Y minus JP 2Y (same-maturity, pure policy rate differential)

### cot_pipeline.py — Layer 2
Pulls CFTC Disaggregated Financial Futures data for EUR and JPY.

Why Disaggregated Leveraged Money specifically:
Asset managers buy currency futures to hedge equity exposure — mechanical,
not a macro view. Leveraged Money (hedge funds and CTAs) takes positions
specifically because of macro theses. When Leveraged Money is crowded,
it means the macro thesis is consensus and reversal risk is elevated.

Calculates:
- Net position (longs minus shorts)
- Net position as percentage of open interest
- 3-year rolling percentile rank (~156 weekly observations)

Why 3-year lookback: The pre-2022 zero-rate environment is a structurally
different regime. Including it would compare today's positioning against
a market that no longer exists. 3 years captures the current rate cycle only.

### create_html_brief.py — Output
Generates the interactive HTML morning brief and supporting chart HTML under `charts/` (iframes + workspace). Deploy copies the latest brief to root `index.html` for GitHub Pages.

---

## Setup

### Requirements
```
python 3.9+
pandas
numpy
matplotlib
requests
yfinance
fredapi
python-dotenv
```

Install:
```bash
pip install -r requirements.txt
```

### FRED API Key
Free API key required from https://fred.stlouisfed.org/docs/api/api_key.html

Create a .env file in the project root:
```
FRED_API_KEY=your_key_here
```

### Run
```bash
python run_all.py
```

Or run individually:
```bash
python pipeline.py
python cot_pipeline.py
python morning_brief.py
python create_html_brief.py
```

---

## Output

**Terminal:** Morning numbers table with FX prices, all yields, all spreads,
percentage changes across 1D, 1W, 1M, 3M, 12M windows. COT summary with
regime classification per pair.

**Charts:** Interactive HTML under `charts/` (iframes used by the brief; also copied into `runs/` when using `run_all.py`).

**Data:** Master CSV saved to /data with full history. Latest snapshot
always available as data/latest_with_cot.csv.

---

## Daily Run Archive
Each execution of `run_all.py` now archives outputs under a date-stamped
directory to keep historical results tidy. The structure for a run on
2026‑02‑26 looks like:

```
runs/
└── 2026-02-26/
    ├── charts/
    │   ├── eurusd_fundamentals.png
    │   ├── eurusd_positioning.png
    │   ├── usdjpy_fundamentals.png
    │   └── usdjpy_positioning.png
    ├── data/
    │   ├── master.csv            # copy of data/master_YYYYMMDD.csv
    │   ├── cot.csv               # copy of latest COT snapshot
    │   └── master_with_cot.csv   # merged master dataset
    └── brief.txt                # today's morning brief
```

Charts and data continue to be written to `charts/`, `data/`, and
`briefs/` as before; the archive step simply copies today's outputs into
the `runs/` tree and strips date suffixes from the filenames. The
`runs/` folder is ignored by Git.


---

## Design Choices and Known Limitations

**Why US 2Y not US 10Y for spreads:**
The 2Y yield is most sensitive to Federal Reserve policy expectations and
reflects the rate path over the short-to-medium term holding period that
drives FX capital flows. The 10Y reflects longer-run growth and inflation
expectations. For FX regime detection, the 2Y is the correct instrument.

**Maturity mismatch (known limitation):**
Using US 2Y versus foreign 10Y is methodologically impure — comparing
instruments of different durations. The same-maturity 2Y vs 2Y spread
is the cleaner comparison. Both are tracked. The cross-maturity spread
is retained because it has historically correlated well with FX moves
and captures the policy signal most directly.

**COT publication lag (known limitation):**
CFTC publishes Tuesday positioning data on Friday at 3:30pm EST.
By Monday morning the data is 6 days old. Around major events — Fed
decisions, ECB meetings, NFP — positioning can shift meaningfully
within that window.

**3-year percentile window (known limitation):**
156 weekly observations is a small sample for statistical robustness.
Longer history would be more robust but would include structurally
different zero-rate regime data.

**No volatility layer yet:**
When implied volatility spikes, forced liquidations override directional
intent. The framework cannot currently distinguish between a deliberate
positioning unwind and a panic unwind. Volatility layer is next priority.

**Why not USD/INR:**
CFTC COT data covers CME-listed futures. USD/INR does not have an
equivalent public disaggregated positioning dataset. The RBI manages
India's capital account differently from G10 central banks. Adding
USD/INR properly requires a different architecture: RBI intervention
proxy from reserve data, oil price correlation layer, and SEBI FPI
flow data as a positioning substitute. Planned as a future extension.

---

## Roadmap

- [x] Layer 1: Rate differentials with daily ECB and MOF yield data
- [x] Layer 2: CFTC COT Leveraged Money positioning with percentile rank
- [x] Pair-specific HTML brief panels (spreads, positioning, cross-asset) via `create_html_brief.py`
- [ ] Morning brief: Clean formatted text output, desk-readable in 60 seconds
- [ ] Multiple COT categories: NonCommercial and Asset Manager alongside Leveraged Money
- [ ] Volatility layer: 30-day realized volatility from existing price data
- [ ] USD/INR extension: Emerging market pair with modified architecture
- [ ] Macro calendar integration: Flag high-impact events within 48 hours

---

## Sample Output

```
======================================================================
  MORNING NUMBERS
======================================================================
  as of: 2026-02-26

  FX PRICES:
  pair          price      1D%      1W%      1M%      3M%     12M%
  ------------------------------------------------------------------
  EURUSD       1.1775   -0.16%   -0.65%   -0.85%   +1.82%  +12.31%
  USDJPY     155.8800   +0.81%   +1.78%   +1.00%   -0.22%   +4.40%
  DXY         97.7000   -0.18%   +0.00%   +1.54%   -1.91%   -7.60%

  RATE DIFFERENTIALS:
  spread                    today    1D chg    1M chg   12M chg
  --------------------------------------------------------------
  US-DE 10Y                 0.66%    +0.00pp    +0.05pp    -0.74pp
  US-DE 2Y                  1.42%    +0.00pp    -0.03pp    -0.56pp
  US-JP 10Y                 1.28%    -0.03pp    +0.03pp    -1.26pp
  US-JP 2Y                  2.21%    +0.03pp    -0.04pp    -0.92pp

  COT POSITIONING:
  EUR: +43,549 contracts | 97th percentile | CROWDED LONG
  JPY: -29,321 contracts | 67th percentile | NEUTRAL
======================================================================
```

---

## Disclaimer

This project is built for research and learning purposes only.
Nothing here constitutes investment advice or trading recommendations.
All data sourced from public institutional sources: Federal Reserve,
ECB, Japan Ministry of Finance, CFTC.
