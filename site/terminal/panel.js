(function (global) {
  'use strict';

  var overlay;
  var panel;
  var closeBtn;
  var activePair = null;
  var panelChartInst = null;

  var PAIR_LABEL = {
    EURUSD: 'EUR/USD',
    USDJPY: 'USD/JPY',
    USDINR: 'USD/INR',
  };

  var PAIR_CODE_MAP = {
    eurusd: 'EURUSD',
    usdjpy: 'USDJPY',
    usdinr: 'USDINR',
  };

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

  function normalizePairCode(pairLike) {
    var raw = String(pairLike || '').trim();
    if (!raw) return '';
    var compact = raw.replace(/[^A-Za-z]/g, '').toLowerCase();
    return PAIR_CODE_MAP[compact] || raw.toUpperCase();
  }

  function dashboardUrlForPair(pairCode) {
    return '/terminal/dashboard.html?pair=' + encodeURIComponent(pairCode);
  }

  function stripDriverPrefix(s) {
    var t = String(s || '').trim();
    if (t.indexOf('Driver:') === 0) return t.slice(7).trim();
    return t;
  }

  function prettyDriverLine(raw) {
    var api = global.FXRLData;
    var inner = stripDriverPrefix(raw);
    if (!inner) return '—';
    if (api && typeof api.formatDriverLabel === 'function') {
      var lab = api.formatDriverLabel(inner);
      return lab ? 'Driver: ' + lab : '—';
    }
    var full = String(raw || '').trim();
    return full.indexOf('Driver:') === 0 ? full : 'Driver: ' + inner;
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
    html.push(
      '<tr><td>Primary driver</td><td>' +
        (article.key_driver ? prettyDriverLine(article.key_driver) : '—') +
        '</td></tr>'
    );
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

  function disposePanelChart() {
    if (panelChartInst && panelChartInst.chart && typeof panelChartInst.chart.dispose === 'function') {
      try {
        if (!panelChartInst.chart.isDisposed()) panelChartInst.chart.dispose();
      } catch (e) {}
    }
    if (panelChartInst && typeof panelChartInst.disposeExtra === 'function') {
      try {
        panelChartInst.disposeExtra();
      } catch (e2) {}
    }
    panelChartInst = null;
  }

  function renderChart(pair) {
    var mount = byId('term-panel-chart');
    if (!mount) return;
    var FX = global.FXRLCharts;
    if (!FX || typeof FX.waitForLWC !== 'function' || typeof FX.area !== 'function') return;
    var api = global.FXRLData;
    if (!api || typeof api.fetchSignalsFromSupabase !== 'function') return;

    disposePanelChart();
    mount.innerHTML = '';

    api
      .fetchSignalsFromSupabase(pair, 90)
      .then(function (rows) {
        var slice = (rows || []).slice(-30);
        var points = slice
          .map(function (row) {
            var v = row && row.spot != null ? parseFloat(String(row.spot).replace(/,/g, '')) : NaN;
            return isFinite(v) ? v : null;
          })
          .filter(function (v) {
            return v != null;
          });

        if (!points.length) return;
        var color = pair === 'EURUSD' ? '#4d8eff' : pair === 'USDJPY' ? '#d4890a' : '#c94040';
        var tuples = [];
        var dayMs = 86400000;
        var now = Date.now();
        for (var i = 0; i < points.length; i++) {
          tuples.push([now - (points.length - 1 - i) * dayMs, points[i]]);
        }
        return FX.waitForLWC().then(function (ready) {
          if (!ready) return;
          return FX.area(mount, tuples, {
            skipRangeButtons: true,
            color: color,
            lineWidth: 2,
            theme: {
              handleScroll: false,
              handleScale: false,
              crosshairMode: 2,
            },
          });
        });
      })
      .then(function (inst) {
        if (inst) panelChartInst = inst;
      })
      .catch(function () {});
  }

  function openPanel(card) {
    activePair = normalizePairCode(card.getAttribute('data-panel-pair'));
    var article = getPairArticle(activePair);
    var pairLabel = PAIR_LABEL[activePair] || activePair;
    var pairUrl = dashboardUrlForPair(activePair);
    var spot = card.getAttribute('data-panel-spot') || '—';
    var driverRaw = card.getAttribute('data-panel-driver') || article.key_driver || '—';
    var driver = driverRaw === '—' ? '—' : prettyDriverLine(driverRaw);
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
    disposePanelChart();
    var mount = byId('term-panel-chart');
    if (mount) mount.innerHTML = '';
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(typeof window !== 'undefined' ? window : this);
