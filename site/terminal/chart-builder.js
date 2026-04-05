/**
 * FX Regime Lab — Terminal Chart Builder
 * Series catalog, composer, PNG export, Quick Charts, theme.
 */
(function (global) {
  'use strict';

  var MASTER_CSV = '/data/latest_with_cot.csv';
  var LS_QUICK = 'fxrl_quickcharts';
  var LS_THEME = 'fxrl_chartbuilder_theme';

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
          } else inQ = false;
        } else cur += c;
      } else {
        if (c === '"') inQ = true;
        else if (c === ',') {
          out.push(cur);
          cur = '';
        } else cur += c;
      }
    }
    out.push(cur);
    return out;
  }

  function parseCsv(text) {
    var lines = text.split(/\r?\n/).filter(function (l) {
      return l.trim().length;
    });
    if (!lines.length) return { headers: [], rows: [] };
    var headers = splitCsvLine(lines[0]).map(function (h, i) {
      var t = h.trim();
      if (!t && i === 0) return 'date';
      return t || 'col_' + i;
    });
    var rows = [];
    for (var r = 1; r < lines.length; r++) {
      var cells = splitCsvLine(lines[r]);
      var o = {};
      for (var c = 0; c < headers.length; c++) {
        o[headers[c]] = cells[c] != null ? cells[c].trim() : '';
      }
      rows.push(o);
    }
    return { headers: headers, rows: rows };
  }

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

  var DATA_CATALOG = {
    categories: [
      {
        id: 'fx_prices',
        label: 'FX PRICES',
        series: [
          { id: 'eurusd_price', label: 'EUR/USD', colour: '#4d8eff', csvColumn: 'EURUSD', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'usdjpy_price', label: 'USD/JPY', colour: '#d4890a', csvColumn: 'USDJPY', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'usdinr_price', label: 'USD/INR', colour: '#c94040', csvColumn: 'USDINR', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'dxy', label: 'DXY', colour: '#9ca3af', csvColumn: 'DXY', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
        ],
      },
      {
        id: 'commodities',
        label: 'COMMODITIES',
        series: [
          { id: 'gold', label: 'Gold', colour: '#e8b870', csvColumn: 'Gold', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'brent', label: 'Brent', colour: '#6b7280', csvColumn: 'Brent', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
        ],
      },
      {
        id: 'rate_spreads',
        label: 'RATE SPREADS',
        series: [
          { id: 'us_de_2y', label: 'US–DE 2Y spread', colour: '#4d8eff', csvColumn: 'US_DE_2Y_spread', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'us_de_10y', label: 'US–DE 10Y spread', colour: '#7aaaf0', csvColumn: 'US_DE_10Y_spread', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'us_jp_2y', label: 'US–JP 2Y spread', colour: '#d4890a', csvColumn: 'US_JP_2Y_spread', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'us_jp_10y', label: 'US–JP 10Y spread', colour: '#e8b870', csvColumn: 'US_JP_10Y_spread', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'us_in_10y', label: 'US–IN 10Y spread', colour: '#c94040', csvColumn: 'US_IN_10Y_spread', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'us_in_policy', label: 'US–IN policy spread', colour: '#e87878', csvColumn: 'US_IN_policy_spread', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'us_curve', label: 'US curve (10Y–2Y)', colour: '#7c6bcf', csvColumn: 'US_curve', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'btp_bund', label: 'BTP–Bund', colour: '#a78bfa', csvColumn: 'BTP_Bund_spread', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
        ],
      },
      {
        id: 'cot_eur',
        label: 'COT — EUR',
        series: [
          { id: 'eurusd_lev_money', label: 'EUR lev money net', colour: '#4d8eff', csvColumn: 'EUR_lev_net', csvFile: MASTER_CSV, defaultType: 'bar', yAxis: 'left' },
          { id: 'eurusd_asset_mgr', label: 'EUR asset mgr net', colour: '#6b7280', csvColumn: 'EUR_assetmgr_net', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'right' },
        ],
      },
      {
        id: 'cot_jpy',
        label: 'COT — JPY',
        series: [
          { id: 'jpy_lev_money', label: 'JPY lev money net', colour: '#d4890a', csvColumn: 'JPY_lev_net', csvFile: MASTER_CSV, defaultType: 'bar', yAxis: 'left' },
          { id: 'jpy_asset_mgr', label: 'JPY asset mgr net', colour: '#6b7280', csvColumn: 'JPY_assetmgr_net', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'right' },
        ],
      },
      {
        id: 'volatility',
        label: 'REALIZED VOL',
        series: [
          { id: 'eurusd_vol_30d', label: 'EUR/USD 30D vol', colour: '#4d8eff', csvColumn: 'EURUSD_vol30', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'eurusd_vol_60d', label: 'EUR/USD 60D vol (est.)', colour: '#7aaaf0', csvColumn: 'EURUSD', csvFile: MASTER_CSV, computed: 'vol60_from_price', defaultType: 'line', yAxis: 'left' },
          { id: 'usdjpy_vol_30d', label: 'USD/JPY 30D vol', colour: '#d4890a', csvColumn: 'USDJPY_vol30', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'usdinr_vol_30d', label: 'USD/INR 30D vol', colour: '#c94040', csvColumn: 'USDINR_vol30', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
        ],
      },
      {
        id: 'regime',
        label: 'REGIME / COMPOSITE',
        series: [
          { id: 'eurusd_composite', label: 'EUR/USD composite score', colour: '#4d8eff', csvColumn: 'eurusd_composite_score', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'usdjpy_composite', label: 'USD/JPY composite score', colour: '#d4890a', csvColumn: 'usdjpy_composite_score', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'usdinr_composite', label: 'USD/INR composite (INR score)', colour: '#c94040', csvColumn: 'inr_composite_score', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
        ],
      },
      {
        id: 'correlations',
        label: 'CORRELATIONS (60D)',
        series: [
          { id: 'dxy_eurusd_corr', label: 'DXY vs EUR/USD', colour: '#4d8eff', csvColumn: 'dxy_eurusd_corr_60d', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'dxy_usdjpy_corr', label: 'DXY vs USD/JPY', colour: '#d4890a', csvColumn: 'dxy_usdjpy_corr_60d', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'dxy_inr_corr', label: 'DXY vs USD/INR', colour: '#c94040', csvColumn: 'dxy_inr_corr_60d', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
          { id: 'gold_inr_corr', label: 'Gold vs USD/INR', colour: '#e8b870', csvColumn: 'gold_inr_corr_60d', csvFile: MASTER_CSV, defaultType: 'line', yAxis: 'left' },
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

  var csvTextCache = {};

  function fetchCsv(path) {
    if (csvTextCache[path]) return Promise.resolve(csvTextCache[path]);
    return fetch(path)
      .then(function (r) {
        if (!r.ok) throw new Error('CSV ' + path);
        return r.text();
      })
      .then(function (t) {
        csvTextCache[path] = t;
        return t;
      });
  }

  function loadSeriesPoints(meta, rows) {
    if (meta.computed === 'vol60_from_price') {
      var spot = rowsToSeries(rows, meta.csvColumn);
      return rollingVol60FromSpot(spot);
    }
    return rowsToSeries(rows, meta.csvColumn);
  }

  var ThemeManager = {
    current: 'dark',
    themes: {
      dark: {
        bg: '#0f1209',
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
        bg: '#ffffff',
        text: '#6b7280',
        textStrong: '#111827',
        axis: '#E2E4E8',
        grid: '#E2E4E8',
        splitLine: '#E2E4E8',
        tooltipBg: '#ffffff',
        tooltipBorder: '#E2E4E8',
        exportFooter: '#F9FAFB',
        exportUrl: '#374151',
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
      '" font-family="IBM Plex Sans,system-ui,sans-serif" font-size="13" font-weight="600">FX Regime Lab</text></svg>';
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
      var self = this;
      var meta = this.catalogMap[id];
      if (!meta || this.active.has(id)) return Promise.resolve();
      if (meta.available === false) return Promise.resolve();
      return fetchCsv(meta.csvFile)
        .then(function (text) {
          var parsed = parseCsv(text);
          var raw = loadSeriesPoints(meta, parsed.rows);
          self.active.set(id, {
            meta: meta,
            raw: raw,
            chartType: meta.defaultType || 'line',
            yAxis: meta.yAxis || 'left',
            lineStyle: 'solid',
            colour: meta.colour,
          });
          if (typeof self.onChange === 'function') self.onChange();
        })
        .catch(function () {
          if (typeof global.console !== 'undefined' && global.console.error) {
            global.console.error('Chart builder: could not load series', id);
          }
        });
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

  function chartBaseAnimation() {
    var b = global.TERMINAL_CHART_BASE;
    var o = {};
    if (b && typeof b === 'object') {
      if (b.animation != null) o.animation = b.animation;
      if (b.animationDuration != null) o.animationDuration = b.animationDuration;
      if (b.animationEasing != null) o.animationEasing = b.animationEasing;
    }
    return o;
  }

  var ChartComposer = {
    buildOption: function (rangeMs, themeName) {
      var T = ThemeManager.themes[themeName] || ThemeManager.themes.dark;
      var reduceMotion =
        typeof global.matchMedia === 'function' &&
        global.matchMedia('(prefers-reduced-motion: reduce)').matches;
      var hasRight = false;
      SeriesManager.active.forEach(function (e) {
        if (e.yAxis === 'right') hasRight = true;
      });

      var yAxis = [
        {
          type: 'value',
          scale: true,
          position: 'left',
          axisLine: { lineStyle: { color: T.axis } },
          axisLabel: { color: T.text, fontSize: 10 },
          splitLine: { lineStyle: { color: T.splitLine } },
        },
      ];
      if (hasRight) {
        yAxis.push({
          type: 'value',
          scale: true,
          position: 'right',
          axisLine: { lineStyle: { color: T.axis } },
          axisLabel: { color: T.text, fontSize: 10 },
          splitLine: { show: false },
        });
      }

      var series = [];
      var si = 0;
      SeriesManager.active.forEach(function (entry, id) {
        var data = SeriesManager._prepareDisplay(entry, rangeMs);
        var yi = entry.yAxis === 'right' && hasRight ? 1 : 0;
        var c = entry.colour || entry.meta.colour;
        var dash = entry.lineStyle === 'dashed' ? [6, 4] : 'solid';
        var name = entry.meta.label;
        var t = entry.chartType;

        if (t === 'scatter') {
          series.push({
            type: 'scatter',
            name: name,
            yAxisIndex: yi,
            data: data,
            symbolSize: 6,
            itemStyle: { color: c },
            emphasis: { focus: 'series' },
          });
        } else if (t === 'bar') {
          series.push({
            type: 'bar',
            name: name,
            yAxisIndex: yi,
            data: data,
            barMaxWidth: 14,
            itemStyle: { color: c },
            emphasis: { focus: 'series' },
          });
        } else if (t === 'area') {
          series.push({
            type: 'line',
            name: name,
            yAxisIndex: yi,
            data: data,
            smooth: 0.35,
            showSymbol: false,
            lineStyle: { width: 1.5, color: c, type: dash },
            areaStyle: { color: c, opacity: 0.12 },
            emphasis: { focus: 'series' },
          });
        } else {
          series.push({
            type: 'line',
            name: name,
            yAxisIndex: yi,
            data: data,
            smooth: 0.35,
            showSymbol: false,
            lineStyle: { width: 1.5, color: c, type: dash },
            emphasis: { focus: 'series' },
          });
        }
        si++;
      });

      return Object.assign(
        {
          backgroundColor: T.bg,
          animation: !reduceMotion,
          animationDuration: reduceMotion ? 0 : 400,
          animationEasing: 'cubicOut',
        },
        chartBaseAnimation(),
        {
          textStyle: {
            fontFamily: '"JetBrains Mono", ui-monospace, monospace',
            fontSize: 11,
            color: T.text,
          },
          tooltip: {
            trigger: 'axis',
            backgroundColor: T.tooltipBg,
            borderColor: T.tooltipBorder,
            borderWidth: 1,
            textStyle: { color: T.textStrong, fontSize: 11 },
          },
          legend: { show: false },
          grid: { left: 56, right: hasRight ? 56 : 24, top: 40, bottom: 48, containLabel: true },
          xAxis: {
            type: 'time',
            axisLine: { lineStyle: { color: T.axis } },
            axisLabel: { color: T.text, fontSize: 10 },
            splitLine: { show: false },
          },
          yAxis: yAxis,
          series: series,
        }
      );
    },
  };

  var ExportManager = {
    exportPNG: function (chart, config) {
      var theme = config.theme === 'light' ? 'light' : 'dark';
      var T = ThemeManager.themes[theme];
      var w = config.width || 1200;
      var h = config.height || 627;
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
      var footerH = 56;
      var chartAreaH = h - footerH;

      var prevBg = chart.getOption().backgroundColor;
      chart.setOption({ backgroundColor: T.bg }, false);
      var url = chart.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: T.bg,
      });
      chart.setOption({ backgroundColor: prevBg }, false);

      var img = new global.Image();
      var self = this;
      return new Promise(function (resolve, reject) {
        img.onerror = reject;
        img.onload = function () {
          try {
            var canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            var ctx = canvas.getContext('2d');
            ctx.fillStyle = T.bg;
            ctx.fillRect(0, 0, w, chartAreaH);
            ctx.drawImage(img, 0, 0, img.width, img.height, 0, 0, w, chartAreaH);

            ctx.fillStyle = T.exportFooter;
            ctx.fillRect(0, chartAreaH, w, footerH);

            var urlFill = T.exportUrl;
            ctx.fillStyle = urlFill;
            ctx.font = '11px "IBM Plex Sans", system-ui, sans-serif';
            ctx.textBaseline = 'middle';
            ctx.fillText('fxregimelab.com', 16, chartAreaH + footerH / 2 - 6);

            var wm = new global.Image();
            wm.onload = function () {
              var wmW = Math.min(180, w * 0.35);
              var wmH = (wm.height / wm.width) * wmW;
              ctx.drawImage(wm, w - wmW - 16, chartAreaH + 8, wmW, wmH);

              if (config.title) {
                ctx.fillStyle = T.textStrong;
                ctx.font = '600 11px "IBM Plex Sans", system-ui, sans-serif';
                ctx.textAlign = 'right';
                ctx.fillText(config.title, w - 16, chartAreaH + 8 + wmH + 12);
                ctx.textAlign = 'left';
              }
              if (config.subtitle) {
                ctx.fillStyle = T.text;
                ctx.font = '10px "IBM Plex Sans", system-ui, sans-serif';
                ctx.textAlign = 'right';
                ctx.fillText(config.subtitle, w - 16, chartAreaH + 8 + wmH + 26);
                ctx.textAlign = 'left';
              }

              if (config.showTimestamp && config.asOfDate) {
                ctx.fillStyle = T.text;
                ctx.font = '10px "IBM Plex Sans", system-ui, sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('Data as of ' + config.asOfDate, w / 2, chartAreaH + footerH - 10);
                ctx.textAlign = 'left';
              }

              canvas.toBlob(function (blob) {
                if (!blob) {
                  reject(new Error('toBlob'));
                  return;
                }
                var a = document.createElement('a');
                var fname = 'fxregimelab_' + (config.fileDate || 'chart') + '.png';
                a.href = URL.createObjectURL(blob);
                a.download = fname;
                a.click();
                URL.revokeObjectURL(a.href);
                resolve();
              });
            };
            wm.onerror = function () {
              ctx.fillStyle = T.textStrong;
              ctx.font = '600 12px "IBM Plex Sans", system-ui, sans-serif';
              ctx.textAlign = 'right';
              ctx.fillText('FX REGIME LAB', w - 16, chartAreaH + 22);
              ctx.textAlign = 'left';
              canvas.toBlob(function (blob) {
                if (!blob) {
                  reject(new Error('toBlob'));
                  return;
                }
                var a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = 'fxregimelab_' + (config.fileDate || 'chart') + '.png';
                a.click();
                URL.revokeObjectURL(a.href);
                resolve();
              });
            };
            wm.src = makeWordmarkSvgDataUri(theme);
          } catch (err) {
            reject(err);
          }
        };
        img.src = url;
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
    var chart = global.echarts.init(opts.chartEl, null, { renderer: 'canvas' });
    var rangeMs = opts.defaultRangeMs || 15552000000;
    var legendEl = opts.legendEl;
    var menuEl = opts.menuEl;
    var latestDateStr = '';

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
      var opt = ChartComposer.buildOption(rangeMs, ThemeManager.current);
      chart.setOption(opt, true);
      refreshLegend();
    }

    SeriesManager.onChange = function () {
      if (typeof opts.onSeriesChange === 'function') opts.onSeriesChange();
      redraw();
    };

    fetchCsv(MASTER_CSV)
      .then(function (text) {
        var p = parseCsv(text);
        if (p.rows.length) {
          latestDateStr = p.rows[p.rows.length - 1].date || '';
          if (opts.tsEl) opts.tsEl.textContent = latestDateStr ? 'As of ' + latestDateStr + ' · CSV' : 'Pipeline —';
        }
      })
      .catch(function () {
        if (opts.tsEl) opts.tsEl.textContent = 'No CSV — run pipeline locally';
      });

    redraw();

    return {
      chart: chart,
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
    };
  }

  global.FXRLChartBuilder = {
    DATA_CATALOG: DATA_CATALOG,
    SeriesManager: SeriesManager,
    ChartComposer: ChartComposer,
    ExportManager: ExportManager,
    QuickCharts: QuickCharts,
    ThemeManager: ThemeManager,
    init: init,
  };
})(typeof window !== 'undefined' ? window : this);
