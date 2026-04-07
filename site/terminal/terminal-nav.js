/**
 * Terminal shell: exit control calls public theme reset then navigates home;
 * active tab from URL (data-path on .term-nav__tab).
 */
(function () {
  'use strict';

  var g = typeof window !== 'undefined' ? window : this;
  var WORDMARK_URL = '/assets/images/wordmark_without_bg.png';
  var LOGO_URL = '/assets/images/logo.png';
  /** Inline SVG if logo.png fails to load (same dimensions as previous placeholder). */
  var LOGO_SVG_FALLBACK =
    '<svg class="term-brand__mark" width="28" height="20" viewBox="0 0 28 20" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
    '<rect x="0" y="0" width="28" height="6" rx="1" fill="#4D8EFF"/>' +
    '<rect x="3" y="8" width="28" height="6" rx="1" fill="#F59E0B"/>' +
    '<rect x="6" y="16" width="28" height="4" rx="1" fill="#F87171"/>' +
    '</svg>';
  var WORDMARK_FALLBACK =
    "data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%22210%22%20height%3D%2222%22%3E%3Ctext%20x%3D%220%22%20y%3D%2216%22%20fill%3D%22%23e8ede8%22%20font-family%3D%22Inter%2Csystem-ui%2Csans-serif%22%20font-size%3D%2213%22%20font-weight%3D%22600%22%3EFX%20Regime%20Lab%3C/text%3E%3C/svg%3E";

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

  function initPairSubNav() {
    var subNav = document.querySelector('.term-pair-tabs');
    if (!subNav) return;
    var tabs = Array.prototype.slice.call(subNav.querySelectorAll('.term-pair-tabs__link[href^="#"]'));
    if (!tabs.length) return;
    var underline = subNav.querySelector('.term-pair-tabs__underline');

    function setActive(tab) {
      tabs.forEach(function (x) {
        x.classList.remove('is-active');
      });
      if (!tab) return;
      tab.classList.add('is-active');
      if (!underline) return;
      var navRect = subNav.getBoundingClientRect();
      var tabRect = tab.getBoundingClientRect();
      underline.style.left = tabRect.left - navRect.left + 'px';
      underline.style.width = tabRect.width + 'px';
    }

    function highlightSection(section) {
      if (!section) return;
      section.classList.remove('section-highlight');
      section.offsetHeight;
      section.classList.add('section-highlight');
      g.setTimeout(function () {
        section.classList.remove('section-highlight');
      }, 1500);
    }

    tabs.forEach(function (tab) {
      tab.addEventListener('click', function (e) {
        var href = tab.getAttribute('href') || '';
        if (!href || href.charAt(0) !== '#') return;
        var target = document.querySelector(href);
        if (!target) return;
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        setActive(tab);
        highlightSection(target);
      });
    });

    var byId = {};
    tabs.forEach(function (tab) {
      var href = tab.getAttribute('href') || '';
      byId[href.slice(1)] = tab;
    });

    var sectionIds = Object.keys(byId);
    var sections = sectionIds
      .map(function (id) {
        return document.getElementById(id);
      })
      .filter(Boolean);

    if (sections.length) {
      var io = new IntersectionObserver(
        function (entries) {
          var winner = null;
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            if (!winner || entry.intersectionRatio > winner.intersectionRatio) {
              winner = entry;
            }
          });
          if (!winner) return;
          var id = winner.target.getAttribute('id');
          if (id && byId[id]) setActive(byId[id]);
        },
        { threshold: [0.2, 0.4, 0.6], rootMargin: '-25% 0px -55% 0px' }
      );
      sections.forEach(function (section) {
        io.observe(section);
      });
    }

    g.addEventListener('resize', function () {
      var active = subNav.querySelector('.term-pair-tabs__link.is-active');
      if (active) setActive(active);
    });

    setActive(subNav.querySelector('.term-pair-tabs__link.is-active') || tabs[0]);
  }

  function hydrateLegacyWordmark() {
    var brand = document.querySelector('.term-nav__brand:not(.term-brand)');
    if (!brand) brand = document.querySelector('.term-nav__brand');
    if (!brand || brand.classList.contains('term-brand')) return;
    var img = brand.querySelector('img.term-nav__wordmark');
    if (!img) {
      img = document.createElement('img');
      img.className = 'term-nav__wordmark';
      img.alt = 'FX Regime Lab';
      brand.textContent = '';
      brand.appendChild(img);
    }
    img.onerror = function () {
      img.onerror = null;
      img.src = WORDMARK_FALLBACK;
    };
    if (!img.getAttribute('src')) {
      img.src = WORDMARK_URL;
    }
  }

  function renderBrand() {
    return (
      '<div style="display:flex;align-items:center;gap:10px">' +
      '<img class="term-brand__mark" src="' +
      LOGO_URL +
      '" alt="" width="28" height="20" loading="lazy" />' +
      '<span style="font-family:\'Inter\',sans-serif;font-size:13px;font-weight:700;letter-spacing:0.12em;color:#E8EDF2">FX REGIME LAB</span>' +
      '</div>'
    );
  }

  function hydrateTerminalBrand() {
    var brand = document.querySelector('.term-brand');
    if (!brand) {
      hydrateLegacyWordmark();
      return;
    }
    brand.innerHTML = renderBrand();
    var mark = brand.querySelector('img.term-brand__mark');
    if (mark) {
      mark.addEventListener(
        'error',
        function onLogoErr() {
          mark.removeEventListener('error', onLogoErr);
          mark.outerHTML = LOGO_SVG_FALLBACK;
        },
        false
      );
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    hydrateTerminalBrand();
    syncTabActive();
    initPairSubNav();
    document.querySelectorAll('a.term-nav__exit, a[data-term-exit]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        leaveTerminal();
      });
    });
  });
})();
