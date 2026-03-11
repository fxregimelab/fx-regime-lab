# charts/base.py
# Shared Plotly helpers used by all chart builders.
# Import from here; do NOT import directly from create_charts_plotly.

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from functools import lru_cache
from core.paths import LATEST_WITH_COT_CSV


def _base_layout(height=None):
    layout = dict(
        template='plotly_dark',
        paper_bgcolor='#0a0e1a',
        plot_bgcolor='#0d1225',
        font=dict(family='Inter, system-ui, sans-serif',
                  color='#cccccc', size=11),
        margin=dict(l=50, r=60, t=30, b=30),
        legend=dict(bgcolor='rgba(0,0,0,0)', borderwidth=0,
                    font=dict(size=10, color='#888888')),
        hovermode='x unified',
        hoverlabel=dict(bgcolor='#111827', bordercolor='#333333',
                        font=dict(color='#cccccc', size=11)),
        dragmode='pan',
        autosize=True,
    )
    if height is not None:
        layout['height'] = height
    return layout


def _style_axes(fig):
    fig.update_xaxes(showgrid=True, gridcolor='#1e1e1e', gridwidth=1,
                     showline=False, zeroline=False,
                     tickfont=dict(size=10, color='#666666'))
    fig.update_yaxes(showgrid=True, gridcolor='#1e1e1e', gridwidth=1,
                     showline=False, zeroline=False,
                     tickfont=dict(size=10, color='#666666'))
    return fig


@lru_cache(maxsize=4)
def _load_and_filter(pair=None, months=12):
    """Load latest_with_cot.csv and return (filtered_df, cutoff_date, today_date).

    The returned DataFrame index is clean 'YYYY-MM-DD' strings.
    cutoff and today are pd.Timestamp objects for use in xaxis range calculations.
    """
    try:
        df = pd.read_csv(LATEST_WITH_COT_CSV, index_col=0, parse_dates=True)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Chart data not found: {LATEST_WITH_COT_CSV}\n"
            "Run pipeline.py then cot_pipeline.py to generate it."
        )
    df.index = pd.to_datetime(df.index, utc=False).tz_localize(None)
    df.index = df.index.normalize()

    today  = pd.Timestamp.today().normalize()
    cutoff = today - pd.DateOffset(months=months)

    d = df[df.index >= cutoff].copy()
    d = d.sort_index()
    d = d[d.index.notna()].copy()
    d = d[~d.index.duplicated(keep='last')].copy()
    d.index = d.index.strftime('%Y-%m-%d')

    return d, cutoff, today


def _add_annotation(fig, x, y, text, color, row, xref, yref):
    fig.add_annotation(x=x, y=y, text=text, font=dict(size=9, color=color),
                       xanchor='left', showarrow=False,
                       xref=xref, yref=yref)
