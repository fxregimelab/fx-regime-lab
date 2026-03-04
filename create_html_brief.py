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

def fig_to_div(fig, height=480):
    if fig is None:
        return '<div style="color:#555;padding:20px;font-size:11px;">Chart unavailable</div>'
    div = pio.to_html(
        fig, 
        full_html=False,
        config=plotly_config,
        include_plotlyjs=False,
        div_id=None
    )
    return f'<div style="width:100%;height:{height}px;overflow:hidden;">{div}</div>'

# Generate all chart divs
eurusd_fund_div  = fig_to_div(build_fundamentals_chart('eurusd'), 400)
eurusd_pos_div   = fig_to_div(build_positioning_chart('eurusd'), 480)
eurusd_vol_div   = fig_to_div(build_vol_correlation_chart('eurusd'), 420)

usdjpy_fund_div  = fig_to_div(build_fundamentals_chart('usdjpy'), 400)
usdjpy_pos_div   = fig_to_div(build_positioning_chart('usdjpy'), 480)
usdjpy_vol_div   = fig_to_div(build_vol_correlation_chart('usdjpy'), 420)

usdinr_fund_div  = fig_to_div(build_fundamentals_chart('usdinr'), 360)

# ============================================================================
# Load brief data from existing generated brief
# ============================================================================
import shutil

def load_latest_brief_data():
    """Load data from latest generated brief file."""
    # Find latest brief file
    brief_files = sorted(glob.glob('briefs/brief_*.html'))
    if not brief_files:
        return None
    return brief_files[-1]

def generate_html_brief():
    """Generate complete HTML brief with Plotly charts and tabs."""
    brief_file = load_latest_brief_data()
    if not brief_file:
        print("No previous brief found. Create a text brief first with morning_brief.py")
        return
    
    # Read the previous brief as template
    with open(brief_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # FIX 3: Change overflow:hidden to overflow:visible in CSS for .chart-pane
    html_content = html_content.replace(
        '.chart-pane {\n    display: none;\n    width: 100%;\n    overflow: hidden;\n}',
        '.chart-pane {\n    display: none;\n    width: 100%;\n    overflow: visible;\n}'
    )
    
    # FIX 1: Replace the tab-click event handler with one that uses setTimeout
    old_tab_handler = '''document.querySelectorAll('.chart-tab').forEach(tab => {
  tab.addEventListener('click', function() {
    const pair = this.dataset.pair;
    const tabIdx = this.dataset.tab;
    
    // deactivate all tabs for this pair
    document.querySelectorAll(
      `.chart-tab[data-pair="${pair}"]`
    ).forEach(t => t.classList.remove('active'));
    
    // hide all panes for this pair
    document.querySelectorAll(
      `.chart-pane[data-pair="${pair}"]`
    ).forEach(p => {
      p.style.display = 'none';
    });
    
    // activate clicked tab
    this.classList.add('active');
    
    // show corresponding pane
    document.querySelector(
      `.chart-pane[data-pair="${pair}"][data-pane="${tabIdx}"]`
    ).style.display = 'block';

    // trigger plotly resize after browser has laid out the newly visible pane
    requestAnimationFrame(() => {
      const plotlyDiv = document.querySelector(
        `.chart-pane[data-pair="${pair}"][data-pane="${tabIdx}"] .js-plotly-plot`
      );
      if (plotlyDiv) {
        Plotly.relayout(plotlyDiv, {autosize: true});
      }
    });
  });
});'''

    new_tab_handler = '''document.querySelectorAll('.chart-tab').forEach(tab => {
  tab.addEventListener('click', function() {
    const pair = this.dataset.pair;
    const tabIdx = this.dataset.tab;
    
    // deactivate all tabs for this pair
    document.querySelectorAll(
      `.chart-tab[data-pair="${pair}"]`
    ).forEach(t => t.classList.remove('active'));
    
    // hide all panes for this pair
    document.querySelectorAll(
      `.chart-pane[data-pair="${pair}"]`
    ).forEach(p => {
      p.style.display = 'none';
    });
    
    // activate clicked tab
    this.classList.add('active');
    
    // show corresponding pane
    document.querySelector(
      `.chart-pane[data-pair="${pair}"][data-pane="${tabIdx}"]`
    ).style.display = 'block';

    // FIX 1: Use setTimeout with 50ms delay to give browser time to paint the block element
    setTimeout(function() {
      const plots = document.querySelectorAll(
        `.chart-pane[data-pair="${pair}"][data-pane="${tabIdx}"] .plotly-graph-div`
      );
      plots.forEach(function(plot) {
        Plotly.relayout(plot, {autosize: true});
      });
    }, 50);
  });
});

// FIX 2: Resize first visible chart on page load
window.addEventListener('load', function() {
  document.querySelectorAll(
    '.chart-pane[data-pane="0"]'
  ).forEach(function(pane) {
    const plots = pane.querySelectorAll('.plotly-graph-div');
    plots.forEach(function(plot) {
      Plotly.relayout(plot, {autosize: true});
    });
  });
});'''
    
    html_content = html_content.replace(old_tab_handler, new_tab_handler)
    
    # Save the modified brief
    os.makedirs('briefs', exist_ok=True)
    output_file = f'briefs/brief_{DATE_SLUG}.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Generated: {output_file}")

if __name__ == '__main__':
    generate_html_brief()