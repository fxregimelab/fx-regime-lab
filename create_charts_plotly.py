import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from charts.base import _base_layout, _style_axes, _load_and_filter, _add_annotation


# ============================================================================
# REFERENCE PROTOTYPE (KEEP INTACT)
# ============================================================================

def build_eurusd_fundamentals_prototype():
    d = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)

    cutoff = pd.Timestamp.today() - pd.DateOffset(months=12)
    d = d[d.index >= cutoff]
    d = d[d['EURUSD'].notna()]

    # The correlation column in the CSV is EURUSD_spread_corr_60d
    corr_col = 'EURUSD_spread_corr_60d'

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.45, 0.35, 0.20],
        vertical_spacing=0.06,
    )

    # --- Subplot 1: EUR/USD price ---
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d['EURUSD'],
            mode='lines',
            line=dict(color='#4da6ff', width=1.5),
            name='EUR/USD',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.4f}<extra></extra>',
        ),
        row=1, col=1,
    )

    # --- Subplot 2: Dual spreads ---
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d['US_DE_10Y_spread'],
            mode='lines',
            line=dict(color='#2980b9'),
            name='US 2Y - DE 10Y',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>',
        ),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d['US_DE_2Y_spread'],
            mode='lines',
            line=dict(color='#e67e22'),
            name='US 2Y - DE 2Y',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>',
        ),
        row=2, col=1,
    )
    fig.add_hline(y=0, line_dash='dash', line_color='#444444', line_width=1, row=2, col=1)

    # --- Subplot 3: Regime correlation ---
    fig.add_trace(
        go.Scatter(
            x=d.index,
            y=d[corr_col],
            mode='lines',
            line=dict(color='#aaaaaa', width=1.5),
            name='60D Corr',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}<extra></extra>',
        ),
        row=3, col=1,
    )
    # INTACT threshold
    fig.add_hline(y=0.6, line_color='#00d4aa', line_dash='dash', line_width=1, row=3, col=1)
    # BROKEN threshold
    fig.add_hline(y=0.3, line_color='#ff4444', line_dash='dash', line_width=1, row=3, col=1)
    # Broken zone (below 0.3)
    fig.add_hrect(y0=-1, y1=0.3, fillcolor='rgba(255,68,68,0.05)', line_width=0, row=3, col=1)
    # Intact zone (above 0.6)
    fig.add_hrect(y0=0.6, y1=1, fillcolor='rgba(0,212,170,0.05)', line_width=0, row=3, col=1)

    # --- Theme ---
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0d0d0d',
        plot_bgcolor='#141414',
        font=dict(family='Inter, system-ui, sans-serif', color='#cccccc', size=11),
        height=520,
        margin=dict(l=50, r=30, t=30, b=30),
        showlegend=False,
        hovermode='x unified',
        hoverlabel=dict(bgcolor='#1a1a1a', bordercolor='#333333',
                        font=dict(color='#cccccc', size=11)),
        xaxis_showgrid=True, xaxis_gridcolor='#1e1e1e', xaxis_gridwidth=1,
        yaxis_showgrid=True, yaxis_gridcolor='#1e1e1e', yaxis_gridwidth=1,
        dragmode='pan',
    )

    fig.update_xaxes(
        showgrid=True, gridcolor='#1e1e1e', gridwidth=1,
        showline=False, zeroline=False,
        tickfont=dict(size=10, color='#666666'),
        range=[cutoff.strftime('%Y-%m-%d'), pd.Timestamp.today().strftime('%Y-%m-%d')],
    )
    fig.update_yaxes(
        showgrid=True, gridcolor='#1e1e1e', gridwidth=1,
        showline=False, zeroline=False,
        tickfont=dict(size=10, color='#666666'),
    )

    # Fix correlation panel y-axis range
    fig.update_yaxes(range=[-1, 1], row=3, col=1)

    # --- Inline end-of-line labels ---
    last_x = d.index[-1]
    inline_annotations = [
        # Subplot 1: EUR/USD price value
        dict(
            x=last_x,
            y=d['EURUSD'].iloc[-1],
            text=f"  {d['EURUSD'].iloc[-1]:.4f}",
            xref='x', yref='y',
            xanchor='left', showarrow=False,
            font=dict(size=10, color='#4da6ff'),
        ),
        # Subplot 2: DE 10Y spread label
        dict(
            x=last_x,
            y=d['US_DE_10Y_spread'].iloc[-1],
            text='  DE 10Y',
            xref='x2', yref='y2',
            xanchor='left', showarrow=False,
            font=dict(size=9, color='#2980b9'),
        ),
        # Subplot 2: DE 2Y spread label
        dict(
            x=last_x,
            y=d['US_DE_2Y_spread'].iloc[-1],
            text='  DE 2Y',
            xref='x2', yref='y2',
            xanchor='left', showarrow=False,
            font=dict(size=9, color='#e67e22'),
        ),
        # Subplot 3: correlation value
        dict(
            x=last_x,
            y=d[corr_col].iloc[-1],
            text=f"  {d[corr_col].iloc[-1]:.3f}",
            xref='x3', yref='y3',
            xanchor='left', showarrow=False,
            font=dict(size=9, color='#cccccc'),
        ),
    ]

    # --- Subplot title annotations ---
    # Row domains (bottom to top): row3=[0,0.20], row2=[0.26,0.61], row1=[0.67,1.0]
    subplot_titles = [
        dict(
            text='EUR/USD PRICE',
            x=0.01, y=1.0,
            xref='paper', yref='paper',
            xanchor='left', yanchor='top',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
        dict(
            text='RATE DIFFERENTIALS (pp) \u2014 narrowing = EUR/USD should rise',
            x=0.01, y=0.61,
            xref='paper', yref='paper',
            xanchor='left', yanchor='top',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
        dict(
            text='REGIME CORRELATION (60D)',
            x=0.01, y=0.20,
            xref='paper', yref='paper',
            xanchor='left', yanchor='top',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
    ]

    fig.update_layout(
        annotations=fig.layout.annotations + tuple(inline_annotations) + tuple(subplot_titles)
    )

    return fig


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
            subtitle='negative = India yields higher = INR strength'
        )
    }
    
    cfg = configs[pair]
    PAIR = pair.upper()
    
    # Load and filter data - use 'd' for filtered data
    d, cutoff, today = _load_and_filter(pair)
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
            name=f"US\u2013{cfg['label_10y']} spread",
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
            name=f"US\u2013{cfg['label_2y']} spread",
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
    
    # --- Inline end-labels ---
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
        annotations=fig.layout.annotations + tuple(inline_annotations) + tuple(panel_titles)
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
            net_col='EUR_net_pos',
            pct_col='EUR_percentile',
            am_net_col='EUR_assetmgr_net',
            am_pct_col='EUR_assetmgr_percentile',
            color_pair='#4da6ff'
        ),
        'usdjpy': dict(
            net_col='JPY_net_pos',
            pct_col='JPY_percentile',
            am_net_col='JPY_assetmgr_net',
            am_pct_col='JPY_assetmgr_percentile',
            color_pair='#ff9944'
        )
    }
    
    cfg = configs[pair]
    
    # Load data
    d, cutoff, today = _load_and_filter(pair)
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
        annotations=fig.layout.annotations + tuple(inline_annotations) + tuple(panel_titles)
    )
    
    return fig


# ============================================================================
# FUNCTION 3: build_vol_correlation_chart(pair)
# ============================================================================

def build_vol_correlation_chart(pair):
    """Build volatility and correlation chart for eurusd or usdjpy only."""
    
    if pair == 'usdinr':
        # USDINR has no vol data currently
        return None
    
    # Configuration
    configs = {
        'eurusd': dict(
            vol_col='EURUSD_vol30',
            pct_col='EURUSD_vol_pct',
            corr_col='EURUSD_spread_corr_60d',
            color='#4da6ff',
            fill_color='rgba(77,166,255,0.12)',
            other_vol='USDJPY_vol30',
            other_label='USD/JPY'
        ),
        'usdjpy': dict(
            vol_col='USDJPY_vol30',
            pct_col='USDJPY_vol_pct',
            corr_col='USDJPY_spread_corr_60d',
            color='#ff9944',
            fill_color='rgba(255,153,68,0.12)',
            other_vol='EURUSD_vol30',
            other_label='EUR/USD'
        )
    }
    
    cfg = configs[pair]
    PAIR = pair.upper()
    
    # Load and filter data
    d, cutoff, today = _load_and_filter(pair)
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
            name='Regime Corr (60D)',
            showlegend=True,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.3f}<extra></extra>',
        ),
        row=2, col=1,
    )
    
    # Correlation zone fills (FIXED - only extreme zones)
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
            text="REGIME CORRELATION (60D ROLLING)",
            x=0.01, y=0.35,
            xref='paper', yref='paper',
            xanchor='left', yanchor='top',
            font=dict(size=9, color='#555555'),
            showarrow=False,
        ),
    ]
    
    fig.update_layout(
        annotations=fig.layout.annotations + tuple(inline_annotations) + tuple(panel_titles)
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
            fx_color='#c084fc',
            fx_label='USD/INR',
        ),
    }

    cfg = configs[pair]
    d, cutoff, today = _load_and_filter(pair)

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
                line=dict(color='#f0a500', width=1.5),
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


# ============================================================================
# FUNCTION 3: build_vol_chart(pair)
# ============================================================================

def build_vol_chart(pair):
    """Build volatility chart for eurusd or usdjpy only."""
    
    if pair == 'usdinr':
        raise ValueError("build_vol_chart() does not support 'usdinr'")
    
    # Configuration
    configs = {
        'eurusd': dict(
            vol_col='EURUSD_vol30',
            pct_col='EURUSD_vol_pct',
            color='#4da6ff',
            fill_color='rgba(77,166,255,0.12)',
            other_vol='USDJPY_vol30',
            other_label='USD/JPY'
        ),
        'usdjpy': dict(
            vol_col='USDJPY_vol30',
            pct_col='USDJPY_vol_pct',
            color='#ff9944',
            fill_color='rgba(255,153,68,0.12)',
            other_vol='EURUSD_vol30',
            other_label='EUR/USD'
        )
    }
    
    cfg = configs[pair]
    PAIR = pair.upper()
    
    # Load data
    d, cutoff, today = _load_and_filter(pair)
    d = d[d[cfg['vol_col']].notna()]


def debug_data():
    df = pd.read_csv('data/latest_with_cot.csv', 
                     index_col=0, parse_dates=True)
    print("=== RAW INDEX INFO ===")
    print(f"Index dtype: {df.index.dtype}")
    print(f"Index type: {type(df.index[0])}")
    print(f"First 3 index values: {df.index[:3].tolist()}")
    print(f"Last 3 index values: {df.index[-3:].tolist()}")
    print(f"Total rows: {len(df)}")
    print(f"EURUSD min: {df['EURUSD'].min()}, max: {df['EURUSD'].max()}")
    print(f"EURUSD null count: {df['EURUSD'].isnull().sum()}")
    
    today = pd.Timestamp.today().normalize()
    cutoff = today - pd.DateOffset(months=12)
    print(f"\n=== FILTER TEST ===")
    print(f"Today: {today}")
    print(f"Cutoff: {cutoff}")
    
    df.index = pd.to_datetime(df.index, utc=False).tz_localize(None)
    df.index = df.index.normalize()
    
    d = df[df.index >= cutoff].copy()
    print(f"Rows after 12M filter: {len(d)}")
    print(f"Filtered EURUSD min: {d['EURUSD'].min():.4f}")
    print(f"Filtered EURUSD max: {d['EURUSD'].max():.4f}")
    print(f"Filtered date range: {d.index[0]} to {d.index[-1]}")
    
    if len(d) > 0:
        print(f"\nFirst 3 filtered dates: {d.index[:3].tolist()}")
        print(f"Last 3 filtered dates: {d.index[-3:].tolist()}")
    
    print(f"\nCutoff as Timestamp: {cutoff}")
    print(f"xaxis range would be: [{cutoff}, {today}]")


if __name__ == '__main__':
    debug_data()
    
    # Generate prototype charts
    from create_charts_plotly import (
        build_fundamentals_chart,
        build_positioning_chart,
        build_vol_correlation_chart
    )
    import plotly.io as pio
    
    # Generate all charts
    charts = [
        ('eurusd', build_fundamentals_chart('eurusd'), 'proto_eurusd_fundamentals.html'),
        ('usdjpy', build_fundamentals_chart('usdjpy'), 'proto_usdjpy_fundamentals.html'),
        ('usdinr', build_fundamentals_chart('usdinr'), 'proto_usdinr_fundamentals.html'),
        ('eurusd', build_positioning_chart('eurusd'), 'proto_eurusd_positioning.html'),
        ('usdjpy', build_positioning_chart('usdjpy'), 'proto_usdjpy_positioning.html'),
        ('eurusd', build_vol_correlation_chart('eurusd'), 'proto_eurusd_vol_correlation.html'),
        ('usdjpy', build_vol_correlation_chart('usdjpy'), 'proto_usdjpy_vol_correlation.html'),
    ]
    
    for pair, fig, fname in charts:
        if fig is not None:
            print(f"Generating {fname}...")
            pio.write_html(fig, fname, auto_open=False)
    
    print("Done!")


def debug_fig_data():
    d, cutoff, today = _load_and_filter()
    
    # Check what data is actually being passed to traces
    print("=== DATA CHECK ===")
    print(f"Rows in filtered data: {len(d)}")
    print(f"EURUSD first value: {d['EURUSD'].iloc[0]:.4f}")
    print(f"EURUSD last value: {d['EURUSD'].iloc[-1]:.4f}")
    print(f"EURUSD_vol30 col exists: {'EURUSD_vol30' in d.columns}")
    if 'EURUSD_vol30' in d.columns:
        vol = d['EURUSD_vol30'].dropna()
        print(f"Vol values range: {vol.min():.4f} to {vol.max():.4f}")
        print(f"Vol first non-null: {vol.iloc[0]:.4f}")
    
    print(f"\nEUR_net_pos col exists: {'EUR_net_pos' in d.columns}")
    if 'EUR_net_pos' in d.columns:
        net = d['EUR_net_pos'].dropna()
        print(f"Net pos range: {net.min():,.0f} to {net.max():,.0f}")
    
    # Build one fig and inspect its actual trace data
    fig = build_fundamentals_chart('eurusd')
    print("\n=== FIGURE TRACE DATA ===")
    for i, trace in enumerate(fig.data):
        if hasattr(trace, 'y') and trace.y is not None:
            y_arr = list(trace.y)
            non_none = [v for v in y_arr if v is not None]
            print(f"Trace {i} ({trace.name}): {len(y_arr)} points, "
                  f"first={non_none[0] if non_none else 'empty'}, "
                  f"last={non_none[-1] if non_none else 'empty'}")
        if hasattr(trace, 'x') and trace.x is not None:
            x_arr = list(trace.x)
            print(f"  x range: {x_arr[0]} to {x_arr[-1]}")
    
    print("\n=== LAYOUT AXES ===")
    layout_dict = fig.to_dict()['layout']
    for key in layout_dict:
        if 'axis' in key and 'range' in str(layout_dict[key]):
            print(f"  {key}: {layout_dict[key]}")


if __name__ == '__main__':
    debug_fig_data()