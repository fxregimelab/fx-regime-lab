# CURSOR RULES — FX REGIME LAB
> This is the system-level rules file for Cursor. Read CONTEXT.md and PLAN.md before every session. These rules are non-negotiable. Every piece of code written in this project must comply with everything below.

---

## WHO YOU ARE BUILDING FOR

You are building the FX Regime Lab for Shreyash Sakhare — a 20-year-old engineering student building toward owning a quantamental macro fund by age 38. This framework is simultaneously a career differentiator, a live research tool, a public track record, and a future product. Every build decision must serve all four purposes simultaneously.

The target audience for the output of this framework includes:
- FX desk practitioners (HSBC, Nomura, Bloomberg correspondents)
- MFE admissions committees (NTU Singapore, HKUST, SMU)
- Institutional fund managers (Graham Capital, Point72, Millennium type shops)
- Future subscribers to a paid intelligence product

Every line of code either moves toward that audience or it doesn't. There is no neutral code in this project.

---

## BEFORE YOU WRITE ANY CODE

1. Read `CONTEXT.md` — understand what the framework is, what it's for, and what decisions are locked
2. Read `PLAN.md` — understand which phase you're building and what comes before and after
3. Understand the Supabase schema — never create a table or column that conflicts with the schema defined in PLAN.md Phase 0
4. Check which pipeline scripts already exist — never rebuild what exists, only extend
5. Confirm the current pipeline execution sequence from **`run.py` `STEPS`:** `fx → cot → inr → vol → oi → rr → merge → text → macro → ai → html → validate → deploy` (no `create_dashboards.py`)

---

## TECHNICAL RULES — NON-NEGOTIABLE

### Language and Libraries
- Python only. No C++. No JavaScript backend.
- Approved libraries: `pandas`, `numpy`, `requests`, `supabase-py`, `yfinance`, `scipy`, `statsmodels`, `matplotlib` (for report generation only), `transformers` (Phase 7 only)
- No ML libraries (scikit-learn, tensorflow, pytorch) until Phase 5 backtesting layer is complete and explicitly requested
- No new dependencies without explicit approval — every new `pip install` adds maintenance burden

### Code Structure
- One file per signal module: `vol_pipeline.py`, `oi_pipeline.py`, `rr_pipeline.py`
- All pipeline scripts follow the same pattern:
  1. Fetch data from source
  2. Compute signal values
  3. Write to Supabase (primary) and CSV fallback (for local dev)
  4. Return signal dict for use by downstream scripts
- Never hardcode dates, API keys, or file paths. Use environment variables and config files.
- Every function has a docstring explaining: what it computes, what it returns, what it writes to Supabase

### Environment Variables (GitHub Actions Secrets)
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY   # CI writes — bypasses RLS
SUPABASE_ANON_KEY           # public dashboard / Cloudflare Pages reads
CME_API_KEY
FRED_API_KEY
```
Never print these. Never log these. Never commit these.

### Error Handling
- Every API call is wrapped in try/except with explicit failure logging
- If a data source fails, pipeline continues with previous day's value and flags the gap in the morning brief
- Never let one failing data source kill the entire pipeline
- Log all failures to a `pipeline_errors` table in Supabase (date, source, error message, timestamp)

### Supabase Writes
- Use upsert (insert or update on conflict) — never plain insert for daily signal tables
- Unique constraint on (date, pair) for all time series tables
- Always check if today's row exists before writing — don't duplicate
- Batch writes where possible — don't write one row per API call when you can batch

### GitHub Actions
- Pipeline cron: **`0 23 * * *`** UTC daily (see `.github/workflows/daily_brief.yml` — after US cash close; weekend runs allowed)
- Secrets injected as environment variables — never in code
- Pipeline failure sends notification (email or Slack webhook — add when available)
- Do not change the cron schedule without explicit instruction

---

## SIGNAL DESIGN RULES

Every signal added to this framework must pass four tests before you build it:

1. **Institutional validity** — A real macro PM at a G10 FX desk uses this signal. Not just "looks quantitative."
2. **Independence** — It is not a noisier version of an existing signal.
3. **Data availability** — Source is free, reliable, automatable, daily or better frequency.
4. **Regime relevance** — It discriminates between trending, mean-reverting, vol-expanding, and crisis regimes.

If a signal doesn't pass all four, do not build it. Flag the failure and ask for clarification.

### Signal Naming Convention
```python
# All signal columns follow this naming convention in Supabase and code:
rate_diff_2y          # Rate differential, 2Y tenor
rate_diff_zscore      # Z-score of rate differential change
cot_lev_money_net     # Leveraged money net contracts
cot_percentile        # COT percentile rank
realized_vol_5d       # 5-day realized vol
implied_vol_30d       # CME CVOL 30-day implied vol
vol_skew              # CVOL Skew (UpVar - DnVar)
risk_reversal_25d     # Synthetic 25-delta RR
oi_delta              # Daily OI change
```

### Percentile Calculation Standard
All percentile calculations use a 52-week (260-trading-day) rolling window. Clip to [0, 100]. This is consistent across all signals — COT, vol, RR.

```python
def compute_percentile(series: pd.Series, window: int = 260) -> float:
    """
    Compute rolling percentile rank for a given series.
    Returns the current value's percentile within the trailing window.
    Window defaults to 52 weeks (260 trading days).
    """
    if len(series) < window:
        window = len(series)
    rolling_window = series.iloc[-window:]
    current_value = series.iloc[-1]
    percentile = (rolling_window < current_value).sum() / len(rolling_window) * 100
    return round(float(percentile), 1)
```

---

## INFRASTRUCTURE RULES

### Supabase
- Use `supabase-py` client library
- All reads use `.select()` with explicit column names — never `select('*')` in production
- All writes use `.upsert()` with `on_conflict='date,pair'` for daily tables
- **Lazy init:** build the client only when `SUPABASE_URL` and a write key are both set; **`None` if missing**. **Never raise `EnvironmentError` on module import** — log warning, skip remote writes, keep pipeline non-blocking (local dev without secrets).
- Reuse one client per process after creation

```python
import logging
import os
from typing import Optional

from supabase import create_client, Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    logger.warning("Supabase URL/key not set — remote writes skipped")
```

### Cloudflare Pages (public site — fxregimelab.com)
- **Phase 0A:** ship full UI shell with **placeholders** before Supabase (see PLAN.md).
- **Phase 0B onward:** read-only Supabase via **anon** key in browser; explicit columns — never `select('*')` in production
- **Bloomberg-style** public tokens: see PLAN Phase 0A (primary `#0a0e1a`, card `#0d1117`, elevated `#111827`, borders `#1e293b` / `#161e2e`, **JetBrains Mono** for figures)
- Mobile responsive — the site is shared on LinkedIn and viewed on mobile

### CSV Fallback
Maintain CSV writes alongside Supabase writes during transition. Once Supabase is verified stable for 30 days, CSV writes can be deprecated. Not before.

```python
def write_signals(data: dict, date: str, pair: str):
    """Write signal data to both Supabase and CSV fallback."""
    # Supabase write (primary)
    try:
        if supabase is None:
            raise RuntimeError("supabase client not configured")
        supabase.table('signals').upsert({
            'date': date,
            'pair': pair,
            **data
        }, on_conflict='date,pair').execute()
    except Exception as e:
        log_pipeline_error('supabase_write', str(e))
    
    # CSV fallback
    csv_path = f"data/{pair.lower()}_signals.csv"
    row = pd.DataFrame([{'date': date, 'pair': pair, **data}])
    if os.path.exists(csv_path):
        row.to_csv(csv_path, mode='a', header=False, index=False)
    else:
        row.to_csv(csv_path, index=False)
```

---

## DESIGN RULES (DASHBOARD AND CHARTS)

### Color System — Always Use These, Never Deviate
```css
/* Background layers */
--bg-primary: #0a0e1a;
--bg-card: #111827;
--bg-header: #0d1424;
--border: #1f2937;
--border-light: #1e293b;

/* Pair identity colors */
--eurusd: #4da6ff;
--usdjpy: #ff9944;
--usdinr: #e74c3c;
--gbpusd: #10b981;
--gold: #f0a500;
--dxy: #e74c3c;

/* Text */
--text-primary: #f9fafb;
--text-secondary: #9ca3af;
--text-muted: #6b7280;

/* Chart grid */
--grid: rgba(30,41,59,0.90);

/* Font */
font-family: 'Inter', system-ui, -apple-system, sans-serif;
```

### Chart.js Standard Config
```javascript
const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      grid: { color: 'rgba(30,41,59,0.90)', lineWidth: 0.8 },
      ticks: { color: '#6b7280', font: { size: 11.5, family: 'Inter' } },
      border: { color: '#374151' }
    },
    y: {
      grid: { color: 'rgba(30,41,59,0.90)', lineWidth: 0.8 },
      ticks: { color: '#6b7280', font: { size: 11, family: 'Inter' } },
      border: { color: '#374151' }
    }
  },
  plugins: {
    legend: {
      labels: {
        color: '#d1d5db',
        font: { size: 12, family: 'Inter' }
      }
    }
  }
};
```

### Dashboard Cards Always Include:
- Current value
- Percentile rank (where applicable)
- Direction vs previous day (▲ / ▼)
- Color coding: green for bullish, red for bearish, gray for neutral — consistently applied per pair identity color
- Source attribution

### Morning Brief HTML Always Includes:
- FX Regime Lab logo (wordmark) in header
- Date and "Data as of [DATE]" label
- Regime call per pair with confidence
- Signal change callouts
- Footer: "Source: FX Regime Lab Pipeline · fxregimelab.com" (see PLAN Phase 3; Substack may appear on other surfaces)

---

## WHAT NOT TO BUILD

Do not build any of the following without explicit instruction:

- Social media sentiment analysis (Reddit, X/Twitter scraping)
- ML models (RandomForest, XGBoost, neural networks) — Phase 5+ only
- DCF models or equity valuation
- C++ components
- Mobile app
- Firebase integration — project uses Supabase
- Any new data source that is not free, automatable, and daily frequency
- New chart types or UI elements just because they look interesting
- Authentication or payment systems — Phase 9 only
- FinBERT or any NLP pipeline — Phase 7 only (sem 7, ~July 2027)

---

## WHAT THIS PROJECT MUST ALWAYS DEMONSTRATE

Every build session should move at least one of these four markers forward:

1. **Signal depth** — the framework detects something it couldn't detect before
2. **Data quality** — the underlying data is more reliable, more timely, or better structured
3. **Infrastructure maturity** — the pipeline is more robust, more automated, or better monitored
4. **Presentation quality** — the output (dashboard, morning brief) reads more like institutional research

If a session ends without moving any of these four markers, the session was spent on the wrong thing. Flag it and redirect.

---

## HOW TO HANDLE AMBIGUITY

If a build request is ambiguous, resolve it in this priority order:

1. **Check PLAN.md** — is this task defined in a phase? Follow the spec exactly.
2. **Apply signal design rules** — does the proposed implementation pass all four signal tests?
3. **Default to less complexity** — simpler implementation that works beats complex implementation that might work
4. **Default to Supabase first** — all persistent data goes to Supabase, not files, not memory
5. **Ask before deviating** — if the right implementation requires breaking any rule in this file, stop and ask explicitly before proceeding

---

## SESSION START CHECKLIST

Every Cursor session on this project begins with:

- [ ] Read CONTEXT.md — full project context confirmed
- [ ] Read PLAN.md — current phase and next phase confirmed
- [ ] Check Supabase schema — no conflicts with planned writes
- [ ] Check existing pipeline scripts — understand what already runs
- [ ] Confirm GitHub Actions secrets are in place for any new API calls
- [ ] Confirm what phase is being built today and what the session deliverable is

Session deliverable must be stated explicitly before any code is written:
> "Today's session will build [X]. It will write to [Supabase tables]. It will run as [run.py step name]. It will be visible at [fxregimelab.com path / brief / charts]."

---

## Data path

- Production: Supabase via Worker-injected credentials (`/assets/supabase-env.js`)
- Fallback: `site/data/*.csv` and `site/static/*.json` copied by `scripts/publish_brief_for_site.py`
- Local dev: `data/*.csv` and `data/*.json` generated by local pipeline runs
- Priority order: Supabase > CSV fallback > user-facing error state

---

## Brief system

- `ai_article.json`: generated by `ai_brief.py` using Claude Haiku
- Published to: `site/data/ai_article.json` (latest)
- Archives: `site/data/ai_article_YYYYMMDD.json`
- Displayed at: `/brief/` (article format, light theme)
- Old dark brief route: `/brief/latest.html` is redirect-only

---

## Browser storage keys (frontend)

Documented keys for the public site and terminal (do not rename without updating this list):

- `fxrl_theme`: **sessionStorage only** (tab-scoped) — not localStorage. Each new tab starts on the public light theme; only the current tab remembers terminal on refresh.
- `fxrl_chartbuilder_theme`: localStorage (`chart-builder.js` — dark/light export theme preference).
- `fxrl_workspace_markers`, `fxrl_workspace_reflines`: localStorage (`workspace.js`).
- `fxrl_quickcharts`: localStorage (`chart-builder.js` — user quick-chart presets).

---

## EXTENSION OF STRATEGY CHATS

This file and the project it governs are an extension of two ongoing strategic conversations:

1. **Framework strategy chat** — decides what to build next, interprets signal output, validates institutional relevance of new signals
2. **Career strategy chat** — governs how the framework connects to MFE applications, internship targeting, LinkedIn positioning, and the SSRN paper

Any major architectural decision that isn't covered in PLAN.md should be taken back to the framework strategy chat before implementation. Cursor builds what the strategy chats decide. The strategy chats do not write code. The build direction flows one way: strategy → plan → cursor → pipeline.
