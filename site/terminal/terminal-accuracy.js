(function (global) {
  'use strict';

  var PAIRS = [
    { code: 'EURUSD', label: 'EUR/USD' },
    { code: 'USDJPY', label: 'USD/JPY' },
    { code: 'USDINR', label: 'USD/INR' },
  ];

  function hasValidation(v) {
    return v === true || v === false;
  }

  function summarize(rows) {
    var evalRows = (rows || []).filter(function (r) {
      return hasValidation(r && r.correct_1d);
    });
    var total = evalRows.length;
    var correct = evalRows.filter(function (r) {
      return r.correct_1d === true;
    }).length;
    var pct = total > 0 ? (correct / total) * 100 : null;
    return { total: total, correct: correct, pct: pct };
  }

  function pctClass(pct) {
    if (!isFinite(pct)) return '';
    if (pct > 60) return 'term-accuracy-item__pct--bull';
    if (pct >= 50) return 'term-accuracy-item__pct--neu';
    return 'term-accuracy-item__pct--bear';
  }

  function setItem(pair, summary) {
    var row = document.querySelector('[data-acc-pair="' + pair.code + '"]');
    if (!row) return;
    var pctEl = row.querySelector('.term-accuracy-item__pct');
    if (!pctEl) return;
    if (!isFinite(summary.pct)) {
      pctEl.textContent = '—';
      pctEl.className = 'term-accuracy-item__pct';
      return;
    }
    pctEl.textContent = Math.round(summary.pct) + '%';
    pctEl.className = 'term-accuracy-item__pct ' + pctClass(summary.pct);
  }

  function setTotal(text) {
    var totalEl = document.getElementById('term-accuracy-total');
    if (totalEl) totalEl.textContent = text;
  }

  function initAccuracyStrip() {
    var api = global.FXRLData;
    if (!api || typeof api.fetchValidationLog !== 'function') {
      return;
    }

    if (typeof api.getSupabaseClient === 'function' && !api.getSupabaseClient()) {
      setTotal('No validation data');
      return;
    }

    Promise.all(
      PAIRS.map(function (pair) {
        return Promise.all([
          api.fetchValidationLog(pair.code, 20),
          api.fetchValidationLog(pair.code, 500),
        ]).then(function (payload) {
          return { pair: pair, rows20: payload[0] || [], rows500: payload[1] || [] };
        });
      })
    )
      .then(function (packs) {
        var totalLogged = 0;
        packs.forEach(function (pack) {
          setItem(pack.pair, summarize(pack.rows20));
          totalLogged += pack.rows500.length;
        });
        if (totalLogged > 0) {
          setTotal(totalLogged + ' predictions logged');
        } else {
          setTotal('No validation data');
        }
      })
      .catch(function () {
        setTotal('No validation data');
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAccuracyStrip);
  } else {
    initAccuracyStrip();
  }
})(typeof window !== 'undefined' ? window : this);
