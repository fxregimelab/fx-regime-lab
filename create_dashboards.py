# create_dashboards.py
# produces four distinct chart files per run:
#   fundamentals and positioning for each FX pair (EUR/USD, USD/JPY)
#   fundamentals = price + spreads
#   positioning   = percentile panels for Lev Money and Asset Manager

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import os
from datetime import datetime

TODAY = datetime.today().strftime('%Y-%m-%d')

# styling constants
GRID_COLOR    = '#ecf0f1'
GRID_LW       = 0.5
GRID_ALPHA     = 0.7
AXIS_BG        = '#fafafa'
FIG_BG         = '#ffffff'
SPREAD_BLUE    = '#2980b9'
SPREAD_ORANGE  = '#e67e22'
BAR_GREEN      = '#27ae60'
BAR_RED        = '#e74c3c'
PCT_LINE_COLOR = '#1a1a2e'
ASSETMGR_LINE  = '#8e44ad'
THRESH_RED     = '#c0392b'
THRESH_GREEN   = '#1e8449'
ZERO_LINE_CLR  = '#2c3e50'

SUBTITLE_SIZE  = 10
SUBTITLE_COLOR = '#4a4a4a'


def load_data():
    path = "data/latest_with_cot.csv"
    if not os.path.exists(path):
        print(f"ERROR: {path} not found")
        print("Run pipeline.py and cot_pipeline.py first")
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    print(f"loaded: {len(df)} rows, {df.shape[1]} columns")
    return df


def _style_ax_basic(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_facecolor(AXIS_BG)
    ax.grid(color=GRID_COLOR, linewidth=GRID_LW, alpha=GRID_ALPHA)


def ordinal(n):
    """Return ordinal string for integer (1st, 2nd, 3rd, 4th...)."""
    try:
        n = int(n)
    except Exception:
        return str(n)
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _parse_key_levels(value):
    """Parse key level from text format like '1.2345 (5)' -> (1.2345, 5)."""
    if pd.isna(value) or value == "" or value == "—":
        return None
    try:
        # Extract price and touch count from "1.2345 (5)"
        parts = str(value).split()
        if len(parts) >= 1:
            price = float(parts[0])
            touches = int(parts[1].strip('()')) if len(parts) > 1 else 1
            return (price, touches)
    except Exception:
        pass
    return None


def _positioning_panel(ax, pct_series, net_series, label, color_line):
    """Build a single percentile/net panel per specification."""
    ax.set_facecolor(AXIS_BG)
    ax.grid(axis='x', visible=False)
    ax.grid(axis='y', color=GRID_COLOR, linewidth=GRID_LW, alpha=GRID_ALPHA)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # percentile line
    ax.plot(pct_series.index, pct_series, color=color_line, linewidth=2.0)
    ax.set_ylim(0, 100)
    ax.set_ylabel('percentile')

    # fill zones
    ax.fill_between(pct_series.index, 80, pct_series.where(pct_series > 80),
                    color='#e74c3c', alpha=0.25)
    ax.fill_between(pct_series.index, pct_series.where(pct_series < 20), 20,
                    color='#27ae60', alpha=0.25)
    ax.fill_between(pct_series.index, 20, 80, color='#f0f0f0', alpha=0.3)

    # threshold lines
    ax.axhline(80, color=THRESH_RED, linestyle='--', linewidth=1.2, alpha=0.7)
    ax.axhline(20, color=THRESH_GREEN, linestyle='--', linewidth=1.2, alpha=0.7)
    ax.axhline(50, color='gray', linestyle='-', linewidth=0.8, alpha=0.4)

    # regime watermark and corner labels
    latest = pct_series.iloc[-1]
    if latest >= 80:
        regime_text, regime_bg_color = "CROWDED LONG", '#c0392b'
    elif latest <= 20:
        regime_text, regime_bg_color = "CROWDED SHORT", '#1e8449'
    else:
        regime_text, regime_bg_color = "NEUTRAL", '#7f8c8d'
    ax.text(0.75, 0.5, regime_text, transform=ax.transAxes,
            fontsize=14, fontweight='bold', ha='center', va='center',
            color=regime_bg_color, alpha=0.15)

    # percentile number in top-right corner
    pct_int = int(latest)
    ax.text(0.98, 0.98, f"{ordinal(pct_int)} pct",
            transform=ax.transAxes,
            fontsize=10, fontweight='bold',
            color=color_line,
            ha='right', va='top',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                      alpha=0.85, edgecolor='none'))

    # regime label just below percentile label
    ax.text(0.98, 0.88, regime_text,
            transform=ax.transAxes,
            fontsize=10, fontweight='bold',
            color='white',
            ha='right', va='top',
            bbox=dict(boxstyle='round,pad=0.3',
                      facecolor=regime_bg_color,
                      alpha=0.9, edgecolor='none'))

    # net annotation
    net_cur = net_series.iloc[-1]
    net_label = 'LONG' if net_cur >= 0 else 'SHORT'
    ax.text(0.02, 0.02,
            f"current: {net_cur:+,.0f} contracts ({net_label})",
            transform=ax.transAxes, fontsize=8, color='#666666', va='bottom')

    ax.set_title(f"{label} Positioning (3Y percentile)",
                 fontsize=SUBTITLE_SIZE, color=SUBTITLE_COLOR)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
    ax.tick_params(axis='x', rotation=30)


def create_fundamentals_chart(df, config):
    """Price + spreads + regime correlation chart"""
    print(f"creating fundamentals chart for {config['name']}")

    # enforce common start date slice
    d = df[df.index >= config['start_date']].copy()
    x_min = d.index[0]
    x_max = d.index[-1]

    fig, axes = plt.subplots(3, 1, figsize=(14, 12),
                             gridspec_kw={'height_ratios': [1.2, 1, 1]},
                             facecolor=FIG_BG)
    fig.suptitle(f"{config['name']} — Fundamentals — {TODAY}",
                 fontsize=13, fontweight='bold', y=0.98)
    fmt = mdates.DateFormatter('%b %y')

    # Panel 1: price + 200d MA
    ax = axes[0]
    _style_ax_basic(ax)

    # shading for yield curve inversion (US 10Y minus 2Y < 0)
    inverted = d['US_curve'] < 0
    ax.fill_between(d.index, 0, 1,
                    where=inverted,
                    transform=ax.get_xaxis_transform(),
                    color='#e8d5f5', alpha=0.4,
                    label='Yield curve inverted')

    price = d[config['price_col']]
    ax.plot(d.index, price, color=config['color_price'], linewidth=1.5,
            label=config['price_label'])
    ma = price.rolling(200).mean()
    ax.plot(d.index, ma, color=config['color_price'], linewidth=1.0,
            linestyle='--', alpha=0.4, label='200D MA')
    latest = price.iloc[-1]
    ax.annotate(f"{latest:.4f}", xy=(d.index[-1], latest),
                xytext=(10, 0), textcoords='offset points',
                fontsize=11, color=config['color_price'], fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                          alpha=0.85, edgecolor='none'))
    ax.set_title(config['price_label'], fontsize=SUBTITLE_SIZE, color=SUBTITLE_COLOR)
    ax.set_ylabel(config['price_label'])
    ax.xaxis.set_major_formatter(fmt)
    ax.tick_params(axis='x', rotation=30)
    ax.legend(fontsize=8, loc='lower right')
    ax.set_xlim(x_min, x_max)

    # Add key levels to price panel
    pair = config.get('pair', 'EURUSD')  # EUR or JPY in the pair column names
    last_row = df.iloc[-1]
    
    # Support levels (green, dashed)
    for i in range(1, 4):
        s_col = f"{pair}_S{i}"
        if s_col in df.columns:
            level_data = _parse_key_levels(last_row.get(s_col))
            if level_data:
                price, touches = level_data
                ax.axhline(y=price, color='#27ae60', linestyle='--', linewidth=1.0, alpha=0.6)
                ax.text(x_max, price, f"  S{i}: {price:.4f}({touches})",
                       fontsize=7, va='center', color='#27ae60', alpha=0.8)
    
    # Resistance levels (red, dashed)
    for i in range(1, 4):
        r_col = f"{pair}_R{i}"
        if r_col in df.columns:
            level_data = _parse_key_levels(last_row.get(r_col))
            if level_data:
                price, touches = level_data
                ax.axhline(y=price, color='#e74c3c', linestyle='--', linewidth=1.0, alpha=0.6)
                ax.text(x_max, price, f"  R{i}: {price:.4f}({touches})",
                       fontsize=7, va='center', color='#e74c3c', alpha=0.8)

    # Panel 2: spreads
    ax = axes[1]
    _style_ax_basic(ax)
    spread_10y = d[config['spread_col_10y']]
    spread_2y  = d[config['spread_col_2y']]
    ax.plot(d.index, spread_10y, color=SPREAD_BLUE, linewidth=1.8,
            label=config['spread_10y_label'])
    ax.plot(d.index, spread_2y, color=SPREAD_ORANGE, linewidth=1.8,
            label=config['spread_2y_label'])
    ax.axhline(y=0, color=ZERO_LINE_CLR, linewidth=1.2,
               linestyle='--', alpha=0.6)
    ax.set_title(f"Rate Differentials (pp)  |  {config['spread_desc']}",
                 fontsize=SUBTITLE_SIZE, color=SUBTITLE_COLOR)
    ax.set_ylabel('spread (pp)')
    ax.xaxis.set_major_formatter(fmt)
    ax.tick_params(axis='x', rotation=30)
    ax.legend(fontsize=8, loc='best')
    ax.set_xlim(x_min, x_max)

    # Panel 3: regime correlation
    ax = axes[2]
    _style_ax_basic(ax)
    
    corr_col = config['corr_col']
    if corr_col in d.columns:
        corr_series = d[corr_col].dropna()
        ax.plot(corr_series.index, corr_series, color='#1a1a2e', linewidth=1.8,
                label='60D rolling correlation')
        
        # threshold lines
        ax.axhline(y=0.6, color=THRESH_GREEN, linestyle='--', linewidth=1.3, alpha=0.8,
                   label='0.60 (INTACT)')
        ax.axhline(y=0.3, color=THRESH_RED, linestyle='--', linewidth=1.3, alpha=0.8,
                   label='0.30 (BROKEN)')
        ax.axhline(y=0, color=ZERO_LINE_CLR, linewidth=1.0, linestyle='-', alpha=0.5)
        
        # zone shading
        ax.fill_between(corr_series.index, 0.6, 1.0, color=THRESH_GREEN, alpha=0.08)
        ax.fill_between(corr_series.index, 0.3, 0.6, color='#f39c12', alpha=0.06)
        ax.fill_between(corr_series.index, -1.0, 0.3, color=THRESH_RED, alpha=0.08)
        
        # annotation at end
        latest_corr = corr_series.iloc[-1]
        ax.annotate(f"{latest_corr:+.3f}", xy=(corr_series.index[-1], latest_corr),
                    xytext=(-10, 0), textcoords='offset points',
                    fontsize=10, fontweight='bold', ha='right', va='center',
                    color='#1a1a2e')
        
        ax.set_ylim(-1, 1)
        ax.set_title(f"Regime Correlation (60D rolling | spread vs {config['price_label']} move)",
                     fontsize=SUBTITLE_SIZE, color=SUBTITLE_COLOR)
        ax.set_ylabel('correlation')
        ax.xaxis.set_major_formatter(fmt)
        ax.tick_params(axis='x', rotation=30)
        ax.legend(fontsize=8, loc='best')
        ax.set_xlim(x_min, x_max)
    else:
        ax.text(0.5, 0.5, 'Correlation data not available',
                transform=ax.transAxes, fontsize=11, ha='center', va='center',
                color='#888888')

    plt.tight_layout(pad=2.0, h_pad=2.5)
    os.makedirs('charts', exist_ok=True)
    path = f"charts/{config['filename']}_fundamentals_{TODAY.replace('-','')}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=FIG_BG)
    print(f"saved: {path}")
    plt.close()
    return path


def create_positioning_chart(df, config):
    print(f"creating positioning chart for {config['name']}")

    # slice using common start date, then compute range
    d = df[df.index >= config['start_date']].copy()
    x_min = d.index[0]
    x_max = d.index[-1]

    fig, axes = plt.subplots(2, 1, figsize=(14, 9),
                             gridspec_kw={'height_ratios': [1, 1]},
                             facecolor=FIG_BG)
    fig.suptitle(f"{config['name']} — Positioning — {TODAY}",
                 fontsize=13, fontweight='bold', y=0.98)

    # Lev Money
    pct = d[config['lev_pct_col']].dropna()
    net = d[config['lev_net_col']].dropna()
    _positioning_panel(axes[0], pct, net, 'Lev Money', PCT_LINE_COLOR)
    axes[0].set_xlim(x_min, x_max)

    # Asset Manager
    pct = d[config['assetmgr_pct_col']].dropna()
    net = d[config['assetmgr_net_col']].dropna()
    _positioning_panel(axes[1], pct, net, 'Asset Manager', ASSETMGR_LINE)
    axes[1].set_xlim(x_min, x_max)

    plt.tight_layout(pad=2.0, h_pad=2.5)
    os.makedirs('charts', exist_ok=True)
    path = f"charts/{config['filename']}_positioning_{TODAY.replace('-','')}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=FIG_BG)
    print(f"saved: {path}")
    plt.close()
    return path


def create_vol_chart(df, pair_config):
    """Volatility chart: realized vol + percentile, with cross-pair comparison."""
    print(f"creating volatility chart for {pair_config['price_label']}")
    
    # slice to common start date (ignore earlier lookback settings)
    df_recent = df[df.index >= pair_config['start_date']].copy()
    # x-range derived from the sliced dataset
    x_min = df_recent.index[0]
    x_max = df_recent.index[-1]
    
    vol_series = df_recent[pair_config['vol_col']].dropna()
    pct_series = df_recent[pair_config['pct_col']].dropna()
    
    # determine regime from latest percentile
    latest_pct = pct_series.iloc[-1] if len(pct_series) > 0 else 50
    if latest_pct >= 90:
        regime_text, regime_bg_color = "EXTREME", '#c0392b'
    elif latest_pct >= 75:
        regime_text, regime_bg_color = "ELEVATED", '#e67e22'
    else:
        regime_text, regime_bg_color = "NORMAL", '#7f8c8d'
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 9),
                             gridspec_kw={'height_ratios': [1, 1]},
                             facecolor=FIG_BG)
    fig.suptitle(f"{pair_config['price_label']} — Volatility — {TODAY}",
                 fontsize=13, fontweight='bold', y=0.98)
    
    # ========== PANEL 1: Realized vol with percentile overlay ==========
    ax1 = axes[0]
    _style_ax_basic(ax1)
    
    # primary axis: vol30 as filled area
    ax1.fill_between(vol_series.index, 0, vol_series,
                     color='#5dade2', alpha=0.4, label=f"{pair_config['price_label']} vol30")
    ax1.plot(vol_series.index, vol_series, color='#5dade2', linewidth=1.5)
    ax1.set_ylabel(pair_config['vol_col_label'], fontsize=SUBTITLE_SIZE)
    ax1.set_ylim(0, vol_series.max() * 1.2)
    
    # secondary axis: percentile
    ax1_r = ax1.twinx()
    ax1_r.plot(pct_series.index, pct_series, color='#1a1a2e', linewidth=2, zorder=5,
               label=f"{pair_config['price_label']} percentile")
    ax1_r.set_ylabel('percentile', fontsize=SUBTITLE_SIZE)
    ax1_r.set_ylim(0, 100)
    
    # zone shading on secondary axis
    ax1_r.fill_between(pct_series.index, 90, 100, color='#c0392b', alpha=0.08)
    ax1_r.fill_between(pct_series.index, 75, 90, color='#e67e22', alpha=0.06)
    
    # threshold lines on secondary axis
    ax1_r.axhline(90, color='#c0392b', linestyle='--', linewidth=1.5, alpha=0.8, label='90th (EXTREME)')
    ax1_r.axhline(75, color='#e67e22', linestyle='--', linewidth=1.5, alpha=0.8, label='75th (ELEVATED)')
    ax1_r.axhline(50, color='gray', linestyle='-', linewidth=0.8, alpha=0.4)
    
    # regime watermark and corner labels
    ax1.text(0.75, 0.5, regime_text, transform=ax1.transAxes,
            fontsize=14, fontweight='bold', ha='center', va='center',
            color=regime_bg_color, alpha=0.15)
    
    # percentile box in upper right
    ax1.text(0.98, 0.98, f"{ordinal(int(latest_pct))} pct",
            transform=ax1.transAxes,
            fontsize=10, fontweight='bold',
            color='white',
            ha='right', va='top',
            bbox=dict(boxstyle='round,pad=0.2', facecolor=regime_bg_color,
                      alpha=0.9, edgecolor='none'))
    
    # regime box below percentile
    ax1.text(0.98, 0.88, regime_text,
            transform=ax1.transAxes,
            fontsize=10, fontweight='bold',
            color='white',
            ha='right', va='top',
            bbox=dict(boxstyle='round,pad=0.3',
                      facecolor=regime_bg_color,
                      alpha=0.9, edgecolor='none'))
    
    # annotations on right edges
    latest_vol = vol_series.iloc[-1]
    ax1.annotate(f"{latest_vol:.1f}%", xy=(vol_series.index[-1], latest_vol),
                xytext=(-10, 0), textcoords='offset points',
                fontsize=10, fontweight='bold', ha='right', va='center',
                color='#5dade2')
    ax1_r.annotate(f"{int(latest_pct)}th", xy=(pct_series.index[-1], latest_pct),
                  xytext=(8, 0), textcoords='offset points',
                  fontsize=10, fontweight='bold', ha='left', va='center',
                  color='#1a1a2e')
    
    ax1.set_title(f"Realized Volatility 30D | {regime_text}",
                 fontsize=SUBTITLE_SIZE, color=SUBTITLE_COLOR)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
    ax1.tick_params(axis='x', rotation=30)
    ax1.set_xlim(x_min, x_max)
    ax1_r.set_xlim(x_min, x_max)
    
    # combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_r.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc='lower right')
    
    # ========== PANEL 2: Cross-pair comparison ==========
    ax2 = axes[1]
    _style_ax_basic(ax2)
    
    # both pairs on same axis
    eurusd_vol = df_recent['EURUSD_vol30'].dropna()
    usdjpy_vol = df_recent['USDJPY_vol30'].dropna()
    
    ax2.plot(eurusd_vol.index, eurusd_vol, color='#1f77b4', linewidth=1.8, label='EUR/USD')
    ax2.plot(usdjpy_vol.index, usdjpy_vol, color='#ff7f0e', linewidth=1.8, label='USD/JPY')
    
    # threshold line: 75th percentile of primary pair's vol (actual vol value)
    primary_vol = df_recent[pair_config['vol_col']].dropna()
    primary_vol_75th = primary_vol.quantile(0.75)
    ax2.axhline(primary_vol_75th, color='#1f77b4', linestyle='--', linewidth=1.2, alpha=0.6,
               label=f"{pair_config['price_label']} 75th ({primary_vol_75th:.1f}%)")
    
    ax2.set_ylabel('annualized vol (%)')
    ax2.set_title('Cross-Pair Vol Comparison | spike in both = systemic risk event',
                 fontsize=SUBTITLE_SIZE, color=SUBTITLE_COLOR)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
    ax2.tick_params(axis='x', rotation=30)
    ax2.set_xlim(x_min, x_max)
    ax2.legend(fontsize=8, loc='lower right')
    
    # annotation in lower left
    ax2.text(0.02, 0.04, 'Both elevated = Regime 3 risk',
            transform=ax2.transAxes,
            fontsize=8, color='#7f8c8d',
            ha='left', va='bottom',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                      alpha=0.7, edgecolor='none'))
    
    plt.tight_layout(pad=2.0, h_pad=2.5)
    os.makedirs('charts', exist_ok=True)
    path = f"charts/{pair_config['filename'].replace('volatility', 'volatility')}_{TODAY.replace('-', '')}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor=FIG_BG)
    print(f"saved: {path}")
    plt.close()
    return path


def create_usdinr_fundamentals_chart():
    """USD/INR price + rate differential (2 panels, standalone load)."""
    print("creating USD/INR fundamentals chart")

    path = "data/latest_with_cot.csv"
    if not os.path.exists(path):
        print(f"ERROR: {path} not found")
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)

    # last 12 months, drop rows where USDINR is null
    cutoff = pd.Timestamp(TODAY) - pd.DateOffset(months=12)
    d = df[df.index >= cutoff].dropna(subset=['USDINR']).copy()
    if len(d) == 0:
        print("ERROR: no USDINR data available")
        return None

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), facecolor='#ffffff')
    fig.suptitle(f"USD/INR -- Price + Rate Differential -- {TODAY}",
                 fontsize=13, fontweight='bold', y=0.98)

    # --- Panel 1: price ---
    ax = axes[0]
    _style_ax_basic(ax)
    price = d['USDINR']
    ax.plot(d.index, price, color='#e74c3c', linewidth=1.5)
    latest_price = float(price.iloc[-1])
    ax.annotate(f"{latest_price:.4f}",
                xy=(d.index[-1], latest_price),
                xytext=(10, 0), textcoords='offset points',
                fontsize=11, color='#e74c3c', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                          alpha=0.85, edgecolor='none'))
    ax.set_ylabel("INR per 1 USD")
    ax.set_title("USD/INR  |  UP = dollar stronger vs rupee",
                 fontsize=SUBTITLE_SIZE, color=SUBTITLE_COLOR)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
    ax.tick_params(axis='x', rotation=30)

    # --- Panel 2: rate differentials ---
    ax = axes[1]
    _style_ax_basic(ax)

    _c10y = 'US_IN_10Y_spread'
    _cpol = 'US_IN_policy_spread'
    s10y_series = d[_c10y].dropna() if _c10y in d.columns else pd.Series(dtype=float)
    spol_series = d[_cpol].dropna() if _cpol in d.columns else pd.Series(dtype=float)

    if len(s10y_series) > 0:
        ax.plot(s10y_series.index, s10y_series, color=SPREAD_BLUE, linewidth=1.8,
                label="US 2Y - IN 10Y (cross)")
    if len(spol_series) > 0:
        ax.plot(spol_series.index, spol_series, color=SPREAD_ORANGE, linewidth=1.8,
                label="US 2Y - IN policy rate")

    ax.axhline(y=0, color=ZERO_LINE_CLR, linewidth=1.2, linestyle='--', alpha=0.6)
    ax.text(d.index[0], 0, '  parity', fontsize=8, va='bottom',
            color=ZERO_LINE_CLR, alpha=0.6)

    ax.set_title("Rate Differentials (pp)  |  negative = India yields higher = INR strength",
                 fontsize=SUBTITLE_SIZE, color=SUBTITLE_COLOR)
    ax.set_ylabel("spread (pp)")
    ax.legend(fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
    ax.tick_params(axis='x', rotation=30)

    # annotate latest values — offset to avoid overlap
    if len(s10y_series) > 0 and len(spol_series) > 0:
        v10y = float(s10y_series.iloc[-1])
        vpol = float(spol_series.iloc[-1])
        y_off_10y = 8  if v10y >= vpol else -12
        y_off_pol  = -12 if v10y >= vpol else  8
        ax.annotate(f"{v10y:.2f}pp",
                    xy=(s10y_series.index[-1], v10y),
                    xytext=(-10, y_off_10y), textcoords='offset points',
                    fontsize=9, fontweight='bold', ha='right', color=SPREAD_BLUE,
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                              alpha=0.85, edgecolor=SPREAD_BLUE))
        ax.annotate(f"{vpol:.2f}pp",
                    xy=(spol_series.index[-1], vpol),
                    xytext=(-10, y_off_pol), textcoords='offset points',
                    fontsize=9, fontweight='bold', ha='right', color=SPREAD_ORANGE,
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                              alpha=0.85, edgecolor=SPREAD_ORANGE))
    elif len(s10y_series) > 0:
        v10y = float(s10y_series.iloc[-1])
        ax.annotate(f"{v10y:.2f}pp",
                    xy=(s10y_series.index[-1], v10y),
                    xytext=(-10, 8), textcoords='offset points',
                    fontsize=9, fontweight='bold', ha='right', color=SPREAD_BLUE,
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                              alpha=0.85, edgecolor=SPREAD_BLUE))
    elif len(spol_series) > 0:
        vpol = float(spol_series.iloc[-1])
        ax.annotate(f"{vpol:.2f}pp",
                    xy=(spol_series.index[-1], vpol),
                    xytext=(-10, 8), textcoords='offset points',
                    fontsize=9, fontweight='bold', ha='right', color=SPREAD_ORANGE,
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                              alpha=0.85, edgecolor=SPREAD_ORANGE))

    plt.tight_layout(pad=2.0, h_pad=2.5)
    os.makedirs('charts', exist_ok=True)
    chart_path = f"charts/usdinr_fundamentals_{TODAY}.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='#ffffff')
    plt.show(block=False)
    plt.pause(2)
    plt.close()
    print(f"saved: {chart_path}")
    return chart_path


def main():
    print("=" * 55)
    print(f"  FX DASHBOARDS REDESIGN -- {TODAY}")
    print("=" * 55 + "\n")
    df = load_data()
    if df is None:
        return

    # determine common start date where all key series are non-null
    key_cols = ['EURUSD', 'USDJPY', 'EUR_percentile', 'JPY_percentile', 
                'EURUSD_vol_pct', 'USDJPY_vol_pct']
    available = df.dropna(subset=key_cols)
    COMMON_START = available.index[0]

    # verify column names
    pct_cols = [c for c in df.columns if 'percentile' in c.lower()]
    net_cols = [c for c in df.columns if 'net_pos' in c.lower()]
    print("percentile columns:", pct_cols)
    print("net_pos columns:", net_cols)

    eur_config = {
        'name': 'EUR/USD',
        'price_col': 'EURUSD',
        'price_label': 'USD per 1 EUR',
        'price_desc': 'UP = euro stronger vs dollar',
        'color_price': '#1f77b4',
        'spread_col_10y': 'US_DE_10Y_spread',
        'spread_col_2y': 'US_DE_2Y_spread',
        'spread_10y_label': 'US 2Y - DE 10Y (cross)',
        'spread_2y_label': 'US 2Y - DE 2Y (same)',
        'spread_desc': 'narrowing = EUR/USD should rise',
        'corr_col': 'EURUSD_spread_corr_60d',
        'pair': 'EURUSD',
        'lev_pct_col': 'EUR_percentile',
        'lev_net_col': 'EUR_net_pos',
        'assetmgr_pct_col': 'EUR_assetmgr_percentile',
        'assetmgr_net_col': 'EUR_assetmgr_net',
        'filename': 'eurusd',
        # start date for slicing (common across all charts)
        'start_date': COMMON_START,
        # fundamental lookback now 36 months to align with other charts
        'lookback_months': 36,
    }

    jpy_config = {
        'name': 'USD/JPY',
        'price_col': 'USDJPY',
        'price_label': 'JPY per 1 USD',
        'price_desc': 'UP = dollar stronger vs yen',
        'color_price': '#ff7f0e',
        'spread_col_10y': 'US_JP_10Y_spread',
        'spread_col_2y': 'US_JP_2Y_spread',
        'spread_10y_label': 'US 2Y - JP 10Y (cross)',
        'spread_2y_label': 'US 2Y - JP 2Y (same)',
        'spread_desc': 'narrowing = USD/JPY should fall',
        'corr_col': 'USDJPY_spread_corr_60d',
        'pair': 'USDJPY',
        'lev_pct_col': 'JPY_percentile',
        'lev_net_col': 'JPY_net_pos',
        'assetmgr_pct_col': 'JPY_assetmgr_percentile',
        'assetmgr_net_col': 'JPY_assetmgr_net',
        'filename': 'usdjpy',
        'start_date': COMMON_START,
        'lookback_months': 36,
    }

    # volatility chart configs
    eurusd_vol_config = {
        'price_label': 'EUR/USD',
        'vol_col': 'EURUSD_vol30',
        'vol_col_label': 'annualized vol (%)',
        'pct_col': 'EURUSD_vol_pct',
        'compare_col': 'USDJPY_vol30',
        'compare_label': 'USD/JPY',
        'filename': 'eurusd_volatility',
        'start_date': COMMON_START,
        'lookback_months': 36,
    }

    usdjpy_vol_config = {
        'price_label': 'USD/JPY',
        'vol_col': 'USDJPY_vol30',
        'vol_col_label': 'annualized vol (%)',
        'pct_col': 'USDJPY_vol_pct',
        'compare_col': 'EURUSD_vol30',
        'compare_label': 'EUR/USD',
        'filename': 'usdjpy_volatility',
        'start_date': COMMON_START,
        'lookback_months': 36,
    }

    create_fundamentals_chart(df, eur_config)
    create_positioning_chart(df, eur_config)
    create_vol_chart(df, eurusd_vol_config)
    create_fundamentals_chart(df, jpy_config)
    create_positioning_chart(df, jpy_config)
    create_vol_chart(df, usdjpy_vol_config)

    print("\n[3/3] creating USD/INR fundamentals chart...")
    usdinr_path = create_usdinr_fundamentals_chart()

    print("\n" + "=" * 55)
    print("  CHARTS COMPLETE")
    print("=" * 55)
    print(f"  USD/INR fundamentals: {usdinr_path}")


if __name__ == '__main__':
    main()
