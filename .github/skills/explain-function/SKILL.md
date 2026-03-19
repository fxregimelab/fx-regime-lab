---
name: explain-function
description: 'Teach and explain concepts when adding a new function to the FX regime framework. Use when: adding a new function, new indicator, new data source, new signal, new chart, or new pipeline step. Explains the financial concept behind the function, how the data flows through the pipeline, which files it touches, and provides a practical code example. Triggers on: "add function", "explain this", "teach me", "how does X work", "new indicator", "new signal", "add data source", "add chart", "I want to understand".'
argument-hint: 'Name or description of the function/concept to explain (e.g. "BTP-Bund spread fetcher", "200D moving average", "realized vol percentile")'
---

# Explain-Function: Teaching Skill for the FX Regime Framework

Every time a new function is added to this project, follow this teaching workflow.
The goal is to understand *why* it exists, *what* it does financially, *how* the data moves, and *where* it lives in the pipeline.

## Who This Is For

Shreyash — first-year engineering student building an institutional-grade FX regime detection framework from scratch. Explanations should be direct, precise, and practical — not simplified, not padded with disclaimers.

---

## Step 1 — Identify the Function Type

Before explaining anything, classify the function being added:

| Type | What It Does | Lives In |
|------|-------------|----------|
| **Data Fetcher** | Pulls raw prices / yields / flows from an API or file | `pipeline.py`, `cot_pipeline.py`, `inr_pipeline.py` |
| **Indicator Calculator** | Transforms raw data into an analytical signal (spread, percentile, vol, MA) | `pipeline.py` or its own module |
| **Chart Builder** | Renders a Plotly figure for one pair/tab | `create_charts_plotly.py`, `charts/` |
| **Brief Generator** | Writes text / HTML narrative from the final CSV | `morning_brief.py`, `create_html_brief.py` |
| **Config / Registry Entry** | Declares a new pair, ticker, series, or differential | `config.py` |
| **Orchestrator** | Calls multiple steps in sequence | `run_all.py`, `run.py` |

---

## Step 2 — Explain the Financial Concept

Answer these three questions in plain market language:

1. **What does this measure?**
   State the economic or market meaning of the signal. Use a real-world example from the framework's pairs (EUR/USD, USD/JPY, USD/INR).
   
2. **Why does it matter for regime detection?**
   Connect it to one of the three regimes:
   - Regime 1 (Rate Differentials Dominant): Capital flows follow yield spreads cleanly
   - Regime 2 (Positioning Dominant): Crowding overrides fundamentals temporarily
   - Regime 3 (Risk Sentiment Dominant): Vol spike forces liquidations, signals break down

3. **What would you expect to see?**
   Describe a concrete directional example — e.g., "When the 10Y BTP-Bund spread widens past 200bp, EUR/USD typically faces sustained downside pressure as ECB credibility risk reprices."

---

## Step 3 — Map the Data Flow

Trace the function through the full pipeline. Use this template:

```
INPUT  → [source: Yahoo Finance / FRED / ECB / MOF / CFTC / manual CSV]
         fetched in: [pipeline.py / cot_pipeline.py / inr_pipeline.py]
         raw column name: [e.g. DE_2Y]

TRANSFORM → [calculation: e.g. "US_2Y minus DE_2Y → US_DE_2Y_spread"]
            lives in: [pipeline.py line ~XXX]
            output column: [e.g. US_DE_2Y_spread]

PERSIST → saved to: [data/latest_with_cot.csv]
          also archived in: [runs/YYYY-MM-DD/data/]

CONSUMED BY:
  - morning_brief.py  → appears in terminal summary
  - create_charts_plotly.py → used in which chart / which subplot
  - create_html_brief.py  → shown in which tab (FUNDAMENTALS / POSITIONING / VOL & CORRELATION)
```

---

## Step 4 — Show the Code Pattern

Show the actual code snippet for this function following the existing conventions of the codebase:

### Data Fetcher Pattern (pipeline.py)
```python
def fetch_<source>_<series>() -> pd.Series:
    # One function, one series. Returns a named pd.Series with DatetimeIndex.
    # Fill forward NaN gaps (weekends / holidays) with .ffill().
    # Never hardcode dates — use START_DATE and TODAY from config.py
    ...
```

### Indicator Calculator Pattern (pipeline.py)
```python
# After all sources are fetched and merged into df:
df['<output_col>'] = df['<series_A>'] - df['<series_B>']        # spread
df['<output_col>_pct'] = df['<series>'].pct_change() * 100      # % change
df['<output_col>_pctile'] = df['<series>'].rank(pct=True) * 100 # rolling percentile
```

### Chart Builder Pattern (create_charts_plotly.py / charts/)
```python
def build_<pair>_<tab>() -> go.Figure:
    # Always uses _load_and_filter() from charts/base.py
    # Always uses _base_layout(), _style_axes(), _add_annotation()
    # Shared x-axis via shared_xaxes=True in make_subplots
    # Colors: price=#4da6ff, spread_A=#2980b9, spread_B=#e67e22, neutral=#aaaaaa
    # Hover: '%{x|%d %b %Y}<br>%{y:.4f}<extra></extra>'
    ...
```

### Config / Registry Pattern (config.py)
```python
# Adding a new pair to PAIRS_REGISTRY — the single source of truth.
# Charts, briefs, and HTML auto-scale from this registry.
"GBPUSD": {
    "price_col":    "GBPUSD",
    "yahoo_ticker": "GBPUSD=X",
    "spread_cols":  ["US_DE_10Y_spread", "US_DE_2Y_spread"],
    "cot_col":      "GBP_Net",
    ...
}
```

---

## Step 5 — Practical Usage: What Changes Where

For every new function, state the exact files that need to change and in what order:

1. `config.py` — add ticker / series / column name to the relevant dict
2. `pipeline.py` (or relevant pipeline) — add fetch function and column update
3. `create_charts_plotly.py` or `charts/` — add or update chart builder
4. `morning_brief.py` — add the value to the terminal summary lines
5. `create_html_brief.py` — wire the new chart into the correct pair/tab
6. `run_all.py` or `run.py` — ensure the step is called in the right order

State which of these steps are **required** vs **optional** for this specific function.

---

## Step 6 — Key Design Rules (Always Remind)

After explaining the function, remind of the relevant rules from the codebase:

- **Single source of truth**: `config.py` owns all tickers, series, column names. Never hardcode strings in two places.
- **Column naming convention**: `{PAIR}_{signal}_{window}` — e.g. `EURUSD_spread_corr_60d`, `JPY_leveraged_pctile`.
- **latest_with_cot.csv is the hub**: Every pipeline writes to this file. Every chart and brief reads from it.
- **No signal without a column**: If it doesn't have a column in the CSV, it can't be charted or briefed.
- **Regime logic is the filter**: Every new indicator should be evaluated through the lens — does this change regime classification? Which regime does it strengthen or challenge?
- **Earnings from place**: No decorative signals. Every function added must produce something analytically useful.

---

## Step 7 — Quick Sanity Check

After implementing, verify:

- [ ] `data/latest_with_cot.csv` contains the new column after running `pipeline.py`
- [ ] `python check_latest.py` shows the new column with a fresh timestamp
- [ ] The chart renders correctly in the browser (no missing data, correct subplot)
- [ ] `morning_brief.py` terminal output includes the new value
- [ ] `run_all.py` completes without errors

---

## Reference Files

- [Framework patterns and conventions](./references/framework-patterns.md)
- [Master plan and known gaps](../../docs/G10_FX_FRAMEWORK_MASTER_PLAN.md)
- [Project context & layout](../../AGENTS.md)
