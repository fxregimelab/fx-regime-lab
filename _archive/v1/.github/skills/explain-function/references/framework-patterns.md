# Framework Patterns & Conventions Reference

Concrete coding conventions enforced in the FX regime framework.
The SKILL.md references this file for Step 4 and Step 6 details.

---

## Column Naming Conventions

| Pattern | Example | Notes |
|---------|---------|-------|
| `{PAIR}` | `EURUSD`, `USDJPY`, `USDINR` | Always uppercase, 6-char |
| `{COUNTRY}_{TENOR}_spread` | `US_DE_10Y_spread` | A minus B, in % |
| `{PAIR}_spread_corr_{N}d` | `EURUSD_spread_corr_60d` | Rolling correlation |
| `{PAIR}_vol_{N}d` | `EURUSD_vol_30d` | Realized vol, annualized |
| `{PAIR}_vol_pctile` | `EURUSD_vol_pctile` | 0–100, 3-year window |
| `{CCY}_leveraged` | `EUR_leveraged` | COT net contracts |
| `{CCY}_leveraged_pctile` | `EUR_leveraged_pctile` | 0–100, 3-year window |
| `chg_{COL}` | `chg_EURUSD`, `chg_US_DE_10Y_spread` | 1-day % change |

---

## The Data Hub: `latest_with_cot.csv`

This is the single file that all scripts read from. It is written by the pipeline(s) and read by charts and briefs.

```
pipeline.py          →  data/latest.csv
cot_pipeline.py      →  merges with latest.csv
inr_pipeline.py      →  merges INR-specific columns
                         → final: data/latest_with_cot.csv  ← charts + briefs read this
```

**Adding a new column:**
1. Compute it in the appropriate pipeline script.
2. Assign to `df['new_col'] = ...`
3. Ensure `df.to_csv('data/latest_with_cot.csv')` (or merge step) includes it.
4. Verify with `python check_latest.py` or `pd.read_csv('data/latest_with_cot.csv').tail(1)`.

---

## Plotly Chart Conventions

### Colors (Dark Theme)
| Role | Hex |
|------|-----|
| Primary price line | `#4da6ff` |
| Spread / series A | `#2980b9` |
| Spread / series B | `#e67e22` |
| Neutral / correlation | `#aaaaaa` |
| Zero line (hline) | `#444444` |
| Background | `#0e1117` (paper) / `#0e1117` (plot) |
| Grid lines | `rgba(255,255,255,0.05)` |

### Subplot Structure (Standard 3-row)
```python
fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    row_heights=[0.45, 0.35, 0.20],  # price / spread / corr or vol
    vertical_spacing=0.06,
)
```

### Hovertemplate Format
```python
# Price:  '%{x|%d %b %Y}<br>%{y:.4f}<extra></extra>'
# Spread: '%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>'
# Percentile: '%{x|%d %b %Y}<br>%{y:.0f}<extra></extra>'
```

### Base Layout (from charts/base.py)
Always call `_base_layout()`, then `_style_axes()`, then `_add_annotation()`.
Never duplicate layout settings inline — extend `_base_layout()` if a new global property is needed.

---

## API Sources Quick Reference

| Source | What It Provides | Python Library / URL |
|--------|-----------------|----------------------|
| Yahoo Finance | FX prices, commodity futures (BZ=F, GC=F) | `yfinance` |
| FRED | US 2Y (DGS2), US 10Y (DGS10) | `fredapi` — requires `FRED_API_KEY` in `.env` |
| ECB SDW | DE 2Y, DE 10Y (Svensson yield curve) | `requests` → ECB REST API |
| MOF Japan | JP 2Y, JP 10Y (JGB yield curve CSV) | `requests` → MOF CSV URLs |
| CFTC COT | EUR/JPY/INR net futures positioning | CSV download → `cot_pipeline.py` |
| FBIL | USD/INR overnight reference rate | `fbil_in10y_cache.csv` (cached) |

---

## Regime Classification Logic

| Regime | Condition | Signal Interpretation |
|--------|-----------|----------------------|
| **1 — Rate Differential Dominant** | Positioning percentile 30–70 | Follow spread direction cleanly |
| **2 — Positioning Dominant** | Positioning percentile >80 or <20 | Reversal risk overrides fundamentals |
| **3 — Risk Sentiment Dominant** | Vol percentile >85 + corr breakdown | Liquidation risk; all signals unreliable |

---

## Pipeline Execution Order

```
run_all.py
  1. pipeline.py          # FX + yields + spreads + commodities → latest.csv
  2. cot_pipeline.py      # COT positioning + merge → latest_with_cot.csv
  3. inr_pipeline.py      # INR-specific data → merged into latest_with_cot.csv
  4. morning_brief.py     # Text summary → briefs/brief_YYYYMMDD.txt
  5. create_html_brief.py # Charts + HTML brief → briefs/brief_YYYYMMDD.html
  6. deploy.py            # Push index.html to GitHub Pages
```

Each step is independent and can be run individually for debugging.

---

## Known Gaps (as of March 2026)

From the master plan — active development targets:

- BTP-Bund spread (eurozone fragmentation, Regime 2 signal for EUR/USD)
- 200D moving average on price panels
- Key S/R levels drawn as horizontal lines on price chart (currently text-only)
- Commodity correlation signals (oil vs INR, gold vs USD)
- Composite regime score (single numeric output per pair)
- Macro calendar injection (event-aware regime weighting)
- USD/INR positioning and vol layers (SEBI FPI data blocked by JS rendering)
