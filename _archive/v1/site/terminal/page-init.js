/**
 * Shared terminal boot helpers: surface load failures without duplicating markup per page.
 */
(function (global) {
  'use strict';

  function ensureErrorHost() {
    var el = document.getElementById('term-page-error');
    if (!el) {
      el = document.createElement('div');
      el.id = 'term-page-error';
      el.setAttribute('hidden', '');
      el.setAttribute('role', 'alert');
      el.style.cssText =
        'margin:1rem;padding:1rem 1.25rem;border:1px solid rgba(148,158,136,0.35);border-radius:8px;background:rgba(17,20,15,0.95);color:#9aa894;font-size:14px;line-height:1.45;';
      var p0 = document.createElement('p');
      p0.className = 'term-page-error__text';
      p0.style.margin = '0';
      el.appendChild(p0);
      if (document.body) document.body.insertBefore(el, document.body.firstChild);
      return el;
    }
    /* Home terminal ships a bare #term-page-error (no text node); normalize so showPageError works. */
    if (!el.querySelector('.term-page-error__text')) {
      var p1 = document.createElement('p');
      p1.className = 'term-page-error__text';
      p1.style.margin = '0';
      el.appendChild(p1);
    }
    if (!el.getAttribute('role')) el.setAttribute('role', 'alert');
    return el;
  }

  function showPageError(message) {
    if (!document.body) return;
    var el = ensureErrorHost();
    el.removeAttribute('hidden');
    var p = el.querySelector('.term-page-error__text');
    if (p) p.textContent = message || 'Something went wrong.';
    /* Inline display:none (e.g. terminal home) stays hidden after removeAttribute('hidden'). */
    try {
      var win = el.ownerDocument && el.ownerDocument.defaultView;
      var cs = win && win.getComputedStyle ? win.getComputedStyle(el) : null;
      if ((cs && cs.display === 'none') || (el.style && String(el.style.display) === 'none')) {
        el.style.display = 'flex';
        el.style.flexDirection = 'column';
        el.style.alignItems = 'center';
        el.style.justifyContent = 'center';
        if (!String(el.style.minHeight || '').trim()) el.style.minHeight = '40vh';
      }
    } catch (_e) {
      el.style.display = 'flex';
    }
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
