/**
 * Public site ↔ terminal theme bridge (session flag + body classes).
 */
(function (global) {
  'use strict';

  var KEY = 'fxrl_theme';
  // fxrl_theme is stored in sessionStorage (not localStorage) so each new tab
  // starts fresh on the public site (theme-light). Only the current tab
  // remembers terminal state on refresh. Intentional — do not change to localStorage.

  function enterTerminal() {
    document.body.classList.remove('theme-light');
    document.body.classList.add('theme-terminal');
    try {
      sessionStorage.setItem(KEY, 'terminal');
    } catch (e) {
      /* ignore */
    }
  }

  function exitTerminal() {
    document.body.classList.remove('theme-terminal');
    document.body.classList.add('theme-light');
    try {
      sessionStorage.removeItem(KEY);
    } catch (e2) {
      /* ignore */
    }
  }

  function isTerminalPath(pathname) {
    var p = pathname || global.location.pathname || '/';
    return p.indexOf('/terminal/') !== -1 || p === '/terminal';
  }

  function getThemeForPath(pathname) {
    return isTerminalPath(pathname) ? 'terminal' : 'light';
  }

  function applyFromUrl() {
    var theme = getThemeForPath(global.location.pathname);
    if (theme === 'terminal') {
      enterTerminal();
    } else {
      document.body.classList.remove('theme-terminal');
      document.body.classList.add('theme-light');
      try {
        sessionStorage.removeItem(KEY);
      } catch (e3) {
        /* ignore */
      }
    }
  }

  function onReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  onReady(applyFromUrl);

  global.FXRLThemeSwitch = {
    enterTerminal: enterTerminal,
    exitTerminal: exitTerminal,
    applyFromUrl: applyFromUrl,
    isTerminalPath: isTerminalPath,
    getThemeForPath: getThemeForPath,
  };

  global.enterTerminal = enterTerminal;
  global.exitTerminal = exitTerminal;
})(typeof window !== 'undefined' ? window : this);
