(function (global) {
  'use strict';

  var overlay;
  var panel;
  var closeBtn;
  var activePair = null;
  var chart = null;

  var PAIR_TO_COLUMN = {
    EURUSD: 'EURUSD',
    USDJPY: 'USDJPY',
    USDINR: 'USDINR',
  };

  var PAIR_LABEL = {
    EURUSD: 'EUR/USD',
    USDJPY: 'USD/JPY',
    USDINR: 'USD/INR',
  };

  function splitCsvLine(line) {
    var out = [];
    var cur = '';
    var inQ = false;
    for (var i = 0; i < line.length; i++) {
      var c = line[i];
      if (inQ) {
        if (c === '"') {
          if (line[i + 1] === '"') {
            cur += '"';
            i++;
          } else {
            inQ = false;
          }
        } else {
          cur += c;
        }
      } else if (c === '"') {
        inQ = true;
      } else if (c === ',') {
        out.push(cur);
        cur = '';
      } else {
        cur += c;
      }
    }
    out.push(cur);
    return out;
  }

  function parseCsv(text) {
    var lines = String(text || '').split(/\r?\n/).filter(function (line) {
      return line.trim();
    });
    if (!lines.length) return [];
    var headers = splitCsvLine(lines[0]);
    var rows = [];
    for (var i = 1; i < lines.length; i++) {
      var cells = splitCsvLine(lines[i]);
      var row = {};
      for (var j = 0; j < headers.length; j++) {
        row[headers[j]] = cells[j] != null ? cells[j].trim() : '';
      }
      rows.push(row);
    }
    return rows;
  }

  function getPairArticle(pair) {
    var intel = global.FXRLHomeIntel || {};
    var sections = intel.sections || {};
    if (pair === 'EURUSD') return sections.eurusd || {};
    if (pair === 'USDJPY') return sections.usdjpy || {};
    if (pair === 'USDINR') return sections.usdinr || {};
    return {};
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    var node = byId(id);
    if (node) node.textContent = value;
  }

  function renderSignalStack(card, article) {
    var target = byId('term-panel-signals');
    if (!target) return;
    var html = [];
    html.push('<table class="term-panel-table">');
    html.push('<tr><td>Regime</td><td>' + (card.getAttribute('data-panel-regime') || article.regime || '—') + '</td></tr>');
    html.push('<tr><td>Confidence</td><td>' + (card.getAttribute('data-panel-confidence') || '—') + '</td></tr>');
    html.push('<tr><td>Primary driver</td><td>' + (article.key_driver || '—') + '</td></tr>');
    html.push('<tr><td>Watch for</td><td>' + (article.watch_for || '—') + '</td></tr>');
    html.push('</table>');
    target.innerHTML = html.join('');
  }

  function renderChanges(pair) {
    var changes = (((global.FXRLHomeIntel || {}).sections || {}).signal_changes || []);
    var list = byId('term-panel-changes');
    if (!list) return;
    var pairLabel = (PAIR_LABEL[pair] || pair).replace('/', '');
    var filtered = changes.filter(function (line) {
      var u = String(line || '').toUpperCase();
      return u.indexOf(pair) >= 0 || u.indexOf(pairLabel) >= 0;
    });
    list.innerHTML = '';
    if (!filtered.length) {
      list.innerHTML = '<li>No material changes today.</li>';
      return;
    }
    filtered.forEach(function (item) {
      var li = document.createElement('li');
      li.textContent = item;
      list.appendChild(li);
    });
  }

  function renderChart(pair) {
    var column = PAIR_TO_COLUMN[pair];
    var mount = byId('term-panel-chart');
    if (!mount || !column || typeof echarts === 'undefined') return;

    fetch('/data/latest_with_cot.csv')
      .then(function (r) { return r.ok ? r.text() : ''; })
      .then(function (text) {
        var rows = parseCsv(text);
        var points = rows.slice(-30).map(function (row) {
          var v = parseFloat(String(row[column] || '').replace(/,/g, ''));
          return isFinite(v) ? v : null;
        }).filter(function (v) { return v != null; });

        if (!points.length) return;
        if (chart) {
          chart.dispose();
          chart = null;
        }
        chart = echarts.init(mount, null, { renderer: 'canvas' });
        var color = pair === 'EURUSD' ? '#4d8eff' : pair === 'USDJPY' ? '#d4890a' : '#c94040';
        chart.setOption({
          animationDuration: 500,
          grid: { top: 8, right: 4, bottom: 4, left: 4 },
          xAxis: { type: 'category', data: points.map(function (_, i) { return i + 1; }), show: false },
          yAxis: { type: 'value', show: false, scale: true },
          series: [
            {
              data: points,
              type: 'line',
              smooth: true,
              symbol: 'none',
              lineStyle: { width: 2, color: color },
              areaStyle: { color: 'rgba(0,0,0,0)' },
            },
          ],
        });
      })
      .catch(function () {});
  }

  function openPanel(card) {
    activePair = card.getAttribute('data-panel-pair');
    var article = getPairArticle(activePair);
    var pairLabel = PAIR_LABEL[activePair] || activePair;
    var pairUrl = card.getAttribute('data-panel-url') || '/terminal/';
    var spot = card.getAttribute('data-panel-spot') || '—';
    var driver = card.getAttribute('data-panel-driver') || article.key_driver || '—';
    var confidence = card.getAttribute('data-panel-confidence') || '—';

    setText('term-panel-pair', pairLabel);
    setText('term-panel-spot', spot);
    setText('term-panel-confidence', confidence);
    setText('term-panel-read', driver);
    setText('term-panel-excerpt', String(article.narrative || '—').split('. ').slice(0, 1).join('. '));

    byId('term-panel-link-top').setAttribute('href', pairUrl);
    byId('term-panel-link-bottom').setAttribute('href', pairUrl);
    byId('term-panel-link-bottom').textContent = '→ Full ' + pairLabel + ' analysis';

    renderSignalStack(card, article);
    renderChanges(activePair);
    renderChart(activePair);
    if (global.FXRLTerminalMotion && typeof global.FXRLTerminalMotion.animateNumbers === 'function') {
      global.FXRLTerminalMotion.animateNumbers(panel);
    }

    overlay.hidden = false;
    panel.removeAttribute('aria-hidden');
    requestAnimationFrame(function () {
      overlay.classList.add('is-open');
      panel.classList.add('is-open');
    });
  }

  function closePanel() {
    panel.classList.remove('is-open');
    overlay.classList.remove('is-open');
    panel.setAttribute('aria-hidden', 'true');
    setTimeout(function () {
      overlay.hidden = true;
    }, 420);
  }

  function init() {
    overlay = byId('term-panel-overlay');
    panel = byId('term-panel');
    closeBtn = byId('term-panel-close');
    if (!overlay || !panel || !closeBtn) return;

    document.querySelectorAll('.term-card[data-panel-pair]').forEach(function (card) {
      card.addEventListener('click', function () {
        openPanel(card);
      });
    });

    overlay.addEventListener('click', closePanel);
    closeBtn.addEventListener('click', closePanel);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && panel.classList.contains('is-open')) {
        closePanel();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})(typeof window !== 'undefined' ? window : this);
