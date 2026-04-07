(function (global) {
  'use strict';

  function forEachNode(list, fn) {
    Array.prototype.forEach.call(list || [], fn);
  }

  function markChartEmptyState(wrapper, mount) {
    if (!mount) return;
    var hasPoints = true;
    if (wrapper && typeof wrapper.getHasData === 'function') {
      hasPoints = !!wrapper.getHasData();
    } else if (wrapper && wrapper.hasData === false) {
      hasPoints = false;
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

  function disposeWrapper(wrapper) {
    if (!wrapper) return;
    try {
      if (typeof wrapper.dispose === 'function') {
        wrapper.dispose();
        return;
      }
      if (wrapper.chart && typeof wrapper.chart.remove === 'function') {
        wrapper.chart.remove();
      }
      if (wrapper.chartTop && typeof wrapper.chartTop.remove === 'function') {
        wrapper.chartTop.remove();
      }
      if (wrapper.chartBottom && typeof wrapper.chartBottom.remove === 'function') {
        wrapper.chartBottom.remove();
      }
      if (typeof wrapper.disposeExtra === 'function') {
        wrapper.disposeExtra();
      }
    } catch (_e) {
      /* ignore */
    }
  }

  function init(root, options) {
    if (!root) return;
    options = options || {};
    var chartInits = options.chartInits || {};
    var sections = root.querySelectorAll('[data-row-key]');

    function runFactory(section, mount, factory) {
      var result;
      try {
        result = factory(mount, section);
      } catch (err) {
        if (typeof console !== 'undefined' && console.error) {
          console.error('FXRLTerminalLazy chart init failed:', section.getAttribute('data-row-key'), err);
        }
        return;
      }
      var done = function (wrapper) {
        if (!section || !mount) return;
        section._chartLoading = false;
        markChartEmptyState(wrapper, mount);
        section._chart = wrapper;
      };
      if (result && typeof result.then === 'function') {
        section._chartLoading = true;
        result.then(done).catch(function (err) {
          section._chartLoading = false;
          if (typeof console !== 'undefined' && console.error) {
            console.error('FXRLTerminalLazy chart async failed:', section.getAttribute('data-row-key'), err);
          }
        });
      } else {
        done(result);
      }
    }

    function initChart(section) {
      if (!section || section._chart || section._chartLoading) return;
      var key = section.getAttribute('data-row-key') || '';
      var mount = section.querySelector('.js-term-echart');
      var noChart = section.getAttribute('data-no-chart') === 'true';
      if (noChart || !mount) return;

      var factory = chartInits[key];
      if (typeof factory !== 'function') return;

      if (!global.LightweightCharts) {
        if (typeof document !== 'undefined') {
          document.addEventListener(
            'lwc-ready',
            function () {
              initChart(section);
            },
            { once: true }
          );
        }
        return;
      }

      runFactory(section, mount, factory);
    }

    function disposeChart(section) {
      if (!section) return;
      section._chartLoading = false;
      if (!section._chart) return;
      disposeWrapper(section._chart);
      section._chart = null;
    }

    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          var section = entry.target;
          if (entry.isIntersecting) {
            section.classList.add('is-inview');
            initChart(section);
            return;
          }
          disposeChart(section);
        });
      },
      {
        root: null,
        threshold: 0.1,
        rootMargin: '-15% 0px -15% 0px',
      }
    );

    forEachNode(sections, function (section) {
      io.observe(section);
    });

    /* When an accordion bar is clicked/activated, init the section's chart
       if it hasn't been created yet (handles the case where the section
       was already intersecting but the panel was collapsed, giving the
       js-term-echart container zero dimensions). */
    forEachNode(root.querySelectorAll('.term-acc__bar'), function (bar) {
      function tryInit() {
        var section = bar.closest('[data-row-key]');
        if (section && !section._chart && !section._chartLoading) {
          setTimeout(function () { initChart(section); }, 80);
        }
      }
      bar.addEventListener('click', tryInit);
      bar.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') tryInit();
      });
    });
  }

  function attachRegimeZoneToggle(toolbarHost, chartWrapper, options) {
    if (!toolbarHost || !options || !options.storageKey || typeof options.apply !== 'function') return;
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
        options.apply(chartWrapper, input.checked);
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
