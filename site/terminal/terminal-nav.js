/**
 * Terminal shell: exit control calls public theme reset then navigates home;
 * active tab from URL (data-path on .term-nav__tab).
 */
(function () {
  'use strict';

  var g = typeof window !== 'undefined' ? window : this;

  function leaveTerminal() {
    if (g.FXRLThemeSwitch && typeof g.FXRLThemeSwitch.exitTerminal === 'function') {
      g.FXRLThemeSwitch.exitTerminal();
    } else {
      try {
        sessionStorage.removeItem('fxrl_theme');
      } catch (e) {
        /* ignore */
      }
      document.body.classList.remove('theme-terminal');
      document.body.classList.add('theme-light');
    }
    g.location.href = '/';
  }

  function syncTabActive() {
    var path = window.location.pathname || '/';
    var pathNorm = path.replace(/\.html$/i, '');
    var tabs = document.querySelectorAll('.term-nav__tab');
    for (var i = 0; i < tabs.length; i++) {
      var tab = tabs[i];
      var tabPath = tab.getAttribute('data-path');
      if (!tabPath) continue;
      var active = false;
      if (tabPath === '/terminal/index') {
        active =
          pathNorm === '/terminal' ||
          pathNorm === '/terminal/' ||
          /\/terminal\/index$/i.test(pathNorm);
      } else {
        active = pathNorm.indexOf(tabPath) !== -1;
      }
      if (active) tab.classList.add('is-active');
      else tab.classList.remove('is-active');
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    syncTabActive();
    document.querySelectorAll('a.term-nav__exit, a[data-term-exit]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        leaveTerminal();
      });
    });
  });
})();
