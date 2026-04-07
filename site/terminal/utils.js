/**
 * Shared terminal utilities (FX Regime Lab).
 * Load before lw-charts-config.js, chart-builder.js, data-client.js, pair inline scripts.
 */
(function (global) {
  'use strict';

  /**
   * Parse a CSV text into [timestamp_ms, value] tuples for chart series.
   * Note: simple comma split — not for quoted fields; use parseMasterCsv in data-client for full master CSV.
   * @param {string} csvText - raw CSV string
   * @param {string} dateCol - column name for the date field
   * @param {string} valueCol - column name for the value field
   * @returns {Array} [[timestamp_ms, number], ...]
   */
  function parseCSVtoTimeSeries(csvText, dateCol, valueCol) {
    var lines = String(csvText || '')
      .trim()
      .split('\n')
      .filter(function (l) {
        return l.trim().length;
      });
    if (!lines.length) return [];
    var headers = lines[0].split(',').map(function (h) {
      return h.trim();
    });
    var dateIdx = headers.indexOf(dateCol);
    var valueIdx = headers.indexOf(valueCol);
    if (dateIdx === -1 || valueIdx === -1) {
      if (global.console && global.console.error) {
        global.console.error('[utils] Column not found: ' + dateCol + ' or ' + valueCol);
      }
      return [];
    }
    var acc = [];
    for (var r = 1; r < lines.length; r++) {
      var cols = lines[r].split(',');
      var ds = cols[dateIdx] != null ? cols[dateIdx].trim() : '';
      var vs = cols[valueIdx] != null ? cols[valueIdx].trim() : '';
      var ts = new Date(ds).getTime();
      var val = parseFloat(vs);
      if (isFinite(ts) && !isNaN(val)) acc.push([ts, val]);
    }
    return acc;
  }

  function formatPct(value, decimals) {
    var d = decimals != null ? decimals : 2;
    var sign = value >= 0 ? '+' : '';
    return sign + value.toFixed(d) + '%';
  }

  function formatBp(value) {
    var sign = value >= 0 ? '+' : '';
    return sign + Math.round(value) + 'bp';
  }

  function formatSign(value, decimals) {
    var d = decimals != null ? decimals : 2;
    var sign = value >= 0 ? '+' : '';
    return sign + value.toFixed(d);
  }

  function timestampToMs(dateString) {
    return new Date(dateString).getTime();
  }

  function getDirectionColour(direction) {
    var map = {
      bullish: 'var(--bullish)',
      bearish: 'var(--bearish)',
      neutral: 'var(--neutral)',
      anomaly: 'var(--anomaly)',
    };
    return map[direction] != null ? map[direction] : 'var(--neutral)';
  }

  function debounce(fn, delay) {
    var timer = null;
    return function () {
      var args = arguments;
      var ctx = this;
      if (timer) clearTimeout(timer);
      timer = setTimeout(function () {
        timer = null;
        fn.apply(ctx, args);
      }, delay);
    };
  }

  global.FXUtils = {
    parseCSVtoTimeSeries: parseCSVtoTimeSeries,
    formatPct: formatPct,
    formatBp: formatBp,
    formatSign: formatSign,
    timestampToMs: timestampToMs,
    getDirectionColour: getDirectionColour,
    debounce: debounce,
  };
})(typeof window !== 'undefined' ? window : this);
