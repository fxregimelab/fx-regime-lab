/**
 * Shared terminal boot helpers: surface load failures without duplicating markup per page.
 */
(function (global) {
  'use strict';

  function ensureErrorHost() {
    var el = document.getElementById('term-page-error');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'term-page-error';
    el.setAttribute('hidden', '');
    el.setAttribute('role', 'alert');
    el.style.cssText =
      'margin:1rem;padding:1rem 1.25rem;border:1px solid rgba(148,158,136,0.35);border-radius:8px;background:rgba(17,20,15,0.95);color:#9aa894;font-size:14px;line-height:1.45;';
    var p = document.createElement('p');
    p.className = 'term-page-error__text';
    p.style.margin = '0';
    el.appendChild(p);
    if (document.body) document.body.insertBefore(el, document.body.firstChild);
    return el;
  }

  function showPageError(message) {
    if (!document.body) return;
    var el = ensureErrorHost();
    el.removeAttribute('hidden');
    var p = el.querySelector('.term-page-error__text');
    if (p) p.textContent = message || 'Something went wrong.';
  }

  /**
   * @param {string} name
   * @param {() => unknown} fn
   * @returns {Promise<void>}
   */
  function safeInit(name, fn) {
    try {
      var r = fn();
      if (r && typeof r.then === 'function') {
        return r.catch(function (e) {
          if (typeof console !== 'undefined' && console.error) console.error('[Terminal]', name, e);
          showPageError(e && e.message ? e.message : 'Load failed');
        });
      }
      return Promise.resolve(r);
    } catch (e) {
      if (typeof console !== 'undefined' && console.error) console.error('[Terminal]', name, e);
      showPageError(e && e.message ? e.message : 'Load failed');
      return Promise.resolve();
    }
  }

  global.FXRLPageInit = {
    showPageError: showPageError,
    safeInit: safeInit,
  };
})(typeof window !== 'undefined' ? window : this);
