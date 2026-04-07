/**
 * PARITY: This file is shared across eurusd.html, usdjpy.html, usdinr.html.
 * Row IDs differ per pair but accordion behaviour is identical. Do not add
 * pair-specific logic here — put it in the pair HTML instead.
 *
 * Terminal pair pages — single-open accordion + lazy Lightweight Charts init.
 */
(function (global) {
  'use strict';

  function resizeRowChart(wrapper, mount) {
    if (!wrapper || !mount) return;
    var w = mount.clientWidth || 600;
    var h = mount.clientHeight || 260;
    if (typeof wrapper.resize === 'function') {
      try {
        wrapper.resize();
      } catch (e) {
        /* ignore */
      }
      return;
    }
    if (wrapper.chartTop && wrapper.chartBottom && typeof wrapper.chartTop.applyOptions === 'function') {
      var wrap = mount.firstElementChild;
      var topEl = wrap && wrap.children[0];
      var botEl = wrap && wrap.children[1];
      try {
        wrapper.chartTop.applyOptions({
          width: w,
          height: topEl ? topEl.clientHeight : Math.max(80, Math.floor(h * 0.55)),
        });
        wrapper.chartBottom.applyOptions({
          width: w,
          height: botEl ? botEl.clientHeight : Math.max(60, Math.floor(h * 0.45)),
        });
      } catch (e2) {
        /* ignore */
      }
      return;
    }
    if (wrapper.chart && typeof wrapper.chart.applyOptions === 'function') {
      try {
        wrapper.chart.applyOptions({ width: w, height: h });
      } catch (e3) {
        /* ignore */
      }
    }
  }

  var COLLAPSED_PX = 48;
  var EXPANDED_MAX_PX = 800;
  var EASE = 'ease-out';
  var DURATION_MS = 300;

  function forEachNode(list, fn) {
    Array.prototype.forEach.call(list, fn);
  }

  function setExpanded(row, expanded) {
    if (expanded) row.classList.add('is-expanded');
    else row.classList.remove('is-expanded');
  }

  function collapseAll(rows) {
    forEachNode(rows, function (row) {
      setExpanded(row, false);
      var b = row.querySelector('.term-acc__bar');
      var sh = row.querySelector('.term-acc__shell');
      if (b) b.setAttribute('aria-expanded', 'false');
      if (sh) sh.classList.remove('term-acc__shell--will-change');
    });
  }

  /**
   * @param {HTMLElement} container - root that contains all [data-term-acc-row]
   * @param {{ chartInits?: Record<string, (mount: HTMLElement, row: HTMLElement) => object|null> }} options
   */
  function init(container, options) {
    if (!container) return;
    options = options || {};
    var chartInits = options.chartInits || {};
    var rows = container.querySelectorAll('[data-term-acc-row]');

    forEachNode(rows, function (row) {
      var shell = row.querySelector('.term-acc__shell');
      var bar = row.querySelector('.term-acc__bar');
      if (!shell || !bar) return;

      if (!bar.hasAttribute('tabindex')) {
        bar.setAttribute('tabindex', '0');
      }

      shell.addEventListener('transitionend', function (e) {
        if (e.propertyName !== 'max-height') return;
        shell.classList.remove('term-acc__shell--will-change');
        if (row._chart) {
          resizeRowChart(row._chart, row.querySelector('.js-term-echart'));
        }
      });

      function onActivate() {
        var key = row.getAttribute('data-row-key') || '';
        var noChart = row.getAttribute('data-no-chart') === 'true';
        var mount = row.querySelector('.js-term-echart');
        if (noChart || !mount) return;

        if (row._chart) {
          resizeRowChart(row._chart, mount);
          return;
        }

        var factory = chartInits[key];
        if (typeof factory === 'function') {
          try {
            row._chart = factory(mount, row);
          } catch (err) {
            console.error('TerminalExpandableRows chart init failed:', key, err);
          }
        }
      }

      bar.addEventListener('click', function () {
        var wasOpen = row.classList.contains('is-expanded');
        collapseAll(rows);
        if (!wasOpen) {
          shell.classList.add('term-acc__shell--will-change');
          setExpanded(row, true);
          bar.setAttribute('aria-expanded', 'true');
          onActivate();
        }
      });

      bar.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          bar.click();
        }
      });
    });

    function collapseOpen() {
      var open = container.querySelector('[data-term-acc-row].is-expanded');
      if (!open) return;
      setExpanded(open, false);
      var b = open.querySelector('.term-acc__bar');
      var sh = open.querySelector('.term-acc__shell');
      if (b) b.setAttribute('aria-expanded', 'false');
      if (sh) sh.classList.remove('term-acc__shell--will-change');
    }

    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      if (!container.querySelector('.is-expanded')) return;
      collapseOpen();
    });
  }

  /**
   * Regime direction shading (EUR/USD price context). Checkbox + localStorage.
   * @param {HTMLElement} toolbarHost - where to prepend the control
   * @param {object} chart - chart wrapper (LWC) or legacy chart handle
   * @param {{ storageKey: string, apply: (chart: object, enabled: boolean) => void }} options
   */
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
        /* ignore apply errors */
      }
      if (chart && typeof chart.resize === 'function') {
        try {
          chart.resize();
        } catch (e) {
          /* ignore */
        }
      } else if (chart) {
        var row = toolbarHost.closest && toolbarHost.closest('[data-term-acc-row]');
        var m = row && row.querySelector('.js-term-echart');
        if (m) resizeRowChart(chart, m);
      }
    }

    input.addEventListener('change', function () {
      global.localStorage.setItem(key, input.checked ? 'true' : 'false');
      apply();
    });

    if (checked) apply();
  }

  global.TerminalExpandableRows = {
    init: init,
    attachRegimeZoneToggle: attachRegimeZoneToggle,
    COLLAPSED_PX: COLLAPSED_PX,
    EXPANDED_MAX_PX: EXPANDED_MAX_PX,
  };
})(typeof window !== 'undefined' ? window : this);
