(function (global) {
  'use strict';

  function forEachNode(list, fn) {
    Array.prototype.forEach.call(list || [], fn);
  }

  function init(root, options) {
    if (!root) return;
    options = options || {};
    var chartInits = options.chartInits || {};
    var sections = root.querySelectorAll('[data-row-key]');
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
        if (section._chartResizeObserver && typeof section._chartResizeObserver.disconnect === 'function') {
          section._chartResizeObserver.disconnect();
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
      threshold: 0,
      rootMargin: '-50% 0px -50% 0px',
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
