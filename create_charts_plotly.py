import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go


# ============================================================================
# SHARED HELPERS
# ============================================================================

def _base_layout(height=520):
    return dict(
        template='plotly_dark',
        paper_bgcolor='#0d0d0d',
        plot_bgcolor='#141414',
        font=dict(family='Inter, system-ui, sans-serif', 
                  color='#cccccc', size=11),
        height=height,
        margin=dict(l=50, r=60, t=30, b=30),
        legend=dict(bgcolor='rgba(0,0,0,0)', borderwidth=0,
                    font=dict(size=10, color='#888888')),
        hovermode='x unified',
        hoverlabel=dict(bgcolor='#1a1a1a', bordercolor='#333333',
                        font=dict(color='#cccccc', size=11)),
        dragmode='pan'
    )


def _style_axes(fig):
    fig.update_xaxes(showgrid=True, gridcolor='#1e1e1e', gridwidth=1,
                     showline=False, zeroline=False,
                     tickfont=dict(size=10, color='#666666'))
    fig.update_yaxes(showgrid=True, gridcolor='#1e1e1e', gridwidth=1,
                     showline=False, zeroline=False,
                     tickfont=dict(size=10, color='#666666'))
    return fig


def _load_and_filter(months=12):
    df = pd.read_csv('data/latest_with_cot.csv', 
                     index_col=0, parse_dates=True)
    cutoff = pd.Timestamp.today() - pd.DateOffset(months=months)
    today_str = pd.Timestamp.today().strftime('%Y-%m-%d')
    cutoff_str = cutoff.strftime('%Y-%m-%d')
    return df[df.index >= cutoff], cutoff_str, today_str


def _add_annotation(fig, x, y, text, color, row, xref, yref):
    fig.add_annotation(x=x, y=y, text=text, font=dict(size=9, color=color),
                       xanchor='left', showarrow=False,
                       xref=xref, yref=yref)


# ============================================================================
# REFERENCE PROTOTYPE (KEEP INTACT)
# ============================================================================

def build_eurusd_fundamentals_prototype():
    df = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)

    cutoff = pd.Timestamp.today() - pd.DateOffset(months=12)
    df = df[df.index >= cutoff]
    df = df[df['EURUSD'].notna()]

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
            x=df.index,
            y=df['EURUSD'],
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
            x=df.index,
            y=df['US_DE_10Y_spread'],
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
            x=df.index,
            y=df['US_DE_2Y_spread'],
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
            x=df.index,
            y=df[corr_col],
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
    last_x = df.index[-1]
    inline_annotations = [
        # Subplot 1: EUR/USD price value
        dict(
            x=last_x,
            y=df['EURUSD'].iloc[-1],
            text=f"  {df['EURUSD'].iloc[-1]:.4f}",
            xref='x', yref='y',
            xanchor='left', showarrow=False,
            font=dict(size=10, color='#4da6ff'),
        ),
        # Subplot 2: DE 10Y spread label
        dict(
            x=last_x,
            y=df['US_DE_10Y_spread'].iloc[-1],
            text='  DE 10Y',
            xref='x2', yref='y2',
            xanchor='left', showarrow=False,
            font=dict(size=9, color='#2980b9'),
        ),
        # Subplot 2: DE 2Y spread label
        dict(
            x=last_x,
            y=df['US_DE_2Y_spread'].iloc[-1],
            text='  DE 2Y',
            xref='x2', yref='y2',
            xanchor='left', showarrow=False,
            font=dict(size=9, color='#e67e22'),
        ),
        # Subplot 3: correlation value
        dict(
            x=last_x,
            y=df[corr_col].iloc[-1],
            text=f"  {df[corr_col].iloc[-1]:.3f}",
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
    
    # Load data
    df, cutoff_str, today_str = _load_and_filter(months=12)
    df = df[df[cfg['price_col']].notna()]
    
    # Always use 2 subplots for all pairs
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.06,
    )
    
    # --- Subplot 1: Price line ---
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[cfg['price_col']],
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
            x=df.index,
            y=df[cfg['spread_10y']],
            mode='lines',
            line=dict(color='#2980b9', width=1.5),
            name=cfg['label_10y'],
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>',
        ),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[cfg['spread_2y']],
            mode='lines',
            line=dict(color='#e67e22', width=1.5),
            name=cfg['label_2y'],
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>',
        ),
        row=2, col=1,
    )
    fig.add_hline(y=0, line_dash='dash', line_color='#333333', line_width=1, 
                  row=2, col=1)
    
    # --- Removed Subplot 3: Correlation ---
    # The correlation subplot has been removed as per requirements.
    # All pairs now use only two subplots.
    
    # --- Apply theme ---
    fig.update_layout(**_base_layout())
    _style_axes(fig)
    
    # Set x-axis range
    fig.update_xaxes(range=[cutoff_str, today_str])
    
    # --- Inline end-labels ---
    last_x = df.index[-1]
    inline_annotations = []
    
    # Row 1: Price value
    inline_annotations.append(dict(
        x=last_x,
        y=df[cfg['price_col']].iloc[-1],
        text=f"  {df[cfg['price_col']].iloc[-1]:.4f}",
        xref='x', yref='y',
        xanchor='left', showarrow=False,
        font=dict(size=9, color=cfg['price_color']),
    ))
    
    # Row 2: Spread labels
    inline_annotations.append(dict(
        x=last_x,
        y=df[cfg['spread_10y']].iloc[-1],
        text=f"  {cfg['label_10y']}",
        xref='x2', yref='y2',
        xanchor='left', showarrow=False,
        font=dict(size=9, color='#2980b9'),
    ))
    inline_annotations.append(dict(
        x=last_x,
        y=df[cfg['spread_2y']].iloc[-1],
        text=f"  {cfg['label_2y']}",
        xref='x2', yref='y2',
        xanchor='left', showarrow=False,
        font=dict(size=9, color='#e67e22'),
    ))
    
    # --- Panel title annotations ---
    # Fixed y positions for 2-row layout
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
    df, cutoff_str, today_str = _load_and_filter(months=12)
    df = df[df[cfg['net_col']].notna()]
    
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
                            for v in df[cfg['net_col']]]
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df[cfg['net_col']],
            marker_color=leveraged_bar_colors,
            marker_opacity=0.7,
            marker_line_width=0,
            width=5 * 24 * 60 * 60 * 1000,  # 5 days in milliseconds
            name='Leveraged Net',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>Net: %{y:+,.0f} contracts<extra></extra>',
        ),
        row=1, col=1, secondary_y=False,
    )
    
    # Percentile line on secondary axis
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[cfg['pct_col']],
            mode='lines',
            line=dict(color='#ffffff', width=2.5),
            name='Leveraged Pct',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>Percentile: %{y:.0f}th<extra></extra>',
        ),
        row=1, col=1, secondary_y=True,
    )
    
    # Horizontal zones and lines for leveraged money
    fig.add_hrect(y0=80, y1=100, fillcolor='rgba(255,68,68,0.07)', 
                  line_width=0, row=1, col=1, secondary_y=True)
    fig.add_hrect(y0=0, y1=20, fillcolor='rgba(0,212,170,0.07)', 
                  line_width=0, row=1, col=1, secondary_y=True)
    fig.add_hline(y=80, line_color='#ff4444', line_dash='dash', line_width=1, 
                  row=1, col=1, secondary_y=True)
    fig.add_hline(y=20, line_color='#00d4aa', line_dash='dash', line_width=1, 
                  row=1, col=1, secondary_y=True)
    fig.add_hline(y=50, line_color='#333333', line_dash='dot', line_width=1, 
                  row=1, col=1, secondary_y=True)
    
    # --- Subplot 2: Asset Manager ---
    am_bar_colors = ['#00d4aa' if v >= 0 else '#ff4444' 
                     for v in df[cfg['am_net_col']]]
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df[cfg['am_net_col']],
            marker_color=am_bar_colors,
            marker_opacity=0.7,
            marker_line_width=0,
            width=5 * 24 * 60 * 60 * 1000,  # 5 days in milliseconds
            name='AM Net',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>Net: %{y:+,.0f} contracts<extra></extra>',
        ),
        row=2, col=1, secondary_y=False,
    )
    
    # Percentile line on secondary axis
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[cfg['am_pct_col']],
            mode='lines',
            line=dict(color='#ffffff', width=2.5),
            name='AM Pct',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>Percentile: %{y:.0f}th<extra></extra>',
        ),
        row=2, col=1, secondary_y=True,
    )
    
    # Horizontal zones and lines for asset manager
    fig.add_hrect(y0=80, y1=100, fillcolor='rgba(255,68,68,0.07)', 
                  line_width=0, row=2, col=1, secondary_y=True)
    fig.add_hrect(y0=0, y1=20, fillcolor='rgba(0,212,170,0.07)', 
                  line_width=0, row=2, col=1, secondary_y=True)
    fig.add_hline(y=80, line_color='#ff4444', line_dash='dash', line_width=1, 
                  row=2, col=1, secondary_y=True)
    fig.add_hline(y=20, line_color='#00d4aa', line_dash='dash', line_width=1, 
                  row=2, col=1, secondary_y=True)
    fig.add_hline(y=50, line_color='#333333', line_dash='dot', line_width=1, 
                  row=2, col=1, secondary_y=True)
    
    # --- Apply theme ---
    fig.update_layout(**_base_layout(height=560))
    _style_axes(fig)
    
    # Set x-axis range
    fig.update_xaxes(range=[cutoff_str, today_str])
    
    # Set secondary y-axis ranges (0-100)
    fig.update_yaxes(range=[0, 100], secondary_y=True, row=1, col=1)
    fig.update_yaxes(range=[0, 100], secondary_y=True, row=2, col=1)
    
    # --- Annotations ---
    last_x = df.index[-1]
    
    # Subplot 1: Leveraged Money values
    latest_net_lev = df[cfg['net_col']].iloc[-1]
    latest_pct_lev = df[cfg['pct_col']].iloc[-1]
    
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
    latest_net_am = df[cfg['am_net_col']].iloc[-1]
    latest_pct_am = df[cfg['am_pct_col']].iloc[-1]
    
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
    
    # Load data
    df, cutoff_str, today_str = _load_and_filter(months=12)
    df = df[df[cfg['vol_col']].notna()]
    
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
            x=df.index,
            y=df[cfg['vol_col']],
            mode='lines',
            fill='tozeroy',
            fillcolor=cfg['fill_color'],
            line=dict(color=cfg['color'], width=1.5),
            name=PAIR,
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>',
        ),
        row=1, col=1, secondary_y=False,
    )
    
    # Percentile line on secondary axis
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[cfg['pct_col']],
            mode='lines',
            line=dict(color='#ffffff', width=2),
            name='Percentile',
            showlegend=False,
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
            x=df.index,
            y=df[cfg['corr_col']],
            mode='lines',
            line=dict(color='#aaaaaa', width=1.5),
            name='Correlation',
            showlegend=False,
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
    
    # Fix y-axis range for correlation
    fig.update_yaxes(range=[-1, 1], row=2, col=1)
    
    # --- Apply theme ---
    fig.update_layout(**_base_layout())
    _style_axes(fig)
    
    # Set x-axis range
    fig.update_xaxes(range=[cutoff_str, today_str])
    
    # --- Inline end-labels ---
    last_x = df.index[-1]
    latest_vol = df[cfg['vol_col']].iloc[-1]
    latest_pct = df[cfg['pct_col']].iloc[-1]
    latest_corr = df[cfg['corr_col']].iloc[-1]
    
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
        # Percentile value
        dict(
            x=last_x,
            y=latest_pct,
            text=f"  {latest_pct:.0f}th pct",
            xref='x', yref='y',
            xanchor='left', showarrow=False,
            font=dict(size=9, color='#aaaaaa'),
        ),
        # Correlation value
        dict(
            x=last_x,
            y=latest_corr,
            text=f"  {latest_corr:.3f}",
            xref='x2', yref='y2',
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
    df, cutoff_str, today_str = _load_and_filter(months=12)
    df = df[df[cfg['vol_col']].notna()]
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.4],
        vertical_spacing=0.08,
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
    )
    
    # --- Subplot 1: Realized Volatility ---
    # Filled area trace
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[cfg['vol_col']],
            mode='lines',
            fill='tozeroy',
            fillcolor=cfg['fill_color'],
            line=dict(color=cfg['color'], width=1.5),
            name=PAIR,
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>',
        ),
        row=1, col=1, secondary_y=False,
    )
    
    # Percentile line on secondary axis
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[cfg['pct_col']],
            mode='lines',
            line=dict(color='#ffffff', width=2),
            name='Percentile',
            showlegend=False,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.0f}th<extra></extra>',
        ),
        row=1, col=1, secondary_y=True,
    )
    
    # Horizontal zones and lines for volatility
    fig.add_hrect(y0=90, y1=100, fillcolor='rgba(255,68,68,0.08)', 
                  line_width=0, row=1, col=1, secondary_y=True)
    fig.add_hrect(y0=75, y1=90, fillcolor='rgba(240,165,0,0.06)', 
                  line_width=0, row=1, col=1, secondary_y=True)
    fig.add_hline(y=90, line_color='#ff4444', line_dash='dash', line_width=1, 
                  row=1, col=1, secondary_y=True)
    fig.add_hline(y=75, line_color='#f0a500', line_dash='dash', line_width=1, 
                  row=1, col=1, secondary_y=True)
    
    # --- Subplot 2: Cross-pair comparison ---
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[cfg['vol_col']],
            mode='lines',
            line=dict(color=cfg['color'], width=1.5),
            name=PAIR,
            showlegend=True,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>',
        ),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[cfg['other_vol']],
            mode='lines',
            line=dict(color='#555555', width=1),
            name=cfg['other_label'],
            showlegend=True,
            hovertemplate='%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>',
        ),
        row=2, col=1,
    )
    
    # --- Apply theme ---
    fig.update_layout(**_base_layout())
    _style_axes(fig)
    
    # Set x-axis range
    fig.update_xaxes(range=[cutoff_str, today_str])
    
    # --- Inline end-labels ---
    last_x = df.index[-1]
    latest_vol = df[cfg['vol_col']].iloc[-1]
    latest_pct = df[cfg['pct_col']].iloc[-1]
    
    inline_annotations = [
        # Volatility value
        dict(
            x=last_x,
            y=latest_vol,
            text=f"  {latest_vol:.2f}%",
            xref='x', yref='y',
            xanchor='left', showarrow=False,
            font=dict(size=9, color=cfg['color']),
        ),
        # Percentile value
        dict(
            x=last_x,
            y=latest_pct,
            text=f"  {latest_pct:.0f}th pct",
            xref='x', yref='y',
            xanchor='left', showarrow=False,
            font=dict(size=9, color='#ffffff'),
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
            text="CROSS-PAIR VOL COMPARISON",
            x=0.01, y=0.4,
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
# MAIN BLOCK - TEST ALL FUNCTIONS
# ============================================================================

if __name__ == "__main__":
    import plotly.io as pio
    config = dict(scrollZoom=True, displayModeBar=False)
    
    for pair in ['eurusd', 'usdjpy', 'usdinr']:
        fig = build_fundamentals_chart(pair)
        pio.write_html(fig, f'proto_{pair}_fundamentals.html', config=config)
        print(f"saved: proto_{pair}_fundamentals.html")
    
    for pair in ['eurusd', 'usdjpy']:
        fig = build_positioning_chart(pair)
        pio.write_html(fig, f'proto_{pair}_positioning.html', config=config)
        print(f"saved: proto_{pair}_positioning.html")
        
        fig = build_vol_correlation_chart(pair)
        if fig is not None:
            pio.write_html(fig, f'proto_{pair}_vol_correlation.html', config=config)
            print(f"saved: proto_{pair}_vol_correlation.html")
