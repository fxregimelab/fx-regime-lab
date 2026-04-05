/**
 * FX Regime Lab — ECharts defaults + factories (terminal Part C).
 * Requires ECharts 5.4.x (cdnjs). Palette aligns with terminal.css tokens.
 */
(function (global) {
  'use strict';

  var COL = {
    bg: '#0f1318',
    grid: '#1c1f18',
    axis: '#252820',
    label: '#4a5245',
    text: '#e8ede8',
    surface: '#191c15',
    border: '#2e3228',
    eur: '#4d8eff',
    jpy: '#d4890a',
    inr: '#c94040',
    bull: '#2d9e6b',
    bear: '#c94040',
    accent: '#3d7eff',
  };

  /**
   * Global ECharts option fragment merged into all terminal charts.
   * (Spec: terminal redesign — dark terminal, mono labels, no glass.)
   */
  var TERMINAL_CHART_BASE = {
    backgroundColor: COL.bg,
    color: [COL.eur, COL.jpy, COL.inr, COL.bull, COL.bear, '#7c6bcf'],
    textStyle: {
      fontFamily: '"JetBrains Mono", ui-monospace, monospace',
      fontSize: 11,
      color: COL.label,
    },
    animation: true,
    animationDuration: 600,
    animationEasing: 'cubicOut',
    animationDurationUpdate: 300,
    lazyUpdate: true,
    grid: {
      left: 48,
      right: 16,
      top: 24,
      bottom: 32,
      containLabel: true,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: COL.surface,
      borderColor: COL.border,
      borderWidth: 1,
      padding: [8, 12],
      textStyle: {
        color: COL.text,
        fontFamily: '"JetBrains Mono", ui-monospace, monospace',
        fontSize: 11,
      },
      axisPointer: {
        type: 'cross',
        crossStyle: { color: COL.label, width: 1, type: 'dashed' },
        lineStyle: { color: COL.axis, type: 'dashed' },
        label: {
          backgroundColor: COL.surface,
          color: COL.text,
          borderColor: COL.border,
          borderWidth: 1,
        },
      },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      axisLine: { lineStyle: { color: COL.axis } },
      axisTick: { lineStyle: { color: COL.axis }, length: 4 },
      axisLabel: { color: COL.label, fontSize: 10, fontFamily: '"JetBrains Mono", ui-monospace, monospace' },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: true, lineStyle: { color: COL.axis } },
      axisTick: { show: true, lineStyle: { color: COL.axis } },
      axisLabel: { color: COL.label, fontSize: 10, fontFamily: '"JetBrains Mono", ui-monospace, monospace' },
      splitLine: { lineStyle: { color: COL.grid, width: 1 } },
    },
  };

  try {
    if (global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      TERMINAL_CHART_BASE.animation = false;
      TERMINAL_CHART_BASE.animationDuration = 0;
    }
  } catch (e) {
    /* ignore */
  }

  function isPlainObject(o) {
    return o !== null && typeof o === 'object' && !Array.isArray(o);
  }

  function deepMerge(base, extra) {
    if (!extra) return base;
    var out = Array.isArray(base) ? base.slice() : Object.assign({}, base);
    Object.keys(extra).forEach(function (k) {
      var ev = extra[k];
      var bv = out[k];
      if (isPlainObject(ev) && isPlainObject(bv)) {
        out[k] = deepMerge(bv, ev);
      } else {
        out[k] = ev;
      }
    });
    return out;
  }

  function baseOption() {
    return JSON.parse(JSON.stringify(TERMINAL_CHART_BASE));
  }

  function initChart(dom) {
    if (!global.echarts) {
      return null;
    }
    return global.echarts.init(dom, null, { renderer: 'canvas' });
  }

  function observeChartResize(container, chart) {
    if (!container || !chart || typeof ResizeObserver !== 'function') return null;
    var t = 0;
    var ro = new ResizeObserver(function () {
      if (t) global.clearTimeout(t);
      t = global.setTimeout(function () {
        t = 0;
        if (chart && typeof chart.resize === 'function') {
          try {
            chart.resize();
          } catch (_e) {
            /* disposed */
          }
        }
      }, 120);
    });
    ro.observe(container);
    ro._cancelFxrlResize = function () {
      if (t) global.clearTimeout(t);
      t = 0;
    };
    return ro;
  }

  /**
   * Two line series on one grid (e.g. spread vs spot).
   * @param {HTMLElement} dom
   * @param {{ categories: string[], series: { name: string, data: number[], color?: string }[] }} spec
   */
  function createTerminalDualLineChart(dom, spec) {
    var chart = initChart(dom);
    if (!chart) return null;
    var categories = spec.categories || [];
    var seriesList = (spec.series || []).map(function (s, i) {
      return {
        type: 'line',
        name: s.name,
        data: s.data || [],
        smooth: 0.35,
        showSymbol: false,
        lineStyle: { width: 1.5, color: s.color || TERMINAL_CHART_BASE.color[i % TERMINAL_CHART_BASE.color.length] },
        itemStyle: { color: s.color },
        emphasis: { focus: 'series' },
      };
    });
    var opt = deepMerge(baseOption(), {
      xAxis: { data: categories, boundaryGap: false },
      yAxis: { type: 'value', scale: true },
      series: seriesList,
      legend: {
        show: seriesList.length > 1,
        top: 0,
        right: 12,
        textStyle: { color: COL.label, fontSize: 10, fontFamily: '"JetBrains Mono", ui-monospace, monospace' },
      },
    });
    chart.setOption(opt, { notMerge: true, lazyUpdate: true });
    return chart;
  }

  /**
   * Stacked bars + line overlay (right y-axis for line).
   * @param {{ categories: string[], stackSeries: { name: string, data: number[], color?: string }[], lineSeries: { name: string, data: number[], color?: string } }} spec
   */
  function createTerminalStackedBarOverlayChart(dom, spec) {
    var chart = initChart(dom);
    if (!chart) return null;
    var categories = spec.categories || [];
    var stack = spec.stackSeries || [];
    var line = spec.lineSeries || { name: 'Overlay', data: [] };
    var barSeries = stack.map(function (s, i) {
      return {
        type: 'bar',
        name: s.name,
        stack: 'total',
        data: s.data || [],
        itemStyle: { color: s.color || TERMINAL_CHART_BASE.color[i % 6] },
        emphasis: { focus: 'series' },
      };
    });
    var opt = deepMerge(baseOption(), {
      tooltip: { trigger: 'axis' },
      xAxis: { data: categories, boundaryGap: true },
      yAxis: [
        { type: 'value', scale: true },
        { type: 'value', scale: true, splitLine: { show: false } },
      ],
      series: barSeries.concat([
        {
          type: 'line',
          name: line.name,
          yAxisIndex: 1,
          data: line.data || [],
          smooth: 0.25,
          showSymbol: false,
          lineStyle: { width: 2, color: line.color || COL.accent },
          itemStyle: { color: line.color || COL.accent },
        },
      ]),
      legend: {
        show: true,
        top: 0,
        textStyle: { color: COL.label, fontSize: 10, fontFamily: '"JetBrains Mono", ui-monospace, monospace' },
      },
    });
    chart.setOption(opt, { notMerge: true, lazyUpdate: true });
    return chart;
  }

  /**
   * Two independent panels (line top, bars bottom by default).
   */
  function createTerminalDualPanelChart(dom, spec) {
    var chart = initChart(dom);
    if (!chart) return null;
    var top = spec.topPanel || { type: 'line', categories: [], series: [] };
    var bot = spec.bottomPanel || { type: 'bar', categories: [], series: [] };
    var bx = baseOption();
    var xa = JSON.parse(JSON.stringify(bx.xAxis));
    var ya = JSON.parse(JSON.stringify(bx.yAxis));
    var opt = {
      backgroundColor: COL.bg,
      color: TERMINAL_CHART_BASE.color,
      textStyle: TERMINAL_CHART_BASE.textStyle,
      animation: true,
      animationDuration: 600,
      animationDurationUpdate: 300,
      lazyUpdate: true,
      grid: [
        { left: 52, right: 20, top: 40, height: '32%' },
        { left: 52, right: 20, top: '58%', height: '32%' },
      ],
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      tooltip: JSON.parse(JSON.stringify(bx.tooltip)),
      xAxis: [
        deepMerge(xa, { gridIndex: 0, data: top.categories || [] }),
        deepMerge(JSON.parse(JSON.stringify(bx.xAxis)), { gridIndex: 1, data: bot.categories || [] }),
      ],
      yAxis: [
        deepMerge(ya, { gridIndex: 0, scale: true }),
        deepMerge(JSON.parse(JSON.stringify(bx.yAxis)), { gridIndex: 1, scale: true }),
      ],
      series: [],
    };

    if (top.type === 'line' && top.series && top.series[0]) {
      opt.series.push({
        type: 'line',
        name: top.series[0].name,
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: top.series[0].data || [],
        smooth: 0.35,
        showSymbol: false,
        lineStyle: { width: 1.5, color: top.series[0].color || COL.eur },
      });
    }
    if (bot.type === 'bar' && bot.series && bot.series[0]) {
      opt.series.push({
        type: 'bar',
        name: bot.series[0].name,
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: bot.series[0].data || [],
        itemStyle: { color: bot.series[0].color || COL.jpy },
      });
    }
    chart.setOption(opt, { notMerge: true, lazyUpdate: true });
    return chart;
  }

  /**
   * Radar (multi-axis snapshot).
   * @param {{ indicator: { name: string, max: number }[], series: { name: string, value: number[], color?: string }[] }} spec
   */
  function createTerminalRadarChart(dom, spec) {
    var chart = initChart(dom);
    if (!chart) return null;
    var indicator = spec.indicator || [];
    var series = (spec.series || []).map(function (s) {
      return {
        type: 'radar',
        name: s.name,
        data: [{ value: s.value || [], name: s.name, itemStyle: { color: s.color } }],
        lineStyle: { width: 1.5, color: s.color || COL.eur },
        areaStyle: { opacity: 0.12, color: s.color || COL.eur },
        symbol: 'none',
      };
    });
    var opt = {
      backgroundColor: COL.bg,
      color: TERMINAL_CHART_BASE.color,
      textStyle: TERMINAL_CHART_BASE.textStyle,
      tooltip: { trigger: 'item' },
      radar: {
        indicator: indicator,
        axisName: { color: COL.label, fontSize: 10, fontFamily: '"JetBrains Mono", ui-monospace, monospace' },
        splitLine: { lineStyle: { color: COL.grid } },
        splitArea: { show: true, areaStyle: { color: [COL.surface, 'transparent'] } },
        axisLine: { lineStyle: { color: COL.axis } },
      },
      series: series,
    };
    chart.setOption(opt, { notMerge: true, lazyUpdate: true });
    return chart;
  }

  /**
   * Histogram as category bar (pre-binned counts).
   * @param {{ bins: string[], counts: number[], color?: string }} spec
   */
  function createTerminalHistogramChart(dom, spec) {
    var chart = initChart(dom);
    if (!chart) return null;
    var bins = spec.bins || [];
    var counts = spec.counts || [];
    var opt = deepMerge(baseOption(), {
      xAxis: { data: bins, boundaryGap: true },
      yAxis: { type: 'value', scale: true },
      series: [
        {
          type: 'bar',
          name: spec.name || 'Frequency',
          data: counts,
          barMaxWidth: 24,
          itemStyle: { color: spec.color || COL.accent },
        },
      ],
      tooltip: { trigger: 'axis' },
    });
    chart.setOption(opt, { notMerge: true, lazyUpdate: true });
    return chart;
  }

  global.TERMINAL_CHART_BASE = TERMINAL_CHART_BASE;
  global.TerminalCharts = {
    createDualLine: createTerminalDualLineChart,
    createStackedBarOverlay: createTerminalStackedBarOverlayChart,
    createDualPanel: createTerminalDualPanelChart,
    createRadar: createTerminalRadarChart,
    createHistogram: createTerminalHistogramChart,
    deepMerge: deepMerge,
    init: initChart,
    observeChartResize: observeChartResize,
  };
})(typeof window !== 'undefined' ? window : this);
