"""
charts/workspace.py
Generates self-contained interactive Analysis Workspace HTML pages.
Returns a complete HTML string (not a Plotly Figure object).

Called by:
  - build_workspace_html(pair)  →  per-card workspace (all series, pair pre-selected)
  - build_global_workspace_html() →  global workspace (all pairs together)
"""

import json
import math
import html as _html
import pandas as pd
from core.paths import LATEST_WITH_COT_CSV

# ---------------------------------------------------------------------------
# Series catalogue  (csv_col, label, group, axis_type, color)
# axis_type: 'price' | 'corr' | 'spread'
# ---------------------------------------------------------------------------
SERIES_CATALOGUE = [
    # FX Prices
    ("EURUSD",               "EUR/USD",          "FX Prices",    "price",  "#4da6ff"),
    ("USDJPY",               "USD/JPY",          "FX Prices",    "price",  "#ff9944"),
    ("USDINR",               "USD/INR",          "FX Prices",    "price",  "#e74c3c"),
    ("DXY",                  "DXY",              "FX Prices",    "price",  "#e2e2e2"),
    # Commodities
    ("Brent",                "Brent ($/bbl)",    "Commodities",  "price",  "#f0a500"),
    ("Gold",                 "Gold ($/oz)",      "Commodities",  "price",  "#ffd700"),
    # Oil Correlations
    ("oil_eurusd_corr_60d",  "Oil↔EUR/USD 60D",  "Oil Corr",    "corr",   "#ff6b6b"),
    ("oil_usdjpy_corr_60d",  "Oil↔USD/JPY 60D",  "Oil Corr",    "corr",   "#ff9b7a"),
    ("oil_inr_corr_60d",     "Oil↔USD/INR 60D",  "Oil Corr",    "corr",   "#ffb89a"),
    # DXY Correlations
    ("dxy_eurusd_corr_60d",  "DXY↔EUR/USD 60D",  "DXY Corr",   "corr",   "#64d2a0"),
    ("dxy_usdjpy_corr_60d",  "DXY↔USD/JPY 60D",  "DXY Corr",   "corr",   "#4bbf8c"),
    ("dxy_inr_corr_60d",     "DXY↔USD/INR 60D",  "DXY Corr",   "corr",   "#8de8c0"),
    # Regime Correlations
    ("EURUSD_spread_corr_60d", "Regime↔EUR/USD",  "Regime Corr", "corr",  "#aaaaaa"),
    ("USDJPY_spread_corr_60d", "Regime↔USD/JPY",  "Regime Corr", "corr",  "#888888"),
    # Rate Spreads
    ("US_DE_10Y_spread",     "US-DE 10Y",        "Rate Spreads", "spread", "#7dd3fc"),
    ("US_DE_2Y_spread",      "US-DE 2Y",         "Rate Spreads", "spread", "#38bdf8"),
    ("US_JP_10Y_spread",     "US-JP 10Y",        "Rate Spreads", "spread", "#fda4af"),
    ("US_JP_2Y_spread",      "US-JP 2Y",         "Rate Spreads", "spread", "#fb7185"),
    ("US_IN_10Y_spread",     "US-IN 10Y",        "Rate Spreads", "spread", "#d8b4fe"),
]

# Default checked series per pair (pair=None means global)
DEFAULTS = {
    "eurusd": {"EURUSD", "Brent", "oil_eurusd_corr_60d", "dxy_eurusd_corr_60d"},
    "usdjpy": {"USDJPY", "Brent", "oil_usdjpy_corr_60d", "dxy_usdjpy_corr_60d"},
    "usdinr": {"USDINR", "Brent", "oil_inr_corr_60d",    "dxy_inr_corr_60d"},
    None:     {"EURUSD", "USDJPY", "USDINR", "Brent"},
}


def _load_series(months=14):
    """Load last `months` months of data from the master CSV."""
    try:
        df = pd.read_csv(LATEST_WITH_COT_CSV, index_col=0, parse_dates=True)
    except Exception:
        return None
    df.index = pd.to_datetime(df.index, utc=False).tz_localize(None).normalize()
    df = df[~df.index.duplicated(keep='last')].sort_index()
    cutoff = pd.Timestamp.today().normalize() - pd.DateOffset(months=months)
    df = df[df.index >= cutoff]
    # Convert index to string dates for JSON
    df.index = df.index.strftime('%Y-%m-%d')
    return df


def _build_data_json(df):
    """Build the DATA JSON object embedded in the workspace HTML."""
    available = [c for (c, *_) in SERIES_CATALOGUE if c in df.columns]
    dates = list(df.index)
    series = {}
    for col in available:
        vals = df[col].tolist()
        # Replace NaN with null for JSON
        series[col] = [None if pd.isna(v) else round(float(v), 6) for v in vals]

    meta = {}
    for col, label, group, axis_type, color in SERIES_CATALOGUE:
        if col in available:
            meta[col] = {"label": label, "group": group, "type": axis_type, "color": color}

    return json.dumps({"dates": dates, "series": series, "meta": meta}, separators=(',', ':'))


def _build_sidebar_html(pair, available_cols):
    """Build the sidebar checkbox groups HTML."""
    defaults = DEFAULTS.get(pair, DEFAULTS[None])
    groups = {}
    for col, label, group, axis_type, color in SERIES_CATALOGUE:
        if col not in available_cols:
            continue
        groups.setdefault(group, []).append((col, label, color, col in defaults))

    html = []
    for group_name, items in groups.items():
        html.append(f'<div class="grp-head">{group_name}</div>')
        for col, label, color, checked in items:
            chk = 'checked' if checked else ''
            html.append(
                f'<label class="s-row">'
                f'<input type="checkbox" data-key="{col}" {chk}>'
                f'<span class="s-dot" style="background:{color}"></span>'
                f'<span class="s-label" title="{label}">{label}</span>'
                f'</label>'
            )
    return '\n'.join(html)


def _build_options_html(available_cols):
    """Build <option> elements for the correlation dropdowns."""
    opts = []
    for col, label, group, *_ in SERIES_CATALOGUE:
        if col in available_cols:
            opts.append(f'<option value="{col}">{label}</option>')
    return '\n'.join(opts)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------
def build_workspace_html(pair=None):
    """
    Generate a self-contained interactive workspace HTML page.
    pair: 'eurusd' | 'usdjpy' | 'usdinr' | None (global)
    """
    df = _load_series()
    if df is None:
        return '<div style="padding:20px;color:#555">Data unavailable</div>'

    available_cols = set(c for (c, *_) in SERIES_CATALOGUE if c in df.columns)
    data_json   = _build_data_json(df)
    sidebar_html = _build_sidebar_html(pair, available_cols)
    options_html = _build_options_html(available_cols)

    date_from = _html.escape(str(df.index[0]), quote=True) if len(df) > 0 else ''
    date_to   = _html.escape(str(df.index[-1]), quote=True) if len(df) > 0 else ''

    title = {
        'eurusd': 'EUR/USD · Analysis Workspace',
        'usdjpy': 'USD/JPY · Analysis Workspace',
        'usdinr': 'USD/INR · Analysis Workspace',
        None:     'All Pairs · Analysis Workspace',
    }.get(pair, 'Analysis Workspace')

    # Second-y label default selection depends on pair
    corr_a_default = {
        'eurusd': 'oil_eurusd_corr_60d',
        'usdjpy': 'oil_usdjpy_corr_60d',
        'usdinr': 'oil_inr_corr_60d',
        None:     'oil_eurusd_corr_60d',
    }.get(pair, 'oil_eurusd_corr_60d')

    corr_b_default = {
        'eurusd': 'dxy_eurusd_corr_60d',
        'usdjpy': 'dxy_usdjpy_corr_60d',
        'usdinr': 'dxy_inr_corr_60d',
        None:     'dxy_eurusd_corr_60d',
    }.get(pair, 'dxy_eurusd_corr_60d')

    # Insert selected attribute for defaults in options
    opts_a = options_html.replace(f'value="{corr_a_default}"', f'value="{corr_a_default}" selected')
    opts_b = options_html.replace(f'value="{corr_b_default}"', f'value="{corr_b_default}" selected')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" crossorigin="anonymous"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d0d0d;color:#cccccc;font-family:'Inter',system-ui,sans-serif;font-size:12px;height:100vh;display:flex;flex-direction:column;overflow:hidden}}
#ctrl{{height:40px;background:#1a1a1a;border-bottom:1px solid #2a2a2a;display:flex;align-items:center;gap:10px;padding:0 14px;flex-shrink:0}}
#ctrl-title{{color:#444;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;white-space:nowrap}}
.ctrl-sep{{width:1px;height:18px;background:#2a2a2a;margin:0 2px}}
#ctrl input[type=date]{{background:#1e1e1e;border:1px solid #2a2a2a;color:#aaa;padding:3px 6px;font-size:11px;border-radius:3px;width:110px}}
#ctrl label{{display:flex;align-items:center;gap:5px;color:#777;font-size:11px;cursor:pointer;white-space:nowrap}}
#ctrl label:hover{{color:#aaa}}
#ctrl input[type=checkbox]{{accent-color:#4da6ff;cursor:pointer}}
.ctrl-btn{{background:#1e1e1e;border:1px solid #2a2a2a;color:#777;padding:3px 10px;font-size:11px;cursor:pointer;border-radius:3px}}
.ctrl-btn:hover{{background:#252525;color:#aaa}}
#ctrl-hint{{flex:1;text-align:right;color:#333;font-size:9px;font-style:italic}}
#main{{display:flex;flex:1;overflow:hidden}}
#sidebar{{width:192px;flex-shrink:0;background:#141414;border-right:1px solid #2a2a2a;overflow-y:auto;display:flex;flex-direction:column}}
.grp-head{{color:#444;font-size:9px;letter-spacing:1px;text-transform:uppercase;padding:9px 12px 4px;border-top:1px solid #1e1e1e}}
.grp-head:first-child{{border-top:none;padding-top:10px}}
.s-row{{display:flex;align-items:center;gap:7px;padding:3px 12px;cursor:pointer;user-select:none}}
.s-row:hover{{background:#1a1a1a}}
.s-row input[type=checkbox]{{cursor:pointer;accent-color:#4da6ff;width:12px;height:12px;flex-shrink:0}}
.s-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
.s-label{{color:#999;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
#corr-box{{margin:10px 8px 12px;background:#111;border:1px solid #222;border-radius:4px;padding:8px 10px}}
.corr-title{{color:#444;font-size:9px;letter-spacing:1px;text-transform:uppercase;margin-bottom:7px}}
.corr-sel{{width:100%;background:#1a1a1a;border:1px solid #252525;color:#aaa;padding:3px 5px;font-size:10px;margin-bottom:5px;border-radius:2px}}
#corr-val{{text-align:center;font-size:18px;font-weight:600;color:#ffffff;padding:5px 0 1px;font-variant-numeric:tabular-nums;letter-spacing:-0.5px}}
#corr-label{{text-align:center;font-size:9px;color:#444;margin-bottom:2px}}
#chart-area{{flex:1;overflow:hidden;position:relative;background:#0d0d0d}}
#chart{{width:100%;height:100%}}
#main.sidebar-hidden #sidebar{{display:none}}
</style></head>
<body>
<div id="ctrl">
  <span id="ctrl-title">{title}</span>
  <div class="ctrl-sep"></div>
  <span style="color:#555;font-size:10px">From</span>
  <input type="date" id="dt-from" value="{date_from}">
  <span style="color:#555;font-size:10px">To</span>
  <input type="date" id="dt-to" value="{date_to}">
  <div class="ctrl-sep"></div>
  <label><input type="checkbox" id="cb-norm"> Normalize to 100</label>
  <button class="ctrl-btn" id="btn-reset">Reset</button>
  <div class="ctrl-sep"></div>
  <button class="ctrl-btn" id="btn-sidebar">&#9664; Hide</button>
  <span id="ctrl-hint">scroll=zoom · drag=pan · click legend=toggle</span>
</div>
<div id="main">
  <div id="sidebar">
{sidebar_html}
    <div id="corr-box">
      <div class="corr-title">Correlation Table</div>
      <select id="corr-a" class="corr-sel">{opts_a}</select>
      <select id="corr-b" class="corr-sel">{opts_b}</select>
      <div id="corr-val">—</div>
      <div id="corr-label">Pearson · selected window</div>
    </div>
  </div>
  <div id="chart-area"><div id="chart"></div></div>
</div>
<script>
const DATA = {data_json};

const LAYOUT_BASE = {{
  paper_bgcolor:'#0d0d0d', plot_bgcolor:'#141414',
  font:{{family:"'Inter',system-ui,sans-serif",size:11,color:'#cccccc'}},
  margin:{{l:52,r:52,t:18,b:36}},
  hovermode:'x unified',
  hoverlabel:{{bgcolor:'#1a1a1a',bordercolor:'#333',font:{{size:10,color:'#ccc'}}}},
  legend:{{orientation:'h',x:0,y:-0.08,xanchor:'left',yanchor:'top',
    bgcolor:'rgba(13,13,13,0)',font:{{size:9,color:'#888'}},itemsizing:'constant'}},
  xaxis:{{
    type:'date', gridcolor:'#1e1e1e', gridwidth:1, showline:false, zeroline:false,
    tickfont:{{size:10,color:'#555'}}, showspikes:true, spikecolor:'#333',
    spikethickness:1, spikemode:'across'
  }},
  yaxis:{{
    gridcolor:'#1e1e1e', gridwidth:1, showline:false, zeroline:false,
    tickfont:{{size:10,color:'#555'}}, showspikes:false
  }},
  yaxis2:{{
    overlaying:'y', side:'right', range:[-1.1,1.1],
    gridcolor:'transparent', showline:false, zeroline:true, zerolinecolor:'#333',
    tickfont:{{size:9,color:'#444'}}, title:{{text:'corr',font:{{size:9,color:'#444'}}}},
    fixedrange:true
  }}
}};

const CONFIG = {{scrollZoom:true,displayModeBar:false,responsive:true}};

function getChecked() {{
  return Array.from(document.querySelectorAll('#sidebar input[type=checkbox][data-key]:checked'))
    .map(cb => cb.dataset.key);
}}

function filterByDate(keys) {{
  const from = document.getElementById('dt-from').value;
  const to   = document.getElementById('dt-to').value;
  const dates = DATA.dates;
  const i0 = from ? dates.findIndex(d => d >= from) : 0;
  const i1 = to   ? dates.findLastIndex(d => d <= to) + 1 : dates.length;
  const slicedDates = dates.slice(i0, i1);
  const slicedSeries = {{}};
  keys.forEach(k => {{
    if (DATA.series[k]) slicedSeries[k] = DATA.series[k].slice(i0, i1);
  }});
  return {{dates: slicedDates, series: slicedSeries}};
}}

function normalize100(vals) {{
  const first = vals.find(v => v !== null && v !== undefined);
  if (first == null || first === 0) return vals;
  return vals.map(v => v === null ? null : (v / first) * 100);
}}

function buildTraces(keys, data, doNorm) {{
  return keys.filter(k => DATA.meta[k]).map(k => {{
    const m = DATA.meta[k];
    const isCorr = m.type === 'corr';
    let yvals = data.series[k] || [];
    if (doNorm && !isCorr) yvals = normalize100(yvals);
    return {{
      x: data.dates, y: yvals,
      type: 'scatter', mode: 'lines',
      name: m.label,
      line: {{color: m.color, width: 1.5}},
      yaxis: isCorr ? 'y2' : 'y',
      hovertemplate: '%{{x|%d %b %Y}}<br>%{{y:.4f}}<extra>' + m.label + '</extra>'
    }};
  }});
}}

function buildLayout(doNorm, data) {{
  const layout = JSON.parse(JSON.stringify(LAYOUT_BASE));
  if (data.dates.length > 0) {{
    layout.xaxis.range = [data.dates[0], data.dates[data.dates.length-1]];
  }}
  if (doNorm) {{
    layout.yaxis.title = {{text:'Indexed (100 = start)', font:{{size:9,color:'#444'}}}};
  }} else {{
    layout.yaxis.title = {{text:'', font:{{size:9,color:'#444'}}}};
  }}
  // Add zero line for corr axis
  layout.shapes = [{{
    type:'line', xref:'paper', x0:0, x1:1,
    yref:'y2', y0:0, y1:0,
    line:{{color:'#2a2a2a', width:1}}
  }}];
  return layout;
}}

function update() {{
  const keys   = getChecked();
  const doNorm = document.getElementById('cb-norm').checked;
  const data   = filterByDate(keys);
  const traces = buildTraces(keys, data, doNorm);
  const layout = buildLayout(doNorm, data);
  Plotly.react('chart', traces, layout, CONFIG);
  updateCorr(data);
}}

function pearson(xs, ys) {{
  const pairs = xs.map((x,i) => [x,ys[i]]).filter(([a,b]) => a!==null && b!==null);
  if (pairs.length < 5) return null;
  const n = pairs.length;
  const mx = pairs.reduce((s,[a])=>s+a,0)/n;
  const my = pairs.reduce((s,[,b])=>s+b,0)/n;
  const num = pairs.reduce((s,[a,b])=>s+(a-mx)*(b-my),0);
  const dx  = Math.sqrt(pairs.reduce((s,[a])=>s+(a-mx)**2,0));
  const dy  = Math.sqrt(pairs.reduce((s,[,b])=>s+(b-my)**2,0));
  return (dx*dy===0) ? 0 : num/(dx*dy);
}}

function updateCorr(filteredData) {{
  const ka = document.getElementById('corr-a').value;
  const kb = document.getElementById('corr-b').value;
  const va = filteredData.series[ka] || (filterByDate([ka]).series[ka] || []);
  const vb = filteredData.series[kb] || (filterByDate([kb]).series[kb] || []);
  // re-fetch if not in filtered data keys
  const da = filterByDate([ka, kb]);
  const r  = pearson(da.series[ka]||[], da.series[kb]||[]);
  const el = document.getElementById('corr-val');
  const lb = document.getElementById('corr-label');
  if (r === null) {{ el.textContent = '—'; el.style.color='#555'; }}
  else {{
    el.textContent = (r >= 0 ? '+' : '') + r.toFixed(3);
    el.style.color = Math.abs(r)>0.6 ? '#00d4aa' : Math.abs(r)>0.3 ? '#f0a500' : '#888';
    lb.textContent = `Pearson · ${{da.dates[0]||''}} → ${{da.dates[da.dates.length-1]||''}}`;
  }}
}}

// Initial render
update();

// Checkbox listeners
document.querySelectorAll('#sidebar input[type=checkbox][data-key]').forEach(cb => {{
  cb.addEventListener('change', update);
}});

// Date range listeners
document.getElementById('dt-from').addEventListener('change', update);
document.getElementById('dt-to').addEventListener('change', update);

// Normalize toggle
document.getElementById('cb-norm').addEventListener('change', update);

// Reset button
document.getElementById('btn-reset').addEventListener('click', function() {{
  document.getElementById('dt-from').value = '{date_from}';
  document.getElementById('dt-to').value   = '{date_to}';
  document.getElementById('cb-norm').checked = false;
  // Reset checkboxes to defaults
  document.querySelectorAll('#sidebar input[type=checkbox][data-key]').forEach(cb => {{
    cb.checked = cb.defaultChecked;
  }});
  update();
}});

// Correlation dropdown listeners
document.getElementById('corr-a').addEventListener('change', function() {{
  updateCorr(filterByDate(getChecked()));
}});
document.getElementById('corr-b').addEventListener('change', function() {{
  updateCorr(filterByDate(getChecked()));
}});

// Sidebar toggle
document.getElementById('btn-sidebar').addEventListener('click', function() {{
  const hidden = document.getElementById('main').classList.toggle('sidebar-hidden');
  this.textContent = hidden ? '\u25b6 Show' : '\u25c4 Hide';
  setTimeout(function() {{
    const area = document.getElementById('chart-area');
    Plotly.relayout('chart', {{width: area.clientWidth, height: area.clientHeight}});
  }}, 50);
}});

// Resize observer to make chart fill container
new ResizeObserver(() => {{
  const area = document.getElementById('chart-area');
  Plotly.relayout('chart', {{width: area.clientWidth, height: area.clientHeight}});
}}).observe(document.getElementById('chart-area'));
</script>
</body></html>'''
    return html


def build_global_workspace_html():
    """Workspace showing all pairs — same as build_workspace_html(pair=None)."""
    return build_workspace_html(pair=None)
