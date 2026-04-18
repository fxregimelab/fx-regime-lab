/* FX Regime Lab — ECharts terminal chart config */
(function (global) {
  'use strict';

  var EC = null;
  var registry = new Map();

  var T = {
    bg: 'transparent',
    grid: '#1e293b',
    border: '#1e293b',
    text: '#94a3b8',
    textPrimary: '#e8edf2',
    eurusd: '#4da6ff',
    usdjpy: '#ff9944',
    usdinr: '#e74c3c',
    bullish: '#2DD4A0',
    bearish: '#F87171',
    neutral: '#8B9BB4',
    anomaly: '#F59E0B',
  };

  function getECharts() {
    return global.echarts || EC;
  }

  function msToSec(ms) {
    return Math.floor(ms / 1000);
  }

  function hexToRgba(hex, alpha) {
    if (!hex || typeof hex !== 'string') return 'rgba(77,166,255,' + alpha + ')';
    var h = hex.replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    if (!isFinite(n)) return 'rgba(77,166,255,' + alpha + ')';
    var r = (n >> 16) & 255;
    var g = (n >> 8) & 255;
    var b = n & 255;
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }

  function parseTime(v) {
    if (v == null) return NaN;
    if (typeof v === 'number') return v > 1e12 ? v : v * 1000;
    var t = Date.parse(String(v).length <= 10 ? String(v) + 'T12:00:00Z' : String(v));
    return isFinite(t) ? t : NaN;
  }

  function normalizeSeriesData(data) {
    if (!Array.isArray(data) || !data.length) return [];
    var out = [];
    for (var i = 0; i < data.length; i++) {
      var d = data[i];
      var t;
      var v;
      if (Array.isArray(d)) {
        t = parseTime(d[0]);
        v = parseFloat(d[1]);
      } else if (d && d.time != null && d.value != null) {
        t = parseTime(d.time);
        v = parseFloat(d.value);
      } else if (d && d.date != null && d.value != null) {
        t = parseTime(d.date);
        v = parseFloat(d.value);
      } else {
        continue;
      }
      if (!isFinite(t) || !isFinite(v)) continue;
      out.push({ time: t, value: v });
    }
    out.sort(function (a, b) {
      return a.time - b.time;
    });
    return out;
  }

  function ensureContainerId(container) {
    if (!container) return '';
    if (!container.id) container.id = 'fxrl-echart-' + Math.random().toString(36).slice(2, 11);
    return container.id;
  }

  function waitForLWC(timeout) {
    var ms = timeout != null ? timeout : 8000;
    if (getECharts()) {
      EC = getECharts();
      return Promise.resolve(true);
    }
    return new Promise(function (resolve) {
      var done = false;
      var start = Date.now();
      var timer = setInterval(function () {
        if (getECharts()) {
          done = true;
          clearInterval(timer);
          EC = getECharts();
          resolve(true);
          return;
        }
        if (Date.now() - start >= ms) {
          done = true;
          clearInterval(timer);
          resolve(false);
        }
      }, 50);
      if (typeof document !== 'undefined') {
        document.addEventListener(
          'echarts-ready',
          function () {
            if (done) return;
            if (getECharts()) {
              done = true;
              clearInterval(timer);
              EC = getECharts();
              resolve(true);
            }
          },
          { once: true }
        );
      }
    });
  }

  function pairColor(pair) {
    var p = String(pair || '').replace('/', '').toUpperCase();
    if (p === 'EURUSD') return T.eurusd;
    if (p === 'USDJPY') return T.usdjpy;
    if (p === 'USDINR') return T.usdinr;
    return T.eurusd;
  }

  function showChartEmpty(container, msg) {
    if (!container) return;
    container.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:center;height:100%;min-height:120px;color:#4A5568;font-family:\'JetBrains Mono\',monospace;font-size:11px;background:#111827;border-radius:4px;">' +
      (msg || 'Signal data not yet available') +
      '</div>';
  }

  function showChartError(container, msg) {
    if (!container) return;
    container.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:center;height:100%;min-height:120px;color:#F87171;font-family:\'JetBrains Mono\',monospace;font-size:11px;background:#111827;border-radius:4px;">' +
      (msg || 'Chart failed to load') +
      '</div>';
  }

  function baseChartOptions(container, themeOpts) {
    var w = Math.max(container && (container.offsetWidth || container.clientWidth) || 0, 300);
    var h = Math.max(container && (container.offsetHeight || container.clientHeight) || 0, 200);
    var th = themeOpts || {};
    return {
      width: w,
      height: h,
      theme: {
        bg: th.bg != null ? th.bg : T.bg,
        text: th.text != null ? th.text : T.text,
        grid: th.grid != null ? th.grid : T.grid,
        border: th.border != null ? th.border : T.border,
      },
    };
  }

  function chartBaseOption(theme) {
    return {
      backgroundColor: theme.bg,
      animation: false,
      textStyle: { color: theme.text, fontFamily: "'JetBrains Mono', monospace", fontSize: 11 },
      grid: { left: 46, right: 14, top: 16, bottom: 28, containLabel: false },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#0f172a',
        borderColor: theme.grid,
        textStyle: { color: theme.textPrimary || T.textPrimary, fontFamily: "'JetBrains Mono', monospace" },
        axisPointer: { type: 'cross', lineStyle: { color: theme.grid } },
      },
      xAxis: {
        type: 'time',
        boundaryGap: false,
        axisLine: { lineStyle: { color: theme.border } },
        splitLine: { show: false },
        axisLabel: { color: theme.text, fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: true, lineStyle: { color: theme.border } },
        splitLine: { lineStyle: { color: theme.grid } },
        axisLabel: { color: theme.text, fontSize: 10 },
      },
    };
  }

  function toSeriesPairs(data) {
    return (data || []).map(function (p) {
      return [p.time, p.value];
    });
  }

  function resolveContainer(containerIdOrEl) {
    return typeof containerIdOrEl === 'string' ? document.getElementById(containerIdOrEl) : containerIdOrEl;
  }

  function disposeInstance(instance) {
    if (!instance) return;
    if (typeof instance.disposeExtra === 'function') {
      try {
        instance.disposeExtra();
      } catch (_e) {}
    }
    if (instance.chartTop && typeof instance.chartTop.dispose === 'function' && !instance.chartTop.isDisposed()) {
      try {
        instance.chartTop.dispose();
      } catch (_e2) {}
    }
    if (instance.chartBottom && typeof instance.chartBottom.dispose === 'function' && !instance.chartBottom.isDisposed()) {
      try {
        instance.chartBottom.dispose();
      } catch (_e3) {}
    }
    if (instance.chart && typeof instance.chart.dispose === 'function' && !instance.chart.isDisposed()) {
      try {
        instance.chart.dispose();
      } catch (_e4) {}
    }
  }

  function register(id, instance) {
    if (!id) return;
    if (registry.has(id)) disposeInstance(registry.get(id));
    registry.set(id, instance);
  }

  function clearRangeBar(container) {
    if (!container || !container.parentElement) return;
    var parent = container.parentElement;
    var bar = parent.querySelector('.fxrl-range-bar[data-chart-id="' + container.id + '"]');
    if (bar) bar.remove();
  }

  function disposeChart(idOrEl) {
    var el = idOrEl && idOrEl.nodeType === 1 ? idOrEl : null;
    if (!el && typeof idOrEl === 'string') el = document.getElementById(idOrEl);
    var id = typeof idOrEl === 'string' ? idOrEl : el && el.id ? el.id : '';

    if (id && registry.has(id)) {
      disposeInstance(registry.get(id));
      registry.delete(id);
    } else if (el && el._echartsInst && typeof el._echartsInst.dispose === 'function') {
      try {
        if (!el._echartsInst.isDisposed()) el._echartsInst.dispose();
      } catch (_e) {}
    }
    if (el) {
      clearRangeBar(el);
      el._echartsInst = undefined;
      el.innerHTML = '';
    }
  }

  function disposeAll() {
    registry.forEach(function (instance) {
      disposeInstance(instance);
    });
    registry.clear();
  }

  function attachResize(container, chart) {
    var ro = new ResizeObserver(function () {
      try {
        if (chart && typeof chart.resize === 'function' && !chart.isDisposed()) chart.resize();
      } catch (_e) {}
    });
    ro.observe(container);
    return ro;
  }

  function setRangeOnChart(chart, fromMs, toMs) {
    if (!chart || typeof chart.setOption !== 'function') return;
    var yAxes = [];
    var opts = chart.getOption() || {};
    var count = Array.isArray(opts.xAxis) ? opts.xAxis.length : 1;
    var xAxes = [];
    for (var i = 0; i < count; i++) {
      xAxes.push({ min: fromMs, max: toMs });
    }
    chart.setOption({ xAxis: xAxes, yAxis: yAxes }, false, true);
  }

  function applyTimeRange(chart, range) {
    if (!chart) return;
    var now = Date.now();
    var ranges = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365 };
    if (!ranges[range]) {
      setRangeOnChart(chart, null, null);
      return;
    }
    var from = now - ranges[range] * 86400000;
    setRangeOnChart(chart, from, now);
  }

  function applyTimeRangeMs(chart, rangeMs) {
    if (!chart || !rangeMs) return;
    var now = Date.now();
    setRangeOnChart(chart, now - Math.floor(rangeMs), now);
  }

  function renderTimeRangeButtons(container, chart) {
    if (!container || !chart || !container.parentElement) return;
    if (!container.id) ensureContainerId(container);
    clearRangeBar(container);
    var parent = container.parentElement;
    var bar = document.createElement('div');
    bar.className = 'fxrl-range-bar';
    bar.dataset.chartId = container.id;
    bar.style.cssText =
      'display:flex;gap:4px;padding:8px 12px 0;font-family:\'JetBrains Mono\',monospace;';
    var ranges = ['1M', '3M', '6M', '1Y', 'All'];
    ranges.forEach(function (r, i) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = r;
      btn.style.cssText =
        'background:transparent;border:1px solid rgba(255,255,255,0.10);color:#8B9BB4;font-size:10px;font-family:inherit;padding:3px 8px;border-radius:3px;cursor:pointer;transition:all 0.15s;';
      btn.addEventListener('click', function () {
        bar.querySelectorAll('button').forEach(function (b) {
          b.style.color = '#8B9BB4';
          b.style.borderColor = 'rgba(255,255,255,0.10)';
        });
        btn.style.color = '#E8EDF2';
        btn.style.borderColor = '#4D8EFF';
        applyTimeRange(chart, r);
      });
      bar.appendChild(btn);
      if (i === 1) setTimeout(function () { btn.click(); }, 0);
    });
    parent.insertBefore(bar, container);
  }

  function addTimeRangeButtons(containerIdOrEl, chartOrInstance) {
    var container = resolveContainer(containerIdOrEl);
    var chart = chartOrInstance && chartOrInstance.chart ? chartOrInstance.chart : chartOrInstance;
    if (!container || !chart) return;
    renderTimeRangeButtons(container, chart);
  }

  function toLineInstance(chart, ro) {
    return {
      chart: chart,
      setRange: function (r) { applyTimeRange(chart, r); },
      setRangeMs: function (ms) { applyTimeRangeMs(chart, ms); },
      hasData: true,
      disposeExtra: function () {
        try {
          ro.disconnect();
        } catch (_e) {}
      },
    };
  }

  function createSingleChart(containerIdOrEl, rawData, opts, kind) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      var container = resolveContainer(containerIdOrEl);
      if (!container) return null;
      var cid = ensureContainerId(container);
      disposeChart(container);
      if (!ready || !getECharts()) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      var data = normalizeSeriesData(rawData);
      if (!data.length) {
        showChartEmpty(container, opts.emptyMessage);
        return null;
      }
      var base = baseChartOptions(container, opts.theme);
      var chart = getECharts().init(container, null, {
        renderer: 'canvas',
        width: base.width,
        height: base.height,
      });
      container._echartsInst = chart;
      var color = opts.color || T.eurusd;
      var series;
      if (kind === 'histogram') {
        series = {
          type: 'bar',
          barMaxWidth: 8,
          itemStyle: { color: color },
          data: toSeriesPairs(data),
        };
      } else {
        series = {
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: opts.lineWidth != null ? opts.lineWidth : 2, color: color },
          itemStyle: { color: color },
          data: toSeriesPairs(data),
        };
        if (kind === 'area') {
          series.areaStyle = { color: hexToRgba(color, 0.2) };
        }
      }
      var option = chartBaseOption({
        bg: base.theme.bg,
        text: base.theme.text,
        border: base.theme.border,
        grid: base.theme.grid,
        textPrimary: T.textPrimary,
      });
      option.series = [series];
      chart.setOption(option, true);
      chart.resize({ width: base.width, height: base.height });
      chart.resize();
      var ro = attachResize(container, chart);
      var inst = toLineInstance(chart, ro);
      register(cid, inst);
      if (!opts.skipRangeButtons) renderTimeRangeButtons(container, chart);
      return inst;
    });
  }

  function createLineChart(container, data, options) {
    return createSingleChart(container, data, options, 'line');
  }

  function createAreaChart(container, data, options) {
    return createSingleChart(container, data, options, 'area');
  }

  function createHistogramChart(container, data, options) {
    return createSingleChart(container, data, options, 'histogram');
  }

  function createMultiLineChart(container, seriesArray, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      container = resolveContainer(container);
      if (!container) return null;
      var cid = ensureContainerId(container);
      disposeChart(container);
      if (!ready || !getECharts()) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      var base = baseChartOptions(container, opts.theme);
      var chart = getECharts().init(container, null, {
        renderer: 'canvas',
        width: base.width,
        height: base.height,
      });
      container._echartsInst = chart;
      var hasData = false;
      var leftSeen = false;
      var rightSeen = false;
      var series = [];
      (seriesArray || []).forEach(function (spec) {
        var pts = normalizeSeriesData(spec && spec.data);
        if (!pts.length) return;
        hasData = true;
        var axis = spec && spec.priceScaleId === 'right' ? 1 : 0;
        if (axis === 0) leftSeen = true;
        else rightSeen = true;
        series.push({
          name: spec && spec.name ? spec.name : '',
          type: 'line',
          smooth: true,
          symbol: 'none',
          yAxisIndex: axis,
          lineStyle: {
            width: spec && spec.lineWidth != null ? spec.lineWidth : 2,
            type: spec && spec.dashed ? 'dashed' : 'solid',
            color: spec && spec.color ? spec.color : T.eurusd,
          },
          itemStyle: { color: spec && spec.color ? spec.color : T.eurusd },
          data: toSeriesPairs(pts),
        });
      });
      if (!hasData) {
        chart.dispose();
        showChartEmpty(container, opts.emptyMessage);
        return null;
      }
      var option = chartBaseOption({
        bg: base.theme.bg,
        text: base.theme.text,
        border: base.theme.border,
        grid: base.theme.grid,
        textPrimary: T.textPrimary,
      });
      option.yAxis = [
        {
          type: 'value',
          show: leftSeen || !rightSeen,
          axisLine: { lineStyle: { color: base.theme.border } },
          splitLine: { lineStyle: { color: base.theme.grid } },
          axisLabel: { color: base.theme.text, fontSize: 10 },
        },
        {
          type: 'value',
          show: rightSeen,
          axisLine: { lineStyle: { color: base.theme.border } },
          splitLine: { show: false },
          axisLabel: { color: base.theme.text, fontSize: 10 },
        },
      ];
      option.series = series;
      chart.setOption(option, true);
      chart.resize({ width: base.width, height: base.height });
      chart.resize();
      var ro = attachResize(container, chart);
      var inst = {
        chart: chart,
        series: series,
        setRangeMs: function (ms) { applyTimeRangeMs(chart, ms); },
        hasData: true,
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (_e) {}
        },
      };
      register(cid, inst);
      if (!opts.skipRangeButtons) renderTimeRangeButtons(container, chart);
      return inst;
    });
  }

  function buildDualPane(container, topSeries, botSeries, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      container = resolveContainer(container);
      if (!container) return null;
      var cid = ensureContainerId(container);
      disposeChart(container);
      if (!ready || !getECharts()) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      container.innerHTML = '';
      var wrap = document.createElement('div');
      wrap.style.cssText = 'display:flex;flex-direction:column;height:100%;min-height:220px;';
      var topEl = document.createElement('div');
      var botEl = document.createElement('div');
      topEl.style.cssText = 'flex:1;min-height:110px;';
      botEl.style.cssText = 'flex:1;min-height:90px;';
      wrap.appendChild(topEl);
      wrap.appendChild(botEl);
      container.appendChild(wrap);
      var baseTop = baseChartOptions(topEl, opts.theme);
      var baseBot = baseChartOptions(botEl, opts.theme);
      var chartTop = getECharts().init(topEl, null, {
        renderer: 'canvas',
        width: baseTop.width,
        height: baseTop.height,
      });
      var chartBottom = getECharts().init(botEl, null, {
        renderer: 'canvas',
        width: baseBot.width,
        height: baseBot.height,
      });
      var topOpt = chartBaseOption({
        bg: baseTop.theme.bg,
        text: baseTop.theme.text,
        border: baseTop.theme.border,
        grid: baseTop.theme.grid,
        textPrimary: T.textPrimary,
      });
      topOpt.series = topSeries;
      var botOpt = chartBaseOption({
        bg: baseBot.theme.bg,
        text: baseBot.theme.text,
        border: baseBot.theme.border,
        grid: baseBot.theme.grid,
        textPrimary: T.textPrimary,
      });
      botOpt.series = botSeries;
      chartTop.setOption(topOpt, true);
      chartBottom.setOption(botOpt, true);
      chartTop.resize({ width: baseTop.width, height: baseTop.height });
      chartTop.resize();
      chartBottom.resize({ width: baseBot.width, height: baseBot.height });
      chartBottom.resize();
      var ro = new ResizeObserver(function () {
        try {
          chartTop.resize();
          chartBottom.resize();
        } catch (_e) {}
      });
      ro.observe(container);
      var inst = {
        chart: chartTop,
        chartTop: chartTop,
        chartBottom: chartBottom,
        setRangeMs: function (ms) {
          applyTimeRangeMs(chartTop, ms);
          applyTimeRangeMs(chartBottom, ms);
        },
        hasData: (topSeries && topSeries.length) || (botSeries && botSeries.length),
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (_e2) {}
        },
      };
      register(cid, inst);
      return inst;
    });
  }

  function createDualPaneCharts(container, topSpec, bottomSpec, opts) {
    var topSeries = [];
    (topSpec || []).forEach(function (spec) {
      var pts = normalizeSeriesData(spec && spec.data);
      if (!pts.length) return;
      topSeries.push({
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: spec && spec.lineWidth != null ? spec.lineWidth : 2,
          type: spec && spec.dashed ? 'dashed' : 'solid',
          color: spec && spec.color ? spec.color : T.eurusd,
        },
        itemStyle: { color: spec && spec.color ? spec.color : T.eurusd },
        areaStyle: spec && spec.area ? { color: hexToRgba(spec.color || T.eurusd, 0.15) } : null,
        data: toSeriesPairs(pts),
      });
    });
    var botSeries = [];
    (bottomSpec || []).forEach(function (spec) {
      var pts = normalizeSeriesData(spec && spec.data);
      if (!pts.length) return;
      botSeries.push({
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: spec && spec.lineWidth != null ? spec.lineWidth : 2, color: spec && spec.color ? spec.color : T.neutral },
        itemStyle: { color: spec && spec.color ? spec.color : T.neutral },
        markLine: spec && spec.zeroLine ? { symbol: ['none', 'none'], data: [{ yAxis: 0, lineStyle: { color: T.border, type: 'dashed' } }] } : null,
        data: toSeriesPairs(pts),
      });
    });
    if (!topSeries.length && !botSeries.length) {
      container = resolveContainer(container);
      if (container) showChartEmpty(container, opts && opts.emptyMessage);
      return Promise.resolve(null);
    }
    return buildDualPane(container, topSeries, botSeries, opts);
  }

  function createCotCompositeChart(container, data, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      container = resolveContainer(container);
      if (!container) return null;
      var cid = ensureContainerId(container);
      disposeChart(container);
      if (!ready || !getECharts()) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      var lev = [];
      var asset = [];
      var pct = [];
      var th20 = data && data.th20;
      var th80 = data && data.th80;
      if (data && Array.isArray(data.dates)) {
        for (var i = 0; i < data.dates.length; i++) {
          var t = parseTime(data.dates[i]);
          if (!isFinite(t)) continue;
          var lv = parseFloat((data.levMoney || [])[i]);
          var av = parseFloat((data.assetMgr || [])[i]);
          var pv = parseFloat((data.percentile || [])[i]);
          if (isFinite(lv)) lev.push([t, lv]);
          if (isFinite(av)) asset.push([t, av]);
          if (isFinite(pv)) pct.push([t, pv]);
        }
      } else {
        lev = toSeriesPairs((data && data.levHistogram) || []);
        asset = toSeriesPairs(normalizeSeriesData((data && data.assetLine) || []));
      }
      if (!lev.length && !asset.length && !pct.length) {
        showChartEmpty(container, opts.emptyMessage);
        return null;
      }
      var base = baseChartOptions(container, opts.theme);
      var chart = getECharts().init(container, null, {
        renderer: 'canvas',
        width: base.width,
        height: base.height,
      });
      container._echartsInst = chart;
      var option = chartBaseOption({
        bg: base.theme.bg,
        text: base.theme.text,
        border: base.theme.border,
        grid: base.theme.grid,
        textPrimary: T.textPrimary,
      });
      option.yAxis = [
        {
          type: 'value',
          axisLine: { lineStyle: { color: base.theme.border } },
          splitLine: { lineStyle: { color: base.theme.grid } },
          axisLabel: { color: base.theme.text, fontSize: 10 },
        },
        {
          type: 'value',
          min: 0,
          max: 100,
          axisLine: { lineStyle: { color: base.theme.border } },
          splitLine: { show: false },
          axisLabel: { color: base.theme.text, fontSize: 10 },
        },
      ];
      option.series = [
        {
          name: 'Lev Money',
          type: 'bar',
          barMaxWidth: 8,
          itemStyle: { color: T.usdjpy },
          data: lev,
          markLine: {
            symbol: ['none', 'none'],
            data: [
              isFinite(th80) ? { yAxis: th80, lineStyle: { color: T.anomaly, type: 'dashed' } } : null,
              isFinite(th20) ? { yAxis: th20, lineStyle: { color: T.anomaly, type: 'dashed' } } : null,
            ].filter(Boolean),
          },
        },
        {
          name: 'Asset Mgr',
          type: 'bar',
          barMaxWidth: 8,
          itemStyle: { color: '#6b7280' },
          data: asset,
        },
        {
          name: 'Percentile',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2, color: T.eurusd },
          itemStyle: { color: T.eurusd },
          data: pct,
        },
      ];
      chart.setOption(option, true);
      chart.resize({ width: base.width, height: base.height });
      chart.resize();
      var ro = attachResize(container, chart);
      var inst = {
        chart: chart,
        setRangeMs: function (ms) { applyTimeRangeMs(chart, ms); },
        hasData: true,
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (_e) {}
        },
      };
      register(cid, inst);
      if (!opts.skipRangeButtons) renderTimeRangeButtons(container, chart);
      return inst;
    });
  }

  function createMomentumDualPane(container, spec, opts) {
    var top = [];
    var bars = (spec && spec.dailyHist) || [];
    if (bars.length) {
      top.push({
        type: 'bar',
        barMaxWidth: 8,
        itemStyle: { color: T.usdjpy },
        data: toSeriesPairs(normalizeSeriesData(bars)),
      });
    }
    var mom = normalizeSeriesData(spec && spec.momoLine);
    if (mom.length) {
      top.push({
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: spec && spec.momColor ? spec.momColor : T.eurusd },
        itemStyle: { color: spec && spec.momColor ? spec.momColor : T.eurusd },
        data: toSeriesPairs(mom),
      });
    }
    var bot = [];
    var spot = normalizeSeriesData(spec && spec.spotLine);
    if (spot.length) {
      bot.push({
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: spec && spec.spotColor ? spec.spotColor : T.textPrimary },
        itemStyle: { color: spec && spec.spotColor ? spec.spotColor : T.textPrimary },
        data: toSeriesPairs(spot),
      });
    }
    if (!top.length && !bot.length) {
      container = resolveContainer(container);
      if (container) showChartEmpty(container, opts && opts.emptyMessage);
      return Promise.resolve(null);
    }
    return buildDualPane(container, top, bot, opts);
  }

  function createFpiComboChart(container, spec, opts) {
    opts = opts || {};
    return waitForLWC().then(function (ready) {
      container = resolveContainer(container);
      if (!container) return null;
      var cid = ensureContainerId(container);
      disposeChart(container);
      if (!ready || !getECharts()) {
        showChartError(container, 'Chart library unavailable');
        return null;
      }
      var bars = toSeriesPairs(normalizeSeriesData((spec && spec.barData) || []));
      var cum = toSeriesPairs(normalizeSeriesData((spec && spec.cumLine) || []));
      if (!bars.length && !cum.length) {
        showChartEmpty(container, opts.emptyMessage);
        return null;
      }
      var base = baseChartOptions(container, opts.theme);
      var chart = getECharts().init(container, null, {
        renderer: 'canvas',
        width: base.width,
        height: base.height,
      });
      container._echartsInst = chart;
      var option = chartBaseOption({
        bg: base.theme.bg,
        text: base.theme.text,
        border: base.theme.border,
        grid: base.theme.grid,
        textPrimary: T.textPrimary,
      });
      option.yAxis = [
        {
          type: 'value',
          axisLine: { lineStyle: { color: base.theme.border } },
          splitLine: { lineStyle: { color: base.theme.grid } },
          axisLabel: { color: base.theme.text, fontSize: 10 },
        },
        {
          type: 'value',
          axisLine: { lineStyle: { color: base.theme.border } },
          splitLine: { show: false },
          axisLabel: { color: base.theme.text, fontSize: 10 },
        },
      ];
      option.series = [
        { type: 'bar', barMaxWidth: 8, itemStyle: { color: T.usdinr }, data: bars },
        {
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2, color: spec && spec.cumColor ? spec.cumColor : T.usdinr },
          itemStyle: { color: spec && spec.cumColor ? spec.cumColor : T.usdinr },
          data: cum,
        },
      ];
      chart.setOption(option, true);
      chart.resize({ width: base.width, height: base.height });
      chart.resize();
      var ro = attachResize(container, chart);
      var inst = {
        chart: chart,
        setRangeMs: function (ms) { applyTimeRangeMs(chart, ms); },
        hasData: true,
        disposeExtra: function () {
          try {
            ro.disconnect();
          } catch (_e) {}
        },
      };
      register(cid, inst);
      if (!opts.skipRangeButtons) renderTimeRangeButtons(container, chart);
      return inst;
    });
  }

  function renderCrossRadarSvg(container, params) {
    if (!container) return;
    var axes = params && params.axes ? params.axes : [];
    var accent = params && params.accent ? params.accent : T.eurusd;
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
    var sb = [];
    sb.push('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%" style="max-height:280px">');
    sb.push('<polygon fill="' + hexToRgba(accent, 0.12) + '" stroke="' + accent + '" stroke-width="0.8" points="' + pts.join(' ') + '"/>');
    sb.push('<polygon fill="rgba(107,114,128,0.1)" stroke="#6b7280" stroke-width="0.6" stroke-dasharray="2 2" points="' + pts2.join(' ') + '"/>');
    sb.push('</svg>');
    container.innerHTML = sb.join('');
  }

  function resizeTabCharts(panel) {
    if (!panel) return;
    panel.querySelectorAll('.term-chart').forEach(function (container) {
      if (container._echartsInst && typeof container._echartsInst.resize === 'function') {
        try {
          container._echartsInst.resize();
        } catch (_e) {}
      }
    });
  }

  global.FXRLCharts = {
    line: createLineChart,
    area: createAreaChart,
    histogram: createHistogramChart,
    createLineChart: createLineChart,
    createAreaChart: createAreaChart,
    createHistogramChart: createHistogramChart,
    createMultiLineChart: createMultiLineChart,
    createDualPaneCharts: createDualPaneCharts,
    createCotCompositeChart: createCotCompositeChart,
    createMomentumDualPane: createMomentumDualPane,
    createFpiComboChart: createFpiComboChart,
    addTimeRangeButtons: addTimeRangeButtons,
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
    resizeTabCharts: resizeTabCharts,
    registry: registry,
    T: T,
  };

  global.TERMINAL_CHART_BASE = {
    color: [T.eurusd, T.usdjpy, T.usdinr, T.bullish, T.bearish, '#7c6bcf'],
    textStyle: { fontFamily: '"JetBrains Mono", monospace', fontSize: 11, color: T.text },
  };
})(window);

if (typeof window.FXRLCharts === 'undefined') {
  console.error('FXRLCharts failed to register. Check lw-charts-config.js for syntax errors.');
} else {
  console.log('FXRLCharts registered successfully (ECharts).');
}
