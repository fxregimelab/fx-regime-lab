import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from charts.base import _base_layout, _style_axes, _load_and_filter, _add_annotation, get_chart_months
from core.paths import LATEST_WITH_COT_CSV


# ============================================================================
# FUNCTION 1: build_fundamentals_chart(pair)
# ============================================================================

def build_fundamentals_chart(pair):
    """Build fundamentals chart for eurusd, usdjpy, or usdinr."""
    
    # Configuration per pair
    configs = {
        'eurusd': dict(
            price_col='EURUSD',
            price_color='#4da6ff',
            spread_10y='US_DE_10Y_spread',
            spread_2y='US_DE_2Y_spread',
            label_10y='DE 10Y',
            label_2y='DE 2Y',
            subtitle='narrowing = EUR/USD should rise'
        ),
        'usdjpy': dict(
            price_col='USDJPY',
            price_color='#ff9944',
            spread_10y='US_JP_10Y_spread',
            spread_2y='US_JP_2Y_spread',
            label_10y='JP 10Y',
            label_2y='JP 2Y',
            subtitle='narrowing = USD/JPY should fall'
        ),
        'usdinr': dict(
            price_col='USDINR',
            price_color='#e74c3c',
            spread_10y='US_IN_10Y_spread',
            spread_2y='US_IN_policy_spread',
            label_10y='IN 10Y',
            label_2y='IN policy',
            legend_10y='US 2Y \u2013 IN 10Y (cross)',
            legend_2y='US 2Y \u2013 IN Repo Rate',
            subtitle='cross spread: US 2Y vs India rates \u2014 negative = INR strength'
        )
    }
    
    cfg = configs[pair]
    PAIR = pair.upper()
    
    # Load and filter data - use 'd' for filtered data
    d, cutoff, today = _load_and_filter(pair, months=get_chart_months())
    d = d[d[cfg['price_col']].notna()].copy()
    
    # Clean USDINR outliers
    if pair == 'usdinr':
        price_col = cfg['price_col']
        q_low = d[price_col].quantile(0.01)
        q_high = d[price_col].quantile(0.99)
        d = d[(d[price_col] >= q_low) & (d[price_col] <= q_high)]
    
    # Use 2 subplots for all pairs (no correlation)
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.06,
    )
    
    # --- Subplot 1: Price line ---
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d[cfg['price_col']],
            mode='lines',
            line=dict(color=cfg['price_color'], width=1.5),
            name=PAIR,
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.4f}<extra></extra>',
        ),
        row=1, col=1,
    )
    
    # --- Subplot 2: Spread lines ---
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d[cfg['spread_10y']],
            mode='lines',
            line=dict(color='#2980b9', width=1.5),
            name=cfg.get('legend_10y', f"US\u2013{cfg['label_10y']} spread"),
            showlegend=True,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>',
        ),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d[cfg['spread_2y']],
            mode='lines',
            line=dict(color='#e67e22', width=1.5),
            name=cfg.get('legend_2y', f"US\u2013{cfg['label_2y']} spread"),
            showlegend=True,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>',
        ),
        row=2, col=1,
    )
    fig.add_hline(y=0, line_dash='dash', line_color='#333333', line_width=1, 
                  row=2, col=1)
    
    # --- Apply theme ---
    fig.update_layout(**_base_layout(height=400 if pair != 'usdinr' else 360))
    _style_axes(fig)

    # --- Legend: rate differential lines (top-right of spreads panel) ---
    fig.update_layout(
        legend=dict(
            x=0.99, y=0.43,
            xanchor='right', yanchor='top',
            bgcolor='rgba(13,13,13,0.85)',
            bordercolor='#2a2a2a', borderwidth=1,
            font=dict(size=9, color='#cccccc'),
            itemsizing='constant',
            tracegroupgap=1,
        )
    )
    
    # Set x-axis ranges for both subplots
    cutoff_str = cutoff.strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    fig.update_layout(
        xaxis =dict(range=[cutoff_str, today_str], type='date'),
        xaxis2=dict(range=[cutoff_str, today_str], type='date'),
    )
    
    # FIX: Explicit y-axis ranges from actual data
    price_data = d[cfg['price_col']].dropna()
    p_min = float(price_data.min())
    p_max = float(price_data.max())
    p_pad = (p_max - p_min) * 0.08
    
    spread1 = d[cfg['spread_10y']].dropna()
    spread2 = d[cfg['spread_2y']].dropna()
    all_s = pd.concat([spread1, spread2])
    s_min = float(all_s.min())
    s_max = float(all_s.max())
    s_pad = (s_max - s_min) * 0.15
    
    fig.update_yaxes(range=[p_min - p_pad, p_max + p_pad], row=1, col=1)
    fig.update_yaxes(range=[s_min - s_pad, s_max + s_pad], row=2, col=1)

    # --- Phase 11a: 200-day moving average on price panel ---
    try:
        df_full = pd.read_csv(LATEST_WITH_COT_CSV, index_col=0, parse_dates=True)
        df_full.index = pd.to_datetime(df_full.index, utc=False).tz_localize(None).normalize()
        df_full = df_full.sort_index()
        df_full = df_full[~df_full.index.duplicated(keep='last')]
        price_full = df_full[cfg['price_col']].dropna()
        ma200_full = price_full.rolling(200, min_periods=100).mean()
        # filter to display window
        ma200_display = ma200_full[ma200_full.index >= cutoff].dropna()
        if len(ma200_display) > 0:
            ma200_x = ma200_display.index.strftime('%Y-%m-%d').tolist()
            fig.add_trace(
                go.Scatter(
                    x=ma200_x,
                    y=ma200_display.values.tolist(),
                    mode='lines',
                    line=dict(color='#444444', width=1, dash='dash'),
                    name='200D MA',
                    showlegend=False,
                    hovertemplate='%{x|%d %b %Y}<br>200D MA: %{y:.4f}<extra></extra>',
                ),
                row=1, col=1,
            )
    except Exception:
        pass  # 200D MA is optional; chart still works without it

    # --- Phase 11b: Key support/resistance levels on price panel ---
    key_level_cols = {
        'S1': ('#00d4aa', 'dash',    'S1'),
        'R1': ('#ff4444', 'dash',    'R1'),
        'S2': ('#00d4aa', 'dot',     'S2'),
        'R2': ('#ff4444', 'dot',     'R2'),
    }
    y_lo = p_min - p_pad
    y_hi = p_max + p_pad
    for suffix, (kl_color, kl_dash, kl_label) in key_level_cols.items():
        col_name = f'{PAIR}_{suffix}'
        if col_name not in d.columns:
            continue
        level_val = d[col_name].dropna()
        if len(level_val) == 0:
            continue
        kl = float(level_val.iloc[-1])
        if not (y_lo <= kl <= y_hi):
            continue  # outside visible range — skip
        fig.add_hline(
            y=kl,
            line_dash=kl_dash,
            line_color=kl_color,
            line_width=0.8,
            opacity=0.5,
            row=1, col=1,
        )
        # label annotation at right edge
        fig.add_annotation(
            x=d.index[-1],
            y=kl,
            text=f'  {kl_label}',
            xref='x',
            yref='y',
            xanchor='left',
            showarrow=False,
            font=dict(size=8, color=kl_color),
        )

    # --- Phase 11c: Yield-curve inversion shading on spread panel ---
    if 'US_curve' in d.columns:
        us_curve = d['US_curve'].ffill()
        inverted = (us_curve < 0)
        if inverted.any():
            dates = pd.to_datetime(d.index)
            in_inv = False
            inv_start = None
            for i, (dt, is_inv) in enumerate(zip(dates, inverted)):
                if is_inv and not in_inv:
                    inv_start = dt
                    in_inv = True
                elif not is_inv and in_inv:
                    fig.add_vrect(
                        x0=inv_start.strftime('%Y-%m-%d'),
                        x1=dt.strftime('%Y-%m-%d'),
                        fillcolor='rgba(255, 80, 0, 0.04)',
                        line_width=0,
                        row=2, col=1,
                    )
                    in_inv = False
            if in_inv and inv_start is not None:
                fig.add_vrect(
                    x0=inv_start.strftime('%Y-%m-%d'),
                    x1=d.index[-1],
                    fillcolor='rgba(255, 80, 0, 0.04)',
                    line_width=0,
                    row=2, col=1,
                )
    
    # --- Inline end-labels ---
    if d.empty:
        return fig
    last_x = d.index[-1]
    inline_annotations = []
    
    # Row 1: Price value
    inline_annotations.append(dict(
        x=last_x,
        y=d[cfg['price_col']].iloc[-1],
        text=f"  {d[cfg['price_col']].iloc[-1]:.4f}",
        xref='x', yref='y',
        xanchor='left', showarrow=False,
        font=dict(size=9, color=cfg['price_color']),
    ))
    
    # Row 2: Spread labels
    inline_annotations.append(dict(
        x=last_x,
        y=d[cfg['spread_10y']].iloc[-1],
        text=f"  {cfg['label_10y']}",
        xref='x2', yref='y2',
        xanchor='left', showarrow=False,
        font=dict(size=9, color='#2980b9'),
    ))
    inline_annotations.append(dict(
        x=last_x,
        y=d[cfg['spread_2y']].iloc[-1],
        text=f"  {cfg['label_2y']}",
        xref='x2', yref='y2',
        xanchor='left', showarrow=False,
        font=dict(size=9, color='#e67e22'),
    ))
    
    # --- Panel title annotations ---
    panel_titles = [
        dict(
            text=f"{PAIR} PRICE",
            x=0.01, y=1.0,
            xref='paper', yref='paper',
            xanchor='left', yanchor='top',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
        dict(
            text=f"RATE DIFFERENTIALS (pp) — {cfg['subtitle']}",
            x=0.01, y=0.55,
            xref='paper', yref='paper',
            xanchor='left', yanchor='top',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
    ]
    
    fig.update_layout(
        annotations=(fig.layout.annotations or ()) + tuple(inline_annotations) + tuple(panel_titles)
    )
    
    return fig


# ============================================================================
# FUNCTION 2: build_positioning_chart(pair)
# ============================================================================

def build_positioning_chart(pair):
    """Build positioning chart for eurusd or usdjpy only."""
    
    if pair == 'usdinr':
        raise ValueError("build_positioning_chart() does not support 'usdinr'")
    
    # Configuration
    configs = {
        'eurusd': dict(
            net_col='EUR_lev_net',
            pct_col='EUR_lev_percentile',
            am_net_col='EUR_assetmgr_net',
            am_pct_col='EUR_assetmgr_percentile',
            color_pair='#4da6ff'
        ),
        'usdjpy': dict(
            net_col='JPY_lev_net',
            pct_col='JPY_lev_percentile',
            am_net_col='JPY_assetmgr_net',
            am_pct_col='JPY_assetmgr_percentile',
            color_pair='#ff9944'
        )
    }
    
    cfg = configs[pair]
    
    # Load data
    d, cutoff, today = _load_and_filter(pair, months=get_chart_months())
    d = d[d[cfg['net_col']].notna()]
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.5],
        vertical_spacing=0.08,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
    )
    
    # --- Subplot 1: Leveraged Money ---
    # Bar chart for net position
    leveraged_bar_colors = ['#00d4aa' if v >= 0 else '#ff4444' 
                            for v in d[cfg['net_col']]]
    
    fig.add_trace(
        go.Bar(
            x=d.index,
            y=d[cfg['net_col']],
            marker_color=leveraged_bar_colors,
            marker_opacity=0.7,
            marker_line_width=0.5,
            marker_line_color='#0d0d0d',
            width=3.5 * 24 * 3600 * 1000,  # 3.5 days in milliseconds
            name='Leveraged Net',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>Net: %{y:+,.0f} contracts<extra></extra>',
        ),
        row=1, col=1, secondary_y=False,
    )
    
    # Percentile line on secondary axis
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d[cfg['pct_col']],
            mode='lines',
            line=dict(color='#ffffff', width=2.5),
            name='Leveraged Pct',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>Percentile: %{y:.0f}th<extra></extra>',
        ),
        row=1, col=1, secondary_y=True,
    )
    
    # Horizontal zones and lines for leveraged money (DIAGNOSTIC 3: reduced opacity 0.07→0.03)
    fig.add_hrect(y0=80, y1=100, fillcolor='rgba(255,68,68,0.03)', 
                  line_width=0, row=1, col=1, secondary_y=True)
    fig.add_hrect(y0=0, y1=20, fillcolor='rgba(0,212,170,0.03)', 
                  line_width=0, row=1, col=1, secondary_y=True)
    fig.add_hline(y=80, line_color='#ff4444', line_dash='dash', line_width=1, 
                  row=1, col=1, secondary_y=True)
    fig.add_hline(y=20, line_color='#00d4aa', line_dash='dash', line_width=1, 
                  row=1, col=1, secondary_y=True)
    fig.add_hline(y=50, line_color='#333333', line_dash='dot', line_width=1, 
                  row=1, col=1, secondary_y=True)
    
    # --- Subplot 2: Asset Manager ---
    am_bar_colors = ['#00d4aa' if v >= 0 else '#ff4444' 
                     for v in d[cfg['am_net_col']]]
    
    fig.add_trace(
        go.Bar(
            x=d.index,
            y=d[cfg['am_net_col']],
            marker_color=am_bar_colors,
            marker_opacity=0.7,
            marker_line_width=0.5,
            marker_line_color='#0d0d0d',
            width=3.5 * 24 * 3600 * 1000,  # 3.5 days in milliseconds
            name='AM Net',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>Net: %{y:+,.0f} contracts<extra></extra>',
        ),
        row=2, col=1, secondary_y=False,
    )
    
    # Percentile line on secondary axis
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d[cfg['am_pct_col']],
            mode='lines',
            line=dict(color='#ffffff', width=2.5),
            name='AM Pct',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>Percentile: %{y:.0f}th<extra></extra>',
        ),
        row=2, col=1, secondary_y=True,
    )
    
    # Horizontal zones and lines for asset manager (DIAGNOSTIC 3: reduced opacity 0.07→0.03)
    fig.add_hrect(y0=80, y1=100, fillcolor='rgba(255,68,68,0.03)', 
                  line_width=0, row=2, col=1, secondary_y=True)
    fig.add_hrect(y0=0, y1=20, fillcolor='rgba(0,212,170,0.03)', 
                  line_width=0, row=2, col=1, secondary_y=True)
    fig.add_hline(y=80, line_color='#ff4444', line_dash='dash', line_width=1, 
                  row=2, col=1, secondary_y=True)
    fig.add_hline(y=20, line_color='#00d4aa', line_dash='dash', line_width=1, 
                  row=2, col=1, secondary_y=True)
    fig.add_hline(y=50, line_color='#333333', line_dash='dot', line_width=1, 
                  row=2, col=1, secondary_y=True)

    # --- Legend proxy traces (no real data — for legend key only) ---
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(symbol='square', size=9, color='#00d4aa'),
        name='Net Long (contracts)', showlegend=True,
    ), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(symbol='square', size=9, color='#ff4444'),
        name='Net Short (contracts)', showlegend=True,
    ), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='lines',
        line=dict(color='#ffffff', width=2),
        name='Pct Rank (0\u2013100)', showlegend=True,
    ), row=1, col=1, secondary_y=True)
    
    # --- Apply theme ---
    fig.update_layout(**_base_layout(height=480))
    _style_axes(fig)

    # --- Legend: bottom-left to avoid top-right regime stamp ---
    fig.update_layout(
        legend=dict(
            x=0.01, y=0.01,
            xanchor='left', yanchor='bottom',
            bgcolor='rgba(13,13,13,0.85)',
            bordercolor='#2a2a2a', borderwidth=1,
            font=dict(size=9, color='#cccccc'),
            itemsizing='constant',
            tracegroupgap=1,
        )
    )
    
    # Set x-axis ranges for both subplots
    cutoff_str = cutoff.strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    fig.update_layout(
        xaxis =dict(range=[cutoff_str, today_str], type='date'),
        xaxis2=dict(range=[cutoff_str, today_str], type='date'),
    )
    
    # FIX: Set y-axis ranges
    # Primary axes - let autorange handle bars
    # Secondary axes - set explicit range [0, 100]
    fig.update_yaxes(range=[0, 100], row=1, col=1, secondary_y=True)
    fig.update_yaxes(range=[0, 100], row=2, col=1, secondary_y=True)
    fig.update_yaxes(autorange=True, row=1, col=1, secondary_y=False)
    fig.update_yaxes(autorange=True, row=2, col=1, secondary_y=False)
    
    # --- Annotations ---
    if d.empty:
        return fig
    last_x = d.index[-1]
    
    # Subplot 1: Leveraged Money values
    latest_net_lev = d[cfg['net_col']].iloc[-1]
    latest_pct_lev = d[cfg['pct_col']].iloc[-1]
    
    # Determine colors for leveraged money
    lev_net_color = '#00d4aa' if latest_net_lev >= 0 else '#ff4444'
    lev_pct_color = '#ff4444' if latest_pct_lev >= 80 else ('#00d4aa' if latest_pct_lev <= 20 else '#aaaaaa')
    
    if latest_pct_lev >= 80:
        lev_regime_text = "CROWDED LONG"
        lev_regime_color = '#f0a500'
    elif latest_pct_lev <= 20:
        lev_regime_text = "CROWDED SHORT"
        lev_regime_color = '#e05c5c'
    else:
        lev_regime_text = "NEUTRAL"
        lev_regime_color = '#555555'
    
    # Subplot 2: Asset Manager values
    latest_net_am = d[cfg['am_net_col']].iloc[-1]
    latest_pct_am = d[cfg['am_pct_col']].iloc[-1]
    
    # Determine colors for asset manager
    am_net_color = '#00d4aa' if latest_net_am >= 0 else '#ff4444'
    am_pct_color = '#ff4444' if latest_pct_am >= 80 else ('#00d4aa' if latest_pct_am <= 20 else '#aaaaaa')
    
    if latest_pct_am >= 80:
        am_regime_text = "CROWDED LONG"
        am_regime_color = '#f0a500'
    elif latest_pct_am <= 20:
        am_regime_text = "CROWDED SHORT"
        am_regime_color = '#e05c5c'
    else:
        am_regime_text = "NEUTRAL"
        am_regime_color = '#555555'
    
    inline_annotations = [
        # Leveraged Money - Net value
        dict(
            x=last_x,
            y=latest_net_lev,
            text=f"{latest_net_lev:+,.0f}",
            xref='x', yref='y',
            xanchor='right', yanchor='bottom',
            showarrow=False,
            font=dict(size=10, weight='bold', color=lev_net_color),
        ),
        # Leveraged Money - Percentile
        dict(
            x=last_x,
            y=latest_pct_lev,
            text=f"  {latest_pct_lev:.0f}th pct",
            xref='x', yref='y2',
            xanchor='left',
            showarrow=False,
            font=dict(size=10, color=lev_pct_color),
        ),
        # Leveraged Money - Regime stamp
        dict(
            text=lev_regime_text,
            x=0.98, y=0.92,
            xref='paper', yref='paper',
            xanchor='right',
            showarrow=False,
            font=dict(size=10, weight='bold', color=lev_regime_color),
        ),
        # Asset Manager - Net value
        dict(
            x=last_x,
            y=latest_net_am,
            text=f"{latest_net_am:+,.0f}",
            xref='x2', yref='y3',
            xanchor='right', yanchor='bottom',
            showarrow=False,
            font=dict(size=10, weight='bold', color=am_net_color),
        ),
        # Asset Manager - Percentile
        dict(
            x=last_x,
            y=latest_pct_am,
            text=f"  {latest_pct_am:.0f}th pct",
            xref='x2', yref='y4',
            xanchor='left',
            showarrow=False,
            font=dict(size=10, color=am_pct_color),
        ),
        # Asset Manager - Regime stamp
        dict(
            text=am_regime_text,
            x=0.98, y=0.42,
            xref='paper', yref='paper',
            xanchor='right',
            showarrow=False,
            font=dict(size=10, weight='bold', color=am_regime_color),
        ),
    ]
    
    # --- Panel titles ---
    panel_titles = [
        dict(
            text="LEVERAGED MONEY — HEDGE FUNDS & CTAs",
            x=0.01, y=1.0,
            xref='paper', yref='paper',
            xanchor='left', yanchor='top',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
        dict(
            text="ASSET MANAGER — PENSION FUNDS & INSTITUTIONALS",
            x=0.01, y=0.5,
            xref='paper', yref='paper',
            xanchor='left', yanchor='top',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
    ]
    
    fig.update_layout(
        annotations=(fig.layout.annotations or ()) + tuple(inline_annotations) + tuple(panel_titles)
    )
    
    return fig


# ============================================================================
# FUNCTION 3: build_vol_correlation_chart(pair)
# ============================================================================

def build_vol_correlation_chart(pair):
    """Build volatility and correlation chart for eurusd, usdjpy, or usdinr."""
    
    # Configuration
    configs = {
        'eurusd': dict(
            vol_col='EURUSD_vol30',
            pct_col='EURUSD_vol_pct',
            corr_col='EURUSD_spread_corr_60d',
            corr_20d_col='EURUSD_corr_20d',
            corr_name='Regime Corr (60D)',
            color='#4da6ff',
            fill_color='rgba(77,166,255,0.12)',
            other_vol='USDJPY_vol30',
            other_label='USD/JPY'
        ),
        'usdjpy': dict(
            vol_col='USDJPY_vol30',
            pct_col='USDJPY_vol_pct',
            corr_col='USDJPY_spread_corr_60d',
            corr_20d_col='USDJPY_corr_20d',
            corr_name='Regime Corr (60D)',
            color='#ff9944',
            fill_color='rgba(255,153,68,0.12)',
            other_vol='EURUSD_vol30',
            other_label='EUR/USD'
        ),
        'usdinr': dict(
            vol_col='USDINR_vol30',
            pct_col='USDINR_vol_pct',
            corr_col='oil_inr_corr_60d',
            corr_20d_col=None,
            corr_name='Oil Corr (60D)',
            color='#e74c3c',
            fill_color='rgba(231,76,60,0.12)',
            other_vol='EURUSD_vol30',
            other_label='EUR/USD'
        )
    }
    
    cfg = configs[pair]
    PAIR = pair.upper()
    
    # Load and filter data
    d, cutoff, today = _load_and_filter(pair, months=get_chart_months())
    d = d[d[cfg['vol_col']].notna()]
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.08,
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
    )
    
    # --- Subplot 1: Realized Volatility ---
    # Filled area trace
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d[cfg['vol_col']],
            mode='lines',
            fill='tozeroy',
            fillcolor=cfg['fill_color'],
            line=dict(color=cfg['color'], width=1.5),
            name=f"30D Vol \u2013 {PAIR} (%)",
            showlegend=True,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>',
        ),
        row=1, col=1, secondary_y=False,
    )
    
    # Percentile line on secondary axis
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d[cfg['pct_col']],
            mode='lines',
            line=dict(color='#ffffff', width=2),
            name='Pct Rank (0\u2013100)',
            showlegend=True,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.0f}th<extra></extra>',
        ),
        row=1, col=1, secondary_y=True,
    )
    
    # Horizontal zones and lines for volatility (FIXED)
    fig.add_hrect(y0=90, y1=100, fillcolor='rgba(255,68,68,0.06)', 
                  line_width=0, row=1, col=1, secondary_y=True)
    fig.add_hrect(y0=75, y1=90, fillcolor='rgba(240,165,0,0.05)', 
                  line_width=0, row=1, col=1, secondary_y=True)
    fig.add_hline(y=90, line_color='#ff4444', line_dash='dash', line_width=1, 
                  row=1, col=1, secondary_y=True)
    fig.add_hline(y=75, line_color='#f0a500', line_dash='dash', line_width=1, 
                  row=1, col=1, secondary_y=True)
    
    # --- Subplot 2: Regime Correlation ---
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d[cfg['corr_col']],
            mode='lines',
            line=dict(color='#aaaaaa', width=1.5),
            name=cfg.get('corr_name', 'Regime Corr (60D)'),
            showlegend=True,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.3f}<extra></extra>',
        ),
        row=2, col=1,
    )

    # 20D correlation trace (Phase 3 dual-window)
    _corr_20d_col = cfg.get('corr_20d_col')
    if _corr_20d_col and _corr_20d_col in d.columns:
        fig.add_trace(
            go.Scatter(
                x=d.index,
                y=d[_corr_20d_col],
                mode='lines',
                line=dict(color='#aaaaaa', width=1.0, dash='dash'),
                opacity=0.5,
                name='Regime Corr (20D)',
                showlegend=True,
                hovertemplate='%{x|%d %b %Y}<br>%{y:.3f}<extra></extra>',
            ),
            row=2, col=1,
        )

    # Correlation zone fills(FIXED - only extreme zones)
    fig.add_hrect(y0=0.6, y1=1.0, fillcolor='rgba(0,212,170,0.04)', 
                  line_width=0, row=2, col=1)
    fig.add_hrect(y0=-1.0, y1=0.3, fillcolor='rgba(255,68,68,0.04)', 
                  line_width=0, row=2, col=1)
    
    # Correlation threshold lines
    fig.add_hline(y=0.6, line_color='#00d4aa', line_dash='dash', line_width=1, 
                  row=2, col=1)
    fig.add_hline(y=0.3, line_color='#ff4444', line_dash='dash', line_width=1, 
                  row=2, col=1)
    fig.add_hline(y=0, line_color='#333333', line_dash='dot', line_width=1, 
                  row=2, col=1)
    
    # --- Apply theme ---
    fig.update_layout(**_base_layout(height=420))
    _style_axes(fig)

    # --- Legend: top-right of vol panel ---
    fig.update_layout(
        legend=dict(
            x=0.99, y=0.99,
            xanchor='right', yanchor='top',
            bgcolor='rgba(13,13,13,0.85)',
            bordercolor='#2a2a2a', borderwidth=1,
            font=dict(size=9, color='#cccccc'),
            itemsizing='constant',
            tracegroupgap=1,
        )
    )
    
    # Set x-axis ranges for both subplots
    cutoff_str = cutoff.strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    fig.update_layout(
        xaxis =dict(range=[cutoff_str, today_str], type='date'),
        xaxis2=dict(range=[cutoff_str, today_str], type='date')
    )
    
    # FIX: Set y-axis ranges
    fig.update_yaxes(autorange=True, row=1, col=1)
    fig.update_yaxes(range=[-1, 1], row=2, col=1)
    
    # --- Inline end-labels ---
    last_x = d.index[-1]
    latest_vol = d[cfg['vol_col']].iloc[-1]
    latest_pct = d[cfg['pct_col']].iloc[-1]
    latest_corr = d[cfg['corr_col']].iloc[-1]
    
    # Determine correlation label color based on value
    if latest_corr > 0.6:
        corr_color = '#00d4aa'
    elif latest_corr < 0.3:
        corr_color = '#ff4444'
    else:
        corr_color = '#888888'
    
    inline_annotations = [
        # Volatility value
        dict(
            x=last_x,
            y=latest_vol,
            text=f"  {latest_vol:.1f}%",
            xref='x', yref='y',
            xanchor='left', showarrow=False,
            font=dict(size=9, color=cfg['color']),
        ),
        # Percentile value — secondary_y=True in row 1 → yref='y2'
        dict(
            x=last_x,
            y=latest_pct,
            text=f"  {latest_pct:.0f}th pct",
            xref='x', yref='y2',
            xanchor='left', showarrow=False,
            font=dict(size=9, color='#aaaaaa'),
        ),
        # Correlation value — row 2 primary axis → yref='y3'
        dict(
            x=last_x,
            y=latest_corr,
            text=f"  {latest_corr:.3f}",
            xref='x2', yref='y3',
            xanchor='left', showarrow=False,
            font=dict(size=9, color=corr_color),
        ),
    ]
    
    # --- Panel titles ---
    panel_titles = [
        dict(
            text="30D REALIZED VOLATILITY (ANNUALIZED)",
            x=0.01, y=1.0,
            xref='paper', yref='paper',
            xanchor='left', yanchor='top',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
        dict(
            text="REGIME CORRELATION (60D / 20D)",
            x=0.01, y=0.35,
            xref='paper', yref='paper',
            xanchor='left', yanchor='top',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
    ]
    
    fig.update_layout(
        annotations=(fig.layout.annotations or ()) + tuple(inline_annotations) + tuple(panel_titles)
    )
    
    return fig


# ============================================================================
# FUNCTION: build_cross_asset_chart(pair)  — Phase 1 & 2 HTML
# Two-row chart:
#   Row 1: Brent price (amber, left-y) vs FX price (pair colour, right-y)
#   Row 2: oil_corr_60d (amber) + dxy_corr_60d (steel-blue), range [-1,1]
# ============================================================================

def build_cross_asset_chart(pair):
    """Cross-asset chart: Brent vs FX price on top, rolling correlations below."""

    configs = {
        'eurusd': dict(
            corr_oil_col='oil_eurusd_corr_60d',
            corr_dxy_col='dxy_eurusd_corr_60d',
            fx_col='EURUSD',
            fx_color='#4da6ff',
            fx_label='EUR/USD',
        ),
        'usdjpy': dict(
            corr_oil_col='oil_usdjpy_corr_60d',
            corr_dxy_col='dxy_usdjpy_corr_60d',
            fx_col='USDJPY',
            fx_color='#ff9944',
            fx_label='USD/JPY',
        ),
        'usdinr': dict(
            corr_oil_col='oil_inr_corr_60d',
            corr_dxy_col='dxy_inr_corr_60d',
            fx_col='USDINR',
            fx_color='#e74c3c',
            fx_label='USD/INR',
        ),
    }

    cfg = configs[pair]
    d, cutoff, today = _load_and_filter(pair, months=get_chart_months())

    has_brent   = 'Brent' in d.columns
    has_fx      = cfg['fx_col'] in d.columns
    has_oil     = cfg['corr_oil_col'] in d.columns
    has_dxy     = cfg['corr_dxy_col'] in d.columns

    if not has_fx:
        return None

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.52, 0.48],
        vertical_spacing=0.10,
        specs=[[{'secondary_y': True}], [{'secondary_y': False}]],
    )

    # ── Row 1: Brent (left y) + FX price (right y) ────────────────────────
    if has_brent:
        fig.add_trace(
            go.Scatter(
                x=d.index,
                y=d['Brent'],
                mode='lines',
                line=dict(color='#f0a500', width=1.5),
                name='Brent ($/bbl)',
                hovertemplate='%{x|%d %b %Y}<br>$%{y:.2f}<extra></extra>',
            ),
            row=1, col=1, secondary_y=False,
        )

    if has_fx:
        fig.add_trace(
            go.Scatter(
                x=d.index,
                y=d[cfg['fx_col']],
                mode='lines',
                line=dict(color=cfg['fx_color'], width=1.5),
                name=cfg['fx_label'],
                hovertemplate='%{x|%d %b %Y}<br>%{y:.4f}<extra></extra>',
            ),
            row=1, col=1, secondary_y=True,
        )

    # ── Row 2: Rolling correlations ────────────────────────────────────────
    if has_oil:
        fig.add_trace(
            go.Scatter(
                x=d.index,
                y=d[cfg['corr_oil_col']],
                mode='lines',
                line=dict(color='#ff6b6b', width=1.5),
                name='Oil corr 60D',
                hovertemplate='%{x|%d %b %Y}<br>%{y:.3f}<extra></extra>',
            ),
            row=2, col=1,
        )

    if has_dxy:
        fig.add_trace(
            go.Scatter(
                x=d.index,
                y=d[cfg['corr_dxy_col']],
                mode='lines',
                line=dict(color='#6c8ebf', width=1.5),
                name='DXY corr 60D',
                hovertemplate='%{x|%d %b %Y}<br>%{y:.3f}<extra></extra>',
            ),
            row=2, col=1,
        )

    # Threshold lines
    fig.add_hline(y= 0.6,  line_color='#00d4aa', line_dash='dash', line_width=1, row=2, col=1)
    fig.add_hline(y= 0.3,  line_color='#555555', line_dash='dot',  line_width=1, row=2, col=1)
    fig.add_hline(y= 0.0,  line_color='#333333', line_dash='dot',  line_width=1, row=2, col=1)
    fig.add_hline(y=-0.3,  line_color='#555555', line_dash='dot',  line_width=1, row=2, col=1)
    fig.add_hline(y=-0.6,  line_color='#ff4444', line_dash='dash', line_width=1, row=2, col=1)

    # Fixed correlation y-range
    fig.update_yaxes(range=[-1, 1], row=2, col=1)
    fig.update_yaxes(autorange=True, row=1, col=1)

    # ── Theme ──────────────────────────────────────────────────────────────
    fig.update_layout(**_base_layout(height=440))
    _style_axes(fig)

    # Legend below the chart, horizontal, with toggle hint
    fig.update_layout(
        legend=dict(
            orientation='h',
            x=0.0, y=-0.09,
            xanchor='left', yanchor='top',
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=9, color='#666666'),
            itemsizing='constant',
            tracegroupgap=8,
        ),
        margin=dict(l=52, r=52, t=18, b=60),  # extra bottom margin for legend
        annotations=[
            dict(
                text='click legend items to show/hide lines',
                x=1.0, y=-0.08,
                xref='paper', yref='paper',
                xanchor='right', yanchor='top',
                font=dict(size=8, color='#333333'),
                showarrow=False,
            )
        ]
    )

    # x-axis range
    cutoff_str = cutoff.strftime('%Y-%m-%d')
    today_str  = today.strftime('%Y-%m-%d')
    fig.update_layout(
        xaxis =dict(range=[cutoff_str, today_str], type='date'),
        xaxis2=dict(range=[cutoff_str, today_str], type='date'),
    )

    # ── Inline end-labels + panel titles ──────────────────────────────────
    last_x = d.index[-1]
    annotations = [
        dict(
            text='COMMODITY vs FX PRICE  (12M)',
            x=0.01, y=1.01,
            xref='paper', yref='paper',
            xanchor='left', yanchor='bottom',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
        dict(
            text='ROLLING 60D CORRELATION',
            x=0.01, y=0.46,
            xref='paper', yref='paper',
            xanchor='left', yanchor='bottom',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
    ]

    # Brent end-label (row1, primary y → yref='y')
    if has_brent:
        latest_brent = d['Brent'].dropna()
        if len(latest_brent) > 0:
            annotations.append(dict(
                x=last_x, y=latest_brent.iloc[-1],
                text=f"  ${latest_brent.iloc[-1]:.1f}",
                xref='x', yref='y',
                xanchor='left', showarrow=False,
                font=dict(size=9, color='#f0a500'),
            ))

    # FX end-label (row1, secondary y → yref='y2')
    if has_fx:
        latest_fx = d[cfg['fx_col']].dropna()
        if len(latest_fx) > 0:
            annotations.append(dict(
                x=last_x, y=latest_fx.iloc[-1],
                text=f"  {latest_fx.iloc[-1]:.4f}",
                xref='x', yref='y2',
                xanchor='left', showarrow=False,
                font=dict(size=9, color=cfg['fx_color']),
            ))

    # Oil corr end-label (row2 → yref='y3')
    if has_oil:
        latest_oil = d[cfg['corr_oil_col']].dropna()
        if len(latest_oil) > 0:
            v = latest_oil.iloc[-1]
            annotations.append(dict(
                x=last_x, y=v,
                text=f'  {v:+.3f}',
                xref='x2', yref='y3',
                xanchor='left', showarrow=False,
                font=dict(size=8, color='#f0a500'),
            ))

    # DXY corr end-label (row2 → yref='y3')
    if has_dxy:
        latest_dxy = d[cfg['corr_dxy_col']].dropna()
        if len(latest_dxy) > 0:
            v = latest_dxy.iloc[-1]
            annotations.append(dict(
                x=last_x, y=v,
                text=f'  {v:+.3f}',
                xref='x2', yref='y3',
                xanchor='left', showarrow=False,
                font=dict(size=8, color='#6c8ebf'),
            ))

    fig.update_layout(annotations=tuple(annotations))
    return fig


