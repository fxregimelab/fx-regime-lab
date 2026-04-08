/* ═══════════════════════════════════════════
   FX Regime Lab — Lightweight Charts Config
   Single source of truth for all terminal charts
   Chart.js must NEVER be imported on terminal pages
═══════════════════════════════════════════ */

(function (global) {
  'use strict';

  var LWC = null;

  function getLWC() {
    return global.LightweightCharts || LWC;
  }

  /* ── Design tokens ─────────────────────── */
  var T = {
    bg: '#111827',
    bgPage: '#080c14',
    grid: 'rgba(255,255,255,0.04)',
    border: 'rgba(255,255,255,0.08)',
    text: '#8B9BB4',
    textPrimary: '#E8EDF2',
    crosshair: 'rgba(255,255,255,0.15)',
    eurusd: '#4D8EFF',
    usdjpy: '#F59E0B',
    usdinr: '#F87171',
    bullish: '#2DD4A0',
    bearish: '#F87171',
    neutral: '#8B9BB4',
    anomaly: '#F59E0B',
    bullishBg: 'rgba(45,212,160,0.06)',
    bearishBg: 'rgba(248,113,113,0.06)',
    neutralBg: 'rgba(139,155,180,0.04)',
  };

  function hexToRgba(hex, alpha) {
    if (!hex || typeof hex !== 'string') return 'rgba(77,142,255,' + alpha + ')';
    var h = hex.replace('#', '');
    if (h.length === 3) {
      h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    }
    var n = parseInt(h, 16);
    if (!isFinite(n)) return 'rgba(77,142,255,' + alpha + ')';
    var r = (n >> 16) & 255;
    var g = (n >> 8) & 255;
    var b = n & 255;
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }

  function msToSec(ms) {
    return Math.floor(ms / 1000);
  }

  /**
   * @param {Array<[number,number]>|Array<{time:number,value:number}>} data
   * @returns {{time:number,value:number}[]}
   */
  function normalizeSeriesData(data) {
    if (!data || !data.length) return [];
    var out = [];
    for (var i = 0; i < data.length; i++) {
      var d = data[i];
      var t;
      var v;
      if (Array.isArray(d)) {
        t = msToSec(d[0]);
        v = parseFloat(d[1]);
      } else if (d && d.time != null && d.value != null) {
        t = typeof d.time === 'number' && d.time > 1e12 ? msToSec(d.time) : d.time;
        v = parseFloat(d.value);
      } else if (d && d.date != null) {
        var dt = d.date;
        if (typeof dt === 'number' && dt > 1e12) t = msToSec(dt);
        else if (typeof dt === 'number') t = dt;
        else t = msToSec(new Date(String(dt) + 'T12:00:00Z').getTime());
        v = parseFloat(d.value);
      } else continue;
      if (!isFinite(t) || v == null || !isFinite(v)) continue;
      out.push({ time: t, value: v });
    }
    out.sort(function (a, b) {
      return a.time - b.time;
    });
    return out;
  }

  function ensureContainerId(container) {
    if (!container) return '';
    if (!container.id) {
      container.id = 'fxrl-lwc-' + Math.random().toString(36).slice(2, 11);
    }
    return container.id;
  }

  /* ── Wait for LWC to load ───────────────── */
  function waitForLWC(timeout) {
    var ms = timeout != null ? timeout : 8000;
    if (global.__lwcReady && global.LightweightCharts) {
      LWC = global.LightweightCharts;
      return Promise.resolve(true);
    }
    return new Promise(function (resolve) {
      var t = setTimeout(function () {
        resolve(false);
      }, ms);
      document.addEventListener(
        'lwc-ready',
        function () {
          clearTimeout(t);
          LWC = global.LightweightCharts;
          resolve(true);
        },
        { once: true }
      );
    });
  }

  /* ── Base chart options ─────────────────── */
  function baseChartOptions(container, themeOpts) {
    var rect = container.getBoundingClientRect();
    var w = rect.width || container.offsetWidth || 600;
    var h = container.offsetHeight > 40 ? container.offsetHeight : 260;
    var th = themeOpts || {};
    var bg = th.bg != null ? th.bg : T.bg;
    var txt = th.text != null ? th.text : T.text;
    var gridC = th.grid != null ? th.grid : T.grid;
    var borderC = th.border != null ? th.border : T.border;
    return {
      width: w,
      height: h,
      watermark: {
        visible: false,
      },
      layout: {
        background: { color: bg },
        textColor: txt,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: gridC },
        horzLines: { color: gridC },
      },
      crosshair: {
        mode: th.crosshairMode != null ? th.crosshairMode : 1,
        vertLine: {
          color: T.crosshair,
          labelBackgroundColor: '#1e293b',
        },
        horzLine: {
          color: T.crosshair,
          labelBackgroundColor: '#1e293b',
        },
      },
      rightPriceScale: {
        borderColor: borderC,
        textColor: txt,
        scaleMargins: { top: 0.08, bottom: 0.12 },
      },
      leftPriceScale: {
        visible: false,
      },
      timeScale: {
        borderColor: borderC,
        textColor: txt,
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: true,
        fixRightEdge: true,
      },
      handleScroll: th.handleScroll !== false,
      handleScale: th.handleScale !== false,
    };
  }

  /* ── Time range helper ──────────────────── */
  function applyTimeRange(chart, range) {
    if (!chart || !chart.timeScale) return;
    var now = Math.floor(Date.now() / 1000);
    var ranges = {
      '1M': 30 * 86400,
      '3M': 90 * 86400,
      '6M': 180 * 86400,
      '1Y': 365 * 86400,
      All: null,
    };
    var seconds = ranges[range];
    if (!seconds) {
      chart.timeScale().fitContent();
      return;
    }
    chart.timeScale().setVisibleRange({
      from: now - seconds,
      to: now,
    });
  }

  function applyTimeRangeMs(chart, rangeMs) {
    if (!chart || !chart.timeScale || !rangeMs) return;
    var now = Math.floor(Date.now() / 1000);
    var from = now - Math.floor(rangeMs / 1000);
    try {
      chart.timeScale().setVisibleRange({ from: from, to: now });
    } catch (e) {
      /* LWC v5 throws if chart has no series or scale not ready */
    }
  }

  /* ── Time range buttons UI ──────────────── */
  function renderTimeRangeButtons(container, chart) {
    if (container.querySelector('.fxrl-range-bar')) return;
    var ranges = ['1M', '3M', '6M', '1Y', 'All'];
    var bar = document.createElement('div');
    bar.className = 'fxrl-range-bar';
    bar.style.cssText =
      'display:flex;gap:4px;padding:8px 12px 0;font-family:\'JetBrains Mono\',monospace;';
    ranges.forEach(function (r, i) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = r;
      btn.dataset.range = r;
      btn.style.cssText =
        'background:transparent;border:1px solid rgba(255,255,255,0.10);color:#8B9BB4;font-size:10px;font-family:inherit;padding:3px 8px;border-radius:3px;cursor:pointer;transition:all 0.15s;';
      btn.addEventListener('click', function () {
        bar.querySelectorAll('button').forEach(function (b) {
          b.classList.remove('active');
          b.style.color = '#8B9BB4';
          b.style.borderColor = 'rgba(255,255,255,0.10)';
        });
        btn.classList.add('active');
        btn.style.color = '#E8EDF2';
        btn.style.borderColor = '#4D8EFF';
        applyTimeRange(chart, r);
      });
      if (i === 1) {
        setTimeout(function () {
          btn.click();
        }, 0);
      }
      bar.appendChild(btn);
    });
    container.insertBefore(bar, container.firstChild);
  }

  /* ── EMPTY / ERROR ──────────────────────── */
  function showChartEmpty(container, msg) {
    container.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:center;height:100%;min-height:120px;color:#4A5568;font-family:\'JetBrains Mono\',monospace;font-size:11px;background:#111827;border-radius:4px;">' +
      (msg || 'Signal data not yet available') +
      '</div>';
  }

  function showChartError(container, msg) {
    container.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:center;height:100%;min-height:120px;color:#F87171;font-family:\'JetBrains Mono\',monospace;font-size:11px;background:#111827;border-radius:4px;">' +
      (msg || 'Chart failed to load') +
      '</div>';
  }

  function pairColor(pair) {
    var p = String(pair || '')
      .replace('/', '')
      .toUpperCase();
    if (p === 'EURUSD') return T.eurusd;
    if (p === 'USDJPY') return T.usdjpy;
    if (p === 'USDINR') return T.usdinr;
    return T.eurusd;
  }

  var registry = new Map();

  function register(id, instance) {
    if (registry.has(id)) {
      try {
        var prev = registry.get(id);
        if (prev && prev.chart && typeof prev.chart.remove === 'function') prev.chart.remove();
      } catch (e) {}
    }
    registry.set(id, instance);
  }

  function disposeChart(id) {
    if (!registry.has(id)) return;
    try {
      var inst = registry.get(id);
      if (inst && inst.chart && typeof inst.chart.remove === 'function') inst.chart.remove();
      if (inst && typeof inst.disposeExtra === 'function') inst.disposeExtra();
    } catch (e2) {}
    registry.delete(id);
  }

  function disposeAll() {
    registry.forEach(function (instance) {
      try {
        if (instance && instance.chart && typeof instance.chart.remove === 'function') {
          instance.chart.remove();
        }
        if (instance && typeof instance.disposeExtra === 'function') instance.disposeExtra();
      } catch (e) {}
    });
    registry.clear();
  }

  function attachResize(container, chart) {
    var ro = new ResizeObserver(function () {
      try {
        var ch = container.offsetHeight > 40 ? container.offsetHeight : 260;
        chart.applyOptions({ width: container.offsetWidth || 600, height: ch });
      } catch (e) {}
    });
    ro.observe(container);
    return ro;
  }

  /* ── LINE CHART ─────────────────────────── */
  function createLineChart(containerId, data, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      var container =
        typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
      if (!container) {
        console.warn('FXRLCharts: container not found:', containerId);
        return null;
      }
      var cid = ensureContainerId(container);
      if (!ready || !global.LightweightCharts) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      var formatted = normalizeSeriesData(data);
      if (!formatted.length) {
        showChartEmpty(container, opts.emptyMessage);
        return null;
      }
      var LW = global.LightweightCharts;
      container.innerHTML = '';
      var chart = LW.createChart(container, baseChartOptions(container, opts.theme));
      var color = opts.color || T.eurusd;
      var series = chart.addSeries(LW.LineSeries, {
        color: color,
        lineWidth: opts.lineWidth != null ? opts.lineWidth : 2,
        priceLineVisible: false,
        lastValueVisible: opts.lastValueVisible !== false,
        lineStyle: opts.dashed ? 2 : 0,
        priceFormat: opts.priceFormat || {
          type: 'price',
          precision: opts.precision != null ? opts.precision : 4,
          minMove: opts.minMove != null ? opts.minMove : 0.0001,
        },
      });
      series.setData(formatted);
      if (!opts.skipRangeButtons) renderTimeRangeButtons(container, chart);
      var ro = attachResize(container, chart);
      var inst = {
        chart: chart,
        series: series,
        setRange: function (r) {
          applyTimeRange(chart, r);
        },
        setRangeMs: function (ms) {
          applyTimeRangeMs(chart, ms);
        },
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (e) {}
        },
        hasData: true,
      };
      register(cid, inst);
      return inst;
    });
  }

  /* ── AREA CHART ─────────────────────────── */
  function createAreaChart(containerId, data, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      var container =
        typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
      if (!container) {
        console.warn('FXRLCharts: container not found:', containerId);
        return null;
      }
      var cid = ensureContainerId(container);
      if (!ready || !global.LightweightCharts) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      var formatted = normalizeSeriesData(data);
      if (!formatted.length) {
        showChartEmpty(container, opts.emptyMessage);
        return null;
      }
      var LW = global.LightweightCharts;
      container.innerHTML = '';
      var chart = LW.createChart(container, baseChartOptions(container, opts.theme));
      var color = opts.color || T.eurusd;
      var series = chart.addSeries(LW.AreaSeries, {
        lineColor: color,
        topColor: hexToRgba(color, 0.2),
        bottomColor: hexToRgba(color, 0),
        lineWidth: opts.lineWidth != null ? opts.lineWidth : 2,
        priceLineVisible: false,
        lastValueVisible: opts.lastValueVisible !== false,
        priceFormat: opts.priceFormat || {
          type: 'price',
          precision: opts.precision != null ? opts.precision : 4,
          minMove: opts.minMove != null ? opts.minMove : 0.0001,
        },
      });
      series.setData(formatted);
      if (!opts.skipRangeButtons) renderTimeRangeButtons(container, chart);
      var ro = attachResize(container, chart);
      var inst = {
        chart: chart,
        series: series,
        setRange: function (r) {
          applyTimeRange(chart, r);
        },
        setRangeMs: function (ms) {
          applyTimeRangeMs(chart, ms);
        },
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (e) {}
        },
        hasData: true,
      };
      register(cid, inst);
      return inst;
    });
  }

  /* ── HISTOGRAM CHART ────────────────────── */
  function createHistogramChart(containerId, data, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      var container =
        typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
      if (!container) {
        console.warn('FXRLCharts: container not found:', containerId);
        return null;
      }
      var cid = ensureContainerId(container);
      if (!ready || !global.LightweightCharts) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      var formatted = normalizeSeriesData(data);
      if (!formatted.length) {
        showChartEmpty(container, opts.emptyMessage);
        return null;
      }
      var LW = global.LightweightCharts;
      container.innerHTML = '';
      var chart = LW.createChart(container, baseChartOptions(container, opts.theme));
      var defC = opts.color || T.eurusd;
      var series = chart.addSeries(LW.HistogramSeries, {
        color: defC,
        priceFormat: opts.priceFormat || { type: 'volume' },
        priceLineVisible: false,
        lastValueVisible: true,
      });
      var histData = formatted.map(function (p) {
        var val = p.value;
        return {
          time: p.time,
          value: val,
          color: val >= 0 ? T.bullish : T.bearish,
        };
      });
      series.setData(histData);
      if (!opts.skipRangeButtons) renderTimeRangeButtons(container, chart);
      var ro = attachResize(container, chart);
      var inst = {
        chart: chart,
        series: series,
        setRange: function (r) {
          applyTimeRange(chart, r);
        },
        setRangeMs: function (ms) {
          applyTimeRangeMs(chart, ms);
        },
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (e) {}
        },
        hasData: true,
      };
      register(cid, inst);
      return inst;
    });
  }

  /**
   * Multi line series on one chart (shared time).
   * @param {HTMLElement} container
   * @param {{ data:array, color:string, lineWidth?:number, dashed?:boolean, priceScaleId?:string, precision?:number }[]} seriesList
   */
  function createMultiLineChart(container, seriesList, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      if (!container) return null;
      ensureContainerId(container);
      if (!ready || !global.LightweightCharts) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      container.innerHTML = '';
      var LW = global.LightweightCharts;
      var chart = LW.createChart(container, baseChartOptions(container, opts.theme));
      var seriesRefs = [];
      var hasRight = false;
      for (var i = 0; i < seriesList.length; i++) {
        var spec = seriesList[i];
        var pts = normalizeSeriesData(spec.data);
        if (!pts.length) continue;
        var psId = spec.priceScaleId || 'left';
        if (psId === 'right') hasRight = true;
        var lineOpts = {
          color: spec.color || T.eurusd,
          lineWidth: spec.lineWidth != null ? spec.lineWidth : 1.5,
          priceLineVisible: false,
          lastValueVisible: true,
          lineStyle: spec.dashed ? 2 : 0,
          priceScaleId: psId,
          priceFormat: {
            type: 'price',
            precision: spec.precision != null ? spec.precision : 4,
            minMove: spec.minMove != null ? spec.minMove : 0.0001,
          },
        };
        var s = chart.addSeries(LW.LineSeries, lineOpts);
        s.setData(pts);
        seriesRefs.push(s);
      }
      chart.priceScale('right').applyOptions({
        visible: hasRight,
        borderColor: T.border,
        textColor: T.text,
      });
      chart.priceScale('left').applyOptions({
        visible: true,
        borderColor: T.border,
        textColor: T.text,
      });
      if (!opts.skipRangeButtons) renderTimeRangeButtons(container, chart);
      var ro = attachResize(container, chart);
      return {
        chart: chart,
        series: seriesRefs,
        setRangeMs: function (ms) {
          applyTimeRangeMs(chart, ms);
        },
        hasData: seriesRefs.length > 0,
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (e) {}
        },
      };
    });
  }

  /**
   * Two stacked charts (e.g. vol + corr), sync visible time range.
   */
  function createDualPaneCharts(container, topSpec, bottomSpec, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      if (!container) return null;
      if (!ready || !global.LightweightCharts) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      function paneHasAnySeries(specs) {
        for (var i = 0; i < (specs || []).length; i++) {
          var sp = specs[i];
          if (!sp) continue;
          if (normalizeSeriesData(sp.data).length) return true;
        }
        return false;
      }
      var willHaveTop = paneHasAnySeries(topSpec);
      var willHaveBot = paneHasAnySeries(bottomSpec);
      if (!willHaveTop && !willHaveBot) {
        showChartEmpty(container, opts.emptyMessage);
        return null;
      }
      container.innerHTML = '';
      var wrap = document.createElement('div');
      wrap.style.display = 'flex';
      wrap.style.flexDirection = 'column';
      wrap.style.height = '100%';
      wrap.style.minHeight = '220px';
      var topEl = document.createElement('div');
      topEl.style.flex = '1';
      topEl.style.minHeight = '100px';
      var botEl = document.createElement('div');
      botEl.style.flex = '1';
      botEl.style.minHeight = '80px';
      wrap.appendChild(topEl);
      wrap.appendChild(botEl);
      container.appendChild(wrap);

      var LW = global.LightweightCharts;
      var chartTop = LW.createChart(topEl, baseChartOptions(topEl, opts.theme));
      var chartBot = LW.createChart(botEl, baseChartOptions(botEl, opts.theme));

      function syncCharts(a, b) {
        a.timeScale().subscribeVisibleLogicalRangeChange(function (range) {
          if (range === null) return;
          try {
            b.timeScale().setVisibleLogicalRange(range);
          } catch (e) {}
        });
      }

      var topSeries = [];
      var botSeries = [];
      topSpec.forEach(function (spec) {
        var pts = normalizeSeriesData(spec.data);
        if (!pts.length) return;
        var s = spec.area
          ? chartTop.addSeries(LW.AreaSeries, {
              lineColor: spec.color,
              topColor: hexToRgba(spec.color, 0.15),
              bottomColor: hexToRgba(spec.color, 0),
              lineWidth: spec.lineWidth || 1.5,
              priceLineVisible: false,
            })
          : chartTop.addSeries(LW.LineSeries, {
              color: spec.color,
              lineWidth: spec.lineWidth || 1.5,
              lineStyle: spec.dashed ? 2 : 0,
              priceLineVisible: false,
            });
        s.setData(pts);
        topSeries.push(s);
      });
      bottomSpec.forEach(function (spec) {
        var pts = normalizeSeriesData(spec.data);
        if (!pts.length) return;
        var s = chartBot.addSeries(LW.LineSeries, {
          color: spec.color || T.neutral,
          lineWidth: spec.lineWidth || 1.2,
          priceLineVisible: false,
        });
        s.setData(pts);
        if (spec.zeroLine) {
          try {
            s.createPriceLine({ price: 0, color: T.border, lineWidth: 1, lineStyle: 2 });
          } catch (e) {}
        }
        botSeries.push(s);
      });

      syncCharts(chartTop, chartBot);
      syncCharts(chartBot, chartTop);

      var ro = new ResizeObserver(function () {
        var w = container.offsetWidth || 600;
        try {
          chartTop.applyOptions({ width: w, height: topEl.clientHeight || 120 });
          chartBot.applyOptions({ width: w, height: botEl.clientHeight || 100 });
        } catch (e) {}
      });
      ro.observe(container);

      return {
        chart: chartTop,
        chartTop: chartTop,
        chartBottom: chartBot,
        setRangeMs: function (ms) {
          if (topSeries.length) applyTimeRangeMs(chartTop, ms);
          if (botSeries.length) applyTimeRangeMs(chartBot, ms);
        },
        hasData: topSeries.length > 0 || botSeries.length > 0,
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (e) {}
          try {
            chartTop.remove();
          } catch (e2) {}
          try {
            chartBot.remove();
          } catch (e3) {}
        },
      };
    });
  }

  /**
   * COT: histogram (lev net) + line (asset mgr) on right scale; optional constant percentile line.
   */
  function createCotCompositeChart(container, spec, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      if (!container) return null;
      if (!ready || !global.LightweightCharts) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      var LW = global.LightweightCharts;
      container.innerHTML = '';
      var chart = LW.createChart(container, baseChartOptions(container, opts.theme));
      var levPts = spec.levHistogram || [];
      var assetPts = normalizeSeriesData(spec.assetLine || []);
      if (!levPts.length && !assetPts.length) {
        showChartEmpty(container, opts.emptyMessage);
        return null;
      }
      var hist = chart.addSeries(LW.HistogramSeries, {
        priceScaleId: 'left',
        priceFormat: { type: 'volume' },
        priceLineVisible: false,
      });
      hist.setData(levPts);
      var line = chart.addSeries(LW.LineSeries, {
        color: spec.assetColor || '#6b7280',
        lineWidth: 1.5,
        priceScaleId: 'right',
        priceLineVisible: false,
        priceFormat: { type: 'price', precision: 0, minMove: 1 },
      });
      if (assetPts.length) line.setData(assetPts);
      if (isFinite(spec.th80)) {
        try {
          hist.createPriceLine({
            price: spec.th80,
            color: T.anomaly,
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: '80th',
          });
        } catch (e) {}
      }
      if (isFinite(spec.th20)) {
        try {
          hist.createPriceLine({
            price: spec.th20,
            color: T.anomaly,
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: '20th',
          });
        } catch (e) {}
      }
      chart.priceScale('left').applyOptions({ visible: true });
      chart.priceScale('right').applyOptions({ visible: assetPts.length > 0 });
      var ro = attachResize(container, chart);
      return {
        chart: chart,
        setRangeMs: function (ms) {
          applyTimeRangeMs(chart, ms);
        },
        hasData: true,
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (e) {}
        },
      };
    });
  }

  /**
   * Momentum: top = histogram (daily %) + line (5d mom, right scale); bottom = spot line.
   */
  function createMomentumDualPane(container, spec, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      if (!container) return null;
      if (!ready || !global.LightweightCharts) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      container.innerHTML = '';
      var wrap = document.createElement('div');
      wrap.style.cssText = 'display:flex;flex-direction:column;height:100%;min-height:240px;';
      var topEl = document.createElement('div');
      topEl.style.cssText = 'flex:1.2;min-height:120px;position:relative;';
      var botEl = document.createElement('div');
      botEl.style.cssText = 'flex:1;min-height:90px;';
      wrap.appendChild(topEl);
      wrap.appendChild(botEl);
      container.appendChild(wrap);
      var LW = global.LightweightCharts;
      var chartTop = LW.createChart(topEl, baseChartOptions(topEl, opts.theme));
      var chartBot = LW.createChart(botEl, baseChartOptions(botEl, opts.theme));
      var retBars = spec.dailyHist || [];
      var momLn = normalizeSeriesData(spec.momoLine || []);
      var spotLn = normalizeSeriesData(spec.spotLine || []);
      var topHas = retBars.length > 0 || momLn.length > 0;
      var botHas = spotLn.length > 0;
      if (retBars.length) {
        var h = chartTop.addSeries(LW.HistogramSeries, {
          priceScaleId: 'left',
          priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
        });
        h.setData(retBars);
        try {
          h.createPriceLine({ price: 0, color: T.border, lineWidth: 1, lineStyle: 2 });
        } catch (e) {}
      }
      if (momLn.length) {
        var m = chartTop.addSeries(LW.LineSeries, {
          color: spec.momColor || T.eurusd,
          lineWidth: 1.2,
          priceScaleId: 'right',
          priceLineVisible: false,
        });
        m.setData(momLn);
      }
      chartTop.priceScale('right').applyOptions({ visible: momLn.length > 0 });
      if (spotLn.length) {
        var sp = chartBot.addSeries(LW.LineSeries, {
          color: spec.spotColor || T.textPrimary,
          lineWidth: 1.2,
          priceLineVisible: false,
        });
        sp.setData(spotLn);
      }
      function syncCharts(a, b) {
        a.timeScale().subscribeVisibleLogicalRangeChange(function (range) {
          if (range === null) return;
          try {
            b.timeScale().setVisibleLogicalRange(range);
          } catch (e) {}
        });
      }
      syncCharts(chartTop, chartBot);
      syncCharts(chartBot, chartTop);
      var ro = new ResizeObserver(function () {
        var w = container.offsetWidth || 600;
        try {
          chartTop.applyOptions({ width: w, height: topEl.clientHeight || 140 });
          chartBot.applyOptions({ width: w, height: botEl.clientHeight || 100 });
        } catch (e) {}
      });
      ro.observe(container);
      return {
        chart: chartTop,
        chartTop: chartTop,
        chartBottom: chartBot,
        setRangeMs: function (ms) {
          if (topHas) applyTimeRangeMs(chartTop, ms);
          if (botHas) applyTimeRangeMs(chartBot, ms);
        },
        hasData: retBars.length > 0 || spotLn.length > 0,
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (e) {}
          try {
            chartTop.remove();
          } catch (e2) {}
          try {
            chartBot.remove();
          } catch (e3) {}
        },
      };
    });
  }

  /**
   * FPI weekly: histogram bars + cumulative line (right).
   */
  function createFpiComboChart(container, spec, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      if (!container) return null;
      if (!ready || !global.LightweightCharts) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      var LW = global.LightweightCharts;
      container.innerHTML = '';
      var chart = LW.createChart(container, baseChartOptions(container, opts.theme));
      var bars = spec.barData || [];
      var cum = normalizeSeriesData(spec.cumLine || []);
      if (!bars.length && !cum.length) {
        showChartEmpty(container, opts.emptyMessage);
        return null;
      }
      if (bars.length) {
        var h = chart.addSeries(LW.HistogramSeries, { priceScaleId: 'left' });
        h.setData(bars);
      }
      if (cum.length) {
        var ln = chart.addSeries(LW.LineSeries, {
          color: spec.cumColor || T.usdinr,
          lineWidth: 1.5,
          priceScaleId: 'right',
          priceLineVisible: false,
        });
        ln.setData(cum);
      }
      chart.priceScale('right').applyOptions({ visible: cum.length > 0 });
      var ro = attachResize(container, chart);
      return {
        chart: chart,
        setRangeMs: function (ms) {
          applyTimeRangeMs(chart, ms);
        },
        hasData: true,
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (e) {}
        },
      };
    });
  }

  /**
   * SVG radar replacement for cross-asset (two polygons: current vs longer avg).
   */
  function renderCrossRadarSvg(container, params) {
    if (!container) return;
    var axes = params.axes || [];
    var accent = params.accent || T.eurusd;
    var n = axes.length || 5;
    var cx = 50;
    var cy = 52;
    var r = 38;
    var pts = [];
    var pts2 = [];
    for (var i = 0; i < n; i++) {
      var ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      var ax = axes[i] || { current: 0, longer: 0 };
      var v = Math.max(0, Math.min(1, ax.current || 0));
      var v2 = Math.max(0, Math.min(1, ax.longer || 0));
      pts.push(cx + r * v * Math.cos(ang) + ',' + (cy + r * v * Math.sin(ang)));
      pts2.push(cx + r * v2 * Math.cos(ang) + ',' + (cy + r * v2 * Math.sin(ang)));
    }
    var poly = pts.join(' ');
    var poly2 = pts2.join(' ');
    var sb = [];
    sb.push('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%" style="max-height:280px">');
    for (var ring = 1; ring <= 4; ring++) {
      var rr = (r * ring) / 4;
      var ringPts = [];
      for (var j = 0; j < n; j++) {
        var a = -Math.PI / 2 + (j * 2 * Math.PI) / n;
        ringPts.push(cx + rr * Math.cos(a) + ',' + (cy + rr * Math.sin(a)));
      }
      sb.push(
        '<polygon fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="0.4" points="' +
          ringPts.join(' ') +
          '"/>'
      );
    }
    for (var k = 0; k < n; k++) {
      var a2 = -Math.PI / 2 + (k * 2 * Math.PI) / n;
      sb.push(
        '<line x1="' +
          cx +
          '" y1="' +
          cy +
          '" x2="' +
          (cx + r * Math.cos(a2)) +
          '" y2="' +
          (cy + r * Math.sin(a2)) +
          '" stroke="rgba(255,255,255,0.1)" stroke-width="0.4"/>'
      );
      var lab = axes[k] && axes[k].label ? String(axes[k].label).replace(/&/g, '&amp;') : '';
      var lx = cx + (r + 8) * Math.cos(a2);
      var ly = cy + (r + 8) * Math.sin(a2);
      sb.push(
        '<text x="' +
          lx +
          '" y="' +
          ly +
          '" fill="#8B9BB4" font-size="5" font-family="JetBrains Mono,monospace" text-anchor="middle">' +
          lab +
          '</text>'
      );
    }
    sb.push(
      '<polygon fill="' +
        hexToRgba(accent, 0.12) +
        '" stroke="' +
        accent +
        '" stroke-width="0.8" points="' +
        poly +
        '"/>'
    );
    sb.push(
      '<polygon fill="rgba(107,114,128,0.1)" stroke="#6b7280" stroke-width="0.6" stroke-dasharray="2 2" points="' +
        poly2 +
        '"/>'
    );
    sb.push('</svg>');
    container.innerHTML = sb.join('');
  }

  global.FXRLCharts = {
    line: createLineChart,
    area: createAreaChart,
    histogram: createHistogramChart,
    createMultiLineChart: createMultiLineChart,
    createDualPaneCharts: createDualPaneCharts,
    createCotCompositeChart: createCotCompositeChart,
    createMomentumDualPane: createMomentumDualPane,
    createFpiComboChart: createFpiComboChart,
    renderCrossRadarSvg: renderCrossRadarSvg,
    pairColor: pairColor,
    applyTimeRange: applyTimeRange,
    applyTimeRangeMs: applyTimeRangeMs,
    waitForLWC: waitForLWC,
    normalizeSeriesData: normalizeSeriesData,
    msToSec: msToSec,
    hexToRgba: hexToRgba,
    register: register,
    disposeChart: disposeChart,
    disposeAll: disposeAll,
    showChartEmpty: showChartEmpty,
    showChartError: showChartError,
    ensureContainerId: ensureContainerId,
    baseChartOptions: baseChartOptions,
    T: T,
  };

  /* Legacy alias for scripts still reading TERMINAL_CHART_BASE.color */
  global.TERMINAL_CHART_BASE = {
    color: [T.eurusd, T.usdjpy, T.usdinr, T.bullish, T.bearish, '#7c6bcf'],
    textStyle: { fontFamily: '"JetBrains Mono", monospace', fontSize: 11, color: T.text },
  };
})(window);

if (typeof window.FXRLCharts === 'undefined') {
  console.error('FXRLCharts failed to register. Check lw-charts-config.js for syntax errors.');
} else {
  console.log('FXRLCharts registered successfully.');
}
