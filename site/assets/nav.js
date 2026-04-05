/**
 * Shared nav: mobile menu + active link from path (UI v2).
 */
(function () {
  'use strict';

  var toggle = document.querySelector('[data-nav-toggle]');
  var overlay = document.querySelector('[data-nav-overlay]');

  function normalizePath(value) {
    var p = (value || '/').replace(/\/+$/, '') || '/';
    if (p === '/brief/index.html' || p === '/brief/latest.html') return '/brief';
    if (p === '/terminal/index.html') return '/terminal';
    return p;
  }

  var path = normalizePath(window.location.pathname || '/');

  document.querySelectorAll('[data-nav-root] a[data-path]').forEach(function (a) {
    var p = a.getAttribute('data-path');
    if (!p) return;
    var pNorm = normalizePath(p);
    var active = path === pNorm || (pNorm !== '/' && path.indexOf(pNorm + '/') === 0);
    if (active) a.classList.add('is-active');
  });

  function close() {
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('nav-open');
  }

  function open() {
    if (toggle) toggle.setAttribute('aria-expanded', 'true');
    document.body.classList.add('nav-open');
  }

  if (toggle && overlay) {
    toggle.addEventListener('click', function () {
      if (document.body.classList.contains('nav-open')) close();
      else open();
    });
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) close();
    });
    overlay.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', close);
    });
  }

  var navRoot = document.querySelector('[data-nav-root]');
  if (navRoot) {
    var ticking = false;
    function syncNavScroll() {
      ticking = false;
      if (window.scrollY > 80) navRoot.classList.add('nav-scrolled');
      else navRoot.classList.remove('nav-scrolled');
    }
    function onScrollNav() {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(syncNavScroll);
      }
    }
    window.addEventListener('scroll', onScrollNav, { passive: true });
    syncNavScroll();
  }
})();
