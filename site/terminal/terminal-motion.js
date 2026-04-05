(function (global) {
  'use strict';

  function parseNumericParts(text) {
    var raw = String(text || '').trim();
    var m = raw.match(/(-?\d+(?:\.\d+)?)/);
    if (!m) return null;
    var num = parseFloat(m[1]);
    if (!isFinite(num)) return null;
    return {
      value: num,
      prefix: raw.slice(0, m.index),
      suffix: raw.slice(m.index + m[1].length),
      decimals: (m[1].split('.')[1] || '').length,
    };
  }

  function easeOut(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function animateNode(node, duration) {
    if (!node || node.dataset.motionDone === '1') return;
    var parsed = parseNumericParts(node.textContent);
    if (!parsed) return;
    node.dataset.motionDone = '1';

    var start = performance.now();
    function frame(now) {
      var p = Math.min(1, (now - start) / duration);
      var eased = easeOut(p);
      var current = parsed.value * eased;
      var rendered = parsed.decimals > 0 ? current.toFixed(parsed.decimals) : String(Math.round(current));
      node.textContent = parsed.prefix + rendered + parsed.suffix;
      if (p < 1) requestAnimationFrame(frame);
      else node.textContent = parsed.prefix + (parsed.decimals > 0 ? parsed.value.toFixed(parsed.decimals) : String(Math.round(parsed.value))) + parsed.suffix;
    }
    requestAnimationFrame(frame);
  }

  function animateNumbers(root) {
    var scope = root || document;
    var selectors = [
      '.term-card__confidence',
      '.term-pair-head__spot',
      '.term-pair-head__score',
      '.term-pair-head__d1',
      '.term-acc__data-val',
      '.term-acc__data-meta',
      '#term-panel-confidence',
      '#term-panel-spot',
    ];
    scope.querySelectorAll(selectors.join(',')).forEach(function (node) {
      animateNode(node, 600);
    });
  }

  function initSectionEntrance() {
    var sections = document.querySelectorAll('.term-magazine-section');
    if (!sections.length) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-inview');
        io.unobserve(entry.target);
      });
    }, { threshold: 0.2 });
    sections.forEach(function (section) {
      io.observe(section);
    });
  }

  function initStickyHead() {
    var head = document.querySelector('.term-pair-head');
    var hero = document.querySelector('#pair-hero');
    if (!head || !hero) return;
    var threshold = hero.offsetHeight * 0.4;
    var onScroll = function () {
      if (global.scrollY > threshold) head.classList.add('is-compact');
      else head.classList.remove('is-compact');
    };
    onScroll();
    global.addEventListener('scroll', onScroll, { passive: true });
  }

  function initWillChangeCleanup() {
    document.addEventListener('transitionend', function (event) {
      var target = event.target;
      if (!target || !target.classList) return;
      if (
        target.classList.contains('term-card') ||
        target.classList.contains('term-regime-card') ||
        target.classList.contains('term-panel') ||
        target.classList.contains('term-slide-panel') ||
        target.classList.contains('term-magazine-section') ||
        target.classList.contains('term-section')
      ) {
        target.style.willChange = 'auto';
      }
    });
  }

  function initPageMotion(root) {
    initWillChangeCleanup();
    initSectionEntrance();
    initStickyHead();
    animateNumbers(root || document);
  }

  document.addEventListener('DOMContentLoaded', function () {
    initPageMotion(document);
  });

  global.FXRLTerminalMotion = {
    animateNumbers: animateNumbers,
    initPageMotion: initPageMotion,
  };
})(typeof window !== 'undefined' ? window : this);
