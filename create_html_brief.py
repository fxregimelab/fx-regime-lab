import os
import glob
import math
import html as _html
import pandas as pd
import numpy as np
import sys
from core.utils import ordinal, embed_image, fmt_pct, color_class
from config import TODAY, TODAY_FMT, DATE_SLUG, get_upcoming_event
from core.utils import _btp_bund_label
from morning_brief import _oil_corr_label, _dxy_corr_label, _gold_corr_label, _rbi_intervention_label, _eur_interpretation, _jpy_interpretation


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
from charts.base import set_chart_months
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
    if label in ('OIL DIVERGENCE', 'GOLD DIVERGENCE'):
        return 'badge-danger'
    if label in ('HIGH', 'STRONG', 'EUR SPECIFIC', 'YEN SPECIFIC', 'INDIA SPECIFIC'):
        return 'badge-success'
    if label in ('MODERATE', 'MIXED', 'DOLLAR REGIME'):
        return 'badge-warning'
    return 'badge-neutral'   # LOW, WEAK, NO DATA

def _value_color_for(label):
    """Map a corr label string to an inline hex color."""
    if label in ('OIL DIVERGENCE', 'GOLD DIVERGENCE'):
        return '#ff4444'
    if label in ('HIGH', 'STRONG', 'EUR SPECIFIC', 'YEN SPECIFIC', 'INDIA SPECIFIC'):
        return '#00d4aa'
    if label in ('MODERATE', 'MIXED'):
        return '#888888'
    if label == 'DOLLAR REGIME':
        return '#f0a500'
    return '#555555'   # LOW, WEAK, NO DATA

def inject_live_card_data(html_content, _re, df=None):
    """
    Regenerate every pair card's header (price, changes, badge) and entire
    brief-left panel (spreads, COT, vol, regime read) with live values from
    data/latest_with_cot.csv so the detail page always matches the landing page.
    """
    import json as _json
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td

    try:
        if df is None:
            df = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)
        row = df.iloc[-1]
    except Exception:
        return html_content

    # Load AI regime reads if fresh (< 24 h)
    _ai_reads = {}
    _ai_path  = os.path.join('data', 'ai_regime_read.json')
    try:
        if os.path.exists(_ai_path):
            with open(_ai_path, encoding='utf-8') as _fh:
                _ai_data = _json.load(_fh)
            _gen_at = _dt.fromisoformat(_ai_data.get('generated_at', '2000-01-01T00:00:00+00:00'))
            if _dt.now(_tz.utc) - _gen_at < _td(hours=24):
                _ai_reads = {k: v for k, v in _ai_data.items()
                             if k in ('eurusd', 'usdjpy', 'usdinr') and v}
    except Exception:
        pass  # silently fall back to hardcoded logic

    def _g(col, default=float('nan')):
        v = row.get(col, default)
        try:
            fv = float(v)
            return default if math.isnan(fv) else fv
        except Exception:
            return default

    def _chg_col(val):  return '#00d4aa' if val >= 0 else '#ff4444'
    def _sign(val):     return '+' if val > 0 else ''

    def _pct_fmt(val):
        if math.isnan(val): return '\u2014', '#888'
        return f'{_sign(val)}{val:.2f}%', _chg_col(val)

    def _pp_fmt(val, favor_narrow=True):
        if math.isnan(val): return '\u2014', '#888'
        color = '#00d4aa' if (val < 0) == favor_narrow else '#ff4444'
        return f'{_sign(val)}{val:.2f}pp', color

    def _vol_pctile_badge(pct):
        if math.isnan(pct): return '\u2014', 'badge-neutral', '\u2014'
        s = f'{pct:.0f}th %ile'
        if pct >= 90: return s, 'badge-danger',  'EXTREME'
        if pct >= 75: return s, 'badge-warning', 'ELEVATED'
        return s, 'badge-neutral', 'NORMAL'

    def _corr_badge(corr):
        if math.isnan(corr): return '\u2014', '#555', 'badge-neutral', 'NO DATA'
        if corr >= 0.6:  return f'{corr:+.3f}', '#00d4aa', 'badge-success',  'INTACT'
        if corr >= 0.3:  return f'{corr:+.3f}', '#888',    'badge-neutral',  'WEAKENING'
        if corr >= -0.3: return f'{corr:+.3f}', '#ff4444', 'badge-danger',   'BROKEN'
        return f'{corr:+.3f}', '#f0a500', 'badge-warning', 'INVERTED'

    def _header_badge(lev_pct, lev_net, am_pct, am_net):
        if math.isnan(lev_pct) and math.isnan(am_pct):
            return 'RATE DIFF ONLY', 'badge-neutral-card'
        if not math.isnan(lev_pct) and lev_pct >= 80 and not math.isnan(lev_net) and lev_net > 0:
            return 'CROWDED LONG', 'badge-crowded-long'
        if not math.isnan(lev_pct) and lev_pct <= 20 and not math.isnan(lev_net) and lev_net < 0:
            return 'CROWDED SHORT', 'badge-crowded-short'
        return 'NEUTRAL', 'badge-neutral-card'

    def _spread_row(name, val, chg, favor_narrow=True):
        val_str = f'{val:.2f}%' if not math.isnan(val) else '\u2014'
        chg_str, c = _pp_fmt(chg, favor_narrow)
        return (f'<div class="brief-row">'
                f'<span class="name">{name}</span>'
                f'<span class="val">{val_str}</span>'
                f'<span class="pct" style="color:{c}">{chg_str}</span></div>\n          ')

    def _cot_row(name, net, pctoi, pct_rank):
        if math.isnan(net): return ''
        net_str   = f'{net:+,.0f}'
        direction = 'LONG' if net > 0 else 'SHORT'
        if not math.isnan(pct_rank):
            pct_str = f'{pct_rank:.0f}th %ile'
            if pct_rank >= 85:   bdg_cls, bdg_lbl = 'badge-danger',  f'CROWDED {direction}'
            elif pct_rank >= 70: bdg_cls, bdg_lbl = 'badge-warning', 'EXTENDED'
            elif pct_rank <= 15: bdg_cls, bdg_lbl = 'badge-danger',  f'CROWDED {direction}'
            else:                bdg_cls, bdg_lbl = 'badge-neutral', f'NEUTRAL {direction}'
        else:
            pct_str, bdg_cls, bdg_lbl = '\u2014', 'badge-neutral', '\u2014'
        net_col = _chg_col(net)
        return (f'<div class="brief-row"><span class="name">{name}</span>'
                f'<span class="pct" style="color:{net_col}">{net_str}</span>'
                f'<span class="pct">{pct_str}</span>'
                f'<span class="badge-mini {bdg_cls}">{bdg_lbl}</span></div>\n          ')

    def _vol_row(vol_val, pct_val):
        vol_str = f'{vol_val:.1f}%' if not math.isnan(vol_val) else '\u2014'
        pctile_str, bdg_cls, bdg_lbl = _vol_pctile_badge(pct_val)
        return (f'<div class="brief-row"><span class="name">30D Vol</span>'
                f'<span class="val">{vol_str}</span>'
                f'<span class="pct">{pctile_str}</span>'
                f'<span class="badge-mini {bdg_cls}">{bdg_lbl}</span></div>\n          ')

    def _corr_row(corr_val):
        corr_str, color, bdg_cls, bdg_lbl = _corr_badge(corr_val)
        return (f'<div class="brief-row"><span class="name">60D Corr</span>'
                f'<span class="pct" style="color:{color}">{corr_str}</span>'
                f'<span></span>'
                f'<span class="badge-mini {bdg_cls}">{bdg_lbl}</span></div>\n          ')

    def _corr_row_20d(corr_val):
        corr_str, color, bdg_cls, bdg_lbl = _corr_badge(corr_val)
        return (f'<div class="brief-row"><span class="name">20D Corr</span>'
                f'<span class="pct" style="color:{color}">{corr_str}</span>'
                f'<span></span>'
                f'<span class="badge-mini {bdg_cls}">{bdg_lbl}</span></div>\n          ')

    def _regime_transition_row():
        return ('<div class="brief-row"><span style="color:#f0a500;font-size:0.58rem;'
                'letter-spacing:0.05em">REGIME TRANSITION \u2014 20D diverging from 60D'
                '</span></div>\n          ')

    def _field_row(label, field, pair_key, is_oil):
        raw = _g(field)
        if math.isnan(raw):
            val_str, color, bdg_cls, bdg_lbl = '\u2014', '#555', 'badge-neutral', 'NO DATA'
        else:
            val_str = f'{raw:+.3f}'
            bdg_lbl, _ = (_oil_corr_label(raw, pair_key) if is_oil
                          else _dxy_corr_label(raw, pair_key))
            color   = _value_color_for(bdg_lbl)
            bdg_cls = _badge_class_for(bdg_lbl)
        return (f'<div class="brief-row"><span class="name">{label}</span>'
                f'<span class="pct" style="color:{color}" data-field="{field}">{val_str}</span>'
                f'<span></span>'
                f'<span class="badge-mini {bdg_cls}" data-badge="{field}">{bdg_lbl}</span>'
                f'</div>\n          ')

    def _df_chg_1w(col):
        """5-row difference for spread columns not pre-computed by pipeline."""
        try:
            s = df[col].dropna()
            return float(s.iloc[-1]) - float(s.iloc[-6]) if len(s) >= 6 else float('nan')
        except Exception:
            return float('nan')

    def _gold_field_row(label, field, pair_key):
        raw = _g(field)
        if math.isnan(raw):
            val_str, color, bdg_cls, bdg_lbl = '\u2014', '#555', 'badge-neutral', 'NO DATA'
        else:
            val_str = f'{raw:+.3f}'
            bdg_lbl, _ = _gold_corr_label(raw, pair_key)
            color   = _value_color_for(bdg_lbl)
            bdg_cls = _badge_class_for(bdg_lbl)
        return (f'<div class="brief-row"><span class="name">{label}</span>'
                f'<span class="pct" style="color:{color}" data-field="{field}">{val_str}</span>'
                f'<span></span>'
                f'<span class="badge-mini {bdg_cls}" data-badge="{field}">{bdg_lbl}</span>'
                f'</div>\n          ')

    def _seasonal_row(season_label):
        return (f'<div class="brief-row"><span class="name">Seasonal window</span>'
                f'<span class="pct" style="color:#f0a500">ACTIVE</span>'
                f'<span></span>'
                f'<span class="badge-mini badge-warning">{season_label}</span>'
                f'</div>\n          ')

    def _btp_row(spread_val, flag_str):
        btp_text, btp_color = _btp_bund_label(flag_str)
        spread_str = f'{spread_val:.2f}pp' if not math.isnan(spread_val) else '\u2014'
        return (f'<div class="brief-row"><span class="name">BTP-Bund (IT-DE)</span>'
                f'<span class="val">{spread_str}</span>'
                f'<span></span>'
                f'<span class="badge-mini" style="color:{btp_color};border-color:{btp_color}">{btp_text}</span>'
                f'</div>\n          ')

    def _g10_composite_row(score_col, label_col):
        score = _g(score_col)
        label = str(row.get(label_col, 'UNKNOWN'))
        if math.isnan(score):
            return ''
        if score > 30:
            score_color, bdg_cls = '#ff4444', 'badge-danger'
        elif score < -30:
            score_color, bdg_cls = '#00d4aa', 'badge-success'
        else:
            score_color, bdg_cls = '#888888', 'badge-neutral'
        bar_pct   = min(abs(score), 100)
        bar_color = '#ff4444' if score > 0 else '#00d4aa'
        return (
            f'<div class="brief-row"><span class="name">Composite Score</span>'
            f'<span class="pct" style="color:{score_color};font-size:1.1em">{score:+.0f}</span>'
            f'<span></span>'
            f'<span class="badge-mini {bdg_cls}">{label}</span>'
            f'</div>\n          '
            f'<div style="height:4px;background:#1e1e1e;margin:4px 0 6px 0;border-radius:2px;">'
            f'<div style="height:4px;width:{bar_pct:.0f}%;background:{bar_color};border-radius:2px;"></div>'
            f'</div>\n          '
        )

    def _rbi_row(chg_str, flag_text, color):
        return (f'<div class="brief-row"><span class="name">RBI Reserves 1W</span>'
                f'<span class="pct" style="color:{color}">{chg_str}</span>'
                f'<span></span>'
                f'<span class="badge-mini" style="color:{color};border-color:{color}">{flag_text}</span>'
                f'</div>\n          ')

    def _composite_block_html(score_col, label_col, rbi_flag_col):
        score = _g(score_col)
        label = str(row.get(label_col, 'UNKNOWN'))
        if math.isnan(score):
            return ''
        if score > 30:
            score_color, bdg_cls = '#ff4444', 'badge-danger'
        elif score < -30:
            score_color, bdg_cls = '#00d4aa', 'badge-success'
        else:
            score_color, bdg_cls = '#888888', 'badge-neutral'
        bar_pct   = min(abs(score), 100)
        bar_color = '#ff4444' if score > 0 else '#00d4aa'
        oil_corr = _g('oil_inr_corr_60d')
        dxy_corr = _g('dxy_inr_corr_60d')
        fpi_raw  = _g('FPI_20D_flow')
        brent1d  = _g('Brent_chg_1D')
        dxy1d    = _g('DXY_chg_1D')
        rate_spr = _g('US_IN_10Y_spread')
        rbi_fv   = str(row.get(rbi_flag_col, 'NEUTRAL'))
        if rbi_fv == 'nan': rbi_fv = 'NEUTRAL'
        _rbi_w = {'ACTIVE SUPPORT': -0.30, 'ACTIVE CAPPING': 0.20, 'NEUTRAL': 0.0, 'UNKNOWN': 0.0}
        def _s(v): return 0.0 if math.isnan(v) else float(v)
        def _sg(v): return 1.0 if v > 0 else (-1.0 if v < 0 else 0.0)
        oil_s  = _s(oil_corr) * _sg(_s(brent1d)) * 0.25 * 100
        dxy_s  = _s(dxy_corr) * _sg(_s(dxy1d))   * 0.20 * 100
        fpi_s  = -min(max(_s(fpi_raw) / 20000, -1.0), 1.0) * 0.25 * 100
        rbi_s  = _rbi_w.get(rbi_fv, 0.0) * 0.20 * 100
        rate_s = _sg(-_s(rate_spr)) * 0.10 * 100
        def _sc(v): return '#cc4444' if v > 0.5 else ('#007a66' if v < -0.5 else '#555555')
        sub_rows = ''.join(
            f'<div class="brief-row" style="font-size:0.85em;padding-left:8px;">'
            f'<span class="name" style="color:#666">{nm}</span>'
            f'<span class="pct" style="color:{_sc(vl)}">{vl:+.0f}</span>'
            f'<span></span><span></span>'
            f'</div>\n          '
            for nm, vl in [('Oil', oil_s), ('Dollar', dxy_s), ('FPI', fpi_s), ('RBI', rbi_s), ('Rate diff', rate_s)]
        )
        return (
            f'<div class="brief-row"><span class="name">Regime Score</span>'
            f'<span class="pct" style="color:{score_color};font-size:1.1em">{score:+.0f}</span>'
            f'<span></span>'
            f'<span class="badge-mini {bdg_cls}">{label}</span>'
            f'</div>\n          '
            f'<div style="height:4px;background:#1e1e1e;margin:4px 0 6px 0;border-radius:2px;">'
            f'<div style="height:4px;width:{bar_pct:.0f}%;background:{bar_color};border-radius:2px;"></div>'
            f'</div>\n          '
            + sub_rows
        )

    pairs_cfg = {
        'eurusd': dict(
            price_col='EURUSD', price_dec=4,
            chg_1d='EURUSD_chg_1D', chg_12m='EURUSD_chg_12M',
            spreads=[
                ('US-DE 10Y', 'US_DE_10Y_spread', 'US_DE_10Y_spread_chg_1W', True),
                ('US-DE 2Y',  'US_DE_2Y_spread',  'US_DE_2Y_spread_chg_1W',  True),
            ],
            cot_lev_net='EUR_lev_net',   cot_lev_pctoi='EUR_lev_pct_oi',   cot_lev_pct='EUR_lev_percentile',
            cot_am_net='EUR_assetmgr_net', cot_am_pctoi='EUR_assetmgr_pct_oi', cot_am_pct='EUR_assetmgr_percentile',
            vol_col='EURUSD_vol30', vol_pct_col='EURUSD_vol_pct',
            corr_col='EURUSD_spread_corr_60d',
            corr_20d_col='EURUSD_corr_20d',
            oil_field='oil_eurusd_corr_60d', oil_pair='EURUSD',
            dxy_field='dxy_eurusd_corr_60d', dxy_pair='EURUSD',
        ),
        'usdjpy': dict(
            price_col='USDJPY', price_dec=2,
            chg_1d='USDJPY_chg_1D', chg_12m='USDJPY_chg_12M',
            spreads=[
                ('US-JP 10Y', 'US_JP_10Y_spread', 'US_JP_10Y_spread_chg_1W', True),
                ('US-JP 2Y',  'US_JP_2Y_spread',  'US_JP_2Y_spread_chg_1W',  True),
            ],
            cot_lev_net='JPY_lev_net',   cot_lev_pctoi='JPY_lev_pct_oi',   cot_lev_pct='JPY_lev_percentile',
            cot_am_net='JPY_assetmgr_net', cot_am_pctoi='JPY_assetmgr_pct_oi', cot_am_pct='JPY_assetmgr_percentile',
            vol_col='USDJPY_vol30', vol_pct_col='USDJPY_vol_pct',
            corr_col='USDJPY_spread_corr_60d',
            corr_20d_col='USDJPY_corr_20d',
            oil_field='oil_usdjpy_corr_60d', oil_pair='USDJPY',
            gold_field='gold_usdjpy_corr_60d', gold_pair='USDJPY',
            dxy_field='dxy_usdjpy_corr_60d', dxy_pair='USDJPY',
        ),
        'usdinr': dict(
            price_col='USDINR', price_dec=2,
            chg_1d='USDINR_chg_1D', chg_12m='USDINR_chg_12M',
            spreads=[
                ('US 2Y–IN 10Y', 'US_IN_10Y_spread',    None, True),
                ('US-IN Policy',  'US_IN_policy_spread', None, True),
            ],
            cot_lev_net=None, cot_lev_pctoi=None, cot_lev_pct=None,
            cot_am_net=None,  cot_am_pctoi=None,  cot_am_pct=None,
            vol_col='USDINR_vol30', vol_pct_col='USDINR_vol_pct',
            corr_col=None,
            corr_20d_col=None,
            oil_field='oil_inr_corr_60d', oil_pair='USDINR',
            gold_field='gold_inr_corr_60d', gold_pair='USDINR',
            seasonal_flag_col='gold_seasonal_flag',
            seasonal_label_col='gold_seasonal_label',
            rbi_chg_col='rbi_reserve_chg_1w',
            rbi_flag_col='rbi_intervention_flag',
            composite_score_col='inr_composite_score',
            composite_label_col='inr_composite_label',
            dxy_field='dxy_inr_corr_60d', dxy_pair='USDINR',
        ),
    }

    # Strip previously injected idempotent strips so re-runs are clean
    html_content = _re.sub(
        r'<!-- BTP-WARN-STRIP -->[\s\S]*?<!-- /BTP-WARN-STRIP -->',
        '', html_content,
    )
    html_content = _re.sub(
        r'<!-- MACRO-EVENT-STRIP -->\n[\s\S]*?<!-- /MACRO-EVENT-STRIP -->\n',
        '', html_content,
    )

    for pair, cfg in pairs_cfg.items():
        card_anchor = f'id="card-{pair}"'
        anchor_pos  = html_content.find(card_anchor)
        if anchor_pos == -1:
            continue
        card_start = html_content.rfind('<div', 0, anchor_pos)

        next_card = html_content.find('<div class="card" id="card-', card_start + 1)
        ws_snap   = html_content.find('<div class="workspace-snap">', card_start)
        boundaries = [x for x in [next_card, ws_snap] if x != -1]
        card_end   = min(boundaries) if boundaries else len(html_content)
        card_html  = html_content[card_start:card_end]

        # ---- card-header spans ----
        price_val        = _g(cfg['price_col'])
        chg_1d_val       = _g(cfg['chg_1d'])
        chg_12m_val      = _g(cfg['chg_12m'])
        price_str        = f"{price_val:.{cfg['price_dec']}f}" if not math.isnan(price_val) else '\u2014'
        chg_1d_str,  c1d = _pct_fmt(chg_1d_val)
        chg_12m_str, c12 = _pct_fmt(chg_12m_val)
        lev_pct = _g(cfg['cot_lev_pct']) if cfg['cot_lev_pct'] else float('nan')
        lev_net = _g(cfg['cot_lev_net']) if cfg['cot_lev_net'] else float('nan')
        am_pct  = _g(cfg['cot_am_pct'])  if cfg['cot_am_pct']  else float('nan')
        am_net  = _g(cfg['cot_am_net'])  if cfg['cot_am_net']  else float('nan')
        badge_txt, badge_cls = _header_badge(lev_pct, lev_net, am_pct, am_net)

        card_html = _re.sub(r'(<span class="ch-price">)[^<]*(</span>)',
                            rf'\g<1>{price_str}\g<2>', card_html, count=1)
        card_html = _re.sub(r'<span class="ch-1d"[^>]*>[^<]*</span>',
                            f'<span class="ch-1d" style="color:{c1d}">{chg_1d_str}</span>',
                            card_html, count=1)
        card_html = _re.sub(r'<span class="ch-12m"[^>]*>[^<]*</span>',
                            f'<span class="ch-12m" style="color:{c12}">{chg_12m_str}</span>',
                            card_html, count=1)
        card_html = _re.sub(r'<span class="ch-badge [^"]*">[^<]*</span>',
                            f'<span class="ch-badge {badge_cls}">{badge_txt}</span>',
                            card_html, count=1)

        # ---- brief-left sections ----
        spread_rows = ''
        for name, val_col, chg_col, favor_narrow in cfg['spreads']:
            val = _g(val_col)
            chg = _g(chg_col) if chg_col else _df_chg_1w(val_col)
            spread_rows += _spread_row(name, val, chg, favor_narrow)
        # BTP-Bund row for EUR/USD only (Phase 9)
        if pair == 'eurusd':
            btp_spread_val = _g('BTP_Bund_spread')
            btp_flag_str   = str(row.get('BTP_Bund_flag', 'UNAVAILABLE'))
            if str(btp_flag_str) == 'nan': btp_flag_str = 'UNAVAILABLE'
            spread_rows += _btp_row(btp_spread_val, btp_flag_str)
        spread_section = (f'<div class="brief-section">\n          '
                          f'<div class="brief-label">RATE DIFFERENTIALS</div>\n          '
                          f'{spread_rows}</div>')

        if cfg['cot_lev_pct']:
            lev_pctoi = _g(cfg['cot_lev_pctoi'])
            am_pctoi  = _g(cfg['cot_am_pctoi'])
            cot_body  = (_cot_row('Lev Money', lev_net, lev_pctoi, lev_pct)
                         + _cot_row('Asset Mgr', am_net,  am_pctoi,  am_pct))
            cot_section = (f'<div class="brief-section">\n          '
                           f'<div class="brief-label">POSITIONING (COT)</div>\n          '
                           f'{cot_body}</div>')
        else:
            cot_section = ('<div class="brief-section">\n          '
                           '<div class="brief-label">POSITIONING (COT)</div>\n          '
                           '<div class="brief-muted">FPI proxy unavailable</div>\n          </div>')

        vol_val  = _g(cfg['vol_col'])
        vol_pct  = _g(cfg['vol_pct_col'])
        corr_val     = _g(cfg['corr_col'])       if cfg['corr_col']            else float('nan')
        corr_20d_val = _g(cfg['corr_20d_col']) if cfg.get('corr_20d_col') else float('nan')
        vc = _vol_row(vol_val, vol_pct)
        if cfg['corr_col']:
            vc += _corr_row(corr_val)
        if cfg.get('corr_20d_col') and not math.isnan(corr_20d_val):
            vc += _corr_row_20d(corr_20d_val)
            if not math.isnan(corr_val) and abs(corr_20d_val - corr_val) > 0.3:
                vc += _regime_transition_row()
        vc += _field_row('Oil corr 60D', cfg['oil_field'], cfg['oil_pair'], is_oil=True)
        if cfg.get('gold_field'):
            vc += _gold_field_row('Gold corr 60D', cfg['gold_field'], cfg['gold_pair'])
            if cfg.get('seasonal_flag_col'):
                flag_numeric = _g(cfg['seasonal_flag_col'])
                if not math.isnan(flag_numeric) and flag_numeric > 0.5:
                    s_label = row.get(cfg['seasonal_label_col'], '')
                    if s_label and str(s_label) not in ('nan', 'None', ''):
                        vc += _seasonal_row(str(s_label))
        vc += _field_row('DXY corr 60D', cfg['dxy_field'], cfg['dxy_pair'], is_oil=False)
        vol_section = (f'<div class="brief-section">\n          '
                       f'<div class="brief-label">VOLATILITY &amp; CORRELATION</div>\n          '
                       f'{vc}</div>')

        # ---- RBI intervention (USD/INR only, Phase 5) ----
        rbi_section = ''
        if cfg.get('rbi_flag_col'):
            rbi_flag_val = str(row.get(cfg['rbi_flag_col'], 'UNKNOWN'))
            rbi_chg_val  = _g(cfg['rbi_chg_col'])
            rbi_text, rbi_color, _rbi_active = _rbi_intervention_label(rbi_flag_val)
            chg_str  = f'{rbi_chg_val:+.1f}B' if not math.isnan(rbi_chg_val) else '\u2014'
            rbi_body = _rbi_row(chg_str, rbi_text, rbi_color)
            rbi_section = (f'<div class="brief-section">\n          '
                           f'<div class="brief-label">CENTRAL BANK ACTIVITY</div>\n          '
                           f'{rbi_body}</div>')

        # ---- INR composite score (USD/INR only, Phase 7) ----
        composite_section = ''
        if cfg.get('composite_score_col'):
            comp_html = _composite_block_html(
                cfg['composite_score_col'],
                cfg['composite_label_col'],
                cfg.get('rbi_flag_col', 'rbi_intervention_flag'),
            )
            if comp_html:
                composite_section = (f'<div class="brief-section">\n          '
                                     f'<div class="brief-label">INR COMPOSITE</div>\n          '
                                     f'{comp_html}</div>')

        # ---- G10 composite score section (EUR/USD and USD/JPY, Phase 8) ----
        g10_composite_section = ''
        if pair == 'eurusd':
            comp_html = _g10_composite_row('eurusd_composite_score', 'eurusd_composite_label')
            if comp_html:
                g10_composite_section = (f'<div class="brief-section">\n          '
                                         f'<div class="brief-label">G10 REGIME COMPOSITE</div>\n          '
                                         f'{comp_html}</div>')
        elif pair == 'usdjpy':
            comp_html = _g10_composite_row('usdjpy_composite_score', 'usdjpy_composite_label')
            if comp_html:
                g10_composite_section = (f'<div class="brief-section">\n          '
                                         f'<div class="brief-label">G10 REGIME COMPOSITE</div>\n          '
                                         f'{comp_html}</div>')

        # ---- regime read: AI text (fresh < 24h) or hardcoded fallback ----
        if pair in _ai_reads:
            regime_text = _ai_reads[pair]
        elif pair == 'eurusd':
            de10_today  = _g('US_DE_10Y_spread')
            de10_12m    = _g('US_DE_10Y_spread_chg_12M')
            regime_text = _eur_interpretation(de10_today, de10_12m, lev_pct, lev_net, am_pct, am_net)
            eur_vol_pct = _g('EURUSD_vol_pct')
            if not math.isnan(eur_vol_pct):
                if eur_vol_pct >= 90:  regime_text += ' vol EXTREME \u2014 forced liquidation risk, fundamental signals unreliable.'
                elif eur_vol_pct >= 75: regime_text += ' vol elevated \u2014 positioning signals less reliable.'
        elif pair == 'usdjpy':
            jp10_today  = _g('US_JP_10Y_spread')
            jp10_12m    = _g('US_JP_10Y_spread_chg_12M')
            regime_text = _jpy_interpretation(jp10_today, jp10_12m, lev_pct, lev_net, am_pct, am_net)
            jpy_vol_pct = _g('USDJPY_vol_pct')
            if not math.isnan(jpy_vol_pct):
                if jpy_vol_pct >= 90:  regime_text += ' vol EXTREME \u2014 forced liquidation risk, fundamental signals unreliable.'
                elif jpy_vol_pct >= 75: regime_text += ' vol elevated \u2014 positioning signals less reliable.'
        else:  # usdinr
            in10_spr = _g('US_IN_10Y_spread')
            in10_str = f'{in10_spr:.2f}%' if not math.isnan(in10_spr) else '\u2014'
            prem     = abs(in10_spr) if not math.isnan(in10_spr) else 0.0
            if not math.isnan(in10_spr) and in10_spr < 0:
                regime_text = (f'US-IN spread at {in10_str}. India yield premium intact at {prem:.2f}pp. '
                               f'Rate differential favors INR strength. FPI positioning data pending.')
            else:
                regime_text = (f'US-IN spread at {in10_str}. Rate differential needs monitoring. '
                               f'FPI positioning data pending.')

        regime_section = (
            '<div class="brief-section regime-read">\n          '
            '<div class="brief-label regime-toggle">REGIME READ '
            '<span class="regime-arrow">\u25b6</span></div>\n          '
            f'<div class="brief-text">{_html.escape(regime_text)}</div>\n        </div>'
        )

        rbi_block       = f'        {rbi_section}\n\n'       if rbi_section       else ''
        composite_block = f'        {composite_section}\n\n' if composite_section else ''
        g10_comp_block  = f'        {g10_composite_section}\n\n' if g10_composite_section else ''
        new_brief_left = ('\n      <div class="brief-left">\n\n'
                          f'        {spread_section}\n\n'
                          f'        {cot_section}\n\n'
                          f'{rbi_block}'
                          f'        {vol_section}\n\n'
                          f'{composite_block}'
                          f'{g10_comp_block}'
                          f'        {regime_section}\n'
                          '      </div>')

        bl_idx = card_html.find('<div class="brief-left">')
        br_idx = card_html.find('<div class="brief-right">')
        if bl_idx != -1 and br_idx != -1:
            card_html = (card_html[:bl_idx].rstrip()
                         + new_brief_left
                         + '\n\n      '
                         + card_html[br_idx:])

        # ---- BTP-Bund top-of-card warning strip (Phase 9, idempotent) ----
        if pair == 'eurusd':
            _btp_flag = str(row.get('BTP_Bund_flag', 'UNAVAILABLE'))
            if _btp_flag == 'nan':
                _btp_flag = 'UNAVAILABLE'
            if _btp_flag in ('ELEVATED', 'STRESS'):
                _strip_bg = '#1a0a00' if _btp_flag == 'ELEVATED' else '#1a0000'
                _strip_fg = '#f0a500' if _btp_flag == 'ELEVATED' else '#ff4444'
                _btp_warn = (
                    f'<!-- BTP-WARN-STRIP -->'
                    f'<div style="background:{_strip_bg};border-bottom:1px solid {_strip_fg}44;'
                    f'padding:6px 16px;font-size:0.82em;color:{_strip_fg};letter-spacing:0.05em;">'
                    f'\u26a0\ufe0f  BTP-Bund {_btp_flag}: Italian sovereign risk elevated'
                    f' \u2014 EUR/USD upside constrained.</div><!-- /BTP-WARN-STRIP -->'
                )
                card_html = _re.sub(
                    r'(<div[^>]+id="card-eurusd"[^>]*>)',
                    lambda m, _w=_btp_warn: m.group(1) + _w,
                    card_html, count=1,
                )
            # ---- Macro event strip before EUR/USD card (Phase 10, idempotent) ----
            _evt = get_upcoming_event()
            if _evt is not None:
                _days   = _evt['days_away']
                _evt_nm = _evt['event']
                _fg     = '#ff4444' if _days <= 1 else '#f0a500'
                _when   = (
                    'Today' if _days == 0 else
                    'Tomorrow' if _days == 1 else
                    f'in {_days} days'
                )
                card_html = (
                    f'<!-- MACRO-EVENT-STRIP -->\n'
                    f'<div class="macro-event-strip" style="background:{_fg}11;'
                    f'border-top:1px solid {_fg}44;border-bottom:1px solid {_fg}44;'
                    f'padding:10px 20px;font-size:0.85em;color:{_fg};'
                    f'letter-spacing:0.05em;text-align:center;">'
                    f'\U0001f4c5 Upcoming: <strong>{_html.escape(_evt_nm)}</strong>'
                    f' \u2014 {_when}</div>\n<!-- /MACRO-EVENT-STRIP -->\n'
                    + card_html
                )

        html_content = html_content[:card_start] + card_html + html_content[card_end:]

    return html_content


def inject_cross_asset_values(html_content, _re, df=None):
    """Replace data-field / data-badge spans with live corr values from CSV."""
    try:
        if df is None:
            df = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)
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


def update_globalbar(html_content, _re, df=None):
    """Replace static globalbar prices with live values + color-coded 1D change spans."""
    try:
        if df is None:
            df = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)
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


def _mini_signal_row(name, val_str, val_color, badge_label, badge_css):
    """Return a single signal row HTML for the landing mini-card."""
    return (
        f'<div class="lc-row">'
        f'<span class="lc-name">{name}</span>'
        f'<span class="lc-val" style="color:{val_color}">{val_str}</span>'
        f'<span class="lc-badge {badge_css}">{badge_label}</span>'
        f'</div>'
    )


def _regime_corr_info(corr_val):
    if math.isnan(corr_val): return '\u2014', '#555', 'badge-neutral', 'NO DATA'
    if corr_val >= 0.6:  return f'{corr_val:+.3f}', '#00d4aa', 'badge-success',  'INTACT'
    if corr_val >= 0.3:  return f'{corr_val:+.3f}', '#888888', 'badge-neutral',  'WEAKENING'
    if corr_val >= -0.3: return f'{corr_val:+.3f}', '#ff4444', 'badge-danger',   'BROKEN'
    return f'{corr_val:+.3f}', '#f0a500', 'badge-warning', 'INVERTED'


def inject_landing_page(html_content, _re, df=None):
    """Inject a full-screen landing/overview page before the first pair card.
    Always rebuilds with fresh data so prices/signals stay current.
    """
    # Remove any existing landing div so we can inject a fresh one with current data
    # Match the full landing block: from <!-- LANDING PAGE --> to the closing </div> + blank line
    html_content = _re.sub(
        r'<!-- LANDING PAGE -->\n<div id="landing">[\s\S]*?<div class="(?:lp-nav-hint|brand-footer)">[\s\S]*?</div>\n</div>\n+',
        '',
        html_content,
    )

    try:
        if df is None:
            df = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)
        if df.empty:
            print('  WARN [inject_landing_page]: CSV is empty — landing page skipped')
            return html_content
        row = df.iloc[-1]
        last_date = df.index[-1]
        date_str  = last_date.strftime('%d %b %Y')
        # IN 10Y freshness
        in10y_date_str = "n/a"
        if "IN_10Y" in df.columns:
            in10y_valid = df["IN_10Y"].dropna()
            if len(in10y_valid) > 0:
                in10y_date_str = in10y_valid.index[-1].strftime('%d %b %Y')
        # COT freshness — cutoff = Tuesday snapshot, published = Friday (+3 days)
        cot_cutoff_str    = "n/a"
        cot_published_str = "n/a"
        try:
            cot_raw           = pd.read_csv('data/cot_latest.csv', index_col=0, parse_dates=True)
            cot_last          = cot_raw.index[-1]
            cot_cutoff_str    = cot_last.strftime('%d %b %Y')
            cot_published_str = (cot_last + pd.Timedelta(days=3)).strftime('%d %b %Y')
        except Exception:
            pass
    except Exception:
        return html_content

    def _g(col, default=float('nan')):
        v = row.get(col, default)
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def _chg_span(pct, big=False):
        if math.isnan(pct): return '\u2014'
        color = '#00d4aa' if pct >= 0 else '#ff4444'
        sign  = '+' if pct >= 0 else ''
        sz    = '14px' if big else '11px'
        return f'<span style="color:{color};font-size:{sz}">{sign}{pct:.2f}%</span>'

    def _price_fmt(col, decimals=4):
        v = _g(col)
        if math.isnan(v): return '\u2014'
        return f'{v:.{decimals}f}'

    def _cot_badge(pct):
        if math.isnan(pct): return '\u2014', 'badge-neutral'
        if pct >= 90: return f'{pct:.0f}th %ile', 'badge-danger'
        if pct >= 75: return f'{pct:.0f}th %ile', 'badge-warning'
        if pct <= 25: return f'{pct:.0f}th %ile', 'badge-danger'
        return f'{pct:.0f}th %ile', 'badge-neutral'

    def _vol_badge(pct):
        if math.isnan(pct): return '\u2014', 'badge-neutral', 'NORMAL'
        if pct >= 90: return f'{pct:.0f}th %ile', 'badge-danger', 'EXTREME'
        if pct >= 75: return f'{pct:.0f}th %ile', 'badge-warning', 'ELEVATED'
        return f'{pct:.0f}th %ile', 'badge-neutral', 'NORMAL'

    # --- EUR/USD mini-card ---
    eur_price       = _price_fmt('EURUSD', 4)
    eur_1d          = _chg_span(_g('EURUSD_chg_1D'), big=True)
    eur_12m         = _chg_span(_g('EURUSD_chg_12M'))
    eur_sp10        = _g('US_DE_10Y_spread')
    eur_sp10_str    = f'{eur_sp10:.2f}%' if not math.isnan(eur_sp10) else '\u2014'
    eur_sp10_dir    = '\u2193' if _g('US_DE_10Y_spread_chg_1W') < 0 else '\u2191'
    eur_sp10_col    = '#00d4aa' if _g('US_DE_10Y_spread_chg_1W') < 0 else '#ff4444'
    eur_lev_pct     = _g('EUR_lev_percentile', float('nan'))
    eur_lev_str, eur_lev_bdg = _cot_badge(eur_lev_pct)
    eur_vol_pct     = _g('EURUSD_vol_pct', float('nan'))
    eur_vol30       = _g('EURUSD_vol30', float('nan'))
    eur_vol_str     = f'{eur_vol30:.1f}%' if not math.isnan(eur_vol30) else '\u2014'
    eur_vol_pctile, eur_vol_bdg, eur_vol_lbl = _vol_badge(eur_vol_pct) if not math.isnan(eur_vol_pct) else ('\u2014', 'badge-neutral', 'NORMAL')
    eur_corr        = _g('EURUSD_spread_corr_60d', float('nan'))
    eur_corr_str, eur_corr_col, eur_corr_bdg, eur_corr_lbl = _regime_corr_info(eur_corr)
    eur_oil_corr    = _g('oil_eurusd_corr_60d', float('nan'))
    eur_oil_lbl, _ = _oil_corr_label(eur_oil_corr, 'EURUSD') if not math.isnan(eur_oil_corr) else ('NO DATA', '')
    eur_oil_col     = '#ff4444' if eur_oil_lbl == 'OIL DIVERGENCE' else '#00d4aa' if eur_oil_lbl == 'HIGH' else '#888'
    eur_oil_bdg     = 'badge-danger' if eur_oil_lbl == 'OIL DIVERGENCE' else 'badge-success' if eur_oil_lbl == 'HIGH' else 'badge-neutral'
    eur_dxy_corr    = _g('dxy_eurusd_corr_60d', float('nan'))
    eur_dxy_lbl, _ = _dxy_corr_label(eur_dxy_corr, 'EURUSD') if not math.isnan(eur_dxy_corr) else ('NO DATA', '')
    eur_dxy_col     = '#4da6ff' if eur_dxy_lbl == 'DOLLAR REGIME' else '#00d4aa' if 'SPECIFIC' in eur_dxy_lbl else '#888'
    eur_dxy_bdg     = 'badge-info' if eur_dxy_lbl == 'DOLLAR REGIME' else 'badge-success' if 'SPECIFIC' in eur_dxy_lbl else 'badge-neutral'

    # --- USD/JPY mini-card ---
    jpy_price       = _price_fmt('USDJPY', 2)
    jpy_1d          = _chg_span(_g('USDJPY_chg_1D'), big=True)
    jpy_12m         = _chg_span(_g('USDJPY_chg_12M'))
    jpy_sp10        = _g('US_JP_10Y_spread')
    jpy_sp10_str    = f'{jpy_sp10:.2f}%' if not math.isnan(jpy_sp10) else '\u2014'
    jpy_sp10_dir    = '\u2193' if _g('US_JP_10Y_spread_chg_1W') < 0 else '\u2191'
    jpy_sp10_col    = '#00d4aa' if _g('US_JP_10Y_spread_chg_1W') < 0 else '#ff4444'
    jpy_lev_pct     = _g('JPY_lev_percentile', float('nan'))
    jpy_lev_str, jpy_lev_bdg = _cot_badge(jpy_lev_pct)
    jpy_vol_pct     = _g('USDJPY_vol_pct', float('nan'))
    jpy_vol30       = _g('USDJPY_vol30', float('nan'))
    jpy_vol_str     = f'{jpy_vol30:.1f}%' if not math.isnan(jpy_vol30) else '\u2014'
    jpy_vol_pctile, jpy_vol_bdg, jpy_vol_lbl = _vol_badge(jpy_vol_pct) if not math.isnan(jpy_vol_pct) else ('\u2014', 'badge-neutral', 'NORMAL')
    jpy_corr        = _g('USDJPY_spread_corr_60d', float('nan'))
    jpy_corr_str, jpy_corr_col, jpy_corr_bdg, jpy_corr_lbl = _regime_corr_info(jpy_corr)
    jpy_oil_corr    = _g('oil_usdjpy_corr_60d', float('nan'))
    jpy_oil_lbl, _ = _oil_corr_label(jpy_oil_corr, 'USDJPY') if not math.isnan(jpy_oil_corr) else ('NO DATA', '')
    jpy_oil_col     = '#ff4444' if jpy_oil_lbl == 'OIL DIVERGENCE' else '#00d4aa' if jpy_oil_lbl == 'HIGH' else '#888'
    jpy_oil_bdg     = 'badge-danger' if jpy_oil_lbl == 'OIL DIVERGENCE' else 'badge-success' if jpy_oil_lbl == 'HIGH' else 'badge-neutral'
    jpy_dxy_corr    = _g('dxy_usdjpy_corr_60d', float('nan'))
    jpy_dxy_lbl, _ = _dxy_corr_label(jpy_dxy_corr, 'USDJPY') if not math.isnan(jpy_dxy_corr) else ('NO DATA', '')
    jpy_dxy_col     = '#4da6ff' if jpy_dxy_lbl == 'DOLLAR REGIME' else '#00d4aa' if 'SPECIFIC' in jpy_dxy_lbl else '#888'
    jpy_dxy_bdg     = 'badge-info' if jpy_dxy_lbl == 'DOLLAR REGIME' else 'badge-success' if 'SPECIFIC' in jpy_dxy_lbl else 'badge-neutral'

    # --- USD/INR mini-card ---
    inr_price       = _price_fmt('USDINR', 2)
    inr_1d          = _chg_span(_g('USDINR_chg_1D'), big=True)
    inr_12m         = _chg_span(_g('USDINR_chg_12M'))
    inr_sp10        = _g('US_IN_10Y_spread')
    inr_sp10_str    = f'{inr_sp10:.2f}%' if not math.isnan(inr_sp10) else '\u2014'
    inr_sp10_dir    = '\u2193' if _g('US_IN_10Y_spread_chg_1W') < 0 else '\u2191'
    inr_sp10_col    = '#00d4aa' if _g('US_IN_10Y_spread_chg_1W') < 0 else '#ff4444'
    inr_oil_corr    = _g('oil_inr_corr_60d', float('nan'))
    inr_oil_lbl, _ = _oil_corr_label(inr_oil_corr, 'USDINR') if not math.isnan(inr_oil_corr) else ('NO DATA', '')
    inr_oil_col     = '#ff4444' if inr_oil_lbl == 'OIL DIVERGENCE' else '#00d4aa' if inr_oil_lbl == 'HIGH' else '#888'
    inr_oil_bdg     = 'badge-danger' if inr_oil_lbl == 'OIL DIVERGENCE' else 'badge-success' if inr_oil_lbl == 'HIGH' else 'badge-neutral'
    inr_dxy_corr    = _g('dxy_inr_corr_60d', float('nan'))
    inr_dxy_lbl, _ = _dxy_corr_label(inr_dxy_corr, 'USDINR') if not math.isnan(inr_dxy_corr) else ('NO DATA', '')
    inr_dxy_col     = '#4da6ff' if inr_dxy_lbl == 'DOLLAR REGIME' else '#00d4aa' if 'SPECIFIC' in inr_dxy_lbl else '#888'
    inr_dxy_bdg     = 'badge-info' if inr_dxy_lbl == 'DOLLAR REGIME' else 'badge-success' if 'SPECIFIC' in inr_dxy_lbl else 'badge-neutral'
    inr_vol_pct     = _g('USDINR_vol_pct', float('nan'))
    inr_vol30       = _g('USDINR_vol30', float('nan'))
    inr_vol_str     = f'{inr_vol30:.1f}%' if not math.isnan(inr_vol30) else '\u2014'
    inr_vol_pctile, inr_vol_bdg, inr_vol_lbl = _vol_badge(inr_vol_pct) if not math.isnan(inr_vol_pct) else ('\u2014', 'badge-neutral', 'NORMAL')

    # --- Cross-asset ticker bar ---
    dxy_val        = _g('DXY')
    brent_val      = _g('Brent')
    gold_val       = _g('Gold')
    dxy_str        = f'{dxy_val:.2f}' if not math.isnan(dxy_val) else '\u2014'
    brent_str      = f'${brent_val:.2f}' if not math.isnan(brent_val) else '\u2014'
    gold_str       = f'${gold_val:,.0f}' if not math.isnan(gold_val) else '\u2014'

    def _ticker_item(label, price, chg_col, pair_color=None, extra_class=''):
        chg = _g(chg_col)
        price_style = f' style="color:{pair_color}"' if pair_color else ''
        css_cls = ('lp-ticker-item ' + extra_class).strip() if extra_class else 'lp-ticker-item'
        return (
            f'<div class="{css_cls}">'
            f'<span class="lp-ticker-label">{label}</span>'
            f'<span class="lp-ticker-price"{price_style}>{price}</span>'
            f'{_chg_span(chg)}'
            f'</div>'
        )

    ticker_html = (
        _ticker_item('DXY', dxy_str, 'DXY_chg_1D') +
        _ticker_item('EUR/USD', eur_price, 'EURUSD_chg_1D', pair_color='#4da6ff') +
        _ticker_item('USD/JPY', jpy_price, 'USDJPY_chg_1D', pair_color='#ff9944') +
        _ticker_item('USD/INR', inr_price, 'USDINR_chg_1D', pair_color='#e74c3c') +
        _ticker_item('Brent', brent_str, 'Brent_chg_1D', extra_class='lp-ticker-item--cross') +
        _ticker_item('Gold', gold_str, 'Gold_chg_1D', extra_class='lp-ticker-item--cross')
    )

    def _pair_card(pair_id, color, display, price_str, chg_1d, chg_12m,
                   spread_str, spread_dir, spread_col,
                   rows_html, spread_label='Rate Spread (10Y)'):
        return f'''<div class="lp-pair-card">
          <div class="lp-card-header" style="border-top:3px solid {color}">
            <span class="lp-pair-label" style="color:{color}">{display}</span>
            <div class="lp-price-block">
              <span class="lp-price">{price_str}</span>
              <span class="lp-1d">{chg_1d}</span>
              <span class="lp-12m-label">12M</span>
              <span class="lp-12m">{chg_12m}</span>
            </div>
          </div>
          <div class="lp-spread-row">
            <span class="lp-spread-label">{spread_label}</span>
            <span class="lp-spread-val" style="color:{spread_col}">{spread_dir} {spread_str}</span>
          </div>
          <div class="lp-signals">{rows_html}</div>
          <a class="lp-drilldown" href="#{pair_id}">View Detail \u2192</a>
        </div>'''

    eur_rows = (
        _mini_signal_row('Lev Money', eur_lev_str, '#fff', f'{eur_lev_pct:.0f}th pct', eur_lev_bdg) +
        _mini_signal_row('Vol 30D', eur_vol_str, '#fff', eur_vol_lbl, eur_vol_bdg) +
        _mini_signal_row('Regime Corr', eur_corr_str, eur_corr_col, eur_corr_lbl, eur_corr_bdg) +
        _mini_signal_row('Oil Corr 60D', f'{eur_oil_corr:+.3f}' if not math.isnan(eur_oil_corr) else '\u2014', eur_oil_col, eur_oil_lbl, eur_oil_bdg) +
        _mini_signal_row('DXY Corr 60D', f'{eur_dxy_corr:+.3f}' if not math.isnan(eur_dxy_corr) else '\u2014', eur_dxy_col, eur_dxy_lbl, eur_dxy_bdg)
    ) if not math.isnan(eur_lev_pct) else (
        _mini_signal_row('Regime Corr', eur_corr_str, eur_corr_col, eur_corr_lbl, eur_corr_bdg) +
        _mini_signal_row('Oil Corr 60D', f'{eur_oil_corr:+.3f}' if not math.isnan(eur_oil_corr) else '\u2014', eur_oil_col, eur_oil_lbl, eur_oil_bdg) +
        _mini_signal_row('DXY Corr 60D', f'{eur_dxy_corr:+.3f}' if not math.isnan(eur_dxy_corr) else '\u2014', eur_dxy_col, eur_dxy_lbl, eur_dxy_bdg)
    )

    jpy_rows = (
        _mini_signal_row('Lev Money', jpy_lev_str, '#fff', f'{jpy_lev_pct:.0f}th pct', jpy_lev_bdg) +
        _mini_signal_row('Vol 30D', jpy_vol_str, '#fff', jpy_vol_lbl, jpy_vol_bdg) +
        _mini_signal_row('Regime Corr', jpy_corr_str, jpy_corr_col, jpy_corr_lbl, jpy_corr_bdg) +
        _mini_signal_row('Oil Corr 60D', f'{jpy_oil_corr:+.3f}' if not math.isnan(jpy_oil_corr) else '\u2014', jpy_oil_col, jpy_oil_lbl, jpy_oil_bdg) +
        _mini_signal_row('DXY Corr 60D', f'{jpy_dxy_corr:+.3f}' if not math.isnan(jpy_dxy_corr) else '\u2014', jpy_dxy_col, jpy_dxy_lbl, jpy_dxy_bdg)
    ) if not math.isnan(jpy_lev_pct) else (
        _mini_signal_row('Regime Corr', jpy_corr_str, jpy_corr_col, jpy_corr_lbl, jpy_corr_bdg) +
        _mini_signal_row('Oil Corr 60D', f'{jpy_oil_corr:+.3f}' if not math.isnan(jpy_oil_corr) else '\u2014', jpy_oil_col, jpy_oil_lbl, jpy_oil_bdg) +
        _mini_signal_row('DXY Corr 60D', f'{jpy_dxy_corr:+.3f}' if not math.isnan(jpy_dxy_corr) else '\u2014', jpy_dxy_col, jpy_dxy_lbl, jpy_dxy_bdg)
    )

    inr_rows = (
        _mini_signal_row('Vol 30D', inr_vol_str, '#fff', inr_vol_lbl, inr_vol_bdg) +
        _mini_signal_row('Oil Corr 60D', f'{inr_oil_corr:+.3f}' if not math.isnan(inr_oil_corr) else '\u2014', inr_oil_col, inr_oil_lbl, inr_oil_bdg) +
        _mini_signal_row('DXY Corr 60D', f'{inr_dxy_corr:+.3f}' if not math.isnan(inr_dxy_corr) else '\u2014', inr_dxy_col, inr_dxy_lbl, inr_dxy_bdg)
    )

    eur_card = _pair_card('card-eurusd', '#4da6ff', 'EUR/USD', eur_price, eur_1d, eur_12m,
                          eur_sp10_str, eur_sp10_dir, eur_sp10_col, eur_rows)
    jpy_card = _pair_card('card-usdjpy', '#ff9944', 'USD/JPY', jpy_price, jpy_1d, jpy_12m,
                          jpy_sp10_str, jpy_sp10_dir, jpy_sp10_col, jpy_rows)
    inr_card = _pair_card('card-usdinr', '#e74c3c', 'USD/INR', inr_price, inr_1d, inr_12m,
                          inr_sp10_str, inr_sp10_dir, inr_sp10_col, inr_rows,
                          spread_label='US 2Y\u2013IN 10Y (cross)')

    wordmark_src = embed_image(os.path.join('logos', 'wordmark without bg.png'))
    wordmark_img = f'<img src="{wordmark_src}" class="lp-wordmark" style="height:108px;width:auto;display:block;margin-bottom:20px;" alt="FX Regime Lab">' if wordmark_src else ''

    # --- Macro event strip (Phase 10) ---
    upcoming_event = get_upcoming_event()
    if upcoming_event is not None:
        days_away = upcoming_event['days_away']
        evt_name  = upcoming_event['event']
        evt_date  = upcoming_event['date']
        if days_away == 0:
            day_str = 'TODAY'
        elif days_away == 1:
            day_str = 'TOMORROW'
        else:
            day_str = f'in {days_away} days'
        strip_color = '#ff4444' if days_away <= 1 else '#f0a500'
        macro_strip_html = (
            f'<div class="lp-macro-strip" style="background:{strip_color}11;border:1px solid {strip_color}44;'
            f'border-radius:4px;padding:6px 14px;margin-bottom:8px;font-size:0.75rem;'
            f'color:{strip_color};letter-spacing:0.04em;text-align:center;">'
            f'&#9888; MACRO EVENT {day_str}: {evt_name} &nbsp;&mdash;&nbsp; {evt_date}'
            f'</div>'
        )
    else:
        macro_strip_html = ''

    from config import TODAY_FMT
    landing_html = f'''<!-- LANDING PAGE -->
<div id="landing">
  <div class="lp-header">
    <div class="lp-title-block">
      <div class="lp-logo-row">{wordmark_img}</div>
      <div class="lp-framework-label">G10 FX Regime Detection Framework</div>
      <div class="lp-morning-brief">Morning Brief</div>
      <div class="lp-date">{TODAY_FMT}</div>
      <div class="lp-meta">FX as of: {date_str} &nbsp;&nbsp;|&nbsp;&nbsp; IN 10Y as of: {in10y_date_str} &nbsp;&nbsp;|&nbsp;&nbsp; COT cutoff: {cot_cutoff_str} (pub&apos;d: {cot_published_str}) &nbsp;&nbsp;|&nbsp;&nbsp; run: {pd.Timestamp.now().strftime("%d %b %Y %H:%M")} IST</div>
    </div>
    <a href="#workspace-snap" class="lp-ws-btn">WORKSPACE &#9654;</a>
  </div>
  {macro_strip_html}<div class="lp-ticker-bar">{ticker_html}</div>
  <div class="lp-grid">
    {eur_card}
    {jpy_card}
    {inr_card}
  </div>
  <div class="brand-footer">FX Regime Lab &middot; fxregimelab.substack.com &middot; Updated daily</div>
</div>

'''

    # Insert before <div class="content">
    html_content = html_content.replace('<div class="content">', landing_html + '<div class="content">', 1)

    # Hide the old globalbar and header since landing page replaces them
    html_content = html_content.replace(
        '<!-- GLOBAL BAR -->',
        '<!-- GLOBAL BAR (superseded by landing page) -->',
    )
    html_content = _re.sub(
        r'(<!-- GLOBAL BAR \(superseded by landing page\) -->)\s*<div class="globalbar">[\s\S]*?</div>',
        r'\1',
        html_content,
    )
    html_content = html_content.replace(
        '<!-- HEADER -->',
        '<!-- HEADER (superseded by landing page) -->',
    )
    html_content = _re.sub(
        r'(<!-- HEADER \(superseded by landing page\) -->)\s*<div class="header">[\s\S]*?</div>\s*</div>',
        r'\1',
        html_content,
    )
    return html_content


def inject_global_css(html_content):
    """Link static/styles.css in <head> (idempotent). Handles both briefs/ and root paths."""
    if 'static/styles.css' in html_content:
        return html_content
    html_content = html_content.replace(
        '</head>',
        '<link rel="stylesheet" href="../static/styles.css">\n</head>',
        1,
    )
    return html_content


def inject_bottom_nav(html_content):
    """Inject fixed bottom navigation strip (idempotent — HTML only; CSS is in static/styles.css)."""
    # Always fix stale HOME href from prior sessions
    html_content = html_content.replace('href="#landing-page"', 'href="#landing"')
    if 'id="pair-nav"' in html_content:
        return html_content
    nav_html = '''<nav id="pair-nav">
  <a href="#landing">OVERVIEW</a>
  <a href="#card-eurusd">EUR/USD</a>
  <a href="#card-usdjpy">USD/JPY</a>
  <a href="#card-usdinr">USD/INR</a>
  <a href="#workspace-snap">WORKSPACE</a>
</nav>'''
    html_content = html_content.replace('</body>\n</html>', nav_html + '\n</body>\n</html>')
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
    # Post-process: make the plotly-graph-div fill its iframe so charts fill the container
    import re as _rcc
    with open(chart_file, 'r', encoding='utf-8') as _cf:
        _ch = _cf.read()
    _ch = _rcc.sub(
        r'style="height:\d+px; width:100%;"',
        'style="height:100%; width:100%;"',
        _ch,
    )
    if '<head>' in _ch and 'html,body{height:100%' not in _ch:
        _ch = _ch.replace(
            '<head>',
            '<head><style>html,body{height:100%;margin:0;padding:0;overflow:hidden;background:#0a0e1a}</style>',
            1,
        )
    with open(chart_file, 'w', encoding='utf-8') as _cf:
        _cf.write(_ch)
    # brief lives in briefs/ so path to charts/ is ../charts/
    # height:100% fills the absolute-positioned chart-pane which fills chart-display-area
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
        _raw = result
        # Post-process Plotly-generated HTML so the graph div fills its iframe
        if 'plotly-graph-div' in _raw:
            import re as _rrr
            _raw = _rrr.sub(
                r'style="height:\d+px; width:100%;"',
                'style="height:100%; width:100%;"',
                _raw,
            )
            if '<head>' in _raw and 'html,body{height:100%' not in _raw:
                _raw = _raw.replace(
                    '<head>',
                    '<head><style>html,body{height:100%;margin:0;padding:0;overflow:hidden;background:#0a0e1a}</style>',
                    1,
                )
        with open(chart_file, 'w', encoding='utf-8') as _fh:
            _fh.write(_raw)
        return (
            f'<iframe src="../{chart_file}" '
            f'style="width:100%;height:100%;border:none;display:block;" '
            f'loading="eager" scrolling="no"></iframe>'
        )
    return fig_to_iframe(result, pair_str, pane_idx, height)


def _build_chart_divs(months: int = 12) -> dict:
    """Build all chart iframes for the given data window (months)."""
    set_chart_months(months)
    chart_divs = {
        (pair, pane): _builder_to_iframe(builder, pair, pane, height)
        for (pair, pane), (builder, pair, height) in CHART_REGISTRY.items()
    }
    _gw_html = build_global_workspace_html()
    with open(f'{CHARTS_DIR}/global_workspace.html', 'w', encoding='utf-8') as _fh:
        _fh.write(_gw_html)
    print('Generated: charts/global_workspace.html')
    return chart_divs

# ============================================================================
# Load brief data from existing generated brief
# ============================================================================
import shutil

def load_latest_brief_data():
    """Load the most recent HTML brief as the base template."""
    brief_files = sorted(glob.glob('briefs/brief_*.html'))
    if brief_files:
        return brief_files[-1]
    # Fallback for GitHub Actions: briefs/ is gitignored so index.html
    # (the previously deployed brief) is the only available template.
    if os.path.exists('index.html'):
        print("No briefs found in briefs/ — using index.html as template")
        return 'index.html'
    return None

def generate_html_brief(months: int = 12):
    """Generate complete HTML brief with charts embedded as iframes."""
    brief_file = load_latest_brief_data()
    if not brief_file:
        print("No previous brief found. Run morning_brief.py first.")
        return

    with open(brief_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # index.html has iframe paths patched to src="charts/" (repo root);
    # briefs/*.html use src="../charts/" (one level up). Reverse the patch
    # so downstream inject/deploy steps work consistently.
    if brief_file == 'index.html':
        html_content = html_content.replace('src="charts/', 'src="../charts/')

    import re as _re

    # Update <title> tag with today's date (prevents stale title in browser tab)
    html_content = _re.sub(
        r'<title>.*?</title>',
        f'<title>G10 FX Morning Brief \u2014 {TODAY_FMT}</title>',
        html_content,
    )

    # Inject favicon (idempotent — embeds logo as browser tab icon)
    if 'rel="icon"' not in html_content:
        _fav_src = embed_image(os.path.join('logos', 'logo without bg.png'))
        if _fav_src:
            html_content = html_content.replace(
                '</title>',
                f'</title>\n<link rel="icon" type="image/png" href="{_fav_src}">',
                1,
            )

    # ------------------------------------------------------------------
    # 1. Build charts for the requested data window, then inject iframes
    # ------------------------------------------------------------------
    chart_divs = _build_chart_divs(months)
    chart_map = {
        (pair, str(pane)): iframe
        for (pair, pane), iframe in chart_divs.items()
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

    # Load data CSV once — shared across all injection functions
    try:
        _shared_df = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)
    except Exception:
        _shared_df = None

    # ------------------------------------------------------------------
    # 1b. Inject live cross-asset correlation values (Phase 1 & 2)
    # ------------------------------------------------------------------
    html_content = inject_cross_asset_values(html_content, _re, df=_shared_df)

    # ------------------------------------------------------------------
    # 1c. Update globalbar with live prices + colored 1D changes
    # ------------------------------------------------------------------
    html_content = update_globalbar(html_content, _re, df=_shared_df)

    # ------------------------------------------------------------------
    # 1d-pre. Inject live data into all pair card headers + brief-left panels
    # ------------------------------------------------------------------
    html_content = inject_live_card_data(html_content, _re, df=_shared_df)

    # ------------------------------------------------------------------
    # 1d. Inject global CSS link (static/styles.css — landing, brand, nav)
    # ------------------------------------------------------------------
    html_content = inject_global_css(html_content)

    # ------------------------------------------------------------------
    # 1d-period. Stamp active period window on landing page header
    # ------------------------------------------------------------------
    _periods = [('1M', 1), ('3M', 3), ('6M', 6), ('12M', 12)]
    _sel_html = '<div class="period-selector">' + ''.join(
        f'<span class="period-btn{" period-btn--active" if m == months else ""}">{label}</span>'
        for label, m in _periods
    ) + '</div>'
    # Replace stale period-selector (any prior run) or inject fresh after .lp-ws-btn
    if 'class="period-selector"' in html_content:
        html_content = _re.sub(
            r'<div class="period-selector">.*?</div>',
            _sel_html, html_content, count=1, flags=_re.DOTALL,
        )
    else:
        html_content = _re.sub(
            r'(<a[^>]+class="lp-ws-btn"[^>]*>[^<]*</a>)',
            r'\1' + _sel_html,
            html_content, count=1,
        )

    # ------------------------------------------------------------------
    # 1e. Inject fixed bottom nav HTML
    # ------------------------------------------------------------------
    html_content = inject_bottom_nav(html_content)

    # ------------------------------------------------------------------
    # 1f. Strip legacy landing page from prior sessions (idempotent)
    # ------------------------------------------------------------------
    # Strip stale inline CSS blocks from prior brief versions (lp-css, brand-v2, pnav-css).
    # These are now served via static/styles.css — stripping prevents duplicate rules.
    html_content = _re.sub(r'/\* lp-css-v\d+ \*/[\s\S]*?/\* end lp-css \*/', '', html_content, flags=_re.DOTALL)
    html_content = _re.sub(r'/\* brand-v\d+ \*/[\s\S]*?/\* end brand-v\d+ \*/', '', html_content, flags=_re.DOTALL)
    html_content = _re.sub(r'/\* pnav-css-v\d+ \*/[\s\S]*?/\* end pnav-css \*/', '', html_content, flags=_re.DOTALL)
    # Remove old <style id="lp-styles"> block
    html_content = _re.sub(
        r'\n?<style id="lp-styles">[\s\S]*?</style>\n?',
        '',
        html_content,
    )
    # Remove old id="landing-page" block
    html_content = _re.sub(
        r'\n?<!-- LANDING PAGE -->\n<div id="landing-page"[\s\S]*?</div>\n?<!-- MAIN CONTENT -->',
        '\n<!-- MAIN CONTENT -->',
        html_content,
    )
    # Remove orphan header-right div left behind by old globalbar/header stripper.
    # Guard: only run when the old header div is actually present (not when already cleaned).
    # Without the guard, the greedy [\s\S]*? matches INTO the landing page on subsequent runs,
    # partially destroying it and preventing inject_landing_page() from stripping it cleanly.
    if '<!-- HEADER (superseded by landing page) -->\n<div class="header">' in html_content:
        html_content = _re.sub(
            r'<!-- HEADER \(superseded by landing page\) -->[\s\S]*?</div>\s*</div>\s*\n',
            '<!-- HEADER (superseded by landing page) -->\n',
            html_content,
        )
    # Remove old body class="has-landing" (use clean body tag)
    html_content = html_content.replace('<body class="has-landing">', '<body>')
    # Strip any orphan HTML between the superseded-header comment and the real landing marker
    # (handles ticker/grid fragments left behind by prior code generation bugs)
    html_content = _re.sub(
        r'(<!-- HEADER \(superseded by landing page\) -->)\s*[\s\S]*?(<!-- LANDING PAGE -->)',
        r'\1\n\2',
        html_content,
    )

    # ------------------------------------------------------------------
    # 1g. Inject full-screen landing overview page (Page 0)
    # ------------------------------------------------------------------
    html_content = inject_landing_page(html_content, _re, df=_shared_df)

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
        'style="visibility:visible; position:absolute; pointer-events:auto; width:100%; height:100%;"',
    )
    html_content = html_content.replace(
        'style="display:none; width:100%;"',
        'style="visibility:hidden; position:absolute; pointer-events:none; width:100%; height:100%;"',
    )
    # Also normalise any existing brief_template pane styles (idempotent)
    html_content = html_content.replace(
        'style="visibility:visible; position:relative; pointer-events:auto; width:100%;"',
        'style="visibility:visible; position:absolute; pointer-events:auto; width:100%; height:100%;"',
    )
    html_content = html_content.replace(
        'style="visibility:hidden; position:absolute; pointer-events:none; width:100%;"',
        'style="visibility:hidden; position:absolute; pointer-events:none; width:100%; height:100%;"',
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
document.querySelectorAll('.chart-tab').forEach(function(tab) {
  tab.addEventListener('click', function() {
    var pair   = this.dataset.pair;
    var tabIdx = this.dataset.tab;

    document.querySelectorAll('.chart-tab[data-pair="' + pair + '"]')
      .forEach(function(t) { t.classList.remove('active'); });

    document.querySelectorAll('.chart-pane[data-pair="' + pair + '"]')
      .forEach(function(p) {
        p.style.visibility    = 'hidden';
        p.style.position      = 'absolute';
        p.style.pointerEvents = 'none';
      });

    this.classList.add('active');

    var pane = document.querySelector(
      '.chart-pane[data-pair="' + pair + '"][data-pane="' + tabIdx + '"]'
    );
    pane.style.visibility    = 'visible';
    pane.style.position      = 'absolute';
    pane.style.pointerEvents = 'auto';
  });
});

document.querySelectorAll('.regime-toggle').forEach(function(lbl) {
  lbl.addEventListener('click', function() {
    this.closest('.regime-read').classList.toggle('open');
  });
});

// Bottom nav active state via IntersectionObserver
(function() {
  var navLinks = document.querySelectorAll('#pair-nav a');
  var targets  = ['landing', 'card-eurusd', 'card-usdjpy', 'card-usdinr', 'workspace-snap'];
  var io = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) {
      if (e.isIntersecting && e.intersectionRatio >= 0.5) {
        navLinks.forEach(function(a) { a.classList.remove('nav-active'); });
        var link = document.querySelector('#pair-nav a[href="#' + e.target.id + '"]');
        if (link) link.classList.add('nav-active');
      }
    });
  }, {threshold: 0.5});
  targets.forEach(function(id) {
    var el = document.getElementById(id);
    if (el) io.observe(el);
  });
})();
'''

    all_scripts = list(_re.finditer(r'(<script>)(.*?)(</script>)', html_content, _re.DOTALL))
    if all_scripts:
        m = all_scripts[-1]
        html_content = html_content[:m.start(2)] + tab_handler + html_content[m.end(2):]

    # ------------------------------------------------------------------
    # 6. Write output
    # ------------------------------------------------------------------
    os.makedirs('briefs', exist_ok=True)
    output_file = f'briefs/brief_{DATE_SLUG}.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Generated: {output_file}")

if __name__ == '__main__':
    import argparse as _ap
    _parser = _ap.ArgumentParser(description='Generate HTML morning brief')
    _parser.add_argument('--months', type=int, default=12,
                         help='Chart data window in months (default: 12)')
    _args = _parser.parse_args()
    generate_html_brief(months=_args.months)
