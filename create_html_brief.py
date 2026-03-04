import os
import glob
import base64
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

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


# ============================================================================
# STEP 3B — Import and call chart functions
# ============================================================================

from create_charts_plotly import (
    build_fundamentals_chart,
    build_positioning_chart, 
    build_vol_correlation_chart
)
import plotly.io as pio

plotly_config = dict(scrollZoom=True, displayModeBar=False, 
                     responsive=True)

def fig_to_div(fig):
    if fig is None:
        return '<div style="color:#555;padding:20px;font-size:11px;">Chart unavailable</div>'
    return pio.to_html(fig, full_html=False, 
                       config=plotly_config,
                       include_plotlyjs=False)

# Generate all chart divs
eurusd_fund_div = fig_to_div(build_fundamentals_chart('eurusd'))
eurusd_pos_div  = fig_to_div(build_positioning_chart('eurusd'))
eurusd_vol_div  = fig_to_div(build_vol_correlation_chart('eurusd'))

usdjpy_fund_div = fig_to_div(build_fundamentals_chart('usdjpy'))
usdjpy_pos_div  = fig_to_div(build_positioning_chart('usdjpy'))
usdjpy_vol_div  = fig_to_div(build_vol_correlation_chart('usdjpy'))

usdinr_fund_div = fig_to_div(build_fundamentals_chart('usdinr'))

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
US_IN_10Y     = safe('US_IN_10Y_spread')         if 'US_IN_10Y_spread'         in df.columns else '—'
US_IN_10Y_12M = safe('US_IN_10Y_spread_chg_12M') if 'US_IN_10Y_spread_chg_12M' in df.columns else '—'
US_IN_pol     = safe('US_IN_policy_spread')       if 'US_IN_policy_spread'       in df.columns else '—'
US_IN_pol_12M = safe('US_IN_policy_spread_chg_12M') if 'US_IN_policy_spread_chg_12M' in df.columns else '—'
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
    usdinr_fund_div
)

def color_val(val, reverse=False):
    try:
        v = float(val)
        if v > 0.001:
            return '#ff4444' if reverse else '#00d4aa'
        elif v < -0.001:
            return '#00d4aa' if reverse else '#ff4444'
        else:
            return '#888888'
    except:
        return '#888888'


# global bar values
_dxy_color  = color_val(DXY_1D)
_dxy_1d_fmt = fmt_pct(DXY_1D)

_brent_price = '—'
if _brent_raw:
    try:
        _brent_price = f"{float(_brent_raw.split(': ', 1)[1]):.2f}"
    except:
        pass

_gold_price = '—'
if _gold_raw:
    try:
        _gold_price = f"{int(round(float(_gold_raw.split(': ', 1)[1]))):,}"
    except:
        pass


# card header badge class lookup
def _badge_cls(regime):
    return {
        'CROWDED LONG':  'badge-crowded-long',
        'CROWDED SHORT': 'badge-crowded-short',
    }.get(regime, 'badge-neutral-card')

_eur_badge_cls = _badge_cls(eur_pos_regime)
_jpy_badge_cls = _badge_cls(jpy_pos_regime)


# build HTML
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>G10 FX Morning Brief — {TODAY_FMT}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: #0d0d0d;
    color: #cccccc;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
}}
.globalbar {{
    width: 100%;
    background: #1a1a1a;
    padding: 6px 20px;
    font-size: 11px;
    color: #888;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    padding: 16px 20px;
    border-bottom: 1px solid #1e1e1e;
}}
.header-left .label {{
    font-size: 10px;
    color: #444;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 6px;
}}
.header-left .title {{
    font-size: 20px;
    font-weight: 600;
    color: #ffffff;
}}
.header-right {{
    font-size: 11px;
    color: #888;
    text-align: right;
    line-height: 1.7;
}}
.content {{
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}}
.card {{
    background: #141414;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    overflow: hidden;
}}
.card-header {{
    height: 40px;
    display: flex;
    align-items: center;
    padding: 0 16px;
    background: #1a1a1a;
    border-bottom: 1px solid #2a2a2a;
}}
.ch-pair {{
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: 1px;
}}
.ch-price {{
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
    margin-left: 16px;
}}
.ch-1d {{
    font-size: 13px;
    margin-left: 12px;
}}
.ch-12m-label {{
    font-size: 11px;
    color: #888;
    margin-left: 12px;
}}
.ch-12m {{
    font-size: 12px;
    margin-left: 4px;
}}
.ch-badge {{
    margin-left: auto;
    padding: 3px 8px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
}}
.badge-crowded-long  {{ background: #f0a500; color: #000000; }}
.badge-crowded-short {{ background: #e05c5c; color: #ffffff; }}
.badge-neutral-card  {{ background: #333333; color: #888888; }}
.card-body {{
    height: 380px;
    display: flex;
    background: #141414;
}}

.brief-left {{
    width: 38%;
    background: #141414;
    border-right: 1px solid #2a2a2a;
    padding: 14px 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
}}
.brief-right {{
    width: 62%;
    background: #0d0d0d;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}}
.chart-tab-bar {{
    height: 36px;
    background: #1a1a1a;
    border-bottom: 1px solid #2a2a2a;
    display: flex;
    align-items: center;
    padding: 0 4px;
    gap: 2px;
}}
.chart-tab {{
    padding: 0 14px;
    height: 28px;
    background: transparent;
    border: none;
    border-radius: 3px;
    color: #555;
    font-size: 10px;
    font-family: inherit;
    letter-spacing: 0.8px;
    cursor: pointer;
    text-transform: uppercase;
    transition: color 0.15s;
}}
.chart-tab:hover {{
    color: #888;
}}
.chart-tab.active {{
    color: #cccccc;
    background: #252525;
}}
.chart-display-area {{
    flex-grow: 1;
    position: relative;
    overflow: hidden;
}}
.chart-pane {{
    display: none;
    height: 100%;
    overflow: auto;
}}
.chart-pane .js-plotly-plot {{
    width: 100% !important;
    height: 100% !important;
    min-height: 480px;
}}
.brief-section {{
    border-top: 1px solid #1e1e1e;
    padding-top: 10px;
}}
.brief-section:first-child {{
    border-top: none;
    padding-top: 0;
}}
.brief-label {{
    color: #555;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}}
.brief-row {{
    display: flex;
    align-items: center;
    line-height: 1.35;
    margin-top: 4px;
}}
.brief-row .name {{
    width: 140px;
    flex-shrink: 0;
    color: #888;
    font-size: 11px;
    white-space: nowrap;
}}
.brief-row .val {{
    width: 80px;
    flex-shrink: 0;
    text-align: right;
    color: #ffffff;
    font-size: 12px;
    font-weight: 600;
}}
.brief-row .pct {{
    flex: 1;
    text-align: right;
    font-size: 11px;
}}
.badge-mini {{
    display: inline-block;
    padding: 1px 6px;
    border-radius: 999px;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    border: 1px solid #2a2a2a;
}}
.badge-mini.badge-neutral {{ background: #1a1a1a; color: #888; }}
.badge-mini.badge-success {{ background: rgba(0, 212, 170, 0.12); color: #00d4aa; border-color: rgba(0, 212, 170, 0.25); }}
.badge-mini.badge-warning {{ background: rgba(240, 165, 0, 0.12); color: #f0a500; border-color: rgba(240, 165, 0, 0.25); }}
.badge-mini.badge-danger  {{ background: rgba(224, 92, 92, 0.12); color: #e05c5c; border-color: rgba(224, 92, 92, 0.25); }}

.brief-text {{
    color: #aaaaaa;
    font-size: 11px;
    line-height: 1.5;
}}
.brief-muted {{
    color: #555;
    font-size: 11px;
}}
.footer {{
    background: #0d0d0d;
    border-top: 1px solid #1e1e1e;
    padding: 10px 20px;
    font-size: 10px;
    color: #555;
}}
</style>
</head>
<body>

<!-- GLOBAL BAR -->
<div class="globalbar">
  DXY {DXY} <span style="color:{_dxy_color}">{_dxy_1d_fmt}</span>
  &nbsp;|&nbsp; Brent ${_brent_price}
  &nbsp;|&nbsp; Gold ${_gold_price}
  &nbsp;|&nbsp; COT: {cot_date}
  &nbsp;|&nbsp; Next COT: {next_cot_date}
  &nbsp;|&nbsp; All prices: prior session close
</div>

<!-- HEADER -->
<div class="header">
  <div class="header-left">
    <div class="label">G10 FX Regime Detection Framework</div>
    <div class="title">Morning Brief &mdash; {TODAY_FMT}</div>
  </div>
  <div class="header-right">
    data as of: {data_date}<br>
    pipeline run: {pipeline_run}
  </div>
</div>

<!-- MAIN CONTENT -->
<div class="content">

  <div class="card" data-pair="eurusd">
    <div class="card-header">
      <span class="ch-pair">EUR/USD</span>
      <span class="ch-price">{EURUSD}</span>
      <span class="ch-1d" style="color:{color_val(EURUSD_1D)}">{fmt_pct(EURUSD_1D)}</span>
      <span class="ch-12m-label">12M:</span>
      <span class="ch-12m" style="color:{color_val(EURUSD_12M)}">{fmt_pct(EURUSD_12M)}</span>
      <span class="ch-badge {_eur_badge_cls}">{eur_pos_regime}</span>
    </div>
    <div class="card-body">
      <div class="brief-left">

        <div class="brief-section">
          <div class="brief-label">RATE DIFFERENTIALS</div>
          <div class="brief-row">
            <span class="name">US-DE 10Y</span>
            <span class="val">{US_DE_10Y}</span>
            <span class="pct" style="color:{color_val(US_DE_10Y_12M, reverse=True)}">{fmt_pct(US_DE_10Y_12M, suffix='pp')}</span>
          </div>
          <div class="brief-row">
            <span class="name">US-DE 2Y</span>
            <span class="val">{US_DE_2Y}</span>
            <span class="pct" style="color:{color_val(US_DE_2Y_12M, reverse=True)}">{fmt_pct(US_DE_2Y_12M, suffix='pp')}</span>
          </div>
        </div>

        <div class="brief-section">
          <div class="brief-label">POSITIONING (COT)</div>
          <div class="brief-row">
            <span class="name">Lev Money</span>
            <span class="pct" style="color:{color_val(EUR_net)}">{EUR_net_disp}</span>
            <span class="pct">{ordinal_or_dash(EUR_lev_pct)}</span>
            <span class="badge-mini {eur_pos_class}">{eur_pos_regime}</span>
          </div>
          <div class="brief-row">
            <span class="name">Asset Manager</span>
            <span class="pct" style="color:{color_val(EUR_am_net)}">{EUR_am_net_disp}</span>
            <span class="pct">{ordinal_or_dash(EUR_am_pct)}</span>
            <span class="badge-mini {pos_regime(EUR_am_pct)[1]}">{pos_regime(EUR_am_pct)[0]}</span>
          </div>
        </div>

        <div class="brief-section">
          <div class="brief-label">VOLATILITY & CORRELATION</div>
          <div class="brief-row">
            <span class="name">30D Vol</span>
            <span class="val">{EURUSD_vol30}</span>
            <span class="pct">{ordinal_or_dash(EURUSD_vol_pct)}</span>
            <span class="badge-mini {eur_vol_class}">{eur_vol_text}</span>
          </div>
          <div class="brief-row">
            <span class="name">60D Corr</span>
            <span class="pct" style="color:{color_val(EURUSD_corr)}">{EURUSD_corr_fmt}</span>
            <span></span>
            <span class="badge-mini {eur_corr_class}">{eur_corr_text}</span>
          </div>
        </div>

        <div class="brief-section">
          <div class="brief-label">REGIME READ</div>
          <div class="brief-text">{eur_read}</div>
        </div>

      </div>
      <div class="brief-right">
        <div class="chart-tab-bar">
          <button class="chart-tab active" data-pair="eurusd" data-tab="0">FUNDAMENTALS</button>
          <button class="chart-tab" data-pair="eurusd" data-tab="1">POSITIONING</button>
          <button class="chart-tab" data-pair="eurusd" data-tab="2">VOL & CORRELATION</button>
        </div>
        <div class="chart-display-area">
          <div class="chart-pane" data-pair="eurusd" data-pane="0" style="display:block;">
            {eurusd_fund_div}
          </div>
          <div class="chart-pane" data-pair="eurusd" data-pane="1" style="display:none;">
            {eurusd_pos_div}
          </div>
          <div class="chart-pane" data-pair="eurusd" data-pane="2" style="display:none;">
            {eurusd_vol_div}
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="card" data-pair="usdjpy">
    <div class="card-header">
      <span class="ch-pair">USD/JPY</span>
      <span class="ch-price">{USDJPY}</span>
      <span class="ch-1d" style="color:{color_val(USDJPY_1D)}">{fmt_pct(USDJPY_1D)}</span>
      <span class="ch-12m-label">12M:</span>
      <span class="ch-12m" style="color:{color_val(USDJPY_12M)}">{fmt_pct(USDJPY_12M)}</span>
      <span class="ch-badge {_jpy_badge_cls}">{jpy_pos_regime}</span>
    </div>
    <div class="card-body">
      <div class="brief-left">

        <div class="brief-section">
          <div class="brief-label">RATE DIFFERENTIALS</div>
          <div class="brief-row">
            <span class="name">US-JP 10Y</span>
            <span class="val">{US_JP_10Y}</span>
            <span class="pct" style="color:{color_val(US_JP_10Y_12M, reverse=True)}">{fmt_pct(US_JP_10Y_12M, suffix='pp')}</span>
          </div>
          <div class="brief-row">
            <span class="name">US-JP 2Y</span>
            <span class="val">{US_JP_2Y}</span>
            <span class="pct" style="color:{color_val(US_JP_2Y_12M, reverse=True)}">{fmt_pct(US_JP_2Y_12M, suffix='pp')}</span>
          </div>
        </div>

        <div class="brief-section">
          <div class="brief-label">POSITIONING (COT)</div>
          <div class="brief-row">
            <span class="name">Lev Money</span>
            <span class="pct" style="color:{color_val(JPY_net)}">{JPY_net_disp}</span>
            <span class="pct">{ordinal_or_dash(JPY_lev_pct)}</span>
            <span class="badge-mini {jpy_pos_class}">{jpy_pos_regime}</span>
          </div>
          <div class="brief-row">
            <span class="name">Asset Manager</span>
            <span class="pct" style="color:{color_val(JPY_am_net)}">{JPY_am_net_disp}</span>
            <span class="pct">{ordinal_or_dash(JPY_am_pct)}</span>
            <span class="badge-mini {pos_regime(JPY_am_pct)[1]}">{pos_regime(JPY_am_pct)[0]}</span>
          </div>
        </div>

        <div class="brief-section">
          <div class="brief-label">VOLATILITY & CORRELATION</div>
          <div class="brief-row">
            <span class="name">30D Vol</span>
            <span class="val">{USDJPY_vol30}</span>
            <span class="pct">{ordinal_or_dash(USDJPY_vol_pct)}</span>
            <span class="badge-mini {jpy_vol_class}">{jpy_vol_text}</span>
          </div>
          <div class="brief-row">
            <span class="name">60D Corr</span>
            <span class="pct" style="color:{color_val(USDJPY_corr)}">{USDJPY_corr_fmt}</span>
            <span></span>
            <span class="badge-mini {jpy_corr_class}">{jpy_corr_text}</span>
          </div>
        </div>

        <div class="brief-section">
          <div class="brief-label">REGIME READ</div>
          <div class="brief-text">{jpy_read}</div>
        </div>

      </div>
      <div class="brief-right">
        <div class="chart-tab-bar">
          <button class="chart-tab active" data-pair="usdjpy" data-tab="0">FUNDAMENTALS</button>
          <button class="chart-tab" data-pair="usdjpy" data-tab="1">POSITIONING</button>
          <button class="chart-tab" data-pair="usdjpy" data-tab="2">VOL & CORRELATION</button>
        </div>
        <div class="chart-display-area">
          <div class="chart-pane" data-pair="usdjpy" data-pane="0" style="display:block;">
            {usdjpy_fund_div}
          </div>
          <div class="chart-pane" data-pair="usdjpy" data-pane="1" style="display:none;">
            {usdjpy_pos_div}
          </div>
          <div class="chart-pane" data-pair="usdjpy" data-pane="2" style="display:none;">
            {usdjpy_vol_div}
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="card" data-pair="usdinr">
    <div class="card-header">
      <span class="ch-pair">USD/INR</span>
      <span class="ch-price">{USDINR}</span>
      <span class="ch-1d" style="color:{color_val(USDINR_1D)}">{fmt_pct(USDINR_1D)}</span>
      <span class="ch-12m-label">12M:</span>
      <span class="ch-12m" style="color:{color_val(USDINR_12M)}">{fmt_pct(USDINR_12M)}</span>
      <span class="ch-badge badge-neutral-card">RATE DIFF ONLY</span>
    </div>
    <div class="card-body">
      <div class="brief-left">

        <div class="brief-section">
          <div class="brief-label">RATE DIFFERENTIALS</div>
          <div class="brief-row">
            <span class="name">US-IN 10Y</span>
            <span class="val">{US_IN_10Y_disp}</span>
            <span class="pct" style="color:{color_val(US_IN_10Y_12M, reverse=True)}">{fmt_pct(US_IN_10Y_12M, suffix='pp')}</span>
          </div>
          <div class="brief-row">
            <span class="name">US-IN Policy</span>
            <span class="val">{US_IN_pol_disp}</span>
            <span class="pct" style="color:{color_val(US_IN_pol_12M, reverse=True)}">{fmt_pct(US_IN_pol_12M, suffix='pp')}</span>
          </div>
        </div>

        <div class="brief-section">
          <div class="brief-label">POSITIONING (COT)</div>
          <div class="brief-muted">FPI proxy unavailable</div>
        </div>

        <div class="brief-section">
          <div class="brief-label">VOLATILITY & CORRELATION</div>
          <div class="brief-row">
            <span class="name">30D Vol</span>
            <span class="val">—</span>
            <span class="pct">—</span>
            <span class="badge-mini badge-neutral">—</span>
          </div>
        </div>

        <div class="brief-section">
          <div class="brief-label">REGIME READ</div>
          <div class="brief-text">{inr_read}</div>
        </div>

      </div>
      <div class="brief-right">
        <div class="chart-tab-bar">
          <button class="chart-tab active" data-pair="usdinr" data-tab="0">FUNDAMENTALS</button>
        </div>
        <div class="chart-display-area">
          <div class="chart-pane" data-pair="usdinr" data-pane="0" style="display:block;">
            {usdinr_fund_div}
          </div>
        </div>
      </div>
    </div>
  </div>

</div>

<!-- FOOTER -->
<div class="footer">
  Data: FRED &middot; ECB SDW &middot; Japan MOF &middot; CFTC &middot; Yahoo Finance | G10 FX Regime Detection Framework &mdash; Shreyash Sakhare
</div>

<script>
document.querySelectorAll('.chart-tab').forEach(tab => {{
  tab.addEventListener('click', function() {{
    const pair = this.dataset.pair;
    const tabIdx = this.dataset.tab;
    
    // deactivate all tabs for this pair
    document.querySelectorAll(
      `.chart-tab[data-pair="${{pair}}"]`
    ).forEach(t => t.classList.remove('active'));
    
    // hide all panes for this pair
    document.querySelectorAll(
      `.chart-pane[data-pair="${{pair}}"]`
    ).forEach(p => {{
      p.style.display = 'none';
    }});
    
    // activate clicked tab
    this.classList.add('active');
    
    // show corresponding pane
    document.querySelector(
      `.chart-pane[data-pair="${{pair}}"][data-pane="${{tabIdx}}"]`
    ).style.display = 'block';

    // trigger plotly resize for the newly visible chart
    const plotlyDiv = document.querySelector(
      `.chart-pane[data-pair="${{pair}}"][data-pane="${{tabIdx}}"] .js-plotly-plot`
    );
    if (plotlyDiv) {{
      Plotly.relayout(plotlyDiv, {{autosize: true}});
    }}
  }});
}});
</script>

</body>
</html>"""

os.makedirs('briefs', exist_ok=True)
output_path = f'briefs/brief_{DATE_SLUG}.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"  saved: {output_path}")
