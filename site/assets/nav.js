/**
 * Shared nav: mobile menu + active link from path (UI v2).
 */
(function () {
  'use strict';

  var toggle = document.querySelector('[data-nav-toggle]');
  var overlay = document.querySelector('[data-nav-overlay]');
  var path = (window.location.pathname || '/').replace(/\/+$/, '') || '/';

  document.querySelectorAll('[data-nav-root] a[data-path]').forEach(function (a) {
    var p = a.getAttribute('data-path');
    if (!p) return;
    var active = path === p || (p !== '/' && path.indexOf(p + '/') === 0);
    if (active) a.classList.add('is-active');
  });

  function close() {
    if (overlay) overlay.classList.remove('is-open');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('nav-open');
  }

  function open() {
    if (overlay) overlay.classList.add('is-open');
    if (toggle) toggle.setAttribute('aria-expanded', 'true');
    document.body.classList.add('nav-open');
  }

  if (toggle && overlay) {
    toggle.addEventListener('click', function () {
      if (overlay.classList.contains('is-open')) close();
      else open();
    });
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) close();
    });
    overlay.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', close);
    });
  }
})();
