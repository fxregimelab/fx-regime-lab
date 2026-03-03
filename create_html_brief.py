import os
import glob
import base64
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

TODAY     = datetime.today().strftime('%Y-%m-%d')
TODAY_FMT = datetime.today().strftime('%A, %d %B %Y')
DATE_SLUG = TODAY.replace('-', '')


def ordinal(n):
    n = int(n)
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{['th','st','nd','rd','th'][min(n%10,4)]}"


def embed_image(filepath):
    if not os.path.exists(filepath):
        return ""
    with open(filepath, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')
    return f"data:image/png;base64,{data}"


def fmt_pct(val, suffix='%', decimals=2):
    try:
        v = float(val)
        sign = '+' if v >= 0 else ''
        return f"{sign}{v:.{decimals}f}{suffix}"
    except:
        return '—'


def color_class(val):
    try:
        return 'positive' if float(val) >= 0 else 'negative'
    except:
        return ''


# load data
path = 'data/latest_with_cot.csv'
if not os.path.exists(path):
    print(f"ERROR: {path} not found")
    sys.exit(1)
df = pd.read_csv(path, index_col=0, parse_dates=True)
row = df.dropna(subset=['EURUSD', 'USDJPY']).iloc[-1]

# data freshness — derived from master CSV
data_date = df.dropna(subset=['EURUSD']).index[-1].strftime('%d %b %Y')

cot_date = '—'
if 'EUR_net_pos' in df.columns:
    _cot_series = df['EUR_net_pos'].dropna()
    if len(_cot_series) > 0:
        cot_date = _cot_series.index[-1].strftime('%d %b %Y')

pipeline_run = datetime.now().strftime('%d %b %Y %H:%M IST')

def get_next_cot_date():
    today = datetime.today()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        # today is friday - check if after 9:30pm IST (3:30pm EST)
        if today.hour >= 21:
            days_until_friday = 7
    next_friday = today + timedelta(days=days_until_friday)
    return next_friday.strftime("%d %b %Y")

next_cot_date = get_next_cot_date()

# commodity snapshot for status bar — best-effort, silent on failure
import yfinance as yf

def get_commodity_price(ticker, label):
    try:
        data = yf.Ticker(ticker).fast_info
        price = round(data['last_price'], 2)
        return f"{label}: {price}"
    except:
        try:
            hist = yf.download(ticker, period="2d", interval="1d",
                             progress=False, auto_adjust=True)
            if len(hist) > 0:
                price = round(float(hist['Close'].iloc[-1]), 2)
                return f"{label}: {price}"
        except:
            pass
    return None

_brent_raw = get_commodity_price('BZ=F', 'Brent')
_gold_raw   = get_commodity_price('GC=F', 'Gold')

def safe(col):
    return row.get(col, '—')

def clean_level(val):
  """Clean key level value: convert NaN or 'nan' string to em dash."""
  if val is None or val == '':
    return '—'
  # Check for actual NaN
  try:
    if pd.isna(val):
      return '—'
  except:
    pass
  # Check for string 'nan'
  if isinstance(val, str):
    if val.lower() == 'nan':
      return '—'
    return val
  # Try to convert to float and back to catch numeric NaN
  try:
    v = float(val)
    if np.isnan(v):
      return '—'
    return str(val)
  except:
    return val if val else '—'

# extract fields
# raw values
EURUSD = safe('EURUSD')
USDJPY = safe('USDJPY')
DXY    = safe('DXY')
# USD/INR — safe fallback if inr_pipeline.py has not been run
_inr_available = 'USDINR' in df.columns and df['USDINR'].notna().any()
USDINR    = safe('USDINR')  if _inr_available else '—'
USDINR_1D = safe('USDINR_chg_1D')  if 'USDINR_chg_1D'  in df.columns else '—'
USDINR_12M= safe('USDINR_chg_12M') if 'USDINR_chg_12M' in df.columns else '—'

# price change columns (raw, will format in template)
EURUSD_1D = safe('EURUSD_chg_1D')
EURUSD_12M= safe('EURUSD_chg_12M')
USDJPY_1D = safe('USDJPY_chg_1D')
USDJPY_12M= safe('USDJPY_chg_12M')
DXY_1D    = safe('DXY_chg_1D')
DXY_12M   = safe('DXY_chg_12M')

# spreads (today + 1W and 12M changes)
US_DE_10Y = safe('US_DE_10Y_spread')
US_DE_10Y_1W = safe('US_DE_10Y_spread_chg_1W')
US_DE_10Y_12M = safe('US_DE_10Y_spread_chg_12M')
US_DE_2Y  = safe('US_DE_2Y_spread')
US_DE_2Y_1W = safe('US_DE_2Y_spread_chg_1W')
US_DE_2Y_12M = safe('US_DE_2Y_spread_chg_12M')
US_JP_10Y = safe('US_JP_10Y_spread')
US_JP_10Y_1W = safe('US_JP_10Y_spread_chg_1W')
US_JP_10Y_12M = safe('US_JP_10Y_spread_chg_12M')
US_JP_2Y  = safe('US_JP_2Y_spread')
US_JP_2Y_1W = safe('US_JP_2Y_spread_chg_1W')
US_JP_2Y_12M = safe('US_JP_2Y_spread_chg_12M')
# US-IN spreads (from inr_pipeline — cross-maturity US 2Y vs IN 10Y)
US_IN_10Y     = safe('US_IN_10Y_spread')    if 'US_IN_10Y_spread'    in df.columns else '—'
US_IN_10Y_12M = '—'   # no 12M change column yet — computed from monthly FRED data
US_IN_pol     = safe('US_IN_policy_spread') if 'US_IN_policy_spread' in df.columns else '—'
US_IN_pol_12M = '—'
# 1W change = current value minus value 5 rows back
def _spread_1w_chg(col):
    if col not in df.columns:
        return '—'
    s = df[col].dropna()
    if len(s) < 6:
        return '—'
    return round(float(s.iloc[-1]) - float(s.iloc[-6]), 4)
US_IN_10Y_1W = _spread_1w_chg('US_IN_10Y_spread')
US_IN_pol_1W = _spread_1w_chg('US_IN_policy_spread')
# FPI flows
FPI_20D_flow = safe('FPI_20D_flow')       if 'FPI_20D_flow'       in df.columns else '—'
FPI_20D_pct  = safe('FPI_20D_percentile') if 'FPI_20D_percentile' in df.columns else '—'

# volatility
EURUSD_vol30 = safe('EURUSD_vol30')
EURUSD_vol_pct = safe('EURUSD_vol_pct')
USDJPY_vol30 = safe('USDJPY_vol30')
USDJPY_vol_pct = safe('USDJPY_vol_pct')

# regime correlation
EURUSD_corr = safe('EURUSD_spread_corr_60d')
USDJPY_corr = safe('USDJPY_spread_corr_60d')

# key levels
EUR_S1 = clean_level(safe('EURUSD_S1'))
EUR_S2 = clean_level(safe('EURUSD_S2'))
EUR_S3 = clean_level(safe('EURUSD_S3'))
EUR_R1 = clean_level(safe('EURUSD_R1'))
EUR_R2 = clean_level(safe('EURUSD_R2'))
EUR_R3 = clean_level(safe('EURUSD_R3'))
JPY_S1 = clean_level(safe('USDJPY_S1'))
JPY_S2 = clean_level(safe('USDJPY_S2'))
JPY_S3 = clean_level(safe('USDJPY_S3'))
JPY_R1 = clean_level(safe('USDJPY_R1'))
JPY_R2 = clean_level(safe('USDJPY_R2'))
JPY_R3 = clean_level(safe('USDJPY_R3'))

# positioning percentiles and nets
EUR_lev_pct = safe('EUR_lev_percentile')
EUR_net = safe('EUR_net_pos')
EUR_am_pct = safe('EUR_assetmgr_percentile')
EUR_am_net = row.get('EUR_assetmgr_net_pos', row.get('EUR_assetmgr_net', EUR_net))
JPY_lev_pct = safe('JPY_lev_percentile')
JPY_net = safe('JPY_net_pos')
JPY_am_pct = safe('JPY_assetmgr_percentile')
JPY_am_net = row.get('JPY_assetmgr_net_pos', row.get('JPY_assetmgr_net', JPY_net))


# helper formatters
def fmt_pct_nosign(val, suffix='%', decimals=2):
  try:
    v = float(val)
    return f"{v:.{decimals}f}{suffix}"
  except:
    return '—'

def fmt_net(val):
  try:
    v = int(float(val))
    sign = '+' if v >= 0 else ''
    return f"{sign}{v:,}"
  except:
    return '—'

def ordinal_or_dash(val):
  try:
    return ordinal(int(float(val)))
  except:
    return '—'

# format basic price strings
try: EURUSD = f"{float(EURUSD):.4f}"
except: pass
try: USDJPY = f"{float(USDJPY):.4f}"
except: pass
try: DXY = f"{float(DXY):.2f}"
except: pass
try: USDINR = f"{float(USDINR):.4f}"
except: pass

# format spreads for display (no sign)
US_DE_10Y = fmt_pct_nosign(US_DE_10Y)
US_DE_2Y = fmt_pct_nosign(US_DE_2Y)
US_JP_10Y = fmt_pct_nosign(US_JP_10Y)
US_JP_2Y = fmt_pct_nosign(US_JP_2Y)
US_IN_10Y_disp = fmt_pct_nosign(US_IN_10Y)
US_IN_pol_disp = fmt_pct_nosign(US_IN_pol)

# format vol30 values with 1 decimal place
def fmt_vol30(val):
  try:
    return f"{round(float(val), 1)}%"
  except:
    return '—'

EURUSD_vol30 = fmt_vol30(EURUSD_vol30)
USDJPY_vol30 = fmt_vol30(USDJPY_vol30)

# format nets for display
EUR_net_disp = fmt_net(EUR_net)
EUR_am_net_disp = fmt_net(EUR_am_net)
JPY_net_disp = fmt_net(JPY_net)
JPY_am_net_disp = fmt_net(JPY_am_net)




# ── status bar ───────────────────────────────────────────────────────────────
def _sb_arrow(chg):
    try:
        v = float(chg)
        if v > 0: return '▲'
        if v < 0: return '▼'
    except: pass
    return '—'

def _sb_cls(chg):
    try:
        v = float(chg)
        if v > 0: return 'sb-pos'
        if v < 0: return 'sb-neg'
    except: pass
    return 'sb-muted'

_sb_parts = [
    f'EUR/USD <span class="sb-price">{EURUSD}</span> <span class="{_sb_cls(EURUSD_1D)}">{_sb_arrow(EURUSD_1D)} {fmt_pct(EURUSD_1D)}</span>',
    f'USD/JPY <span class="sb-price">{USDJPY}</span> <span class="{_sb_cls(USDJPY_1D)}">{_sb_arrow(USDJPY_1D)} {fmt_pct(USDJPY_1D)}</span>',
    f'DXY <span class="sb-price">{DXY}</span> <span class="{_sb_cls(DXY_1D)}">{_sb_arrow(DXY_1D)} {fmt_pct(DXY_1D)}</span>',
]
_usdinr_price = df['USDINR'].dropna().iloc[-1]     if 'USDINR'        in df.columns and df['USDINR'].notna().any()        else None
_usdinr_chg   = df['USDINR_chg_1D'].dropna().iloc[-1] if 'USDINR_chg_1D' in df.columns and df['USDINR_chg_1D'].notna().any() else None
try:
    _usdinr_price = float(_usdinr_price)
    _usdinr_chg   = float(_usdinr_chg)
    if not pd.isna(_usdinr_price):
        _u_arrow = '▲' if _usdinr_chg > 0 else '▼' if _usdinr_chg < 0 else '—'
        _u_color = 'green' if _usdinr_chg > 0 else '#e74c3c' if _usdinr_chg < 0 else 'white'
        _sb_parts.append(
            f'USD/INR <span class="sb-price">{_usdinr_price:.2f}</span>'
            f' <span style="color:{_u_color}">{_u_arrow} {_usdinr_chg:+.2f}%</span>'
        )
except (TypeError, ValueError):
    pass
if _brent_raw:
    try:
        _v = float(_brent_raw.split(': ', 1)[1])
        _sb_parts.append(f'Brent <span class="sb-price">${_v:.2f}</span>')
    except:
        pass
if _gold_raw:
    try:
        _v = float(_gold_raw.split(': ', 1)[1])
        _sb_parts.append(f'Gold <span class="sb-price">${int(round(_v)):,}</span>')
    except:
        pass

_sb_sep = ' <span class="sb-sep">|</span> '
statusbar_html = (
    '<div class="statusbar">'
    f'<span>{_sb_sep.join(_sb_parts)}</span>'
    f'<span class="sb-updated">Updated: {pipeline_run}</span>'
    '</div>'
)
# ─────────────────────────────────────────────────────────────────────────────

charts = {
    'eurusd_fund':  embed_image(f'charts/eurusd_fundamentals_{DATE_SLUG}.png'),
    'eurusd_pos':   embed_image(f'charts/eurusd_positioning_{DATE_SLUG}.png'),
    'eurusd_vol':   embed_image(f'charts/eurusd_volatility_{DATE_SLUG}.png'),
    'usdjpy_fund':  embed_image(f'charts/usdjpy_fundamentals_{DATE_SLUG}.png'),
    'usdjpy_pos':   embed_image(f'charts/usdjpy_positioning_{DATE_SLUG}.png'),
    'usdjpy_vol':   embed_image(f'charts/usdjpy_volatility_{DATE_SLUG}.png'),
}

usdinr_fundamentals_files = sorted(glob.glob("charts/usdinr_fundamentals_*.png"))
usdinr_fundamentals_b64   = (
    base64.b64encode(open(usdinr_fundamentals_files[-1], 'rb').read()).decode()
    if usdinr_fundamentals_files else None
)


def vol_flag(pct):
    try:
        p = float(pct)
    except:
        return "—", "badge-neutral"
    if p >= 90: return "EXTREME", "badge-extreme"
    if p >= 75: return "ELEVATED", "badge-elevated"
    return "NORMAL", "badge-neutral"


def corr_flag(corr_val):
    """Return correlation status flag and CSS class.
    
    INTACT: correlation > 0.6 (spread changes drive FX moves)
    WEAKENING: correlation 0.3 - 0.6 (regime becoming uncertain)
    BROKEN: correlation < 0.3 (fundamentals decoupled from FX)
    """
    try:
        c = float(corr_val)
    except:
        return "—", "badge-neutral"
    if c > 0.6: return "INTACT", "badge-success"
    if c > 0.3: return "WEAKENING", "badge-warning"
    return "BROKEN", "badge-danger"


def fmt_corr(val):
    """Format correlation value."""
    try:
        c = float(val)
        return f"{c:+.3f}"
    except:
        return "—"


def pos_regime(pct):
    """Return positioning regime label and CSS class."""
    try:
        p = float(pct)
    except:
        return "—", "badge-neutral"
    if p >= 80: return "CROWDED LONG", "badge-danger"
    if p <= 20: return "CROWDED SHORT", "badge-success"
    return "NEUTRAL", "badge-neutral"


def fmt_pct(val, suffix='%', decimals=2):
    try:
        v = float(val)
        sign = '+' if v >= 0 else ''
        return f"{sign}{v:.{decimals}f}{suffix}"
    except:
        return '—'


def color_class(val):
    try:
        return 'positive' if float(val) >= 0 else 'negative'
    except:
        return ''

# format correlation for display
EURUSD_corr_fmt = fmt_corr(EURUSD_corr)
USDJPY_corr_fmt = fmt_corr(USDJPY_corr)

# prepare regime badges
eur_pos_regime, eur_pos_class = pos_regime(EUR_lev_pct)
jpy_pos_regime, jpy_pos_class = pos_regime(JPY_lev_pct)

eur_vol_text, eur_vol_class = vol_flag(EURUSD_vol_pct)
jpy_vol_text, jpy_vol_class = vol_flag(USDJPY_vol_pct)

eur_corr_text, eur_corr_class = corr_flag(EURUSD_corr)
jpy_corr_text, jpy_corr_class = corr_flag(USDJPY_corr)

# USD/INR FPI regime
def fpi_regime(flow_val, pct_val):
    """Return FPI regime badge text and CSS class."""
    try:
        float(flow_val)
        p = float(pct_val)
        if p >= 80: return "INFLOWS CROWDED", "badge-danger"
        if p <= 20: return "OUTFLOWS CROWDED", "badge-success"
        return "NEUTRAL", "badge-neutral"
    except:
        return "DATA LIMITED", "badge-neutral"

FPI_20D_flow_disp = fmt_net(FPI_20D_flow) if FPI_20D_flow != '—' else 'unavailable'
FPI_20D_pct_disp  = ordinal_or_dash(FPI_20D_pct)

# INR regime: use spread data if available, regardless of FPI
_inr_spread_available = (
    'US_IN_10Y_spread' in df.columns and df['US_IN_10Y_spread'].notna().any()
)
if _inr_spread_available:
    _raw_spread = df['US_IN_10Y_spread'].dropna().iloc[-1]
    _spread_disp = f"{_raw_spread:.2f}"
    _premium_pp = abs(_raw_spread)
    inr_read = (
        f"US-IN spread at {_spread_disp}%. "
        f"India yield premium intact at {_premium_pp:.2f}pp. "
        "Rate differential favors INR strength. "
        "FPI positioning data pending Playwright integration."
    )
    inr_fpi_text  = "RATE DIFF ONLY"
    inr_fpi_class = "badge-neutral"
else:
    inr_read = "run inr_pipeline.py to populate USD/INR data."
    inr_fpi_text  = "DATA LIMITED"
    inr_fpi_class = "badge-neutral"

# regime read texts
eur_read = (
    "Spread compression supports EUR strength. "
    f"Leveraged Money {ordinal(int(EUR_lev_pct))} and Asset Manager {ordinal(int(EUR_am_pct))} both crowded long — "
    "dual category confirmation, strongest reversal risk signal this framework produces."
)
jpy_read = (
    "Spread compression favors lower USD/JPY. "
    f"Leveraged Money {ordinal(int(JPY_lev_pct))} and Asset Manager {ordinal(int(JPY_am_pct))} both neutral — "
    "carry partially intact, BoJ path is key variable."
)
# append vol warnings
if jpy_vol_text != 'NORMAL':
    jpy_read += f" vol {jpy_vol_text.lower()} — positioning signals less reliable."

usdinr_fund_html = (
    f'<img src="data:image/png;base64,{usdinr_fundamentals_b64}" style="width:100%;border-radius:4px;" class="chart-img" onclick="openLightbox(this)">'
    if usdinr_fundamentals_b64 is not None
    else '<div style="color:#484f58;padding:40px;text-align:center;font-size:12px;">Chart not available — run create_dashboards.py first</div>'
)

# build HTML
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>G10 FX Morning Brief — {TODAY_FMT}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: #0d1117;
    color: #e6edf3;
    font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    padding: 24px;
    max-width: 1400px;
    margin: 0 auto;
}}
.header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 1px solid #30363d;
    padding-bottom: 12px;
    margin-bottom: 20px;
}}
.header h1 {{
    font-size: 16px;
    font-weight: 600;
    color: #58a6ff;
    letter-spacing: 0.5px;
}}
.header .meta {{
    font-size: 11px;
    color: #8b949e;
    text-align: right;
    line-height: 1.6;
}}
.grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
}}
.grid-3 {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
    margin-bottom: 12px;
}}
.card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 14px 16px;
}}
.card-title {{
    font-size: 10px;
    font-weight: 600;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 10px;
    border-bottom: 1px solid #21262d;
    padding-bottom: 6px;
}}
table {{ width: 100%; border-collapse: collapse; }}
th {{
    font-size: 10px;
    color: #8b949e;
    text-align: right;
    padding: 3px 6px 6px;
    font-weight: 400;
}}
th:first-child {{ text-align: left; }}
td {{
    padding: 4px 6px;
    font-size: 12px;
    text-align: right;
    border-top: 1px solid #21262d;
}}
td:first-child {{ text-align: left; color: #e6edf3; font-weight: 500; }}
.positive {{ color: #3fb950; }}
.negative {{ color: #f85149; }}
.neutral-text {{ color: #8b949e; }}
.badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
.badge-danger   {{ background: #3d1f1f; color: #f85149; border: 1px solid #5a2020; }}
.badge-success  {{ background: #1f3d2a; color: #3fb950; border: 1px solid #204d2e; }}
.badge-neutral  {{ background: #1f2937; color: #8b949e; border: 1px solid #374151; }}
.badge-elevated {{ background: #3d2e1f; color: #d29922; border: 1px solid #5a421f; }}
.badge-extreme  {{ background: #3d1f1f; color: #f85149; border: 1px solid #5a2020; }}
.regime-block {{
    margin-bottom: 14px;
    padding-bottom: 14px;
    border-bottom: 1px solid #21262d;
}}
.regime-block:last-child {{ border-bottom: none; margin-bottom: 0; }}
.regime-pair {{
    font-size: 13px;
    font-weight: 600;
    color: #58a6ff;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.regime-text {{
    color: #c9d1d9;
    line-height: 1.6;
    font-size: 12px;
}}
.charts-section {{ margin-bottom: 12px; }}
.pair-label {{
    font-size: 11px;
    font-weight: 600;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
    padding-left: 4px;
}}
.chart-img {{
    width: 100%;
    height: auto;
    border-radius: 4px;
    cursor: pointer;
    border: 1px solid #30363d;
    transition: border-color 0.2s;
    display: block;
}}
.chart-img:hover {{ border-color: #58a6ff; }}
.chart-card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px;
}}
.chart-label {{
    font-size: 9px;
    color: #8b949e;
    text-align: center;
    margin-top: 5px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}
.footer {{
    margin-top: 20px;
    padding-top: 12px;
    border-top: 1px solid #21262d;
    font-size: 10px;
    color: #484f58;
    display: flex;
    justify-content: space-between;
}}
/* Status bar */
.statusbar {{
    background: #1a1a2e;
    margin: -24px -24px 20px -24px;
    padding: 7px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: #8b949e;
    border-bottom: 1px solid #21262d;
}}
.sb-price   {{ color: #e6edf3; font-weight: 600; }}
.sb-pos     {{ color: #3fb950; }}
.sb-neg     {{ color: #f85149; }}
.sb-muted   {{ color: #8b949e; }}
.sb-sep     {{ color: #484f58; }}
.sb-updated {{ color: #6e7681; padding-left: 16px; flex-shrink: 0; }}
/* Lightbox */
.lightbox {{
    display: none;
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.92);
    z-index: 1000;
    cursor: pointer;
    justify-content: center;
    align-items: center;
}}
.lightbox.active {{ display: flex; }}
.lightbox img {{
    max-width: 95vw;
    max-height: 95vh;
    border-radius: 4px;
    object-fit: contain;
}}
</style>
</head>
<body>
<!-- STATUS BAR -->
{statusbar_html}
<!-- HEADER -->
<div class="header">
  <div>
    <div style="font-size:11px;color:#8b949e;margin-bottom:4px;">G10 FX REGIME DETECTION FRAMEWORK</div>
    <h1>MORNING BRIEF — {TODAY_FMT.upper()}</h1>
  </div>
  <div class="meta">
    data as of: {data_date}<br>
    COT as of: {cot_date}<br>
    next COT: {next_cot_date}<br>
    pipeline run: {pipeline_run}
  </div>
</div>

<!-- ROW 1: PRICES full width -->
<div class="card" style="margin-bottom:12px;">
  <div class="card-title">Prices</div>
  <table>
    <tr>
      <th>Pair</th><th>Price</th><th>1D</th><th>12M</th>
    </tr>
    <tr><td>EUR/USD</td><td>{EURUSD}</td><td class="{color_class(EURUSD_1D)}">{fmt_pct(EURUSD_1D)}</td><td class="{color_class(EURUSD_12M)}">{fmt_pct(EURUSD_12M)}</td></tr>
    <tr><td>USD/JPY</td><td>{USDJPY}</td><td class="{color_class(USDJPY_1D)}">{fmt_pct(USDJPY_1D)}</td><td class="{color_class(USDJPY_12M)}">{fmt_pct(USDJPY_12M)}</td></tr>
    <tr><td>DXY</td><td>{DXY}</td><td class="{color_class(DXY_1D)}">{fmt_pct(DXY_1D)}</td><td class="{color_class(DXY_12M)}">{fmt_pct(DXY_12M)}</td></tr>
    <tr><td>USD/INR</td><td>{USDINR}</td><td class="{color_class(USDINR_1D)}">{fmt_pct(USDINR_1D)}</td><td class="{color_class(USDINR_12M)}">{fmt_pct(USDINR_12M)}</td></tr>
  </table>
</div>

<!-- ROW 2: RATE DIFFERENTIALS left | VOLATILITY right -->
<div class="grid-2">
  <div class="card">
    <div class="card-title">Rate Differentials <span style="color:#484f58;font-weight:400;">(narrowing = foreign ccy strengthens)</span></div>
    <table>
      <tr><th>Spread</th><th>Today</th><th>1W chg</th><th>12M chg</th></tr>
      <tr><td>US-DE 10Y (cross)</td><td>{US_DE_10Y}</td><td class="{color_class(US_DE_10Y_1W)}">{fmt_pct(US_DE_10Y_1W,'pp')}</td><td class="{color_class(US_DE_10Y_12M)}">{fmt_pct(US_DE_10Y_12M,'pp')}</td></tr>
      <tr><td>US-DE 2Y (same)</td><td>{US_DE_2Y}</td><td class="{color_class(US_DE_2Y_1W)}">{fmt_pct(US_DE_2Y_1W,'pp')}</td><td class="{color_class(US_DE_2Y_12M)}">{fmt_pct(US_DE_2Y_12M,'pp')}</td></tr>
      <tr><td>US-JP 10Y (cross)</td><td>{US_JP_10Y}</td><td class="{color_class(US_JP_10Y_1W)}">{fmt_pct(US_JP_10Y_1W,'pp')}</td><td class="{color_class(US_JP_10Y_12M)}">{fmt_pct(US_JP_10Y_12M,'pp')}</td></tr>
      <tr><td>US-JP 2Y (same)</td><td>{US_JP_2Y}</td><td class="{color_class(US_JP_2Y_1W)}">{fmt_pct(US_JP_2Y_1W,'pp')}</td><td class="{color_class(US_JP_2Y_12M)}">{fmt_pct(US_JP_2Y_12M,'pp')}</td></tr>
      <tr style="border-top:1px solid #30363d;"><td>US-IN 10Y (cross) *</td><td>{US_IN_10Y_disp}</td><td class="{color_class(US_IN_10Y_1W)}">{fmt_pct(US_IN_10Y_1W,'pp')}</td><td class="neutral-text">{US_IN_10Y_12M}</td></tr>
      <tr><td>US-IN policy</td><td>{US_IN_pol_disp}</td><td class="{color_class(US_IN_pol_1W)}">{fmt_pct(US_IN_pol_1W,'pp')}</td><td class="neutral-text">{US_IN_pol_12M}</td></tr>
    </table>
    <div style="font-size:10px;color:#484f58;margin-top:6px;">* IN 10Y = FRED monthly, ~30 day lag</div>
  </div>
  <div class="card">
    <div class="card-title">Volatility <span style="color:#484f58;font-weight:400;">(30D realized, annualized | 3Y pct)</span></div>
    <table>
      <tr><th>Pair</th><th>Vol</th><th>Percentile</th><th>Flag</th></tr>
      <tr><td>EUR/USD</td><td>{EURUSD_vol30}</td><td>{ordinal_or_dash(EURUSD_vol_pct)}</td><td><span class="badge {eur_vol_class}">{eur_vol_text}</span></td></tr>
      <tr><td>USD/JPY</td><td>{USDJPY_vol30}</td><td>{ordinal_or_dash(USDJPY_vol_pct)}</td><td><span class="badge {jpy_vol_class}">{jpy_vol_text}</span></td></tr>
    </table>
  </div>
</div>

<!-- ROW 2.5: REGIME CORRELATION -->
<div class="card">
  <div class="card-title">Regime Correlation <span style="color:#484f58;font-weight:400;">(60D rolling | spread vs FX move)</span></div>
  <table>
    <tr><th>Pair</th><th>Correlation</th><th>Flag</th></tr>
    <tr><td>EUR/USD</td><td>{EURUSD_corr_fmt}</td><td><span class="badge {eur_corr_class}">{eur_corr_text}</span></td></tr>
    <tr><td>USD/JPY</td><td>{USDJPY_corr_fmt}</td><td><span class="badge {jpy_corr_class}">{jpy_corr_text}</span></td></tr>
  </table>
</div>

<!-- ROW 2.75: KEY LEVELS -->
<div class="card">
  <div class="card-title">Key Levels <span style="color:#484f58;font-weight:400;">(180D | S=support, R=resistance)</span></div>
  <table>
    <tr><th colspan="4">EUR/USD</th></tr>
    <tr><td><strong>S3</strong></td><td>{EUR_S3}</td><td><strong>S2</strong></td><td>{EUR_S2}</td></tr>
    <tr><td><strong>S1</strong></td><td>{EUR_S1}</td><td><strong>R1</strong></td><td>{EUR_R1}</td></tr>
    <tr><td><strong>R2</strong></td><td>{EUR_R2}</td><td><strong>R3</strong></td><td>{EUR_R3}</td></tr>
    <tr style="border-top: 1px solid #30363d;"><th colspan="4">USD/JPY</th></tr>
    <tr><td><strong>S3</strong></td><td>{JPY_S3}</td><td><strong>S2</strong></td><td>{JPY_S2}</td></tr>
    <tr><td><strong>S1</strong></td><td>{JPY_S1}</td><td><strong>R1</strong></td><td>{JPY_R1}</td></tr>
    <tr><td><strong>R2</strong></td><td>{JPY_R2}</td><td><strong>R3</strong></td><td>{JPY_R3}</td></tr>
  </table>
</div>

<!-- ROW 3: POSITIONING — EUR left | JPY right -->
<div class="grid-2">
  <div class="card">
    <div class="card-title">EUR/USD Positioning <span style="color:#484f58;font-weight:400;">(COT Disaggregated)</span></div>
    <table>
      <tr><th>Category</th><th>Net Contracts</th><th>Percentile</th><th>Regime</th></tr>
      <tr><td>Lev Money</td><td class="{color_class(EUR_net)}">{EUR_net_disp}</td><td>{ordinal_or_dash(EUR_lev_pct)}</td><td><span class="badge {eur_pos_class}">{eur_pos_regime}</span></td></tr>
      <tr><td>Asset Manager</td><td class="{color_class(EUR_am_net)}">{EUR_am_net_disp}</td><td>{ordinal_or_dash(EUR_am_pct)}</td><td><span class="badge {eur_pos_class}">{eur_pos_regime}</span></td></tr>
    </table>
  </div>
  <div class="card">
    <div class="card-title">USD/JPY Positioning <span style="color:#484f58;font-weight:400;">(COT Disaggregated)</span></div>
    <table>
      <tr><th>Category</th><th>Net Contracts</th><th>Percentile</th><th>Regime</th></tr>
      <tr><td>Lev Money</td><td class="{color_class(JPY_net)}">{JPY_net_disp}</td><td>{ordinal_or_dash(JPY_lev_pct)}</td><td><span class="badge {jpy_pos_class}">{jpy_pos_regime}</span></td></tr>
      <tr><td>Asset Manager</td><td class="{color_class(JPY_am_net)}">{JPY_am_net_disp}</td><td>{ordinal_or_dash(JPY_am_pct)}</td><td><span class="badge {jpy_pos_class}">{jpy_pos_regime}</span></td></tr>
    </table>
  </div>
</div>

<!-- ROW 3.5: USD/INR POSITIONING -->
<div class="card" style="margin-bottom:12px;">
  <div class="card-title">USD/INR Positioning <span style="color:#484f58;font-weight:400;">(SEBI FPI Proxy)</span></div>
  <table>
    <tr><th>Category</th><th>Net Flow (20D)</th><th>Percentile</th><th>Regime</th></tr>
    <tr><td>FPI Debt Flow (20D)</td><td class="neutral-text">{FPI_20D_flow_disp}</td><td>{FPI_20D_pct_disp}</td><td><span class="badge {inr_fpi_class}">{inr_fpi_text}</span></td></tr>
  </table>
  <div style="font-size:10px;color:#484f58;margin-top:6px;">* FPI flow proxy — not equivalent to CFTC COT. JS-rendered source pending Playwright integration.</div>
</div>

<!-- ROW 4: REGIME READ full width -->
<div class="card" style="margin-bottom:12px;">
  <div class="card-title">Regime Read</div>
  <div class="regime-block">
    <div class="regime-pair">
      EUR/USD
      <span class="badge {eur_pos_class}">{eur_pos_regime}</span>
    </div>
    <div class="regime-text">
      {eur_read}
    </div>
  </div>
  <div class="regime-block">
    <div class="regime-pair">
      USD/JPY
      <span class="badge {jpy_pos_class}">{jpy_pos_regime}</span>
    </div>
    <div class="regime-text">
      {jpy_read}
    </div>
  </div>
  <div class="regime-block">
    <div class="regime-pair">
      USD/INR
      <span class="badge {inr_fpi_class}">{inr_fpi_text}</span>
    </div>
    <div class="regime-text">
      {inr_read}
    </div>
  </div>
</div>

<!-- ROW 5: EUR/USD CHARTS -->
<div class="charts-section">
  <div class="pair-label">EUR/USD — Charts</div>
  <div class="grid-3">
    <div class="chart-card">
      <img class="chart-img" src="{charts['eurusd_fund']}" onclick="openLightbox(this)">
      <div class="chart-label">Fundamentals</div>
    </div>
    <div class="chart-card">
      <img class="chart-img" src="{charts['eurusd_pos']}" onclick="openLightbox(this)">
      <div class="chart-label">Positioning</div>
    </div>
    <div class="chart-card">
      <img class="chart-img" src="{charts['eurusd_vol']}" onclick="openLightbox(this)">
      <div class="chart-label">Volatility</div>
    </div>
  </div>
</div>

<!-- ROW 6: USD/JPY CHARTS -->
<div class="charts-section">
  <div class="pair-label">USD/JPY — Charts</div>
  <div class="grid-3">
    <div class="chart-card">
      <img class="chart-img" src="{charts['usdjpy_fund']}" onclick="openLightbox(this)">
      <div class="chart-label">Fundamentals</div>
    </div>
    <div class="chart-card">
      <img class="chart-img" src="{charts['usdjpy_pos']}" onclick="openLightbox(this)">
      <div class="chart-label">Positioning</div>
    </div>
    <div class="chart-card">
      <img class="chart-img" src="{charts['usdjpy_vol']}" onclick="openLightbox(this)">
      <div class="chart-label">Volatility</div>
    </div>
  </div>
</div>

<!-- ROW 7: USD/INR CHARTS -->
<div class="charts-section">
  <div class="pair-label">USD/INR — Charts</div>
  <div style="max-width:700px;margin:0 auto;">
    <div class="chart-card">
      {usdinr_fund_html}
      <div class="chart-label">Fundamentals</div>
    </div>
  </div>
</div>

<!-- FOOTER -->
<div class="footer">
  <span>G10 FX Regime Detection Framework — Shreyash Sakhare</span>
  <span>Data: FRED · ECB · Japan MOF · RBI/FRED · CFTC · Yahoo Finance</span>
</div>

<div class="lightbox" id="lightbox" onclick="closeLightbox()">
  <img id="lightbox-img" src="">
</div>

<script>
function openLightbox(img) {{
    document.getElementById('lightbox-img').src = img.src;
    document.getElementById('lightbox').classList.add('active');
}}
function closeLightbox() {{
    document.getElementById('lightbox').classList.remove('active');
}}
document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeLightbox();
}});
</script>
</body>
</html>"""

os.makedirs('briefs', exist_ok=True)
output_path = f'briefs/brief_{DATE_SLUG}.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"  saved: {output_path}")
