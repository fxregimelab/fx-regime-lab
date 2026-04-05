/**
 * FX Regime Lab — Terminal Analysis Workspace (exploration only; no export).
 * Uses FXRLChartBuilder.DATA_CATALOG from chart-builder.js; separate series state.
 */
(function (global) {
  'use strict';

  var MASTER_CSV = '/data/latest_with_cot.csv';
  var LS_MARKERS = 'fxrl_workspace_markers';
  var LS_REFLINES = 'fxrl_workspace_reflines';
  var csvCache = {};

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
    var t = new Date(dateStr + 'T12:00:00Z').getTime();
    return isFinite(t) ? t : NaN;
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

  function filterByDateRange(pts, fromStr, toStr) {
    var tFrom = fromStr ? ts(fromStr) : -Infinity;
    var tTo = toStr ? ts(toStr) + 86400000 - 1 : Infinity;
    return pts.filter(function (p) {
      return p[0] >= tFrom && p[0] <= tTo;
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

  function fetchCsv(path) {
    if (csvCache[path]) return Promise.resolve(csvCache[path]);
    return fetch(path)
      .then(function (r) {
        if (!r.ok) throw new Error('CSV ' + path);
        return r.text();
      })
      .then(function (t) {
        csvCache[path] = t;
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

  function catalogMapFrom(catalog) {
    var m = {};
    (catalog.categories || []).forEach(function (cat) {
      (cat.series || []).forEach(function (s) {
        m[s.id] = s;
      });
    });
    return m;
  }

  /** Independent workspace series registry (does not use FXRLChartBuilder.SeriesManager). */
  var WorkspaceSeriesManager = {
    active: new Map(),
    catalogMap: {},
    onChange: null,

    bindCatalog: function (catalog) {
      this.catalogMap = catalogMapFrom(catalog);
    },

    addSeries: function (id) {
      var self = this;
      var meta = this.catalogMap[id];
      if (!meta || this.active.has(id)) return Promise.resolve();
      return fetchCsv(meta.csvFile || MASTER_CSV)
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
            global.console.error('Workspace: could not load series', id);
          }
        });
    },

    removeSeries: function (id) {
      this.active.delete(id);
      if (typeof this.onChange === 'function') this.onChange();
    },

    clear: function () {
      this.active.clear();
      if (typeof this.onChange === 'function') this.onChange();
    },
  };

  function monthShort(m) {
    return ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m] || '';
  }

  function formatRangeShort(fromStr, toStr) {
    if (!fromStr || !toStr) return '';
    var d0 = new Date(fromStr + 'T12:00:00Z');
    var d1 = new Date(toStr + 'T12:00:00Z');
    var a = monthShort(d0.getUTCMonth()) + ' ' + d0.getUTCDate();
    var b = monthShort(d1.getUTCMonth()) + ' ' + d1.getUTCDate();
    var y0 = d0.getUTCFullYear();
    var y1 = d1.getUTCFullYear();
    if (y0 === y1) return a + '–' + b + ' ' + y1;
    return a + ' ' + y0 + '–' + b + ' ' + y1;
  }

  function mapToDayIndex(pts) {
    return pts.map(function (p, i) {
      return [i, p[1]];
    });
  }

  function primaryDatesForIndex(pts) {
    return pts.map(function (p) {
      var d = new Date(p[0]);
      return d.toISOString().slice(0, 10);
    });
  }

  function dateToPrimaryDayIndex(primaryPts, dateStr) {
    var t = ts(dateStr);
    for (var i = 0; i < primaryPts.length; i++) {
      if (Math.abs(primaryPts[i][0] - t) < 43200000) return i;
    }
    var ds = primaryDatesForIndex(primaryPts);
    return ds.indexOf(dateStr);
  }

  function dayIndexToApproxDate(fromStr, dayIndex) {
    var d = new Date((fromStr || '2000-01-01') + 'T12:00:00Z');
    d.setUTCDate(d.getUTCDate() + dayIndex);
    return d.toISOString().slice(0, 10);
  }

  function getAnomalyColor() {
    try {
      var v = global.getComputedStyle(global.document.documentElement).getPropertyValue('--anomaly');
      if (v && v.trim()) return v.trim();
    } catch (e) { /* ignore */ }
    return '#d4890a';
  }

  function deepMerge(a, b) {
    if (global.TerminalCharts && typeof global.TerminalCharts.deepMerge === 'function') {
      return global.TerminalCharts.deepMerge(a, b);
    }
    return Object.assign({}, a, b);
  }

  function terminalBaseClone() {
    var b = global.TERMINAL_CHART_BASE;
    if (!b) return {};
    return JSON.parse(JSON.stringify(b));
  }

  function buildSeriesPayload(entry, data, opt) {
    var c = entry.colour || entry.meta.colour;
    var dash = entry.lineStyle === 'dashed' ? [6, 4] : 'solid';
    var t = entry.chartType;
    var yi = opt.yAxisIndex || 0;
    var name = opt.name;
    var lineOpacity = opt.lineOpacity != null ? opt.lineOpacity : 1;
    var extraLine = { opacity: lineOpacity };

    if (t === 'scatter') {
      return {
        type: 'scatter',
        name: name,
        yAxisIndex: yi,
        data: data,
        symbolSize: 6,
        itemStyle: { color: c, opacity: lineOpacity },
        emphasis: { focus: 'series' },
      };
    }
    if (t === 'bar') {
      return {
        type: 'bar',
        name: name,
        yAxisIndex: yi,
        data: data,
        barMaxWidth: 14,
        itemStyle: { color: c, opacity: lineOpacity },
        emphasis: { focus: 'series' },
      };
    }
    if (t === 'area') {
      return {
        type: 'line',
        name: name,
        yAxisIndex: yi,
        data: data,
        smooth: 0.35,
        showSymbol: false,
        lineStyle: Object.assign({ width: 1.5, color: c, type: opt.forceDashed ? 'dashed' : dash }, extraLine),
        areaStyle: { color: c, opacity: 0.12 * lineOpacity },
        emphasis: { focus: 'series' },
      };
    }
    return {
      type: 'line',
      name: name,
      yAxisIndex: yi,
      data: data,
      smooth: 0.35,
      showSymbol: false,
      lineStyle: Object.assign(
        { width: 1.5, color: c, type: opt.forceDashed ? 'dashed' : dash },
        extraLine
      ),
      emphasis: { focus: 'series' },
    };
  }

  function buildWorkspaceOption(ctx) {
    var COL = getAnomalyColor();
    var sm = ctx.seriesManager;
    var dateFrom = ctx.dateFrom;
    var dateTo = ctx.dateTo;
    var dateFromB = ctx.dateFromB;
    var dateToB = ctx.dateToB;
    var compareOn = ctx.compareOn;
    var eventMarkers = ctx.eventMarkers || [];
    var refLines = ctx.refLines || [];

    var base = terminalBaseClone();
    var hasRight = false;
    sm.active.forEach(function (e) {
      if (e.yAxis === 'right') hasRight = true;
    });

    var yAxis = [
      {
        type: 'value',
        scale: true,
        position: 'left',
        axisLine: { lineStyle: { color: base.yAxis && base.yAxis.axisLine ? base.yAxis.axisLine.lineStyle.color : '#252820' } },
        axisLabel: {
          color: base.textStyle ? base.textStyle.color : '#8a9485',
          fontSize: 10,
          fontFamily: '"JetBrains Mono", ui-monospace, monospace',
        },
        splitLine: {
          lineStyle: { color: base.yAxis && base.yAxis.splitLine ? base.yAxis.splitLine.lineStyle.color : '#1c1f18' },
        },
      },
    ];
    if (hasRight) {
      yAxis.push({
        type: 'value',
        scale: true,
        position: 'right',
        axisLine: { lineStyle: { color: '#252820' } },
        axisLabel: {
          color: base.textStyle ? base.textStyle.color : '#8a9485',
          fontSize: 10,
          fontFamily: '"JetBrains Mono", ui-monospace, monospace',
        },
        splitLine: { show: false },
      });
    }

    var series = [];
    var markLineData = [];
    var firstPrimaryPts = null;

    sm.active.forEach(function (entry, id) {
      var priRaw = filterByDateRange(entry.raw, dateFrom, dateTo);
      if (!firstPrimaryPts && priRaw.length) firstPrimaryPts = priRaw;

      if (!compareOn) {
        var yi = entry.yAxis === 'right' && hasRight ? 1 : 0;
        var dataTime = priRaw;
        series.push(
          buildSeriesPayload(entry, dataTime, {
            name: entry.meta.label,
            yAxisIndex: yi,
            lineOpacity: 1,
          })
        );
      } else {
        var cmpRaw = filterByDateRange(entry.raw, dateFromB, dateToB);
        var idxPri = mapToDayIndex(priRaw);
        var idxCmp = mapToDayIndex(cmpRaw);
        var sufPri = formatRangeShort(dateFrom, dateTo);
        var sufCmp = formatRangeShort(dateFromB, dateToB);
        var yi2 = entry.yAxis === 'right' && hasRight ? 1 : 0;
        series.push(
          buildSeriesPayload(entry, idxPri, {
            name: entry.meta.label + ' (' + sufPri + ')',
            yAxisIndex: yi2,
            lineOpacity: 1,
            forceDashed: false,
          })
        );
        var cmpEntry =
          entry.chartType === 'bar'
            ? Object.assign({}, entry, { chartType: 'line' })
            : entry;
        series.push(
          buildSeriesPayload(cmpEntry, idxCmp, {
            name: entry.meta.label + ' (' + sufCmp + ')',
            yAxisIndex: yi2,
            lineOpacity: 0.5,
            forceDashed: true,
          })
        );
      }
    });

    var xAxis;
    if (!compareOn) {
      xAxis = {
        type: 'time',
        axisLine: { lineStyle: { color: '#252820' } },
        axisLabel: {
          color: base.textStyle ? base.textStyle.color : '#8a9485',
          fontSize: 10,
          fontFamily: '"JetBrains Mono", ui-monospace, monospace',
        },
        splitLine: { show: false },
      };
      eventMarkers.forEach(function (m) {
        if (!m.date) return;
        var tx = ts(m.date);
        if (!isFinite(tx)) return;
        markLineData.push({
          xAxis: tx,
          lineStyle: { color: COL, type: 'dashed', width: 1 },
          label: {
            show: true,
            position: 'insideEndTop',
            formatter: m.label || '',
            color: COL,
            fontSize: 10,
            fontFamily: '"IBM Plex Sans", system-ui, sans-serif',
          },
        });
      });
    } else {
      var maxX = 0;
      sm.active.forEach(function (entry) {
        var a = filterByDateRange(entry.raw, dateFrom, dateTo).length;
        var b = filterByDateRange(entry.raw, dateFromB, dateToB).length;
        maxX = Math.max(maxX, a, b);
      });
      maxX = Math.max(maxX - 1, 0);
      xAxis = {
        type: 'value',
        min: 0,
        max: maxX,
        axisLine: { lineStyle: { color: '#252820' } },
        axisLabel: {
          color: base.textStyle ? base.textStyle.color : '#8a9485',
          fontSize: 10,
          fontFamily: '"JetBrains Mono", ui-monospace, monospace',
          formatter: function (v) {
            var n = Math.round(v);
            return Math.abs(v - n) < 0.05 ? 'd' + n : '';
          },
        },
        splitLine: { show: false },
      };
      if (firstPrimaryPts && firstPrimaryPts.length) {
        eventMarkers.forEach(function (m) {
          var di = dateToPrimaryDayIndex(firstPrimaryPts, m.date);
          if (di < 0) return;
          markLineData.push({
            xAxis: di,
            lineStyle: { color: COL, type: 'dashed', width: 1 },
            label: {
              show: true,
              position: 'insideEndTop',
              formatter: m.label || '',
              color: COL,
              fontSize: 10,
              fontFamily: '"IBM Plex Sans", system-ui, sans-serif',
            },
          });
        });
      }
    }

    refLines.forEach(function (r) {
      markLineData.push({
        yAxis: r.yValue,
        lineStyle: { color: r.colour || '#94a3b8', type: 'solid', width: 1 },
        label: {
          show: true,
          formatter: r.label || 'Ref',
          position: 'end',
          color: r.colour || '#94a3b8',
          fontSize: 10,
          fontFamily: '"IBM Plex Sans", system-ui, sans-serif',
        },
      });
    });

    if (markLineData.length) {
      if (!series.length) {
        var ghostData = compareOn ? [[0, 0], [1, 0]] : [];
        series.push({
          type: 'line',
          name: '_workspace',
          data: ghostData,
          showSymbol: false,
          lineStyle: { width: 0, opacity: 0 },
          silent: true,
          tooltip: { show: false },
          legendHoverLink: false,
          showInLegend: false,
        });
      }
      series[0].markLine = {
        symbol: 'none',
        animation: false,
        data: markLineData,
      };
    }

    var bxTooltip = base.tooltip || {};
    var visibleSeries = series.filter(function (s) {
      return s.showInLegend !== false;
    });
    var showLegend =
      (compareOn && visibleSeries.length > 0) || (!compareOn && visibleSeries.length > 1);

    var opt = deepMerge(base, {
      toolbox: { show: false },
      backgroundColor: base.backgroundColor || 'transparent',
      grid: { left: 56, right: hasRight ? 56 : 20, top: 44, bottom: 72, containLabel: true },
      dataZoom: [
        { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
        {
          type: 'slider',
          xAxisIndex: 0,
          height: 24,
          bottom: 10,
          borderColor: '#2e3228',
          fillerColor: 'rgba(61, 126, 255, 0.15)',
          handleStyle: { color: '#3d7eff' },
          textStyle: { color: '#8a9485', fontSize: 10 },
        },
      ],
      tooltip: deepMerge(bxTooltip, {
        trigger: 'axis',
        textStyle: {
          fontFamily: '"JetBrains Mono", ui-monospace, monospace',
          fontSize: 11,
        },
      }),
      legend: {
        show: showLegend,
        top: 4,
        right: 12,
        type: 'scroll',
        textStyle: {
          color: base.textStyle ? base.textStyle.color : '#8a9485',
          fontSize: 10,
          fontFamily: '"JetBrains Mono", ui-monospace, monospace',
        },
      },
      xAxis: xAxis,
      yAxis: yAxis,
      series: series,
    });

    opt.xAxis = xAxis;
    opt.yAxis = yAxis;
    opt.series = series;

    return opt;
  }

  function loadJsonLs(key, fallback) {
    try {
      var s = global.localStorage.getItem(key);
      if (!s) return fallback;
      var j = JSON.parse(s);
      return Array.isArray(j) ? j : fallback;
    } catch (e) {
      if (global.console && global.console.error) {
        global.console.error('[Workspace] Failed to parse localStorage key ' + key + ':', e);
      }
      try {
        global.localStorage.removeItem(key);
      } catch (e2) { /* ignore */ }
      return fallback;
    }
  }

  function saveJsonLs(key, arr) {
    try {
      global.localStorage.setItem(key, JSON.stringify(arr));
    } catch (e2) { /* ignore */ }
  }

  function init(opts) {
    var chart = global.TerminalCharts ? global.TerminalCharts.init(opts.chartEl) : global.echarts.init(opts.chartEl);
    if (!chart) return null;

    var catalog = (global.FXRLChartBuilder && global.FXRLChartBuilder.DATA_CATALOG) || { categories: [] };
    WorkspaceSeriesManager.bindCatalog(catalog);

    var latestDateStr = '';
    var dateFrom = '';
    var dateTo = '';
    var dateFromB = '';
    var dateToB = '';
    var compareOn = false;
    var eventMarkers = loadJsonLs(LS_MARKERS, []);
    var refLines = loadJsonLs(LS_REFLINES, []);
    var waitingMarker = false;
    var waitingRefLine = false;
    var dragRef = { index: -1 };

    function persistMarkers() {
      saveJsonLs(LS_MARKERS, eventMarkers);
    }
    function persistRefLines() {
      saveJsonLs(LS_REFLINES, refLines);
    }

    function getCtx() {
      return {
        seriesManager: WorkspaceSeriesManager,
        dateFrom: dateFrom,
        dateTo: dateTo,
        dateFromB: dateFromB,
        dateToB: dateToB,
        compareOn: compareOn,
        eventMarkers: eventMarkers,
        refLines: refLines,
      };
    }

    function redraw() {
      chart.setOption(buildWorkspaceOption(getCtx()), true);
    }

    WorkspaceSeriesManager.onChange = redraw;

    function setShortcutMonths(m) {
      if (!latestDateStr) return;
      dateTo = latestDateStr;
      var d = new Date(latestDateStr + 'T12:00:00Z');
      d.setUTCMonth(d.getUTCMonth() - m);
      dateFrom = d.toISOString().slice(0, 10);
      if (opts.onDatesChange) opts.onDatesChange();
      redraw();
    }

    function setShortcutDays(days) {
      if (!latestDateStr) return;
      dateTo = latestDateStr;
      var d = new Date(latestDateStr + 'T12:00:00Z');
      d.setUTCDate(d.getUTCDate() - days);
      dateFrom = d.toISOString().slice(0, 10);
      if (opts.onDatesChange) opts.onDatesChange();
      redraw();
    }

    fetchCsv(MASTER_CSV)
      .then(function (text) {
        var p = parseCsv(text);
        if (p.rows.length) {
          latestDateStr = p.rows[p.rows.length - 1].date || '';
          dateTo = latestDateStr;
          var d = new Date(latestDateStr + 'T12:00:00Z');
          d.setUTCMonth(d.getUTCMonth() - 12);
          dateFrom = d.toISOString().slice(0, 10);
          dateToB = latestDateStr;
          var d2 = new Date(latestDateStr + 'T12:00:00Z');
          d2.setUTCMonth(d2.getUTCMonth() - 6);
          dateFromB = d2.toISOString().slice(0, 10);
          if (opts.tsEl) {
            opts.tsEl.textContent = latestDateStr ? 'As of ' + latestDateStr + ' · CSV' : 'Pipeline —';
          }
          if (opts.onDatesChange) opts.onDatesChange();
        }
      })
      .catch(function () {
        if (opts.tsEl) opts.tsEl.textContent = 'No CSV — run pipeline locally';
      })
      .finally(function () {
        redraw();
      });

    var zr = chart.getZr();

    function anchorXForGrid() {
      if (compareOn) return 0;
      var t0 = NaN;
      WorkspaceSeriesManager.active.forEach(function (entry) {
        var pri = filterByDateRange(entry.raw, dateFrom, dateTo);
        if (pri.length) {
          var mid = pri[Math.floor(pri.length / 2)][0];
          if (!isFinite(t0)) t0 = mid;
        }
      });
      return isFinite(t0) ? t0 : Date.now();
    }

    function gridFromPixel(x, y) {
      try {
        return chart.convertFromPixel({ gridIndex: 0 }, [x, y]);
      } catch (e) {
        return null;
      }
    }

    function findRefLineAt(x, y) {
      var xa = anchorXForGrid();
      for (var i = 0; i < refLines.length; i++) {
        try {
          var py = chart.convertToPixel({ gridIndex: 0 }, [xa, refLines[i].yValue]);
          if (py && Math.abs(y - py[1]) < 10) return i;
        } catch (e2) { /* ignore */ }
      }
      return -1;
    }

    zr.on('mousedown', function (e) {
      if (dragRef.index >= 0) return;
      var idx = findRefLineAt(e.offsetX, e.offsetY);
      if (idx < 0) return;
      dragRef.index = idx;
      var ev = e.event;
      if (ev) {
        ev.preventDefault();
        ev.stopPropagation();
      }
    });

    global.addEventListener('mousemove', function (ev) {
      if (dragRef.index < 0) return;
      var rect = opts.chartEl.getBoundingClientRect();
      var x = ev.clientX - rect.left;
      var y = ev.clientY - rect.top;
      var g = gridFromPixel(x, y);
      if (g && isFinite(g[1])) {
        refLines[dragRef.index].yValue = g[1];
        redraw();
      }
    });

    global.addEventListener('mouseup', function () {
      if (dragRef.index >= 0) {
        persistRefLines();
        dragRef.index = -1;
      }
    });

    zr.on('contextmenu', function (e) {
      var idx = findRefLineAt(e.offsetX, e.offsetY);
      if (idx < 0) return;
      var ev = e.event;
      if (ev) ev.preventDefault();
      refLines.splice(idx, 1);
      persistRefLines();
      redraw();
    });

    zr.on('click', function (e) {
      if (dragRef.index >= 0) return;
      if (!waitingMarker) return;
      var g = gridFromPixel(e.offsetX, e.offsetY);
      if (!g) return;
      var dateStr;
      if (compareOn) {
        var di = Math.round(g[0]);
        if (di < 0) return;
        dateStr = dayIndexToApproxDate(dateFrom, di);
      } else {
        var t = g[0];
        if (!isFinite(t)) return;
        dateStr = new Date(t).toISOString().slice(0, 10);
      }
      var lab = global.prompt('Marker label (max 20 characters):', '') || '';
      lab = String(lab).slice(0, 20);
      eventMarkers.push({ date: dateStr, label: lab });
      persistMarkers();
      waitingMarker = false;
      if (opts.onModeChange) opts.onModeChange();
      redraw();
    });

    function setWaitingMarker(on) {
      waitingMarker = !!on;
      if (waitingMarker) waitingRefLine = false;
      if (opts.onModeChange) opts.onModeChange();
      opts.chartEl.style.cursor = waitingMarker ? 'crosshair' : '';
    }

    function setWaitingRefLine(on) {
      waitingRefLine = !!on;
      if (waitingRefLine) waitingMarker = false;
      if (opts.onModeChange) opts.onModeChange();
    }

    function addReferenceLine() {
      var firstRaw = [];
      WorkspaceSeriesManager.active.forEach(function (entry) {
        if (!firstRaw.length) firstRaw = entry.raw;
      });
      var g0 = filterByDateRange(firstRaw, dateFrom, dateTo);
      var ys = [];
      for (var i = 0; i < g0.length; i++) {
        if (isFinite(g0[i][1])) ys.push(g0[i][1]);
      }
      var yVal = ys.length ? ys.reduce(function (a, b) {
        return a + b;
      }, 0) / ys.length : 0;
      var lab = global.prompt('Reference line label (optional):', 'Ref') || 'Ref';
      lab = String(lab).slice(0, 24);
      refLines.push({ yValue: yVal, label: lab, colour: '#94a3b8' });
      persistRefLines();
      setWaitingRefLine(false);
      redraw();
    }

    /** @type {ResizeObserver | null} */
    var ro = null;
    if (global.ResizeObserver) {
      ro = new global.ResizeObserver(function () {
        chart.resize();
      });
      ro.observe(opts.chartEl);
    }

    return {
      chart: chart,
      seriesManager: WorkspaceSeriesManager,
      redraw: redraw,
      getLatestDate: function () {
        return latestDateStr;
      },
      getDates: function () {
        return {
          from: dateFrom,
          to: dateTo,
          fromB: dateFromB,
          toB: dateToB,
          compare: compareOn,
        };
      },
      setDates: function (a) {
        if (a.from != null) dateFrom = a.from;
        if (a.to != null) dateTo = a.to;
        if (a.fromB != null) dateFromB = a.fromB;
        if (a.toB != null) dateToB = a.toB;
        redraw();
      },
      setCompare: function (on) {
        compareOn = !!on;
        redraw();
      },
      setShortcutMonths: setShortcutMonths,
      setShortcutDays: setShortcutDays,
      setWaitingMarker: setWaitingMarker,
      addReferenceLine: addReferenceLine,
      isWaitingMarker: function () {
        return waitingMarker;
      },
      getMarkers: function () {
        return eventMarkers;
      },
      getRefLines: function () {
        return refLines;
      },
      destroy: function () {
        if (ro) ro.disconnect();
      },
    };
  }

  global.FXRLWorkspace = {
    init: init,
    WorkspaceSeriesManager: WorkspaceSeriesManager,
    buildWorkspaceOption: buildWorkspaceOption,
    LS_MARKERS: LS_MARKERS,
    LS_REFLINES: LS_REFLINES,
  };
})(typeof window !== 'undefined' ? window : this);
