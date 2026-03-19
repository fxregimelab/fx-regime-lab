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

html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1200">
<title>USD/INR — RBI Changed the Rules</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
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
    width: 1200px; height: 500px;
    background: #0B1120;
    border-radius: 10px; border: 1px solid #152035;
    display: flex; flex-direction: column; overflow: hidden;
  }
  .hdr {
    height: 48px; background: #080e1c;
    border-bottom: 1px solid #152035;
    padding: 0 22px;
    display: flex; align-items: center; justify-content: space-between;
    flex-shrink: 0;
  }
  .hdr-left { display: flex; align-items: center; gap: 12px; }
  .hdr-left .logo { height: 24px; opacity: 0.95; display: block; }
  .hdr-title {
    color: #fff; font-size: 16px; font-weight: 700;
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

  /* Layout */
  .content { display: flex; flex: 1; min-height: 0; }

  /* Left Panel */
  .left-panel {
    flex: 4; /* 40% */
    background: #111827;
    border-right: 1px solid #1F2937;
    padding: 20px 24px;
    display: flex; flex-direction: column;
    justify-content: flex-start;
  }
  
  .metric-large { margin-bottom: 12px; }
  .metric-large .label { color: #9CA3AF; font-size: 14px; font-weight: 500; margin-bottom: 4px; }
  .metric-large .value-row { display: flex; align-items: baseline; gap: 12px; }
  .metric-large .value { color: #FFF; font-size: 32px; font-weight: 700; line-height: 1; }
  .metric-large .pill {
    background: rgba(239,68,68,0.15); color: #EF4444;
    padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
  }

  .divider { height: 1px; background: #1F2937; margin: 10px 0; }

  .row-item {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 8px;
  }
  .row-item .title { color: #9CA3AF; font-size: 11px; font-weight: 600; width: 110px;}
  .row-item .val { color: #E5E7EB; font-size: 13px; font-weight: 600; width: 50px; text-align: right; }
  .row-item .tag-container { flex: 1; display: flex; justify-content: flex-end; align-items: center; gap: 6px; }
  
  .tag { font-size: 9px; font-weight: 700; padding: 3px 6px; border-radius: 3px; letter-spacing: 0.05em; }
  .tag-red { background: rgba(239,68,68,0.15); color: #EF4444; border: 1px solid rgba(239,68,68,0.3); }
  .tag-yellow { background: rgba(245,158,11,0.15); color: #F59E0B; border: 1px solid rgba(245,158,11,0.3); }
  .tag-green { background: rgba(16,185,129,0.15); color: #10B981; border: 1px solid rgba(16,185,129,0.3); }
  .tag-gray { background: rgba(156,163,175,0.15); color: #9CA3AF; border: 1px solid rgba(156,163,175,0.3); }
  
  .sub-text { font-size: 9px; color: #6B7280; font-weight: 500; }

  /* New Row */
  .new-row {
    background: #EF4444;
    border-radius: 4px;
    padding: 8px 12px;
    display: flex; align-items: center; justify-content: center;
    margin: 4px 0;
  }
  .new-row span { color: #FFF; font-size: 13px; font-weight: 700; letter-spacing: 0.02em; }

  /* Composite Bar */
  .composite-bar { margin-top: 8px; display: flex; flex-direction: column; gap: 6px;}
  .breakdown-row { display: flex; gap: 2px; height: 8px; width: 100%; border-radius: 2px; overflow: hidden; background: #1F2937; margin-bottom: 4px;}
  .breakdown-leg { display: flex; gap: 8px; font-size: 9px; color: #9CA3AF; justify-content: space-between; }
  .b-item { display: flex; align-items: center; gap: 4px; }
  .b-dot { width: 6px; height: 6px; border-radius: 50%; }

  /* Right Panel */
  .right-panel {
    flex: 6; /* 60% */
    display: flex; flex-direction: column;
    padding: 12px 16px 4px 12px; gap: 0;
  }
  .panel-top    { flex: 6; min-height: 0; position: relative; }
  .panel-bottom { flex: 4; min-height: 0; position: relative; margin-top: 4px;}
  .panel-label {
    position: absolute; top: 4px; left: 16px;
    color: #6B7280; font-size: 10px; font-weight: 600;
    letter-spacing: 0.05em; text-transform: uppercase; z-index: 10;
  }

  .footer {
    height: 28px; padding: 0 22px;
    display: flex; align-items: center; justify-content: space-between;
    border-top: 1px solid #101828; flex-shrink: 0;
  }
  .footer span { color: #1e2d45; font-size: 10.5px; }
  .footer .fr   { color: #253550; font-size: 11px; }
  
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
    <div class="hdr-left">
      <img src="LOGO_PLACEHOLDER" alt="FX Regime Lab" class="logo">
      <div class="hdr-title">USD/INR — RBI Changed the Rules</div>
    </div>
    <div class="hdr-right">
      <div class="badge">&#9888;&thinsp; REGIME SHIFT</div>
      <div class="hdr-date">Data as of Mar 27, 2026</div>
    </div>
  </div>

  <div class="content">
    <div class="left-panel">
      <div class="metric-large">
        <div class="label">USD / INR</div>
        <div class="value-row">
          <div class="value">94.31</div>
          <div class="pill">+1.32% WoW</div>
        </div>
      </div>

      <div class="divider"></div>

      <div class="row-item">
        <div class="title">VOL 30D</div>
        <div class="val">7.3%</div>
        <div class="tag-container">
          <span class="sub-text">↑ from ELEVATED</span>
          <span class="tag tag-red">EXTREME</span>
        </div>
      </div>

      <div class="row-item">
        <div class="title">OIL CORR 60D</div>
        <div class="val">-0.036</div>
        <div class="tag-container">
          <span class="tag tag-gray">LOW</span>
        </div>
      </div>

      <div class="row-item">
        <div class="title">GOLD CORR 60D</div>
        <div class="val">-0.305</div>
        <div class="tag-container">
          <span class="tag tag-red">GOLD DIVERGENCE</span>
        </div>
      </div>

      <div class="row-item">
        <div class="title">DXY CORR 60D</div>
        <div class="val">-0.137</div>
        <div class="tag-container">
          <span class="tag tag-yellow">INDIA SPECIFIC</span>
        </div>
      </div>

      <div class="row-item">
        <div class="title">RBI RESERVES</div>
        <div class="val">-4.7B</div>
        <div class="tag-container">
          <span class="tag tag-yellow">ACTIVE SUPPORT</span>
        </div>
      </div>

      <div class="divider"></div>

      <div class="new-row">
        <span>RBI NOP CAP: $100M — NEW</span>
      </div>

      <div class="divider"></div>

      <div class="row-item" style="margin-bottom:4px;">
        <div class="title">INR COMPOSITE</div>
        <div class="val">+25.4</div>
        <div class="tag-container">
          <span class="tag tag-gray">NEUTRAL</span>
        </div>
      </div>
      
      <div class="composite-bar">
        <div class="breakdown-row">
          <!-- Oil: -1, DXY: -3, RBI: -6, FPI: +25, Rate: +10 -->
          <div style="width: 2.2%; background: #EF4444; opacity: 0.6;" title="Oil -1"></div>
          <div style="width: 6.7%; background: #EF4444; opacity: 0.8;" title="DXY -3"></div>
          <div style="width: 13.3%; background: #EF4444;" title="RBI -6"></div>
          <div style="width: 22.2%; background: #10B981; opacity: 0.7;" title="Rate +10"></div>
          <div style="width: 55.6%; background: #10B981;" title="FPI +25"></div>
        </div>
        <div class="breakdown-leg">
          <div class="b-item"><div class="b-dot" style="background:#EF4444"></div> Neg: RBI(-6) DXY(-3) Oil(-1)</div>
          <div class="b-item"><div class="b-dot" style="background:#10B981"></div> Pos: FPI(+25) Rate(+10)</div>
        </div>
      </div>

    </div>
    
    <div class="right-panel">
      <div class="panel-top">
        <div class="panel-label">USD/INR Spot</div>
        <canvas id="chartTop"></canvas>
      </div>
      <div class="panel-bottom">
        <div class="panel-label">USD/INR Implied Vol Pct Rank</div>
        <canvas id="chartBot"></canvas>
      </div>
    </div>

  </div>

  <div class="footer">
    <span>Source: FX Regime Lab Pipeline &nbsp;&middot;&nbsp; 2026</span>
    <span class="fr">fxregimelab.substack.com</span>
  </div>
</div>

<button class="dl-btn" id="dlBtn" onclick="exportPNG()">&#8681;&nbsp; Export PNG (2&times;)</button>

<script>
const FONT = "'Inter', system-ui, -apple-system, sans-serif";

const labels = ['Jan 02','Jan 05','Jan 06','Jan 07','Jan 08','Jan 09','Jan 12','Jan 13','Jan 14','Jan 15','Jan 16','Jan 19','Jan 20','Jan 21','Jan 22','Jan 23','Jan 26','Jan 27','Jan 28','Jan 29','Jan 30','Feb 02','Feb 03','Feb 04','Feb 05','Feb 06','Feb 09','Feb 10','Feb 11','Feb 12','Feb 13','Feb 16','Feb 17','Feb 18','Feb 19','Feb 20','Feb 23','Feb 24','Feb 25','Feb 26','Feb 27','Mar 02','Mar 03','Mar 04','Mar 05','Mar 06','Mar 09','Mar 10','Mar 11','Mar 12','Mar 13','Mar 16','Mar 17','Mar 18','Mar 19','Mar 20','Mar 23','Mar 24','Mar 25','Mar 26','Mar 27'];

const priceData = [89.962,90.007,90.233,90.166,89.864,89.905,90.236,90.133,90.273,90.183,90.362,90.702,90.905,91.118,91.537,91.558,91.501,91.713,91.534,92.041,91.782,91.687,90.246,90.423,90.125,90.315,90.588,90.823,90.588,90.736,90.564,90.571,90.783,90.626,90.794,91.041,90.727,91.02,90.918,90.951,91.007,91.08,91.563,92.009,92.123,91.787,91.936,91.221,92.165,92.229,92.39,92.564,92.283,92.391,93.247,93.082,93.895,93.244,94.3,94.694,94.31];

const volPctData = [91.8,91.5,91.5,86.0,83.3,83.2,84.5,84.4,84.4,83.7,82.4,83.6,81.3,81.9,84.0,82.8,82.1,79.9,79.2,82.3,83.7,77.4,91.9,91.8,91.8,91.8,91.4,91.3,91.4,91.3,91.3,91.1,91.0,91.4,90.3,90.5,90.9,91.4,91.4,91.1,91.0,89.4,91.4,91.5,91.1,91.4,91.4,91.9,94.7,93.3,93.1,93.1,85.7,85.4,87.0,87.0,89.8,91.1,93.3,93.3,94.6];

const MONTH_IDX = { 0: 'Jan', 21: 'Feb', 41: 'Mar' };

const sharedXConfig = {
  grid: { color: '#1F2937', drawBorder: false },
  border: { display: false },
  ticks: {
    color: '#9CA3AF',
    font: { size: 10, family: FONT },
    maxRotation: 0,
    callback: function(value, index) { return MONTH_IDX[index] !== undefined ? MONTH_IDX[index] : ''; },
    autoSkip: false
  }
};

/* ── TOP PANEL CHART ────────────────────────────────────────────────── */
const annoTop = {
  line94: {
    type: 'line', yMin: 94.0, yMax: 94.0,
    borderColor: 'rgba(56,189,248,0.5)', borderWidth: 1.5, borderDash: [4,4]
  },
  lbl94: {
    type: 'label', xValue: 'Jan 02', yValue: 94.0,
    content: '94 — Week 4', color: 'rgba(56,189,248,0.7)',
    font: { size: 9, weight: '600', family: FONT },
    textAlign: 'left', xAdjust: 4, yAdjust: -8, padding: 0
  },
  line93: {
    type: 'line', yMin: 93.0, yMax: 93.0,
    borderColor: 'rgba(56,189,248,0.5)', borderWidth: 1.5, borderDash: [4,4]
  },
  lbl93: {
    type: 'label', xValue: 'Jan 02', yValue: 93.0,
    content: '93 — Week 3', color: 'rgba(56,189,248,0.7)',
    font: { size: 9, weight: '600', family: FONT },
    textAlign: 'left', xAdjust: 4, yAdjust: -8, padding: 0
  },
  latestDot: {
    type: 'point', xValue: 'Mar 27', yValue: 94.31,
    radius: 4.5, backgroundColor: '#0B1120',
    borderColor: '#FF4757', borderWidth: 2
  },
  latestLbl: {
    type: 'label', xValue: 'Mar 27', yValue: 94.31,
    yAdjust: -15, xAdjust: -15,
    content: '94.31',
    color: '#FF4757',
    font: { size: 10, weight: '600', family: FONT }, padding: 0
  }
};

const ctxTop = document.getElementById('chartTop').getContext('2d');
new Chart(ctxTop, {
  type: 'line',
  data: {
    labels,
    datasets: [{
      label: 'USD/INR Spot',
      data: priceData,
      borderColor: '#FF4757',
      borderWidth: 2.5,
      pointRadius: 0,
      tension: 0.1,
      fill: false
    }]
  },
  options: {
    animation: false,
    responsive: true,
    maintainAspectRatio: false,
    layout: { padding: { top: 20, right: 30, bottom: 0, left: 10 } },
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false },
      annotation: { annotations: annoTop }
    },
    scales: {
      x: sharedXConfig,
      y: {
        min: 89, max: 95,
        grid: { color: '#1F2937', drawBorder: false },
        border: { display: false },
        ticks: {
          color: '#9CA3AF',
          font: { size: 10, family: FONT },
          stepSize: 1
        }
      }
    }
  }
});

/* ── BOTTOM PANEL CHART ─────────────────────────────────────────────── */
const annoBot = {
  line90: {
    type: 'line', yMin: 90, yMax: 90,
    borderColor: 'rgba(239,68,68,0.5)', borderWidth: 1.5, borderDash: [4,4]
  },
  lbl90: {
    type: 'label', xValue: 'Jan 02', yValue: 90,
    content: '90 - EXTREME', color: 'rgba(239,68,68,0.7)',
    font: { size: 9, weight: '600', family: FONT },
    textAlign: 'left', xAdjust: 4, yAdjust: -8, padding: 0
  },
  line75: {
    type: 'line', yMin: 75, yMax: 75,
    borderColor: 'rgba(245,158,11,0.5)', borderWidth: 1.5, borderDash: [4,4]
  },
  lbl75: {
    type: 'label', xValue: 'Jan 02', yValue: 75,
    content: '75 - ELEVATED', color: 'rgba(245,158,11,0.7)',
    font: { size: 9, weight: '600', family: FONT },
    textAlign: 'left', xAdjust: 4, yAdjust: -8, padding: 0
  },
  bounceLbl: {
    type: 'label', xValue: 'Mar 24', yValue: 78,
    content: '↑ Back to EXTREME', color: 'rgba(239,68,68,0.8)',
    font: { size: 10, weight: '600', family: FONT },
    textAlign: 'right', xAdjust: -20, yAdjust: 10, padding: 0
  },
  latestDot: {
    type: 'point', xValue: 'Mar 27', yValue: 94.6,
    radius: 4, backgroundColor: '#0B1120',
    borderColor: '#F97316', borderWidth: 2
  }
};

const ctxBot = document.getElementById('chartBot').getContext('2d');
new Chart(ctxBot, {
  type: 'line',
  data: {
    labels,
    datasets: [{
      label: 'USD/INR Vol Pct Rank',
      data: volPctData,
      borderColor: '#F97316',
      backgroundColor: 'rgba(249,115,22,0.15)',
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.3,
      fill: true
    }]
  },
  options: {
    animation: false,
    responsive: true,
    maintainAspectRatio: false,
    layout: { padding: { top: 20, right: 30, bottom: 5, left: 10 } },
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false },
      annotation: { annotations: annoBot }
    },
    scales: {
      x: sharedXConfig,
      y: {
        min: 60, max: 100,
        grid: { color: '#1F2937', drawBorder: false },
        border: { display: false },
        ticks: {
          color: '#9CA3AF',
          font: { size: 10, family: FONT },
          stepSize: 10
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
    backgroundColor: '#060b14', logging: false, imageTimeout: 15000
  }).then(canvas => {
    canvas.toBlob(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'usdinr_regime_shift.png';
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
</html>
"""

html = html.replace("LOGO_PLACEHOLDER", logo_data_url)

with open(os.path.join("pages", "usdinr_regime_shift.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("Written pages/usdinr_regime_shift.html, size:", round(len(html)/1024), "KB")
