(function (global) {
  'use strict';

  function forEachNode(list, fn) {
    Array.prototype.forEach.call(list || [], fn);
  }

  function init(root, options) {
    if (!root) return;
    if (!global.echarts) {
      if (typeof document !== 'undefined') {
        document.addEventListener(
          'echarts-ready',
          function () {
            init(root, options);
          },
          { once: true }
        );
      }
      return;
    }
    options = options || {};
    var chartInits = options.chartInits || {};
    var sections = root.querySelectorAll('[data-row-key]');
    function seriesHasPoints(data) {
      return !!(data && data.length);
    }

    function markChartEmptyState(chart, mount) {
      if (!chart || !mount) return;
      var opt;
      try {
        opt = chart.getOption();
      } catch (_e) {
        return;
      }
      var series = opt && opt.series;
      if (!series || !series.length) return;
      var hasPoints = false;
      for (var i = 0; i < series.length; i++) {
        if (seriesHasPoints(series[i].data)) {
          hasPoints = true;
          break;
        }
      }
      var prev = mount.querySelector('.term-chart-empty-msg');
      if (hasPoints) {
        if (prev) prev.remove();
        mount.classList.remove('is-chart-empty');
        return;
      }
      mount.classList.add('is-chart-empty');
      if (prev) return;
      var p = document.createElement('p');
      p.className = 'term-chart-empty-msg';
      p.setAttribute('role', 'status');
      p.textContent =
        'No series in this range. Data follows the daily pipeline (~23:00 UTC); see methodology for definitions.';
      mount.appendChild(p);
    }

    function initChart(section) {
      if (!section || section._chart) return;
      var key = section.getAttribute('data-row-key') || '';
      var mount = section.querySelector('.js-term-echart');
      var noChart = section.getAttribute('data-no-chart') === 'true';
      if (noChart || !mount) return;

      var factory = chartInits[key];
      if (typeof factory !== 'function') return;
      try {
        var chart = factory(mount, section);
        if (!chart) return;
        markChartEmptyState(chart, mount);
        section._chart = chart;
        if (
          global.TerminalCharts &&
          typeof global.TerminalCharts.observeChartResize === 'function'
        ) {
          section._chartResizeObserver = global.TerminalCharts.observeChartResize(mount, chart);
        }
      } catch (err) {
        if (typeof console !== 'undefined' && console.error) {
          console.error('FXRLTerminalLazy chart init failed:', key, err);
        }
      }
    }

    function disposeChart(section) {
      if (!section || !section._chart) return;
      try {
        if (section._chartResizeObserver) {
          if (typeof section._chartResizeObserver._cancelFxrlResize === 'function') {
            section._chartResizeObserver._cancelFxrlResize();
          }
          if (typeof section._chartResizeObserver.disconnect === 'function') {
            section._chartResizeObserver.disconnect();
          }
        }
      } catch (_e) {
        /* ignore */
      }
      section._chartResizeObserver = null;
      try {
        if (typeof section._chart.dispose === 'function') {
          section._chart.dispose();
        }
      } catch (_e2) {
        /* ignore */
      }
      section._chart = null;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var section = entry.target;
        if (entry.isIntersecting) {
          section.classList.add('is-inview');
          initChart(section);
          return;
        }
        // Free memory when the section scrolls far outside viewport.
        disposeChart(section);
      });
    }, {
      root: null,
      threshold: 0.1,
      rootMargin: '-15% 0px -15% 0px',
    });

    forEachNode(sections, function (section) {
      io.observe(section);
    });
  }

  function attachRegimeZoneToggle(toolbarHost, chart, options) {
    if (!toolbarHost || !chart || !options || !options.storageKey || typeof options.apply !== 'function') return;
    var key = options.storageKey;
    var checked = global.localStorage.getItem(key) === 'true';

    var wrap = document.createElement('div');
    wrap.className = 'term-regime-toggle';
    wrap.innerHTML =
      '<label class="term-regime-toggle__label">' +
      '<input type="checkbox" class="term-regime-toggle__input" />' +
      '<span class="term-regime-toggle__text">Regime direction zone</span>' +
      '</label>';

    var input = wrap.querySelector('input');
    input.checked = checked;
    toolbarHost.insertBefore(wrap, toolbarHost.firstChild);

    function apply() {
      try {
        options.apply(chart, input.checked);
      } catch (e) {
        /* ignore */
      }
      try {
        global.localStorage.setItem(key, input.checked ? 'true' : 'false');
      } catch (e2) {
        /* ignore */
      }
    }

    input.addEventListener('change', apply);
    apply();
  }

  global.FXRLTerminalLazy = {
    init: init,
    attachRegimeZoneToggle: attachRegimeZoneToggle,
  };
})(typeof window !== 'undefined' ? window : this);
