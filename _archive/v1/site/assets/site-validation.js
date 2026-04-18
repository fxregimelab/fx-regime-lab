/**
 * Marketing shell: load validation_log summaries from Supabase (anon).
 * Shows real rolling accuracy only when enough evaluated rows exist; else disclaimer.
 */
(function (global) {
  'use strict';

  /** Min evaluated rows (correct_1d true/false) in 20d window to show percentages. */
  var MIN_EVALUATED_20D = 25;
  var PAIRS = [
    { code: 'EURUSD', label: 'EUR/USD' },
    { code: 'USDJPY', label: 'USD/JPY' },
    { code: 'USDINR', label: 'USD/INR' },
  ];

  var DISCLAIMER =
    'Framework live from April 2026 — out-of-sample validation is accumulating. See Methodology for how NEUTRAL calls are scored.';

  var DISCLAIMER_SHORT =
    'Validation accumulating (since Apr 2026). Rolling accuracy appears after enough evaluated days.';

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

  function getClient() {
    var url = global.__SUPABASE_URL__;
    var key = global.__SUPABASE_ANON_KEY__;
    if (!url || !key || !global.supabase || typeof global.supabase.createClient !== 'function') {
      return null;
    }
    return global.supabase.createClient(url, key);
  }

  function fetchValidation(client, pair, days) {
    var n = Math.max(1, Math.min(500, days || 30));
    var start = new Date();
    start.setDate(start.getDate() - n);
    var startStr = start.toISOString().split('T')[0];
    return client
      .from('validation_log')
      .select(
        'date,pair,predicted_direction,predicted_regime,confidence,actual_direction,actual_return_1d,correct_1d'
      )
      .eq('pair', pair)
      .gte('date', startStr)
      .order('date', { ascending: false })
      .then(function (res) {
        if (res.error) throw res.error;
        return res.data || [];
      })
      .catch(function () {
        return [];
      });
  }

  /**
   * @returns {Promise<{ evaluated20: number, total500: number, byPair: Object, showAccuracy: boolean }>}
   */
  function loadMarketingValidation() {
    var client = getClient();
    if (!client) {
      return Promise.resolve({
        evaluated20: 0,
        total500: 0,
        byPair: {},
        showAccuracy: false,
      });
    }
    return Promise.all(
      PAIRS.map(function (p) {
        return Promise.all([
          fetchValidation(client, p.code, 20),
          fetchValidation(client, p.code, 500),
        ]).then(function (arr) {
          return { code: p.code, label: p.label, rows20: arr[0], rows500: arr[1] };
        });
      })
    ).then(function (packs) {
      var evaluated20 = 0;
      var total500 = 0;
      var byPair = {};
      packs.forEach(function (pack) {
        var s20 = summarize(pack.rows20);
        evaluated20 += s20.total;
        total500 += (pack.rows500 || []).filter(function (r) {
          return hasValidation(r && r.correct_1d);
        }).length;
        byPair[pack.code] = { label: pack.label, summary20: s20 };
      });
      var showAccuracy = evaluated20 >= MIN_EVALUATED_20D;
      return { evaluated20: evaluated20, total500: total500, byPair: byPair, showAccuracy: showAccuracy };
    });
  }

  function formatAccuracyBar(payload) {
    if (!payload.showAccuracy) {
      return { html: DISCLAIMER, short: 'Validation accumulating' };
    }
    var parts = [];
    PAIRS.forEach(function (p) {
      var s = payload.byPair[p.code] && payload.byPair[p.code].summary20;
      if (!s || !isFinite(s.pct)) {
        parts.push(p.label + ' —');
      } else {
        parts.push(p.label + ' ' + Math.round(s.pct) + '%');
      }
    });
    var line = 'Accuracy (20d, evaluated days): ' + parts.join(' · ');
    return { html: line, short: line };
  }

  global.FXRLSiteValidation = {
    MIN_EVALUATED_20D: MIN_EVALUATED_20D,
    DISCLAIMER: DISCLAIMER,
    DISCLAIMER_SHORT: DISCLAIMER_SHORT,
    loadMarketingValidation: loadMarketingValidation,
    formatAccuracyBar: formatAccuracyBar,
    summarize: summarize,
  };
})(typeof window !== 'undefined' ? window : this);
