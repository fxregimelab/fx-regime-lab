/**
 * Shared nav: mobile menu + active link from path (UI v2) + Research dropdown.
 */
(function () {
  'use strict';

  var toggle = document.querySelector('[data-nav-toggle]');
  var overlay = document.querySelector('[data-nav-overlay]');

  function normalizePath(value) {
    var p = (value || '/').replace(/\/+$/, '') || '/';
    if (p === '/brief/index.html' || p === '/brief/latest.html') return '/brief';
    if (p === '/terminal/index.html') return '/terminal';
    if (p === '/terminal/overview.html') return '/terminal/overview';
    if (p === '/newsletter/index.html') return '/newsletter';
    return p;
  }

  var path = normalizePath(window.location.pathname || '/');

  document.querySelectorAll('[data-nav-root] a[data-path]').forEach(function (a) {
    if (a.closest('.v2-nav__dropdown')) return;
    var p = a.getAttribute('data-path');
    if (!p) return;
    var pNorm = normalizePath(p);
    var active = path === pNorm || (pNorm !== '/' && path.indexOf(pNorm + '/') === 0);
    if (active) a.classList.add('is-active');
  });

  function researchSectionActive(p) {
    if (p.indexOf('/dashboard') === 0) return true;
    if (p.indexOf('/performance') === 0) return true;
    if (p.indexOf('/methodology') === 0) return true;
    if (p.indexOf('/newsletter') === 0) return true;
    if (p === '/terminal/overview' || p.indexOf('/terminal/overview/') === 0) return true;
    return false;
  }

  document.querySelectorAll('[data-nav-research-trigger]').forEach(function (btn) {
    if (researchSectionActive(path)) btn.classList.add('is-active');
  });

  function closeOverlayResearch() {
    document.querySelectorAll('[data-nav-overlay-subs]').forEach(function (el) {
      el.classList.remove('is-open');
      el.setAttribute('hidden', '');
    });
    document.querySelectorAll('[data-nav-overlay-research-trigger]').forEach(function (b) {
      b.setAttribute('aria-expanded', 'false');
    });
  }

  function close() {
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('nav-open');
    closeOverlayResearch();
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

  var overlayResearchBtn = document.querySelector('[data-nav-overlay-research-trigger]');
  var overlaySubs = document.querySelector('[data-nav-overlay-subs]');
  if (overlayResearchBtn && overlaySubs) {
    overlayResearchBtn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var openNow = !overlaySubs.classList.contains('is-open');
      if (openNow) {
        overlaySubs.classList.add('is-open');
        overlaySubs.removeAttribute('hidden');
      } else {
        overlaySubs.classList.remove('is-open');
        overlaySubs.setAttribute('hidden', '');
      }
      overlayResearchBtn.setAttribute('aria-expanded', openNow ? 'true' : 'false');
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
