import os
import re

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
os.chdir(_ROOT)

# Extract base64 logo from existing file
with open(os.path.join("pages", "eur_reconnection_journey.html"), "r", encoding="utf-8") as f:
    existing = f.read()

m = re.search(r'(data:image/png;base64,[A-Za-z0-9+/=]+)', existing)
logo_data_url = m.group(1) if m else ""
print("Logo extracted, length:", len(logo_data_url))

html = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1200">
<title>USD/JPY — Price Rising, Correlation Screaming the Other Way</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    background: #060b14;
    display: flex; flex-direction: column; align-items: center;
    padding: 32px 24px; min-height: 100vh;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    gap: 14px;
  }
  .card {
    width: 1200px; height: 550px;
    background: #0B1120;
    border-radius: 10px; border: 1px solid #152035;
    display: flex; flex-direction: column; overflow: hidden;
  }
  .hdr {
    height: 44px; background: #080e1c;
    border-bottom: 1px solid #152035;
    padding: 0 22px;
    display: flex; align-items: center; justify-content: space-between;
    flex-shrink: 0;
  }
  .hdr-right { display: flex; align-items: center; gap: 14px; }
  .badge {
    background: rgba(231,76,60,0.10);
    border: 1px solid rgba(231,76,60,0.22);
    color: #f87171; font-size: 9.5px; font-weight: 700;
    letter-spacing: 0.10em; text-transform: uppercase;
    padding: 3px 9px; border-radius: 3px;
  }
  .hdr-date { color: #3a4a65; font-size: 10.5px; }
  .title-block { padding: 9px 22px 4px; flex-shrink: 0; }
  .title-block h1 {
    color: #D8E0EA; font-size: 15.5px; font-weight: 700;
    letter-spacing: 0.01em; line-height: 1.3;
  }
  .title-block p { color: #2d3d57; font-size: 10px; margin-top: 2px; }
  /* Two panels stacked */
  .panels { display: flex; flex-direction: column; flex: 1; min-height: 0; padding: 4px 14px 2px 14px; gap: 0; }
  .panel-top    { flex: 6; min-height: 0; position: relative; }
  .panel-bottom { flex: 4; min-height: 0; position: relative; }
  .panel-label {
    position: absolute; top: 4px; left: 4px;
    color: #2d3d57; font-size: 9px; font-weight: 600;
    letter-spacing: 0.09em; text-transform: uppercase;
  }
  .footer {
    height: 28px; padding: 0 22px;
    display: flex; align-items: center; justify-content: space-between;
    border-top: 1px solid #101828; flex-shrink: 0;
  }
  .footer span { color: #1e2d45; font-size: 10px; }
  .footer .fr   { color: #253550; font-size: 10.5px; }
  .dl-btn {
    background: #0f1c30; color: #4a5c78;
    border: 1px solid #1a2d48; border-radius: 6px;
    padding: 8px 22px; font-size: 12px; font-weight: 500;
    font-family: inherit; cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }
  .dl-btn:hover    { background: #162540; color: #c0cfe4; }
  .dl-btn:disabled { opacity: 0.45; cursor: default; }
</style>
</head>
<body>

<div class="card" id="exportCard">
  <div class="hdr">
    <img src="LOGO_PLACEHOLDER" alt="FX Regime Lab" style="height:28px;opacity:0.95;display:block;">
    <div class="hdr-right">
      <div class="badge">&#9888;&thinsp; BoJ Watch</div>
      <div class="hdr-date">Data as of Mar 27, 2026</div>
    </div>
  </div>

  <div class="title-block">
    <h1>USD/JPY &mdash; Price Rising, Correlation Screaming the Other Way</h1>
    <p>USD/JPY spot (top) &nbsp;&middot;&nbsp;
       USD/JPY vs. US&minus;JP 10Y spread correlation, 60D &amp; 20D (bottom) &nbsp;&middot;&nbsp;
       Feb&ndash;Mar 2026</p>
  </div>

  <div class="panels">
    <div class="panel-top">
      <div class="panel-label">USD/JPY Price</div>
      <canvas id="chartTop"></canvas>
    </div>
    <div class="panel-bottom">
      <div class="panel-label">Regime Correlation</div>
      <canvas id="chartBot"></canvas>
    </div>
  </div>

  <div class="footer">
    <span>Source: FX Regime Lab Pipeline &nbsp;&middot;&nbsp;
      USD/JPY spot vs. US&minus;JP 10Y rate spread &nbsp;&middot;&nbsp; Pipeline-verified Mar 27, 2026</span>
    <span class="fr">fxregimelab.substack.com</span>
  </div>
</div>

<button class="dl-btn" id="dlBtn" onclick="exportPNG()">&#8681;&nbsp; Export PNG (2&times;)</button>

<script>
const FONT = "'Inter', system-ui, -apple-system, sans-serif";

/* ── Pipeline-verified data Feb 2 – Mar 27, 2026 ─────────────────────── */
const labels = [
  "Feb 02","Feb 03","Feb 04","Feb 05","Feb 06","Feb 09","Feb 10",
  "Feb 11","Feb 12","Feb 13","Feb 16","Feb 17","Feb 18","Feb 19",
  "Feb 20","Feb 23","Feb 24","Feb 25","Feb 26","Feb 27","Mar 02",
  "Mar 03","Mar 04","Mar 05","Mar 06","Mar 09","Mar 10","Mar 11",
  "Mar 12","Mar 13","Mar 16","Mar 17","Mar 18","Mar 19","Mar 20",
  "Mar 23","Mar 24","Mar 25","Mar 26","Mar 27"
];

const priceData = [
  155.202,155.443,155.799,156.917,156.784,157.244,156.132,
  154.482,153.269,152.821,152.779,153.609,153.149,154.693,
  155.160,154.339,154.635,155.880,156.200,155.859,156.633,
  157.257,157.773,156.983,157.534,158.427,157.848,158.114,
  159.075,159.206,159.568,159.105,158.889,159.795,157.924,
  159.234,158.479,158.718,159.384,159.704
];

const c60Data = [
  -0.1638,-0.1608,-0.1579,-0.1881,-0.1936,-0.2138,-0.2074,
  -0.2272,-0.1625,-0.1572,-0.1121,-0.0626,-0.0742,-0.0746,
  -0.0722,-0.0537,-0.0511,-0.0612,-0.0625,-0.0556,-0.0039,
  -0.0159,-0.0073,-0.0121, 0.0099, 0.0093, 0.0021, 0.0112,
   0.0169, 0.0144, 0.0126, 0.0163, 0.0380, 0.0360,-0.0733,
  -0.1133,-0.1309,-0.1325,-0.1211,-0.1221
];

const c20Data = [
   0.0181, 0.0076, 0.0186,-0.0552,-0.0543,-0.0991,-0.1054,
  -0.0777, 0.0328, 0.0085,-0.0571, 0.0506, 0.0393,-0.0038,
   0.0247, 0.0671, 0.0539, 0.2090, 0.2193, 0.2288, 0.2017,
   0.1729, 0.1856, 0.2715, 0.2798, 0.2455, 0.2053, 0.2740,
   0.1402, 0.1093, 0.0931, 0.0565, 0.0085,-0.0063,-0.3034,
  -0.4635,-0.5042,-0.4936,-0.4491,-0.4720
];

/* Month-start indices for x-axis ticks */
const MONTH_IDX_TOP = { 0: 'Feb', 20: 'Mar' };
const MONTH_IDX_BOT = { 0: 'Feb', 20: 'Mar' };

/* ── Top panel annotations ──────────────────────────────────────────── */
const annoTop = {
  boj160: {
    type: 'line', yMin: 160, yMax: 160,
    borderColor: 'rgba(231,76,60,0.38)', borderWidth: 1.2, borderDash: [5,4]
  },
  lbl160: {
    type: 'label', xValue: 'Feb 02', yValue: 160.06,
    content: '160 — BoJ Alert',
    color: 'rgba(231,76,60,0.55)',
    font: { size: 8.5, weight: '600', family: FONT },
    textAlign: 'left', xAdjust: 4, padding: 0
  },
  /* Vertical BoJ line */
  bojLine: {
    type: 'line', xMin: 'Mar 19', xMax: 'Mar 19',
    borderColor: 'rgba(148,163,184,0.22)', borderWidth: 1, borderDash: [3,3]
  },
  bojLabel: {
    type: 'label', xValue: 'Mar 19', yValue: 155.5,
    content: 'BoJ Hold',
    color: 'rgba(148,163,184,0.45)',
    font: { size: 8, weight: '500', family: FONT },
    xAdjust: -1, padding: 0
  },
  /* Latest price dot */
  latestDotG: {
    type: 'point', xValue: 'Mar 27', yValue: 159.704,
    radius: 10, backgroundColor: 'rgba(255,159,67,0.12)', borderWidth: 0
  },
  latestDot: {
    type: 'point', xValue: 'Mar 27', yValue: 159.704,
    radius: 4.5, backgroundColor: '#0B1120',
    borderColor: '#FF9F43', borderWidth: 2
  },
  latestLbl: {
    type: 'label', xValue: 'Mar 27', yValue: 159.704,
    yAdjust: -16, xAdjust: -22,
    content: '159.70',
    color: '#e8943a',
    font: { size: 9.5, weight: '600', family: FONT }, padding: 0
  },
  wowLbl: {
    type: 'label', xValue: 'Mar 23', yValue: 158.2,
    content: '+1.13% WoW \u2191',
    color: 'rgba(255,159,67,0.65)',
    font: { size: 9, weight: '500', family: FONT }, padding: 0
  }
};

/* ── Bottom panel annotations ───────────────────────────────────────── */
const annoBot = {
  zeroLine: {
    type: 'line', yMin: 0, yMax: 0,
    borderColor: '#1e3050', borderWidth: 1.5, borderDash: [5,4]
  },
  redFill: {
    type: 'box', yMin: -0.62, yMax: 0,
    backgroundColor: 'rgba(255,71,87,0.05)', borderWidth: 0,
    drawTime: 'beforeDatasetsDraw'
  },
  bojLineBot: {
    type: 'line', xMin: 'Mar 19', xMax: 'Mar 19',
    borderColor: 'rgba(148,163,184,0.22)', borderWidth: 1, borderDash: [3,3]
  },
  /* Latest 20D dot */
  dot20Glow: {
    type: 'point', xValue: 'Mar 27', yValue: -0.4720,
    radius: 10, backgroundColor: 'rgba(255,71,87,0.10)', borderWidth: 0
  },
  dot20: {
    type: 'point', xValue: 'Mar 27', yValue: -0.4720,
    radius: 4.5, backgroundColor: '#0B1120',
    borderColor: '#FF4757', borderWidth: 2
  },
  lbl20: {
    type: 'label', xValue: 'Mar 27', yValue: -0.4720,
    yAdjust: -15, xAdjust: -22,
    content: '\u22120.472',
    color: '#e84a57',
    font: { size: 9.5, weight: '600', family: FONT }, padding: 0
  },
  lbl20sub: {
    type: 'label', xValue: 'Mar 20', yValue: -0.54,
    content: 'Strongest negative in months',
    color: 'rgba(255,71,87,0.45)',
    font: { size: 8.5, weight: '500', family: FONT }, padding: 0
  },
  /* Latest 60D dot */
  dot60: {
    type: 'point', xValue: 'Mar 27', yValue: -0.1221,
    radius: 4, backgroundColor: '#0B1120',
    borderColor: '#4A90D9', borderWidth: 2
  },
  lbl60: {
    type: 'label', xValue: 'Mar 27', yValue: -0.1221,
    yAdjust: 16, xAdjust: -22,
    content: '\u22120.122',
    color: '#4a90d9',
    font: { size: 9.5, weight: '600', family: FONT }, padding: 0
  }
};

/* ── Shared tick config ─────────────────────────────────────────────── */
function xTickCallback(monthIdx) {
  return function(value, index) {
    return monthIdx[index] !== undefined ? monthIdx[index] : '';
  };
}

const sharedXConfig = {
  grid: { color: '#0a1428', drawBorder: false },
  border: { display: false },
  ticks: {
    color: '#2d3d57',
    font: { size: 10, family: FONT },
    maxRotation: 0,
    autoSkip: false
  }
};

/* ── TOP PANEL CHART ────────────────────────────────────────────────── */
const ctxTop = document.getElementById('chartTop').getContext('2d');
new Chart(ctxTop, {
  type: 'line',
  data: {
    labels,
    datasets: [{
      label: 'USD/JPY',
      data: priceData,
      borderColor: '#FF9F43',
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.25,
      fill: false
    }]
  },
  options: {
    animation: false,
    responsive: true,
    maintainAspectRatio: false,
    layout: { padding: { top: 12, right: 54, bottom: 0, left: 4 } },
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false },
      annotation: { annotations: annoTop }
    },
    scales: {
      x: {
        ...sharedXConfig,
        ticks: {
          ...sharedXConfig.ticks,
          callback: xTickCallback(MONTH_IDX_TOP)
        }
      },
      y: {
        min: 152, max: 161,
        grid: { color: '#0a1428', drawBorder: false },
        border: { display: false },
        ticks: {
          color: '#2d3d57',
          font: { size: 10, family: FONT },
          stepSize: 1,
          callback: v => v.toFixed(0)
        }
      }
    }
  }
});

/* ── BOTTOM PANEL CHART ─────────────────────────────────────────────── */
const ctxBot = document.getElementById('chartBot').getContext('2d');
new Chart(ctxBot, {
  type: 'line',
  data: {
    labels,
    datasets: [
      {
        label: '60D Correlation',
        data: c60Data,
        borderColor: '#4A90D9',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.30,
        fill: false,
        order: 2
      },
      {
        label: '20D Correlation',
        data: c20Data,
        borderColor: '#FF4757',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.30,
        fill: false,
        order: 1
      }
    ]
  },
  options: {
    animation: false,
    responsive: true,
    maintainAspectRatio: false,
    layout: { padding: { top: 6, right: 54, bottom: 2, left: 4 } },
    plugins: {
      legend: {
        display: true, position: 'top', align: 'end',
        labels: {
          color: '#4a5c78',
          font: { size: 10, family: FONT, weight: '500' },
          useBorderRadius: true, borderRadius: 2,
          boxWidth: 20, boxHeight: 2, padding: 14,
          generateLabels: chart => chart.data.datasets.map((ds, i) => ({
            text: ds.label,
            fillStyle: ds.borderColor,
            strokeStyle: ds.borderColor,
            lineWidth: 0,
            hidden: false,
            datasetIndex: i
          }))
        }
      },
      tooltip: { enabled: false },
      annotation: { annotations: annoBot }
    },
    scales: {
      x: {
        ...sharedXConfig,
        ticks: {
          ...sharedXConfig.ticks,
          callback: xTickCallback(MONTH_IDX_BOT)
        }
      },
      y: {
        min: -0.62, max: 0.32,
        grid: { color: '#0a1428', drawBorder: false },
        border: { display: false },
        ticks: {
          color: '#2d3d57',
          font: { size: 10, family: FONT },
          stepSize: 0.2,
          callback: v => v === 0 ? '0.0' : (v > 0 ? '+' + v.toFixed(1) : v.toFixed(1))
        }
      }
    }
  }
});

/* ── PNG Export ─────────────────────────────────────────────────────── */
function exportPNG() {
  const btn = document.getElementById('dlBtn');
  btn.disabled = true; btn.textContent = 'Generating\u2026';
  html2canvas(document.getElementById('exportCard'), {
    scale: 2, allowTaint: false, useCORS: false,
    backgroundColor: '#0B1120', logging: false, imageTimeout: 15000
  }).then(canvas => {
    canvas.toBlob(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'jpy_correlation_flip_fxregimelab.png';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      btn.disabled = false; btn.innerHTML = '&#8681;&nbsp; Export PNG (2&times;)';
    }, 'image/png');
  }).catch(err => {
    btn.disabled = false; btn.innerHTML = '&#8681;&nbsp; Export PNG (2&times;)';
    alert('Export failed: ' + err.message);
  });
}
</script>
</body>
</html>'''

html = html.replace("LOGO_PLACEHOLDER", logo_data_url)

with open(os.path.join("pages", "jpy_correlation_flip.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("Written pages/jpy_correlation_flip.html, size:", round(len(html)/1024), "KB")
