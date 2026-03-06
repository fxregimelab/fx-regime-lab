import os
import glob
import math
import pandas as pd
import numpy as np
import sys
from core.utils import ordinal, embed_image, fmt_pct, color_class
from config import TODAY, TODAY_FMT, DATE_SLUG
from morning_brief import _oil_corr_label, _dxy_corr_label


# ============================================================================
# STEP 3B — Build charts as standalone HTML files and embed via <iframe>
#
# Why iframes? pio.to_html() embeds inline <script> tags that run before the
# browser flex layout is computed → container width=0 → broken charts.
# Each iframe gets its own full document layout so Plotly always renders at
# the correct container size, with no script timing issues.
# ============================================================================

from charts.registry import CHART_REGISTRY
from charts.workspace import build_global_workspace_html
import plotly.io as pio

plotly_config = dict(scrollZoom=True, displayModeBar=False)

CHARTS_DIR = 'charts'
os.makedirs(CHARTS_DIR, exist_ok=True)

# ============================================================================
# Cross-asset value injection helpers (Phase 1 & 2)
# ============================================================================

_OIL_FIELDS = {
    'oil_eurusd_corr_60d': 'EURUSD',
    'oil_usdjpy_corr_60d': 'USDJPY',
    'oil_inr_corr_60d':    'USDINR',
}
_DXY_FIELDS = {
    'dxy_eurusd_corr_60d': 'EURUSD',
    'dxy_usdjpy_corr_60d': 'USDJPY',
    'dxy_inr_corr_60d':    'USDINR',
}

def _badge_class_for(label):
    """Map a corr label string to a badge-mini CSS modifier."""
    if label in ('OIL DIVERGENCE',):
        return 'badge-danger'
    if label in ('HIGH', 'EUR SPECIFIC', 'YEN SPECIFIC', 'INDIA SPECIFIC'):
        return 'badge-success'
    if label in ('MODERATE', 'MIXED', 'DOLLAR REGIME'):
        return 'badge-warning'
    return 'badge-neutral'   # LOW, NO DATA

def _value_color_for(label):
    """Map a corr label string to an inline hex color."""
    if label == 'OIL DIVERGENCE':
        return '#ff4444'
    if label in ('HIGH', 'EUR SPECIFIC', 'YEN SPECIFIC', 'INDIA SPECIFIC'):
        return '#00d4aa'
    if label in ('MODERATE', 'MIXED'):
        return '#888888'
    if label == 'DOLLAR REGIME':
        return '#f0a500'
    return '#555555'   # LOW, NO DATA

def inject_cross_asset_values(html_content, _re):
    """Replace data-field / data-badge spans with live corr values from CSV."""
    try:
        df  = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)
        row = df.iloc[-1]
    except Exception:
        return html_content

    all_fields = list(_OIL_FIELDS.items()) + list(_DXY_FIELDS.items())

    for field_name, pair_key in all_fields:
        raw = row.get(field_name, float('nan'))
        is_oil = field_name in _OIL_FIELDS

        if isinstance(raw, float) and math.isnan(raw):
            formatted = '&mdash;'
            label     = 'NO DATA'
        else:
            formatted = f'{raw:+.3f}'
            if is_oil:
                label, _ = _oil_corr_label(raw, pair_key)
            else:
                label, _ = _dxy_corr_label(raw, pair_key)

        color       = _value_color_for(label)
        badge_cls   = _badge_class_for(label)

        # Replace data-field span (value + color)
        html_content = _re.sub(
            rf'<span[^>]*\bdata-field="{_re.escape(field_name)}"[^>]*>[^<]*</span>',
            f'<span class="pct" style="color:{color}" data-field="{field_name}">{formatted}</span>',
            html_content,
        )
        # Replace data-badge span (badge class + label text)
        html_content = _re.sub(
            rf'<span[^>]*\bdata-badge="{_re.escape(field_name)}"[^>]*>[^<]*</span>',
            f'<span class="badge-mini {badge_cls}" data-badge="{field_name}">{label}</span>',
            html_content,
        )

    return html_content


def update_globalbar(html_content, _re):
    """Replace static globalbar prices with live values + color-coded 1D change spans."""
    try:
        df  = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)
        row = df.iloc[-1]
    except Exception:
        return html_content

    def _colored(pct):
        if isinstance(pct, float) and math.isnan(pct):
            return ''
        color = '#00d4aa' if pct >= 0 else '#ff4444'
        sign  = '+' if pct >= 0 else ''
        return f' <span style="color:{color}">{sign}{pct:.2f}%</span>'

    # Assets: (csv_price_col, csv_chg_col, display_prefix, fmt)
    assets = [
        ('DXY',   'DXY_chg_1D',   'DXY ',       lambda v: f'{v:.2f}'),
        ('Brent', 'Brent_chg_1D', 'Brent $',     lambda v: f'{v:.2f}'),
        ('Gold',  'Gold_chg_1D',  'Gold $',       lambda v: f'{v:,.0f}'),
    ]

    parts = []
    for price_col, chg_col, prefix, fmt in assets:
        price = row.get(price_col, float('nan'))
        chg   = row.get(chg_col,   float('nan'))
        if isinstance(price, float) and math.isnan(price):
            continue
        parts.append(f'{prefix}{fmt(price)}{_colored(chg)}')

    if not parts:
        return html_content

    # Build replacement for the DXY ... Gold section inside the globalbar
    new_segment = '\n  '.join(
        (parts[0] if i == 0 else f'&nbsp;|&nbsp; {parts[i]}')
        for i, _ in enumerate(parts)
    )

    # Replace only the price+change portion (between start of globalbar and COT info)
    html_content = _re.sub(
        r'(class="globalbar">)[\s\S]*?(&nbsp;\|&nbsp; COT:)',
        lambda m: m.group(1) + '\n  ' + new_segment + '\n  ' + m.group(2),
        html_content,
    )
    return html_content


# ============================================================================
# LANDING PAGE (Page 0) — full-screen overview with live signal grid
# ============================================================================

def inject_landing_page(html_content, _re):
    """Build and inject a full-screen landing page (Page 0) before the pair cards."""
    if 'id="landing-page"' in html_content:
        return html_content  # idempotent

    try:
        df  = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)
        row = df.iloc[-1]
    except Exception:
        return html_content

    # ---- helpers ----
    def _c(v):
        if isinstance(v, float) and math.isnan(v):
            return '#555'
        return '#00d4aa' if v >= 0 else '#ff4444'

    def _s(v, fmt='+.2f'):
        if isinstance(v, float) and math.isnan(v):
            return '—'
        return f'{v:{fmt}}'

    def _nan(v):
        return isinstance(v, float) and math.isnan(v)

    def _badge(label, bg, fg):
        return f'<span class="lp-badge" style="background:{bg};color:{fg}">{label}</span>'

    _BADGE_MAP = {
        'BROKEN':         ('#2a0000', '#ff4444'), 'INTACT':          ('#002a1a', '#00d4aa'),
        'WEAKENING':      ('#2a1500', '#f0a500'), 'REBUILDING':      ('#002a1a', '#00d4aa'),
        'CROWDED LONG':   ('#2a1a00', '#f0a500'), 'CROWDED SHORT':   ('#2a0000', '#e05c5c'),
        'NEUTRAL':        ('#1a1a1a', '#666666'), 'NORMAL':          ('#1a1a1a', '#888888'),
        'LONG':           ('#1a2a00', '#8bc34a'),  'SHORT':           ('#1a0000', '#e05c5c'),
        'ELEVATED':       ('#2a1a00', '#f0a500'), 'EXTREME':         ('#2a0000', '#ff4444'),
        'HIGH':           ('#002a1a', '#00d4aa'), 'MODERATE':        ('#1a1a1a', '#888888'),
        'LOW':            ('#1a1a1a', '#555555'), 'OIL DIVERGENCE':  ('#2a0000', '#ff4444'),
        'DOLLAR REGIME':  ('#1a1a2a', '#4da6ff'), 'MIXED':           ('#1a1a1a', '#888888'),
        'EUR SPECIFIC':   ('#1a2a1a', '#00d4aa'), 'YEN SPECIFIC':    ('#1a2a1a', '#00d4aa'),
        'INDIA SPECIFIC': ('#1a2a1a', '#00d4aa'),
    }

    def _cbadge(label):
        bg, fg = _BADGE_MAP.get(label, ('#1a1a1a', '#666'))
        return _badge(label, bg, fg)

    def _vol_lbl(pct):
        if _nan(pct): return 'NORMAL'
        if pct >= 90: return 'EXTREME'
        if pct >= 75: return 'ELEVATED'
        return 'NORMAL'

    def _regime_lbl(corr):
        if _nan(corr): return 'NO DATA'
        v = abs(corr)
        if v >= 0.5: return 'INTACT'
        if v >= 0.25: return 'WEAKENING'
        return 'BROKEN'

    def _cot_lbl(pct):
        if _nan(pct): return 'NEUTRAL'
        if pct >= 90: return 'CROWDED LONG'
        if pct >= 75: return 'LONG'
        if pct <= 10: return 'CROWDED SHORT'
        if pct <= 25: return 'SHORT'
        return 'NEUTRAL'

    # ---- header metadata from existing HTML ----
    m_title = _re.search(r'<div class="title">([^<]+)</div>', html_content)
    m_ts    = _re.search(r'data as of:\s*([^\n<]+)', html_content)
    m_run   = _re.search(r'pipeline run:\s*([^\n<]+)', html_content)
    brief_title = (m_title.group(1) if m_title else f'Morning Brief &mdash; {TODAY_FMT}')
    data_as_of  = m_ts.group(1).strip().rstrip('<br>').strip()  if m_ts  else ''
    run_ts      = m_run.group(1).strip() if m_run else ''

    # ---- market assets row ----
    def _asset_block(name, price_col, fmt_price, chg_col):
        price = row.get(price_col, float('nan'))
        chg   = row.get(chg_col,   float('nan'))
        if _nan(price): return ''
        chg_s = (f'<span style="color:{_c(chg)};font-size:11px">{_s(chg)}%</span>'
                 if not _nan(chg) else '')
        return (f'<div class="lp-asset">'
                f'<span class="lp-asset-name">{name}</span>'
                f'<span class="lp-asset-price">{price:{fmt_price}}</span>'
                f'{chg_s}</div>')

    market_row = (
        _asset_block('DXY',   'DXY',   '.2f', 'DXY_chg_1D')   +
        _asset_block('Brent', 'Brent', '.2f', 'Brent_chg_1D') +
        _asset_block('Gold',  'Gold',  ',.0f', 'Gold_chg_1D')
    )

    # ---- pair mini-cards ----
    def _sig_row(label, val_html, badge_html=''):
        return (f'<div class="lp-sig-row">'
                f'<span class="lp-sig-name">{label}</span>'
                f'<span style="display:flex;align-items:center;gap:4px">'
                f'{val_html}{badge_html}</span></div>')

    def _pair_card(display, pair_key, price_col, chg_1d, chg_12m,
                   spr_name, spr_col, spr_chg_col,
                   cot_col, vol_col, vol_pct_col, corr_col,
                   oil_col, dxy_col, pair_color):
        price  = row.get(price_col, float('nan'))
        p1d    = row.get(chg_1d,    float('nan'))
        p12m   = row.get(chg_12m,   float('nan'))
        spr    = row.get(spr_col,        float('nan')) if spr_col else float('nan')
        spr_ch = row.get(spr_chg_col,    float('nan')) if spr_chg_col else float('nan')
        cot    = row.get(cot_col,        float('nan')) if cot_col else float('nan')
        vol    = row.get(vol_col,        float('nan')) if vol_col else float('nan')
        volp   = row.get(vol_pct_col,    float('nan')) if vol_pct_col else float('nan')
        corr   = row.get(corr_col,       float('nan')) if corr_col else float('nan')
        oil    = row.get(oil_col,        float('nan')) if oil_col else float('nan')
        dxy_c  = row.get(dxy_col,        float('nan')) if dxy_col else float('nan')

        # price display
        if not _nan(price):
            if price < 10:    price_s = f'{price:.4f}'
            elif price < 100: price_s = f'{price:.3f}'
            else:             price_s = f'{price:.2f}'
        else:
            price_s = '—'

        p1d_s  = f'<span style="color:{_c(p1d)}">{_s(p1d)}%</span>'
        p12m_s = f'<span style="color:{_c(p12m)}">12M {_s(p12m)}%</span>'

        rows_html = ''
        # rate spread
        if not _nan(spr):
            sv = f'{spr:.3f}%' if abs(spr) < 10 else f'{spr:.2f}%'
            sc = ('—' if _nan(spr_ch) else
                  f'<span style="color:{_c(-spr_ch)};font-size:9px">{_s(spr_ch,"+.2f")}pp</span>')
            rows_html += _sig_row(spr_name, f'<span style="color:#888">{sv}</span>', sc)
        # COT
        if not _nan(cot):
            rows_html += _sig_row('COT Lev',
                f'<span style="color:#888">{cot:.0f}th</span>', _cbadge(_cot_lbl(cot)))
        # vol
        if not _nan(vol):
            rows_html += _sig_row('30D Vol',
                f'<span style="color:#888">{vol:.1f}%</span>', _cbadge(_vol_lbl(volp)))
        # 60D regime corr
        if not _nan(corr):
            rows_html += _sig_row('60D Corr',
                f'<span style="color:#888">{corr:+.3f}</span>', _cbadge(_regime_lbl(corr)))
        # oil corr
        if not _nan(oil):
            oil_lbl, _ = _oil_corr_label(oil, pair_key)
            rows_html += _sig_row('Oil corr',
                f'<span style="color:#888">{oil:+.3f}</span>', _cbadge(oil_lbl))
        # dxy corr
        if not _nan(dxy_c):
            dxy_lbl, _ = _dxy_corr_label(dxy_c, pair_key)
            rows_html += _sig_row('DXY corr',
                f'<span style="color:#888">{dxy_c:+.3f}</span>', _cbadge(dxy_lbl))

        return (f'<div class="lp-pair-card">'
                f'<div class="lp-pair-name" style="color:{pair_color}">{display}</div>'
                f'<div class="lp-pair-price">{price_s}</div>'
                f'<div class="lp-pair-changes">{p1d_s}'
                f'<span style="color:#2a2a2a">|</span>{p12m_s}</div>'
                f'{rows_html}</div>')

    eur_card = _pair_card(
        'EUR/USD', 'EURUSD', 'EURUSD', 'EURUSD_chg_1D', 'EURUSD_chg_12M',
        'US-DE 10Y', 'US_DE_10Y_spread', 'US_DE_10Y_spread_chg_12M',
        'EUR_lev_percentile', 'EURUSD_vol30', 'EURUSD_vol_pct',
        'EURUSD_spread_corr_60d', 'oil_eurusd_corr_60d', 'dxy_eurusd_corr_60d',
        pair_color='#4da6ff')

    jpy_card = _pair_card(
        'USD/JPY', 'USDJPY', 'USDJPY', 'USDJPY_chg_1D', 'USDJPY_chg_12M',
        'US-JP 10Y', 'US_JP_10Y_spread', 'US_JP_10Y_spread_chg_12M',
        'JPY_lev_percentile', 'USDJPY_vol30', 'USDJPY_vol_pct',
        'USDJPY_spread_corr_60d', 'oil_usdjpy_corr_60d', 'dxy_usdjpy_corr_60d',
        pair_color='#f0a500')

    inr_card = _pair_card(
        'USD/INR', 'USDINR', 'USDINR', 'USDINR_chg_1D', 'USDINR_chg_12M',
        'US-IN 10Y', 'US_IN_10Y_spread', 'US_IN_10Y_spread_chg_12M',
        None, None, None, None,
        'oil_inr_corr_60d', 'dxy_inr_corr_60d',
        pair_color='#e74c3c')

    # ---- landing page CSS (injected into <head>) ----
    lp_css = '''<style id="lp-styles">
/* ---- Landing page (Page 0) ---- */
.snap-page { height: 100vh; scroll-snap-align: start; display: flex; flex-direction: column; overflow: hidden; }
#landing-page { padding: 22px 28px 16px; background: #0a0a0a; }
.lp-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #1e1e1e; }
.lp-fw-label { font-size: 8px; color: #444; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 3px; }
.lp-brief-title { font-size: 15px; color: #fff; font-weight: 600; }
.lp-ts { font-size: 9px; color: #444; text-align: right; line-height: 1.7; }
.lp-markets { display: flex; gap: 22px; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #1e1e1e; flex-shrink: 0; align-items: baseline; }
.lp-asset { display: flex; align-items: baseline; gap: 6px; }
.lp-asset-name { font-size: 8px; color: #555; letter-spacing: 0.1em; text-transform: uppercase; }
.lp-asset-price { font-size: 13px; color: #fff; font-weight: 600; }
.lp-pairs { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; flex: 1; min-height: 0; overflow: hidden; }
.lp-pair-card { background: #111; border: 1px solid #1e1e1e; border-radius: 4px; padding: 12px 14px; display: flex; flex-direction: column; gap: 4px; overflow: hidden; }
.lp-pair-name { font-size: 8px; letter-spacing: 0.14em; text-transform: uppercase; font-weight: 700; margin-bottom: 2px; }
.lp-pair-price { font-size: 24px; color: #fff; font-weight: 700; line-height: 1.1; }
.lp-pair-changes { display: flex; gap: 8px; font-size: 11px; margin-bottom: 3px; }
.lp-sig-row { display: flex; justify-content: space-between; align-items: center; font-size: 10px; border-top: 1px solid #161616; padding-top: 3px; }
.lp-sig-name { color: #555; }
.lp-badge { padding: 1px 5px; border-radius: 2px; font-size: 8px; letter-spacing: 0.06em; text-transform: uppercase; font-weight: 600; }
.lp-nav { display: flex; justify-content: center; gap: 10px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #1e1e1e; flex-shrink: 0; }
.lp-nav-btn { padding: 5px 16px; border: 1px solid #2a2a2a; background: #141414; color: #555; font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase; text-decoration: none; border-radius: 3px; transition: color 0.15s, border-color 0.15s; }
.lp-nav-btn:hover { color: #ccc; border-color: #555; }
/* Hide legacy header + globalbar when landing page is present */
.has-landing .globalbar, .has-landing .header { display: none !important; }
/* Fixed bottom pair navigation */
#pair-nav { position: fixed; bottom: 0; left: 0; right: 0; height: 26px; background: rgba(10,10,10,0.95); backdrop-filter: blur(8px); border-top: 1px solid #1e1e1e; display: flex; justify-content: center; align-items: center; gap: 14px; z-index: 9999; }
.pnav-btn { font-size: 9px; letter-spacing: 0.12em; color: #333; text-transform: uppercase; text-decoration: none; padding: 0 8px; transition: color 0.15s; }
.pnav-btn.active { color: #fff; }
.pnav-btn:hover { color: #888; }
html { scroll-padding-bottom: 26px; }
/* Chart fill — panes fill the entire chart-display-area */
/* chart-fill-v2 */
.chart-display-area { flex: 1; min-height: 0; position: relative; overflow: hidden; }
.chart-display-area .chart-pane { position: absolute; top: 0; right: 0; bottom: 0; left: 0; width: 100%; height: 100%; }
.chart-display-area .chart-pane iframe { width: 100%; height: 100%; border: none; display: block; }
</style>'''

    if '<style id="lp-styles">' not in html_content:
        html_content = html_content.replace('</head>', lp_css + '\n</head>', 1)

    # ---- landing page HTML ----
    landing_html = (
        '<!-- LANDING PAGE -->\n'
        '<div id="landing-page" class="snap-page">\n'
        '  <div class="lp-header">\n'
        '    <div>\n'
        f'      <div class="lp-fw-label">G10 FX Regime Detection Framework</div>\n'
        f'      <div class="lp-brief-title">{brief_title}</div>\n'
        '    </div>\n'
        '    <div class="lp-ts">\n'
        + (f'      data as of: {data_as_of}<br>\n' if data_as_of else '')
        + (f'      pipeline run: {run_ts}\n' if run_ts else '')
        + '    </div>\n'
        '  </div>\n'
        f'  <div class="lp-markets">{market_row}</div>\n'
        f'  <div class="lp-pairs">{eur_card}{jpy_card}{inr_card}</div>\n'
        '  <div class="lp-nav">\n'
        '    <a href="#card-eurusd" class="lp-nav-btn">EUR/USD &#9654;</a>\n'
        '    <a href="#card-usdjpy" class="lp-nav-btn">USD/JPY &#9654;</a>\n'
        '    <a href="#card-usdinr" class="lp-nav-btn">USD/INR &#9654;</a>\n'
        '    <a href="#workspace-snap" class="lp-nav-btn">WORKSPACE &#9654;</a>\n'
        '  </div>\n'
        '</div>\n'
    )

    # Insert before <!-- MAIN CONTENT --> or <div class="content">
    for anchor in ['<!-- MAIN CONTENT -->', '<div class="content">']:
        if anchor in html_content:
            html_content = html_content.replace(anchor, landing_html + anchor, 1)
            break

    # Add has-landing class to <body>
    if 'class="has-landing"' not in html_content:
        html_content = html_content.replace('<body>', '<body class="has-landing">', 1)

    return html_content


def fig_to_iframe(fig, pair, pane, height=480):
    """Save figure as a standalone HTML file and return an <iframe> tag."""
    if fig is None:
        return (
            f'<div style="color:#555;padding:20px;font-size:11px;'
            f'height:{height}px;">Chart unavailable</div>'
        )
    chart_file = f'{CHARTS_DIR}/{pair}_{pane}.html'
    pio.write_html(
        fig,
        file=chart_file,
        config=plotly_config,
        full_html=True,
        include_plotlyjs='cdn',
        auto_open=False,
    )
    # brief lives in briefs/ so path to charts/ is ../charts/
    return (
        f'<iframe src="../{chart_file}" '
        f'style="width:100%;height:100%;border:none;display:block;" '
        f'loading="eager" scrolling="no"></iframe>'
    )

def _builder_to_iframe(builder, pair_str, pane_idx, height):
    """Call a chart builder; handle both go.Figure and raw-HTML-str returns."""
    result = builder(pair_str)
    if isinstance(result, str):
        chart_file = f'{CHARTS_DIR}/{pair_str}_{pane_idx}.html'
        with open(chart_file, 'w', encoding='utf-8') as _fh:
            _fh.write(result)
        return (
            f'<iframe src="../{chart_file}" '
            f'style="width:100%;height:100%;border:none;display:block;" '
            f'loading="eager" scrolling="no"></iframe>'
        )
    return fig_to_iframe(result, pair_str, pane_idx, height)


# Build all chart iframes from the registry at import time.
CHART_DIVS = {
    (pair, pane): _builder_to_iframe(builder, pair, pane, height)
    for (pair, pane), (builder, pair, height) in CHART_REGISTRY.items()
}

# Generate the global Analysis Workspace (all pairs)
_gw_html = build_global_workspace_html()
with open(f'{CHARTS_DIR}/global_workspace.html', 'w', encoding='utf-8') as _fh:
    _fh.write(_gw_html)
print('Generated: charts/global_workspace.html')

# ============================================================================
# Load brief data from existing generated brief
# ============================================================================
import shutil

def load_latest_brief_data():
    """Load the most recent HTML brief as the base template."""
    brief_files = sorted(glob.glob('briefs/brief_*.html'))
    if not brief_files:
        return None
    return brief_files[-1]

def generate_html_brief():
    """Generate complete HTML brief with charts embedded as iframes."""
    brief_file = load_latest_brief_data()
    if not brief_file:
        print("No previous brief found. Run morning_brief.py first.")
        return

    with open(brief_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    import re as _re

    # ------------------------------------------------------------------
    # 1. Inject chart iframes into chart-pane divs
    # ------------------------------------------------------------------
    chart_map = {
        (pair, str(pane)): iframe
        for (pair, pane), iframe in CHART_DIVS.items()
    }
    for (pair, pane_str), new_content in chart_map.items():
        pattern = (
            rf'(<div class="chart-pane"[^>]*data-pair="{pair}"[^>]*'
            rf'data-pane="{pane_str}"[^>]*>)'
            rf'(\n[^\n]*)'
        )
        html_content = _re.sub(
            pattern,
            lambda m, c=new_content: m.group(1) + '\n' + c,
            html_content,
        )

    # ------------------------------------------------------------------
    # 1b. Inject live cross-asset correlation values (Phase 1 & 2)
    # ------------------------------------------------------------------
    html_content = inject_cross_asset_values(html_content, _re)

    # ------------------------------------------------------------------
    # 1c. Update globalbar with live prices + colored 1D changes
    # ------------------------------------------------------------------
    html_content = update_globalbar(html_content, _re)

    # ------------------------------------------------------------------
    # 1d. Inject landing page (Page 0) with live market overview
    # ------------------------------------------------------------------
    html_content = inject_landing_page(html_content, _re)

    # ------------------------------------------------------------------
    # 1e. Add id attributes to pair cards + workspace for anchor nav
    # ------------------------------------------------------------------
    for _pair_id, _pair_val in [('card-eurusd','eurusd'),('card-usdjpy','usdjpy'),('card-usdinr','usdinr')]:
        if f'id="{_pair_id}"' not in html_content:
            html_content = html_content.replace(
                f'<div class="card" data-pair="{_pair_val}">',
                f'<div class="card" id="{_pair_id}" data-pair="{_pair_val}">',
                1,
            )
    if 'id="workspace-snap"' not in html_content:
        html_content = html_content.replace(
            '<div class="workspace-snap">',
            '<div class="workspace-snap" id="workspace-snap">',
            1,
        )

    # ------------------------------------------------------------------
    # 2. CSS patches (idempotent — cascade through version history)
    # ------------------------------------------------------------------

    # brief-left/right: use flex shorthand + min-width:0 to prevent bleed
    html_content = html_content.replace(
        '.brief-left {\n    width: 38%;\n',
        '.brief-left {\n    flex: 0 0 38%;\n    min-width: 0;\n    box-sizing: border-box;\n',
    )
    html_content = html_content.replace(
        '.brief-right {\n    width: 62%;\n',
        '.brief-right {\n    flex: 1 1 0;\n    min-width: 0;\n',
    )
    # brief-right overflow: visible so iframes size naturally
    html_content = html_content.replace(
        '.brief-right {\n    flex: 1 1 0;\n    min-width: 0;\n    background: #0d0d0d;\n    display: flex;\n    flex-direction: column;\n    overflow-y: auto;\n}',
        '.brief-right {\n    flex: 1 1 0;\n    min-width: 0;\n    background: #0d0d0d;\n    display: flex;\n    flex-direction: column;\n    overflow: visible;\n}',
    )

    # card-body: add align-items:stretch so left/right panels fill full height
    html_content = html_content.replace(
        '.card-body {\n    height: auto;\n    display: flex;\n    background: #141414;\n}',
        '.card-body {\n    height: auto;\n    display: flex;\n    align-items: stretch;\n    background: #141414;\n}',
    )

    # card-body: remove all fixed/min heights — height: auto, content drives it
    for _cb_old in [
        '.card-body {\n    height: 380px;\n',
        '.card-body {\n    min-height: 380px;\n',
        '.card-body {\n    min-height: 520px;\n',
        '.card-body {\n    min-height: 560px;\n    height: auto;\n',
        '.card-body {\n    min-height: 520px;\n    height: auto;\n',
    ]:
        html_content = html_content.replace(_cb_old, '.card-body {\n    height: auto;\n')

    # chart-display-area: strip any explicit height — JS syncs it to active iframe
    for _cda_old in [
        '.chart-display-area {\n    flex-grow: 1;\n    position: relative;\n    overflow: hidden;\n}',
        '.chart-display-area {\n    flex-grow: 1;\n    min-height: 420px;\n    position: relative;\n    overflow: hidden;\n}',
        '.chart-display-area {\n    flex-grow: 1;\n    min-height: 480px;\n    position: relative;\n    overflow: hidden;\n}',
        '.chart-display-area {\n    flex-grow: 1;\n\n    position: relative;\n    overflow: hidden;\n}',
    ]:
        html_content = html_content.replace(
            _cda_old,
            '.chart-display-area {\n    flex-grow: 1;\n    position: relative;\n    overflow: hidden;\n}'
        )

    # brief-row: tighten name column, add tabular number alignment
    html_content = html_content.replace(
        '.brief-label {\n    color: #555;\n    font-size: 9px;\n    text-transform: uppercase;\n    letter-spacing: 1px;\n    margin-bottom: 8px;\n}',
        '.brief-label {\n    color: #555;\n    font-size: 9px;\n    text-transform: uppercase;\n    letter-spacing: 1px;\n    margin-bottom: 6px;\n}',
    )
    html_content = html_content.replace(
        '.brief-row {\n    display: flex;\n    align-items: center;\n    line-height: 1.35;\n    margin-top: 4px;\n}',
        '.brief-row {\n    display: flex;\n    align-items: center;\n    line-height: 1.35;\n    margin-top: 3px;\n}',
    )
    html_content = html_content.replace(
        '.brief-row .name {\n    width: 140px;\n',
        '.brief-row .name {\n    width: 118px;\n',
    )
    html_content = html_content.replace(
        '.brief-row .val {\n    width: 80px;\n    flex-shrink: 0;\n    text-align: right;\n    color: #ffffff;\n    font-size: 12px;\n    font-weight: 600;\n}',
        '.brief-row .val {\n    width: 58px;\n    flex-shrink: 0;\n    text-align: right;\n    color: #ffffff;\n    font-size: 12px;\n    font-weight: 600;\n    font-variant-numeric: tabular-nums;\n}',
    )
    html_content = html_content.replace(
        '.brief-row .pct {\n    flex: 1;\n    text-align: right;\n    font-size: 11px;\n}',
        '.brief-row .pct {\n    flex: 1;\n    text-align: right;\n    font-size: 11px;\n    font-variant-numeric: tabular-nums;\n}',
    )

    # compactness — density pass (terminal-style reading, not website cards)
    html_content = html_content.replace(
        '.content {\n    padding: 20px;\n',
        '.content {\n    padding: 14px 20px;\n',
    )
    html_content = html_content.replace(
        '    gap: 16px;\n}\n.card {',
        '    gap: 12px;\n}\n.card {',
    )
    html_content = html_content.replace(
        '.card-header {\n    height: 40px;\n',
        '.card-header {\n    height: 34px;\n',
    )
    html_content = html_content.replace(
        '.ch-price {\n    font-size: 18px;\n',
        '.ch-price {\n    font-size: 15px;\n',
    )
    # brief-left padding + gap
    for _old, _new in [
        ('    padding: 14px 16px;\n', '    padding: 10px 12px;\n'),
        ('    gap: 12px;\n}\n.brief-right', '    gap: 8px;\n}\n.brief-right'),
    ]:
        html_content = html_content.replace(_old, _new, 1)
    html_content = html_content.replace(
        '.brief-section {\n    border-top: 1px solid #1e1e1e;\n    padding-top: 10px;\n}',
        '.brief-section {\n    border-top: 1px solid #1e1e1e;\n    padding-top: 6px;\n}',
    )
    html_content = html_content.replace(
        '    margin-bottom: 6px;\n}\n.brief-row {',
        '    margin-bottom: 4px;\n}\n.brief-row {',
    )
    html_content = html_content.replace(
        '.brief-row {\n    display: flex;\n    align-items: center;\n    line-height: 1.35;\n    margin-top: 3px;\n}',
        '.brief-row {\n    display: flex;\n    align-items: center;\n    line-height: 1.25;\n    margin-top: 2px;\n}',
    )
    html_content = html_content.replace(
        '.chart-tab-bar {\n    height: 36px;\n',
        '.chart-tab-bar {\n    height: 30px;\n',
    )
    html_content = html_content.replace(
        '.chart-tab {\n    padding: 0 14px;\n    height: 28px;\n',
        '.chart-tab {\n    padding: 0 12px;\n    height: 24px;\n',
    )

    # idempotent: strip spurious extra </div> between brief-left and brief-right
    html_content = html_content.replace(
        '      </div>\n\n      </div>\n      <div class="brief-right">',
        '      </div>\n\n      <div class="brief-right">',
    )
    # idempotent: insert missing </div> (brief-left close) if regime-read goes straight into brief-right
    html_content = html_content.replace(
        '        </div>\n\n      <div class="brief-right">',
        '        </div>\n      </div>\n\n      <div class="brief-right">',
    )

    # header compression + font hierarchy
    html_content = html_content.replace(
        '.header {\n    display: flex;\n    justify-content: space-between;\n    align-items: flex-end;\n    padding: 16px 20px;\n',
        '.header {\n    display: flex;\n    justify-content: space-between;\n    align-items: flex-end;\n    padding: 8px 20px;\n',
    )
    html_content = html_content.replace(
        '.header-left .title {\n    font-size: 20px;\n',
        '.header-left .title {\n    font-size: 14px;\n',
    )
    html_content = html_content.replace(
        '.ch-pair {\n    font-size: 13px;\n    font-weight: 600;\n    color: #ffffff;\n    letter-spacing: 1px;\n}',
        '.ch-pair {\n    font-size: 11px;\n    font-weight: 600;\n    color: #888;\n    letter-spacing: 1.5px;\n}',
    )
    html_content = html_content.replace(
        '.brief-section {\n    border-top: 1px solid #1e1e1e;\n',
        '.brief-section {\n    border-top: 1px solid #252525;\n',
    )

    # scroll-snap: each card occupies one full viewport (idempotent)
    if 'scroll-snap-type' not in html_content:
        _snap_css = (
            '/* ---- full-screen scroll-snap ---- */\n'
            'html { scroll-snap-type: y mandatory; overflow-y: scroll; }\n'
            '.content { padding: 0; gap: 0; }\n'
            '.card { height: 100vh; scroll-snap-align: start; border-radius: 0;\n'
            '        border-left: none; border-right: none;\n'
            '        display: flex; flex-direction: column; }\n'
            '.card-body { flex: 1; min-height: 0; }\n'
            '.workspace-snap { height: 100vh; scroll-snap-align: start;\n'
            '  display: flex; flex-direction: column; background: #0d0d0d; }\n'
            '.ws-header { height: 36px; display: flex; align-items: center;\n'
            '  padding: 0 20px; background: #1a1a1a; border-top: 1px solid #2a2a2a;\n'
            '  font-size: 10px; font-weight: 700; letter-spacing: 2px; color: #555;\n'
            '  text-transform: uppercase; flex-shrink: 0; }\n'
            '.ws-iframe-wrap { flex: 1; min-height: 0; overflow: hidden; }\n'
            '.ws-iframe-wrap iframe { width: 100%; height: 100%; border: none; display: block; }'
        )
        html_content = html_content.replace(
            '.footer {\n    background: #0d0d0d;\n',
            _snap_css + '\n.footer {\n    background: #0d0d0d;\n',
        )

    # workspace section: upgrade old static div to snap-page (idempotent)
    if 'class="workspace-snap"' not in html_content:
        html_content = _re.sub(
            r'<!-- GLOBAL ANALYSIS WORKSPACE -->[\s\S]*?</div>\s*</div>',
            (
                '<!-- GLOBAL ANALYSIS WORKSPACE -->\n'
                '<div class="workspace-snap">\n'
                '  <div class="ws-header">ANALYSIS WORKSPACE &mdash; ALL PAIRS</div>\n'
                '  <div class="ws-iframe-wrap">\n'
                '    <div class="chart-pane" data-pair="global" data-pane="0" '
                'style="visibility:visible;position:relative;pointer-events:auto;width:100%;height:100%;">\n'
                '<iframe src="../charts/global_workspace.html" '
                'style="width:100%;height:calc(100vh - 36px);border:none;display:block;" '
                'loading="eager" scrolling="no"></iframe>\n'
                '    </div>\n'
                '  </div>\n'
                '</div>'
            ),
            html_content,
        )

    # collapsible REGIME READ — inject CSS after .brief-section:first-child (idempotent)
    _regime_css = (
        '.brief-section.regime-read .brief-text { display: none; }\n'
        '.brief-section.regime-read.open .brief-text { display: block; }\n'
        '.brief-label.regime-toggle { cursor: pointer; display: flex; align-items: center; justify-content: space-between; }\n'
        '.regime-arrow { color: #444; font-size: 8px; transition: transform 0.15s; }\n'
        '.brief-section.regime-read.open .regime-arrow { transform: rotate(90deg); }'
    )
    if '.regime-arrow' not in html_content:
        html_content = html_content.replace(
            '.brief-section:first-child {\n    border-top: none;\n    padding-top: 0;\n}',
            '.brief-section:first-child {\n    border-top: none;\n    padding-top: 0;\n}\n' + _regime_css,
        )

    # REGIME READ — add regime-read class + toggle markup (idempotent guard on class already present)
    if 'class="brief-section regime-read"' not in html_content:
        html_content = html_content.replace(
            '        <div class="brief-section">\n          <div class="brief-label">REGIME READ</div>',
            '        <div class="brief-section regime-read">\n          <div class="brief-label regime-toggle">REGIME READ <span class="regime-arrow">▶</span></div>',
        )

    # ------------------------------------------------------------------
    # 3. Pane visibility (display → visibility so hidden panes keep size)
    # ------------------------------------------------------------------
    html_content = html_content.replace(
        'style="display:block; width:100%;"',
        'style="visibility:visible; position:relative; pointer-events:auto; width:100%;"',
    )
    html_content = html_content.replace(
        'style="display:none; width:100%;"',
        'style="visibility:hidden; position:absolute; pointer-events:none; width:100%;"',
    )

    # ------------------------------------------------------------------
    # 4. Remove stale deferred-init scripts from previous runs
    # ------------------------------------------------------------------
    html_content = _re.sub(
        r'\n?<script>\s*\(function\(\)\{\s*var _orig = Plotly\.newPlot.*?\}\)\(\);\s*</script>\n?',
        '',
        html_content,
        flags=_re.DOTALL,
    )

    # ------------------------------------------------------------------
    # 5. Replace last plain <script> block with clean tab handler
    #    (iframes are self-contained; no Plotly.Plots.resize needed)
    # ------------------------------------------------------------------
    tab_handler = '''
// Normalise all panes inside .chart-display-area to position:absolute fill
document.querySelectorAll('.chart-display-area .chart-pane').forEach(function(p) {
  p.style.position = 'absolute';
  p.style.top = '0'; p.style.right = '0'; p.style.bottom = '0'; p.style.left = '0';
  p.style.width = '100%'; p.style.height = '100%';
});

document.querySelectorAll('.chart-tab').forEach(function(tab) {
  tab.addEventListener('click', function() {
    var pair   = this.dataset.pair;
    var tabIdx = this.dataset.tab;

    document.querySelectorAll('.chart-tab[data-pair="' + pair + '"]')
      .forEach(function(t) { t.classList.remove('active'); });

    document.querySelectorAll('.chart-pane[data-pair="' + pair + '"]')
      .forEach(function(p) {
        p.style.visibility    = 'hidden';
        p.style.pointerEvents = 'none';
      });

    this.classList.add('active');
    var pane = document.querySelector(
      '.chart-pane[data-pair="' + pair + '"][data-pane="' + tabIdx + '"]'
    );
    pane.style.visibility    = 'visible';
    pane.style.pointerEvents = 'auto';
  });
});

document.querySelectorAll('.regime-toggle').forEach(function(lbl) {
  lbl.addEventListener('click', function() {
    this.closest('.regime-read').classList.toggle('open');
  });
});

// Pair nav active state via IntersectionObserver
if (typeof IntersectionObserver !== 'undefined') {
  var _navBtns = document.querySelectorAll('.pnav-btn[data-target]');
  if (_navBtns.length) {
    var _io = new IntersectionObserver(function(entries) {
      entries.forEach(function(e) {
        if (e.isIntersecting) {
          _navBtns.forEach(function(a) { a.classList.remove('active'); });
          var a = document.querySelector('.pnav-btn[data-target="' + e.target.id + '"]');
          if (a) a.classList.add('active');
        }
      });
    }, { threshold: 0.5 });
    ['landing-page','card-eurusd','card-usdjpy','card-usdinr','workspace-snap'].forEach(function(id) {
      var el = document.getElementById(id);
      if (el) _io.observe(el);
    });
  }
}
'''

    all_scripts = list(_re.finditer(r'(<script>)(.*?)(</script>)', html_content, _re.DOTALL))
    if all_scripts:
        m = all_scripts[-1]
        html_content = html_content[:m.start(2)] + tab_handler + html_content[m.end(2):]

    # ------------------------------------------------------------------
    # 5b. Inject fixed bottom pair nav (idempotent)
    # ------------------------------------------------------------------
    if 'id="pair-nav"' not in html_content:
        _nav_html = (
            '<nav id="pair-nav">\n'
            '  <a href="#landing-page" class="pnav-btn" data-target="landing-page">HOME</a>\n'
            '  <a href="#card-eurusd" class="pnav-btn" data-target="card-eurusd">EUR/USD</a>\n'
            '  <a href="#card-usdjpy" class="pnav-btn" data-target="card-usdjpy">USD/JPY</a>\n'
            '  <a href="#card-usdinr" class="pnav-btn" data-target="card-usdinr">USD/INR</a>\n'
            '  <a href="#workspace-snap" class="pnav-btn" data-target="workspace-snap">WS</a>\n'
            '</nav>\n'
        )
        html_content = html_content.replace('</body>', _nav_html + '</body>', 1)

    # ------------------------------------------------------------------
    # 6. Write output
    # ------------------------------------------------------------------
    os.makedirs('briefs', exist_ok=True)
    output_file = f'briefs/brief_{DATE_SLUG}.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Generated: {output_file}")

if __name__ == '__main__':
    generate_html_brief()
