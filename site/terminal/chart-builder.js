/**
 * FX Regime Lab — Terminal Chart Builder
 * Series catalog, Lightweight Charts preview, PNG export, Quick Charts, theme.
 */
(function (global) {
  'use strict';

  var DATA_SOURCE = 'supabase';
  var LS_QUICK = 'fxrl_quickcharts';
  var LS_THEME = 'fxrl_chartbuilder_theme';
  var LIGHT_BG = '#FAFAF8';
  var DARK_BG = '#0b0e14';
  var PREFETCH_PAIRS = ['EURUSD', 'USDJPY', 'USDINR'];
  var PREFETCH_COLUMNS = [
    'spot',
    'rate_diff_2y',
    'rate_diff_10y',
    'cot_lev_money_net',
    'cot_asset_mgr_net',
    'cot_percentile',
    'realized_vol_5d',
    'realized_vol_20d',
    'cross_asset_dxy',
    'cross_asset_oil',
    'cross_asset_vix',
  ];
  var DATA = {
    EURUSD: null,
    USDJPY: null,
    USDINR: null,
  };
  var SERIES_AVAILABILITY = {};
  var PREFETCH_DONE = false;
  var _paperTextureCanvas = null;

  // Mirror of data-client.js mapping; used only for local column lookup.
  var SIGNAL_TO_CSV = {
    EURUSD: {
      spot: 'EURUSD',
      rate_diff_2y: 'US_DE_2Y_spread',
      rate_diff_10y: 'US_DE_10Y_spread',
      rate_diff_zscore: 'US_DE_2Y_spread_zscore',
      cot_lev_money_net: 'EUR_lev_net',
      cot_asset_mgr_net: 'EUR_assetmgr_net',
      cot_percentile: 'EUR_lev_percentile',
      realized_vol_5d: 'EURUSD_vol5',
      realized_vol_20d: 'EURUSD_vol30',
      cross_asset_dxy: 'DXY',
      cross_asset_oil: 'Brent',
      cross_asset_vix: 'VIX',
    },
    USDJPY: {
      spot: 'USDJPY',
      rate_diff_2y: 'US_JP_2Y_spread',
      rate_diff_10y: 'US_JP_10Y_spread',
      rate_diff_zscore: 'US_JP_2Y_spread_zscore',
      cot_lev_money_net: 'JPY_lev_net',
      cot_asset_mgr_net: 'JPY_assetmgr_net',
      cot_percentile: 'JPY_lev_percentile',
      realized_vol_5d: 'USDJPY_vol5',
      realized_vol_20d: 'USDJPY_vol30',
      cross_asset_dxy: 'DXY',
      cross_asset_oil: 'Brent',
      cross_asset_vix: 'VIX',
    },
    USDINR: {
      spot: 'USDINR',
      rate_diff_2y: 'US_IN_policy_spread',
      rate_diff_10y: 'US_IN_10Y_spread',
      rate_diff_zscore: 'US_IN_policy_spread_zscore',
      realized_vol_5d: 'USDINR_vol5',
      realized_vol_20d: 'USDINR_vol30',
      cross_asset_dxy: 'DXY',
      cross_asset_oil: 'Brent',
      cross_asset_vix: 'VIX',
    },
  };
  var CSV_TO_SIGNAL = {};
  Object.keys(SIGNAL_TO_CSV).forEach(function (pair) {
    var m = SIGNAL_TO_CSV[pair];
    Object.keys(m).forEach(function (dbCol) {
      var csvCol = m[dbCol];
      if (!CSV_TO_SIGNAL[csvCol]) CSV_TO_SIGNAL[csvCol] = [];
      CSV_TO_SIGNAL[csvCol].push({ pair: pair, dbCol: dbCol });
    });
  });

  function num(x) {
    if (x === '' || x == null) return NaN;
    var n = parseFloat(String(x).replace(/,/g, ''));
    return isFinite(n) ? n : NaN;
  }

  function ts(dateStr) {
    var iso = String(dateStr || '').trim() + 'T12:00:00Z';
    var U = global.FXUtils;
    if (U && typeof U.timestampToMs === 'function') {
      var t0 = U.timestampToMs(iso);
      return isFinite(t0) ? t0 : NaN;
    }
    var t1 = new Date(iso).getTime();
    return isFinite(t1) ? t1 : NaN;
  }

  function rollingVol60FromSpot(spotSeries) {
    var out = [];
    for (var i = 0; i < spotSeries.length; i++) {
      if (i < 61) {
        out.push([spotSeries[i][0], NaN]);
        continue;
      }
      var rets = [];
      for (var j = i - 59; j <= i; j++) {
        var p0 = spotSeries[j - 1][1];
        var p1 = spotSeries[j][1];
        if (!isFinite(p0) || !isFinite(p1) || p0 <= 0) continue;
        rets.push(Math.log(p1 / p0));
      }
      if (rets.length < 50) {
        out.push([spotSeries[i][0], NaN]);
        continue;
      }
      var m = rets.reduce(function (a, b) {
        return a + b;
      }, 0) / rets.length;
      var v = 0;
      for (var k = 0; k < rets.length; k++) v += (rets[k] - m) * (rets[k] - m);
      v = Math.sqrt(v / (rets.length - 1)) * Math.sqrt(252) * 100;
      out.push([spotSeries[i][0], v]);
    }
    return out;
  }

  function rowsToSeries(rows, col) {
    var out = [];
    for (var i = 0; i < rows.length; i++) {
      var t = ts(rows[i].date);
      var v = num(rows[i][col]);
      if (isFinite(t) && isFinite(v)) out.push([t, v]);
    }
    return out;
  }

  function filterByRange(pts, rangeMs) {
    if (!rangeMs) return pts;
    var cut = Date.now() - rangeMs;
    return pts.filter(function (p) {
      return p[0] >= cut;
    });
  }

  function valueAtOrBefore(pts, t0) {
    var v = NaN;
    for (var i = 0; i < pts.length; i++) {
      if (pts[i][0] <= t0) v = pts[i][1];
      else break;
    }
    return v;
  }

  function deepClone(o) {
    return JSON.parse(JSON.stringify(o));
  }

  function hasFinitePoints(pts) {
    if (!Array.isArray(pts) || !pts.length) return false;
    for (var i = 0; i < pts.length; i++) {
      if (isFinite(pts[i][0]) && isFinite(pts[i][1])) return true;
    }
    return false;
  }

  function clonePoints(pts) {
    if (!Array.isArray(pts)) return [];
    return pts.map(function (p) {
      return [p[0], p[1]];
    });
  }

  var DATA_CATALOG = {
    categories: [
      {
        id: 'fx_prices',
        label: 'FX PRICES',
        series: [
          { id: 'eurusd_price', label: 'EUR/USD', colour: '#4d8eff', csvColumn: 'EURUSD', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'usdjpy_price', label: 'USD/JPY', colour: '#d4890a', csvColumn: 'USDJPY', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'usdinr_price', label: 'USD/INR', colour: '#c94040', csvColumn: 'USDINR', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'dxy', label: 'DXY', colour: '#9ca3af', csvColumn: 'DXY', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
        ],
      },
      {
        id: 'commodities',
        label: 'COMMODITIES',
        series: [
          { id: 'gold', label: 'Gold', colour: '#e8b870', csvColumn: 'Gold', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'brent', label: 'Brent', colour: '#6b7280', csvColumn: 'Brent', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
        ],
      },
      {
        id: 'rate_spreads',
        label: 'RATE SPREADS',
        series: [
          { id: 'us_de_2y', label: 'US–DE 2Y spread', colour: '#4d8eff', csvColumn: 'US_DE_2Y_spread', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'us_de_10y', label: 'US–DE 10Y spread', colour: '#7aaaf0', csvColumn: 'US_DE_10Y_spread', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'us_jp_2y', label: 'US–JP 2Y spread', colour: '#d4890a', csvColumn: 'US_JP_2Y_spread', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'us_jp_10y', label: 'US–JP 10Y spread', colour: '#e8b870', csvColumn: 'US_JP_10Y_spread', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'us_in_10y', label: 'US–IN 10Y spread', colour: '#c94040', csvColumn: 'US_IN_10Y_spread', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'us_in_policy', label: 'US–IN policy spread', colour: '#e87878', csvColumn: 'US_IN_policy_spread', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'us_curve', label: 'US curve (10Y–2Y)', colour: '#7c6bcf', csvColumn: 'US_curve', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'btp_bund', label: 'BTP–Bund', colour: '#a78bfa', csvColumn: 'BTP_Bund_spread', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
        ],
      },
      {
        id: 'cot_eur',
        label: 'COT — EUR',
        series: [
          { id: 'eurusd_lev_money', label: 'EUR lev money net', colour: '#4d8eff', csvColumn: 'EUR_lev_net', csvFile: DATA_SOURCE, defaultType: 'bar', yAxis: 'left' },
          { id: 'eurusd_asset_mgr', label: 'EUR asset mgr net', colour: '#6b7280', csvColumn: 'EUR_assetmgr_net', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'right' },
        ],
      },
      {
        id: 'cot_jpy',
        label: 'COT — JPY',
        series: [
          { id: 'jpy_lev_money', label: 'JPY lev money net', colour: '#d4890a', csvColumn: 'JPY_lev_net', csvFile: DATA_SOURCE, defaultType: 'bar', yAxis: 'left' },
          { id: 'jpy_asset_mgr', label: 'JPY asset mgr net', colour: '#6b7280', csvColumn: 'JPY_assetmgr_net', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'right' },
        ],
      },
      {
        id: 'volatility',
        label: 'REALIZED VOL',
        series: [
          { id: 'eurusd_vol_30d', label: 'EUR/USD 30D vol', colour: '#4d8eff', csvColumn: 'EURUSD_vol30', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'eurusd_vol_60d', label: 'EUR/USD 60D vol (est.)', colour: '#7aaaf0', csvColumn: 'EURUSD', csvFile: DATA_SOURCE, computed: 'vol60_from_price', defaultType: 'line', yAxis: 'left' },
          { id: 'usdjpy_vol_30d', label: 'USD/JPY 30D vol', colour: '#d4890a', csvColumn: 'USDJPY_vol30', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'usdinr_vol_30d', label: 'USD/INR 30D vol', colour: '#c94040', csvColumn: 'USDINR_vol30', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
        ],
      },
      {
        id: 'regime',
        label: 'REGIME / COMPOSITE',
        series: [
          { id: 'eurusd_composite', label: 'EUR/USD composite score', colour: '#4d8eff', csvColumn: 'eurusd_composite_score', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'usdjpy_composite', label: 'USD/JPY composite score', colour: '#d4890a', csvColumn: 'usdjpy_composite_score', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'usdinr_composite', label: 'USD/INR composite (INR score)', colour: '#c94040', csvColumn: 'inr_composite_score', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
        ],
      },
      {
        id: 'correlations',
        label: 'CORRELATIONS (60D)',
        series: [
          { id: 'dxy_eurusd_corr', label: 'DXY vs EUR/USD', colour: '#4d8eff', csvColumn: 'dxy_eurusd_corr_60d', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'dxy_usdjpy_corr', label: 'DXY vs USD/JPY', colour: '#d4890a', csvColumn: 'dxy_usdjpy_corr_60d', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'dxy_inr_corr', label: 'DXY vs USD/INR', colour: '#c94040', csvColumn: 'dxy_inr_corr_60d', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
          { id: 'gold_inr_corr', label: 'Gold vs USD/INR', colour: '#e8b870', csvColumn: 'gold_inr_corr_60d', csvFile: DATA_SOURCE, defaultType: 'line', yAxis: 'left' },
        ],
      },
    ],
  };

  function catalogById() {
    var m = {};
    DATA_CATALOG.categories.forEach(function (cat) {
      cat.series.forEach(function (s) {
        m[s.id] = s;
      });
    });
    return m;
  }

  var BUILT_IN_PRESETS = [
    {
      id: 'safe_haven',
      label: 'Safe Haven Breakdown',
      description: 'EUR/USD, USD/JPY, Gold, DXY indexed to baseline',
      series: ['eurusd_price', 'usdjpy_price', 'gold', 'dxy'],
      types: { all: 'line' },
      indexed: true,
      baselineDate: 'auto',
    },
    {
      id: 'rate_diff_vs_price',
      label: 'Rate Differential vs Price',
      description: 'EUR/USD price + US–DE 2Y spread',
      series: ['eurusd_price', 'us_de_2y'],
      types: { eurusd_price: 'line', us_de_2y: 'bar' },
      yAxis: { eurusd_price: 'left', us_de_2y: 'right' },
    },
    {
      id: 'cot_overview',
      label: 'COT Positioning',
      description: 'EUR lev money net + asset mgr net',
      series: ['eurusd_lev_money', 'eurusd_asset_mgr'],
      types: { eurusd_lev_money: 'bar', eurusd_asset_mgr: 'line' },
      yAxis: { eurusd_asset_mgr: 'right' },
    },
    {
      id: 'vol_regime',
      label: 'Volatility Regime',
      description: 'EUR/USD 30D and 60D realized vol',
      series: ['eurusd_vol_30d', 'eurusd_vol_60d'],
      types: { all: 'line' },
    },
    {
      id: 'regime_composite',
      label: 'Regime Signal Composite',
      description: 'All three pair composite scores',
      series: ['eurusd_composite', 'usdjpy_composite', 'usdinr_composite'],
      types: { all: 'line' },
    },
  ];

  function loadSeriesPoints(meta, rows) {
    if (meta.computed === 'vol60_from_price') {
      var spot = rowsToSeries(rows, meta.csvColumn);
      return rollingVol60FromSpot(spot);
    }
    return rowsToSeries(rows, meta.csvColumn);
  }

  function createPaperTexture(ctx) {
    var patternCanvas = document.createElement('canvas');
    patternCanvas.width = 200;
    patternCanvas.height = 200;
    var pCtx = patternCanvas.getContext('2d');
    pCtx.fillStyle = LIGHT_BG;
    pCtx.fillRect(0, 0, 200, 200);
    for (var i = 0; i < 800; i++) {
      var x = Math.random() * 200;
      var y = Math.random() * 200;
      var opacity = Math.random() * 0.04;
      pCtx.fillStyle = 'rgba(100, 90, 60, ' + opacity.toFixed(4) + ')';
      pCtx.fillRect(x, y, 1, 1);
    }
    return ctx.createPattern(patternCanvas, 'repeat');
  }

  function getPaperTextureBackground() {
    if (_paperTextureCanvas) {
      return { image: _paperTextureCanvas, repeat: 'repeat' };
    }
    _paperTextureCanvas = document.createElement('canvas');
    _paperTextureCanvas.width = 200;
    _paperTextureCanvas.height = 200;
    var ctx = _paperTextureCanvas.getContext('2d');
    if (!ctx) return LIGHT_BG;
    ctx.fillStyle = LIGHT_BG;
    ctx.fillRect(0, 0, 200, 200);
    for (var i = 0; i < 800; i++) {
      var x = Math.random() * 200;
      var y = Math.random() * 200;
      var opacity = Math.random() * 0.04;
      ctx.fillStyle = 'rgba(100, 90, 60, ' + opacity.toFixed(4) + ')';
      ctx.fillRect(x, y, 1, 1);
    }
    return { image: _paperTextureCanvas, repeat: 'repeat' };
  }

  function resolveFromSignalCache(csvColumn) {
    var refs = CSV_TO_SIGNAL[csvColumn] || [];
    for (var i = 0; i < refs.length; i++) {
      var ref = refs[i];
      var pairData = DATA[ref.pair];
      var pts = pairData && pairData[ref.dbCol];
      if (hasFinitePoints(pts)) return clonePoints(pts);
    }
    return [];
  }

  function resolveSeriesRaw(meta) {
    if (!meta) return [];
    if (meta.computed === 'vol60_from_price') {
      var spot = resolveFromSignalCache(meta.csvColumn);
      return hasFinitePoints(spot) ? rollingVol60FromSpot(spot) : [];
    }
    var fromSignals = resolveFromSignalCache(meta.csvColumn);
    if (hasFinitePoints(fromSignals)) return fromSignals;
    return [];
  }

  function updateSidebarAvailability() {
    DATA_CATALOG.categories.forEach(function (cat) {
      cat.series.forEach(function (meta) {
        var raw = resolveSeriesRaw(meta);
        var available = hasFinitePoints(raw);
        meta.available = available;
        SERIES_AVAILABILITY[meta.id] = {
          available: available,
          pending: !available,
        };
      });
    });
    return SERIES_AVAILABILITY;
  }

  function prefetchAllData() {
    var DC = global.FXRLData;
    var fetchSignals = DC && typeof DC.fetchSignals === 'function' ? DC.fetchSignals : null;
    var boot =
      DC && typeof DC.initDataClient === 'function' ? DC.initDataClient() : Promise.resolve(null);

    return boot.then(function () {
      if (!fetchSignals) {
        PREFETCH_DONE = true;
        return updateSidebarAvailability();
      }
      return Promise.allSettled(
        PREFETCH_PAIRS.map(function (pair) {
          return fetchSignals(pair, PREFETCH_COLUMNS, '2020-01-01').then(function (data) {
            return { pair: pair, data: data };
          });
        })
      ).then(function (results) {
        results.forEach(function (result) {
          if (result.status === 'fulfilled') {
            var value = result.value || {};
            DATA[value.pair] = value.data || null;
          }
        });
        PREFETCH_DONE = true;
        return updateSidebarAvailability();
      });
    });
  }

  var ThemeManager = {
    current: 'dark',
    themes: {
      dark: {
        bg: DARK_BG,
        text: '#8a9485',
        textStrong: '#e8ede8',
        axis: '#252820',
        grid: '#1c1f18',
        splitLine: '#1c1f18',
        tooltipBg: '#191c15',
        tooltipBorder: '#2e3228',
        exportFooter: '#131510',
        exportUrl: '#8a9485',
        wordmarkDataUri: null,
      },
      light: {
        bg: LIGHT_BG,
        text: '#6B6355',
        textStrong: '#1E1A12',
        axis: '#E8E4DC',
        grid: '#E8E4DC',
        splitLine: '#E8E4DC',
        tooltipBg: '#FFFEF8',
        tooltipBorder: '#E0D8C8',
        exportFooter: LIGHT_BG,
        exportUrl: 'rgba(80,70,50,0.5)',
        wordmarkDataUri: null,
      },
    },
    init: function () {
      try {
        var s = global.localStorage.getItem(LS_THEME);
        if (s === 'light' || s === 'dark') this.current = s;
      } catch (e) { /* ignore */ }
    },
    applyTheme: function (name) {
      if (name !== 'light' && name !== 'dark') name = 'dark';
      this.current = name;
      try {
        global.localStorage.setItem(LS_THEME, name);
      } catch (e2) { /* ignore */ }
    },
    colors: function () {
      return this.themes[this.current];
    },
  };

  function makeWordmarkSvgDataUri(theme) {
    var fill = theme === 'light' ? '#111827' : '#e8ede8';
    var svg =
      '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="22">' +
      '<text x="0" y="16" fill="' +
      fill +
      '" font-family="Inter,system-ui,sans-serif" font-size="13" font-weight="600">FX Regime Lab</text></svg>';
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }

  var SeriesManager = {
    active: new Map(),
    indexedMode: false,
    catalogMap: catalogById(),
    onChange: null,

    setIndexedMode: function (on, baselineTs) {
      this.indexedMode = !!on;
      this._baselineTs = baselineTs || null;
    },

    _computeBaselineTs: function () {
      var mins = [];
      this.active.forEach(function (entry) {
        if (entry.raw.length) mins.push(entry.raw[0][0]);
      });
      if (!mins.length) return null;
      return Math.max.apply(null, mins);
    },

    _prepareDisplay: function (entry, rangeMs) {
      var pts = filterByRange(entry.raw, rangeMs);
      if (!SeriesManager.indexedMode) return pts;
      var t0 = SeriesManager._baselineTs != null ? SeriesManager._baselineTs : SeriesManager._computeBaselineTs();
      if (t0 == null) return pts;
      var base = valueAtOrBefore(entry.raw, t0);
      if (!isFinite(base) || base === 0) return pts;
      return pts.map(function (p) {
        return [p[0], isFinite(p[1]) ? (100 * p[1]) / base : NaN];
      });
    },

    _baselineTs: null,

    addSeries: function (id) {
      var meta = this.catalogMap[id];
      if (!meta || this.active.has(id)) return Promise.resolve();
      if (meta.available === false) return Promise.resolve(false);
      var raw = resolveSeriesRaw(meta);
      if (!hasFinitePoints(raw)) return Promise.resolve(false);
      this.active.set(id, {
        meta: meta,
        raw: raw,
        chartType: meta.defaultType || 'line',
        yAxis: meta.yAxis || 'left',
        lineStyle: 'solid',
        colour: meta.colour,
      });
      if (typeof this.onChange === 'function') this.onChange();
      return Promise.resolve(true);
    },

    removeSeries: function (id) {
      this.active.delete(id);
      if (typeof this.onChange === 'function') this.onChange();
    },

    setChartType: function (id, type) {
      var e = this.active.get(id);
      if (!e) return;
      e.chartType = type;
      if (typeof this.onChange === 'function') this.onChange();
    },

    setYAxis: function (id, side) {
      var e = this.active.get(id);
      if (!e) return;
      e.yAxis = side === 'right' ? 'right' : 'left';
      if (typeof this.onChange === 'function') this.onChange();
    },

    setColour: function (id, hex) {
      var e = this.active.get(id);
      if (!e) return;
      e.colour = hex;
      if (typeof this.onChange === 'function') this.onChange();
    },

    setLineStyle: function (id, style) {
      var e = this.active.get(id);
      if (!e) return;
      e.lineStyle = style === 'dashed' ? 'dashed' : 'solid';
      if (typeof this.onChange === 'function') this.onChange();
    },

    clear: function () {
      this.active.clear();
      this.indexedMode = false;
      this._baselineTs = null;
      if (typeof this.onChange === 'function') this.onChange();
    },
    hasDataSeries: function () {
      if (!this.active.size) return false;
      var hasData = false;
      this.active.forEach(function (entry) {
        if (hasFinitePoints(entry.raw)) hasData = true;
      });
      return hasData;
    },

    snapshotForPreset: function () {
      var out = { series: [], configs: {} };
      this.active.forEach(function (entry, id) {
        out.series.push(id);
        out.configs[id] = {
          chartType: entry.chartType,
          yAxis: entry.yAxis,
          colour: entry.colour,
          lineStyle: entry.lineStyle,
        };
      });
      out.indexedMode = this.indexedMode;
      return out;
    },

    restoreFromSnapshot: function (snap) {
      var self = this;
      this.clear();
      this.setIndexedMode(!!snap.indexedMode, null);
      var chain = Promise.resolve();
      (snap.series || []).forEach(function (id) {
        chain = chain.then(function () {
          return self.addSeries(id).then(function () {
            var c = snap.configs && snap.configs[id];
            if (c) {
              if (c.chartType) self.setChartType(id, c.chartType);
              if (c.yAxis) self.setYAxis(id, c.yAxis);
              if (c.colour) self.setColour(id, c.colour);
              if (c.lineStyle) self.setLineStyle(id, c.lineStyle);
            }
          });
        });
      });
      return chain;
    },
  };

  /**
   * Map catalog series id to Supabase signals (pair, column) for single-series LWC preview.
   * @returns {{ pair: string, column: string }|null}
   */
  function resolvePairColumnForSeries(seriesId) {
    var meta = SeriesManager.catalogMap[seriesId];
    if (!meta || meta.computed === 'vol60_from_price') return null;
    var refs = CSV_TO_SIGNAL[meta.csvColumn] || [];
    if (refs.length) return { pair: refs[0].pair, column: refs[0].dbCol };
    var col = meta.csvColumn;
    if (!col || typeof col !== 'string') return null;
    var c = col.toLowerCase();
    if (c.indexOf('eurusd') === 0 || c.indexOf('eur_') === 0 || c === 'dxy_eurusd_corr_60d') {
      return { pair: 'EURUSD', column: col };
    }
    if (c.indexOf('usdjpy') === 0 || c.indexOf('jpy_') === 0 || c === 'dxy_usdjpy_corr_60d') {
      return { pair: 'USDJPY', column: col };
    }
    if (
      c.indexOf('usdinr') === 0 ||
      c.indexOf('inr_') === 0 ||
      c === 'dxy_inr_corr_60d' ||
      c === 'gold_inr_corr_60d'
    ) {
      return { pair: 'USDINR', column: col };
    }
    return null;
  }

  /**
   * Build / rebuild a Lightweight Charts instance for the chart builder preview.
   */
  function buildChartBuilderLwc(chartEl, rangeMs, themeName) {
    var FX = global.FXRLCharts;
    var LW = global.LightweightCharts;
    if (!chartEl || !FX || !LW || typeof FX.normalizeSeriesData !== 'function') return null;
    var Th = ThemeManager.themes[themeName] || ThemeManager.themes.dark;
    var isLight = themeName === 'light';
    var themeOpts = {
      bg: isLight ? LIGHT_BG : DARK_BG,
      text: Th.text,
      grid: Th.grid,
      border: Th.axis,
      handleScroll: true,
      handleScale: true,
    };
    var chart = LW.createChart(chartEl, FX.baseChartOptions(chartEl, themeOpts));
    var hasLeft = false;
    var hasRight = false;
    SeriesManager.active.forEach(function (entry) {
      if (entry.yAxis === 'right') hasRight = true;
      else hasLeft = true;
    });
    chart.applyOptions({
      leftPriceScale: {
        visible: hasLeft,
        borderColor: Th.axis,
        textColor: Th.text,
        scaleMargins: { top: 0.08, bottom: 0.12 },
      },
      rightPriceScale: {
        visible: hasRight || !hasLeft,
        borderColor: Th.axis,
        textColor: Th.text,
        scaleMargins: { top: 0.08, bottom: 0.12 },
      },
    });

    SeriesManager.active.forEach(function (entry) {
      var raw = SeriesManager._prepareDisplay(entry, rangeMs);
      var normalized = FX.normalizeSeriesData(raw);
      if (!normalized.length) return;
      var c = entry.colour || entry.meta.colour;
      var priceScaleId = entry.yAxis === 'right' ? 'right' : 'left';
      var lineStyle = entry.lineStyle === 'dashed' ? 2 : 0;
      var t = entry.chartType;

      if (t === 'bar') {
        var hb = chart.addSeries(LW.HistogramSeries, {
          color: c,
          priceScaleId: priceScaleId,
          priceLineVisible: false,
        });
        hb.setData(normalized);
      } else if (t === 'area') {
        var ar = chart.addSeries(LW.AreaSeries, {
          lineColor: c,
          topColor: FX.hexToRgba(c, 0.2),
          bottomColor: FX.hexToRgba(c, 0),
          lineWidth: 1.5,
          priceScaleId: priceScaleId,
          lineStyle: lineStyle,
          priceLineVisible: false,
        });
        ar.setData(normalized);
      } else if (t === 'scatter') {
        var sc;
        try {
          sc = chart.addSeries(LW.LineSeries, {
            color: c,
            lineWidth: 2,
            priceScaleId: priceScaleId,
            lineStyle: lineStyle,
            priceLineVisible: false,
            lastValueVisible: false,
            pointMarkersVisible: true,
          });
        } catch (eSc) {
          sc = chart.addSeries(LW.LineSeries, {
            color: c,
            lineWidth: 2,
            priceScaleId: priceScaleId,
            lineStyle: lineStyle,
            priceLineVisible: false,
            lastValueVisible: false,
          });
        }
        sc.setData(normalized);
      } else {
        var ln = chart.addSeries(LW.LineSeries, {
          color: c,
          lineWidth: 1.5,
          priceScaleId: priceScaleId,
          lineStyle: lineStyle,
          priceLineVisible: false,
        });
        ln.setData(normalized);
      }
    });

    FX.applyTimeRangeMs(chart, rangeMs);
    return chart;
  }

  var ExportManager = {
    deriveExportPair: function () {
      var pairs = {};
      SeriesManager.active.forEach(function (entry) {
        var c = entry.meta.csvColumn || '';
        if (/USDJPY|JPY_|US_JP_/i.test(c)) pairs.USDJPY = true;
        else if (/USDINR|INR_|US_IN_/i.test(c)) pairs.USDINR = true;
        else pairs.EURUSD = true;
      });
      var keys = Object.keys(pairs);
      if (!keys.length) return 'chart';
      if (keys.length > 1) return 'multi';
      return keys[0].toLowerCase();
    },
    loadImage: function (src) {
      return new Promise(function (resolve, reject) {
        var img = new global.Image();
        img.onload = function () { resolve(img); };
        img.onerror = reject;
        img.src = src;
      });
    },
    drawWordmark: function (ctx, theme, w, h) {
      var self = this;
      var x = w - 180;
      var y = h - 44;
      var targetW = 160;
      var opacity = theme === 'dark' ? 0.85 : 0.7;
      var usedFallbackForLight = false;
      return (theme === 'light'
        ? this.loadImage('/assets/images/wordmark_dark.png').catch(function () {
          usedFallbackForLight = true;
          return self.loadImage('/assets/images/wordmark_without_bg.png');
        })
        : this.loadImage('/assets/images/wordmark_without_bg.png').catch(function () {
          return self.loadImage(makeWordmarkSvgDataUri(theme));
        }))
        .then(function (wm) {
          var wmH = (wm.height / wm.width) * targetW;
          ctx.save();
          ctx.globalAlpha = opacity;
          if (theme === 'light' && usedFallbackForLight) {
            ctx.filter = 'invert(1)';
          }
          ctx.drawImage(wm, x, y, targetW, wmH);
          ctx.restore();
        }).catch(function () {
          ctx.save();
          ctx.globalAlpha = opacity;
          ctx.fillStyle = theme === 'dark' ? 'rgba(255,255,255,0.78)' : 'rgba(30,25,15,0.7)';
          ctx.font = '600 14px "Inter", system-ui, sans-serif';
          ctx.fillText('FX REGIME LAB', x, y + 18);
          ctx.restore();
        });
    },
    addBranding: function (ctx, config, w, h) {
      var theme = config.theme === 'light' ? 'light' : 'dark';
      var title = config.title || '';
      var subtitle = config.subtitle || '';
      ctx.save();
      ctx.fillStyle = theme === 'dark' ? 'rgba(255,255,255,0.4)' : 'rgba(80,70,50,0.5)';
      ctx.font = '11px "JetBrains Mono", ui-monospace, monospace';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'alphabetic';
      ctx.fillText('fxregimelab.com', 16, h - 16);

      if (title) {
        ctx.fillStyle = theme === 'dark' ? 'rgba(255,255,255,0.7)' : 'rgba(30,25,15,0.7)';
        ctx.font = '600 13px "Inter", system-ui, sans-serif';
        ctx.fillText(title, 16, 24);
      }
      if (subtitle) {
        ctx.fillStyle = theme === 'dark' ? 'rgba(255,255,255,0.5)' : 'rgba(30,25,15,0.55)';
        ctx.font = '11px "Inter", system-ui, sans-serif';
        ctx.fillText(subtitle, 16, 42);
      }
      if (config.showTimestamp && config.asOfDate) {
        ctx.fillStyle = theme === 'dark' ? 'rgba(255,255,255,0.42)' : 'rgba(80,70,50,0.5)';
        ctx.font = '10px "Inter", system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Data as of ' + config.asOfDate, w / 2, h - 16);
      }
      ctx.restore();
      return this.drawWordmark(ctx, theme, w, h);
    },
    triggerDownload: function (canvas, pair, dateStr) {
      var link = document.createElement('a');
      var safeDate = (dateStr || '').replace(/-/g, '') || 'chart';
      link.download = 'fxregimelab_' + pair + '_' + safeDate + '.png';
      link.href = canvas.toDataURL('image/png');
      link.click();
    },
    exportPNG: function (chart, config) {
      var theme = config.theme === 'light' ? 'light' : 'dark';
      var w = config.width || 1200;
      var h = config.height || 627;
      var chartEl = config.chartEl;
      if (!SeriesManager.hasDataSeries()) {
        return Promise.reject(new Error('NO_DATA_SERIES'));
      }
      if (!chart || typeof chart.takeScreenshot !== 'function') {
        return Promise.reject(new Error('NO_CHART'));
      }
      if (w < 100 || h < 100) {
        if (global.console && global.console.error) {
          global.console.error('[ExportManager] Invalid export dimensions');
        }
        return Promise.reject(new Error('invalid dimensions'));
      }
      if (w > 4000 || h > 4000) {
        if (global.console && global.console.error) {
          global.console.error('[ExportManager] Export dimensions too large');
        }
        return Promise.reject(new Error('dimensions too large'));
      }
      var prevW = chartEl ? chartEl.clientWidth : null;
      var prevH = chartEl ? chartEl.clientHeight : null;
      var self = this;
      chart.applyOptions({ width: w, height: h });
      return new Promise(function (resolve, reject) {
        global.requestAnimationFrame(function () {
          global.requestAnimationFrame(function () {
            var shot;
            try {
              shot = chart.takeScreenshot();
            } catch (e) {
              if (chartEl && prevW != null && prevH != null) {
                chart.applyOptions({ width: prevW, height: prevH });
              }
              reject(e);
              return;
            }
            function finishWithCanvas(cv) {
              if (!cv || typeof cv.toDataURL !== 'function') {
                if (chartEl && prevW != null && prevH != null) {
                  chart.applyOptions({ width: prevW, height: prevH });
                }
                reject(new Error('SCREENSHOT_FAILED'));
                return;
              }
              var dataURL = cv.toDataURL('image/png');
              self.loadImage(dataURL).then(function (img) {
                var canvas = document.createElement('canvas');
                canvas.width = w;
                canvas.height = h;
                var ctx = canvas.getContext('2d');
                if (!ctx) {
                  if (chartEl && prevW != null && prevH != null) {
                    chart.applyOptions({ width: prevW, height: prevH });
                  }
                  reject(new Error('canvas context unavailable'));
                  return;
                }
                if (theme === 'light') {
                  var pattern = createPaperTexture(ctx);
                  ctx.fillStyle = pattern || LIGHT_BG;
                  ctx.fillRect(0, 0, w, h);
                } else {
                  ctx.fillStyle = DARK_BG;
                  ctx.fillRect(0, 0, w, h);
                }
                ctx.drawImage(img, 0, 0, w, h);
                self.addBranding(ctx, config, w, h).then(function () {
                  if (chartEl && prevW != null && prevH != null) {
                    chart.applyOptions({ width: prevW, height: prevH });
                  }
                  self.triggerDownload(canvas, config.pair || self.deriveExportPair(), config.fileDate || config.asOfDate || '');
                  resolve();
                }).catch(function (err) {
                  if (chartEl && prevW != null && prevH != null) {
                    chart.applyOptions({ width: prevW, height: prevH });
                  }
                  reject(err);
                });
              }).catch(function (err) {
                if (chartEl && prevW != null && prevH != null) {
                  chart.applyOptions({ width: prevW, height: prevH });
                }
                reject(err);
              });
            }
            if (shot && typeof shot.then === 'function') {
              shot.then(finishWithCanvas).catch(function (err) {
                if (chartEl && prevW != null && prevH != null) {
                  chart.applyOptions({ width: prevW, height: prevH });
                }
                reject(err);
              });
            } else {
              finishWithCanvas(shot);
            }
          });
        });
      });
    },
  };

  var QuickCharts = {
    BUILT_IN_PRESETS: BUILT_IN_PRESETS,

    loadUserPresets: function () {
      try {
        var raw = global.localStorage.getItem(LS_QUICK);
        if (!raw) return [];
        var j = JSON.parse(raw);
        return Array.isArray(j) ? j : [];
      } catch (e) {
        if (global.console && global.console.error) {
          global.console.error('[ChartBuilder] Failed to parse fxrl_quickcharts:', e);
        }
        try {
          global.localStorage.removeItem(LS_QUICK);
        } catch (e2) { /* ignore */ }
        return [];
      }
    },

    saveUserPresets: function (arr) {
      try {
        global.localStorage.setItem(LS_QUICK, JSON.stringify(arr));
      } catch (e2) { /* ignore */ }
    },

    loadPreset: function (presetId) {
      var built = BUILT_IN_PRESETS.find(function (p) {
        return p.id === presetId;
      });
      var user = this.loadUserPresets().find(function (p) {
        return p.id === presetId;
      });
      var p = built || user;
      if (!p) return Promise.resolve();

      SeriesManager.clear();
      SeriesManager.setIndexedMode(!!p.indexed, null);

      if (user && !built) {
        var chainU = Promise.resolve();
        (p.series || []).forEach(function (sid) {
          chainU = chainU.then(function () {
            return SeriesManager.addSeries(sid);
          });
        });
        return chainU
          .then(function () {
            return patchUserPresetConfigs(user);
          })
          .then(function () {
            if (p.indexed) SeriesManager.setIndexedMode(true, null);
            if (typeof SeriesManager.onChange === 'function') SeriesManager.onChange();
          });
      }

      var chain = Promise.resolve();
      (p.series || []).forEach(function (sid) {
        chain = chain.then(function () {
          return SeriesManager.addSeries(sid).then(function () {
            var types = p.types || {};
            var typ = types[sid] || types.all || 'line';
            SeriesManager.setChartType(sid, typ);
            if (p.yAxis && p.yAxis[sid]) SeriesManager.setYAxis(sid, p.yAxis[sid]);
          });
        });
      });
      return chain.then(function () {
        if (p.indexed) SeriesManager.setIndexedMode(true, null);
        if (typeof SeriesManager.onChange === 'function') SeriesManager.onChange();
      });
    },

    saveCurrentAsPreset: function (name) {
      var snap = SeriesManager.snapshotForPreset();
      if (!snap.series.length) return null;
      var id = 'u_' + Date.now();
      var arr = this.loadUserPresets();
      arr.push({
        id: id,
        label: name,
        description: 'Saved quick chart',
        series: snap.series,
        types: {},
        yAxis: {},
        indexed: snap.indexedMode,
        configs: snap.configs,
      });
      this.saveUserPresets(arr);
      return id;
    },

    deleteUserPreset: function (id) {
      var arr = this.loadUserPresets().filter(function (p) {
        return p.id !== id;
      });
      this.saveUserPresets(arr);
    },
  };

  function patchUserPresetConfigs(preset) {
    var keys = Object.keys(preset.configs || {});
    return keys.reduce(function (chain, id) {
      return chain.then(function () {
        var c = preset.configs[id];
        if (SeriesManager.active.has(id)) {
          if (c.chartType) SeriesManager.setChartType(id, c.chartType);
          if (c.yAxis) SeriesManager.setYAxis(id, c.yAxis);
          if (c.colour) SeriesManager.setColour(id, c.colour);
          if (c.lineStyle) SeriesManager.setLineStyle(id, c.lineStyle);
        }
      });
    }, Promise.resolve());
  }

  function init(opts) {
    ThemeManager.init();
    var chart = null;
    var resizeObs = null;
    var chartEl = opts.chartEl;
    var rangeMs = opts.defaultRangeMs || 15552000000;
    var legendEl = opts.legendEl;
    var menuEl = opts.menuEl;
    var latestDateStr = '';

    function destroyChart() {
      var FX = global.FXRLCharts;
      if (FX && typeof FX.disposeChart === 'function') {
        FX.disposeChart('chart-builder-preview');
      }
      if (resizeObs) {
        try {
          resizeObs.disconnect();
        } catch (e) {}
        resizeObs = null;
      }
      if (chart && typeof chart.remove === 'function') {
        try {
          chart.remove();
        } catch (e2) {}
      }
      chart = null;
      try {
        global.__chartBuilderInstance = null;
      } catch (e3) { /* ignore */ }
    }

    function refreshLegend() {
      if (!legendEl) return;
      legendEl.innerHTML = '';
      SeriesManager.active.forEach(function (entry, id) {
        var row = document.createElement('div');
        row.className = 'cb-legend__item';
        row.setAttribute('data-series-id', id);
        var dot = document.createElement('span');
        dot.className = 'cb-legend__dot';
        dot.style.background = entry.colour;
        var lab = document.createElement('span');
        lab.className = 'cb-legend__label';
        lab.textContent = entry.meta.label;
        row.appendChild(dot);
        row.appendChild(lab);
        row.addEventListener('click', function (e) {
          e.stopPropagation();
          openContextMenu(id, e.pageX, e.pageY);
        });
        legendEl.appendChild(row);
      });
    }

    function openContextMenu(seriesId, x, y) {
      if (!menuEl) return;
      menuEl.innerHTML = '';
      menuEl.className = 'cb-ctx cb-ctx--open';
      menuEl.style.left = Math.min(x, global.innerWidth - 200) + 'px';
      menuEl.style.top = Math.min(y, global.innerHeight - 220) + 'px';

      function addSection(title) {
        var t = document.createElement('div');
        t.className = 'cb-ctx__title';
        t.textContent = title;
        menuEl.appendChild(t);
      }

      function addItem(label, fn) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'cb-ctx__item';
        b.textContent = label;
        b.addEventListener('click', function (ev) {
          ev.stopPropagation();
          fn();
          closeMenu();
        });
        menuEl.appendChild(b);
      }

      addSection('Chart type');
      ['line', 'area', 'bar', 'scatter'].forEach(function (t) {
        addItem(t.charAt(0).toUpperCase() + t.slice(1), function () {
          SeriesManager.setChartType(seriesId, t);
        });
      });
      addSection('Y-axis');
      addItem('Left', function () {
        SeriesManager.setYAxis(seriesId, 'left');
      });
      addItem('Right', function () {
        SeriesManager.setYAxis(seriesId, 'right');
      });
      addSection('Line style');
      addItem('Solid', function () {
        SeriesManager.setLineStyle(seriesId, 'solid');
      });
      addItem('Dashed', function () {
        SeriesManager.setLineStyle(seriesId, 'dashed');
      });
    }

    function closeMenu() {
      if (menuEl) {
        menuEl.className = 'cb-ctx';
        menuEl.innerHTML = '';
      }
    }

    global.document.addEventListener('click', closeMenu);

    function redraw() {
      redrawAsync().catch(function (err) {
        if (global.console && global.console.error) {
          global.console.error('[ChartBuilder] redraw', err);
        }
      });
    }

    /**
     * Single-series preview: fetch from Supabase, dispose/recreate via FXRLCharts helpers.
     * Multi-series and vol60 stay on buildChartBuilderLwc.
     */
    async function loadSeriesIntoChartPreview(seriesId, ref, rangeMs, themeName) {
      var FX = global.FXRLCharts;
      var DC = global.FXRLData;
      if (!FX || !DC || typeof DC.fetchSignalsFromSupabase !== 'function') return null;
      var entry = SeriesManager.active.get(seriesId);
      if (!entry) return null;
      var ready = await FX.waitForLWC();
      if (!ready) return null;

      var days = Math.min(1825, Math.max(365, Math.ceil(rangeMs / 86400000) + 5));
      var rows = await DC.fetchSignalsFromSupabase(ref.pair, days);
      if (!rows || !rows.length) return null;

      var col = ref.column;
      var cutoff = Date.now() - rangeMs;
      var data = [];
      for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        var v = r[col];
        if (v === null || v === undefined || v === '') continue;
        var ds = String(r.date || '').slice(0, 10);
        var t = ts(ds);
        if (!isFinite(t) || t < cutoff) continue;
        data.push({ date: ds, value: parseFloat(v) });
      }
      if (!data.length) return null;

      var cfg = DC.SIGNAL_CHART_MAP && DC.SIGNAL_CHART_MAP[col];
      var ut = (entry.chartType || 'line').toLowerCase();
      var chartKind;
      if (ut === 'bar') chartKind = 'histogram';
      else if (ut === 'area') chartKind = 'area';
      else chartKind = 'line';

      var color = entry.colour || (FX.pairColor ? FX.pairColor(ref.pair) : '#4D8EFF');
      var prec = cfg && cfg.precision != null ? cfg.precision : 2;
      var Th = ThemeManager.themes[themeName] || ThemeManager.themes.dark;
      var isLight = themeName === 'light';
      var themeOpts = {
        bg: isLight ? LIGHT_BG : DARK_BG,
        text: Th.text,
        grid: Th.grid,
        border: Th.axis,
      };

      var commonOpts = {
        color: color,
        precision: prec,
        theme: themeOpts,
        skipRangeButtons: true,
        dashed: ut === 'scatter',
      };

      FX.disposeChart('chart-builder-preview');
      chartEl.innerHTML = '';

      var instance = null;
      if (chartKind === 'histogram') {
        instance = await FX.histogram('chart-builder-preview', data, commonOpts);
      } else if (chartKind === 'area') {
        instance = await FX.area('chart-builder-preview', data, commonOpts);
      } else {
        instance = await FX.line('chart-builder-preview', data, commonOpts);
      }

      if (instance && instance.chart && typeof FX.applyTimeRangeMs === 'function') {
        FX.applyTimeRangeMs(instance.chart, rangeMs);
      }
      return instance;
    }

    async function redrawAsync() {
      destroyChart();
      if (!chartEl) return;
      chartEl.innerHTML = '';
      refreshLegend();

      if (!global.LightweightCharts) {
        if (typeof opts.onEmptyState === 'function') opts.onEmptyState(true);
        return;
      }

      var FX = global.FXRLCharts;

      if (!SeriesManager.hasDataSeries()) {
        if (typeof opts.onEmptyState === 'function') {
          opts.onEmptyState(true);
        }
        if (FX && typeof FX.showChartEmpty === 'function') {
          FX.showChartEmpty(chartEl, 'Select a data series to begin');
        }
        return;
      }

      if (typeof opts.onEmptyState === 'function') {
        opts.onEmptyState(false);
      }

      var singleId = null;
      SeriesManager.active.forEach(function (_, id) {
        singleId = id;
      });
      var metaOne = singleId ? SeriesManager.catalogMap[singleId] : null;
      var refOne = singleId ? resolvePairColumnForSeries(singleId) : null;
      if (SeriesManager.active.size === 1 && singleId && refOne && metaOne && metaOne.computed !== 'vol60_from_price') {
        var instSingle = await loadSeriesIntoChartPreview(singleId, refOne, rangeMs, ThemeManager.current);
        if (instSingle && instSingle.chart) {
          chart = instSingle.chart;
          global.__chartBuilderInstance = instSingle;
          resizeObs = new ResizeObserver(function () {
            if (!chart || !chartEl) return;
            try {
              chart.applyOptions({
                width: chartEl.clientWidth || 600,
                height: chartEl.clientHeight || 340,
              });
            } catch (e) {}
          });
          resizeObs.observe(chartEl);
          return;
        }
      }

      chart = buildChartBuilderLwc(chartEl, rangeMs, ThemeManager.current);
      if (!chart) {
        if (typeof opts.onEmptyState === 'function') {
          opts.onEmptyState(true);
        }
        return;
      }

      if (FX && typeof FX.register === 'function') {
        FX.register('chart-builder-preview', {
          chart: chart,
          disposeExtra: function () {},
        });
      }
      global.__chartBuilderInstance = { chart: chart };

      resizeObs = new ResizeObserver(function () {
        if (!chart || !chartEl) return;
        try {
          chart.applyOptions({
            width: chartEl.clientWidth || 600,
            height: chartEl.clientHeight || 340,
          });
        } catch (e) {}
      });
      resizeObs.observe(chartEl);
    }

    SeriesManager.onChange = function () {
      if (typeof opts.onSeriesChange === 'function') opts.onSeriesChange();
      redraw();
    };

    prefetchAllData()
      .then(function () {
        var spotPts = DATA.EURUSD && DATA.EURUSD.spot;
        if (spotPts && spotPts.length) {
          latestDateStr = new Date(spotPts[spotPts.length - 1][0]).toISOString().slice(0, 10);
          if (opts.tsEl) opts.tsEl.textContent = latestDateStr ? 'As of ' + latestDateStr + ' · data loaded' : 'Pipeline —';
        } else if (opts.tsEl) {
          opts.tsEl.textContent = 'Data pending — pipeline refresh';
        }
        if (typeof opts.onDataPrefetched === 'function') {
          opts.onDataPrefetched(deepClone(SERIES_AVAILABILITY));
        }
      })
      .catch(function () {
        if (opts.tsEl) opts.tsEl.textContent = 'Data pending — pipeline refresh';
      })
      .finally(function () {
        redraw();
      });

    redraw();

    var app = {
      chartEl: chartEl,
      setRange: function (ms) {
        rangeMs = ms;
        redraw();
      },
      getRange: function () {
        return rangeMs;
      },
      redraw: redraw,
      closeMenu: closeMenu,
      getLatestDate: function () {
        return latestDateStr;
      },
      getAvailability: function () {
        return deepClone(SERIES_AVAILABILITY);
      },
    };
    Object.defineProperty(app, 'chart', {
      configurable: true,
      enumerable: true,
      get: function () {
        return chart;
      },
    });
    return app;
  }

  global.FXRLChartBuilder = {
    DATA_CATALOG: DATA_CATALOG,
    SeriesManager: SeriesManager,
    ExportManager: ExportManager,
    QuickCharts: QuickCharts,
    ThemeManager: ThemeManager,
    prefetchAllData: prefetchAllData,
    updateSidebarAvailability: updateSidebarAvailability,
    createPaperTexture: createPaperTexture,
    getDataStore: function () {
      return {
        signals: deepClone(DATA),
        masterRows: 0,
        prefetched: PREFETCH_DONE,
      };
    },
    init: init,
  };
})(typeof window !== 'undefined' ? window : this);
