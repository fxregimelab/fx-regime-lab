/**
 * Section reveal — IntersectionObserver (threshold 0.15).
 * Each target is revealed at most once (unobserve after intersect).
 */
(function () {
  'use strict';

  var reduce = typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function countUp(el, target, suffix, dur) {
    var start = performance.now();
    function tick(now) {
      var p = Math.min(1, (now - start) / dur);
      var ease = easeOutCubic(p);
      el.textContent = Math.round(target * ease) + (suffix || '');
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  function revealStatsNumbers(container) {
    container.querySelectorAll('.num[data-count]').forEach(function (nel) {
      var t = parseInt(nel.getAttribute('data-count'), 10);
      if (isNaN(t)) return;
      var suf = nel.getAttribute('data-suffix') || '';
      if (reduce) {
        nel.textContent = t + suf;
        return;
      }
      countUp(nel, t, suf, 800);
    });
  }

  if (reduce) {
    document.querySelectorAll('[data-reveal="headline"]').forEach(function (el) {
      el.classList.add('fx-reveal-init', 'fx-reveal-headline', 'fx-reveal-in');
    });
    document.querySelectorAll('[data-reveal="sub"]').forEach(function (el) {
      el.classList.add('fx-reveal-init', 'fx-reveal-sub', 'fx-reveal-in');
    });
    document.querySelectorAll('[data-reveal-stagger="cards"]').forEach(function (wrap) {
      Array.prototype.forEach.call(wrap.children, function (k) {
        k.classList.add('fx-reveal-init', 'fx-reveal-card', 'fx-reveal-in');
      });
    });
    document.querySelectorAll('[data-reveal-stagger="rows"]').forEach(function (tbody) {
      Array.prototype.forEach.call(tbody.querySelectorAll('tr'), function (r) {
        r.classList.add('fx-reveal-init', 'fx-reveal-tr', 'fx-reveal-in');
      });
    });
    document.querySelectorAll('[data-reveal="stats"]').forEach(function (box) {
      box.classList.add('fx-reveal-init', 'fx-reveal-stats-wrap', 'fx-reveal-in');
      revealStatsNumbers(box);
    });
    return;
  }

  function observeOnce(el, onIn) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          onIn(e.target);
          io.unobserve(e.target);
        });
      },
      { threshold: 0.15 }
    );
    io.observe(el);
  }

  document.querySelectorAll('[data-reveal="headline"]').forEach(function (el) {
    el.classList.add('fx-reveal-init', 'fx-reveal-headline');
    observeOnce(el, function (t) {
      requestAnimationFrame(function () {
        t.classList.add('fx-reveal-in');
      });
    });
  });

  document.querySelectorAll('[data-reveal="sub"]').forEach(function (el) {
    el.classList.add('fx-reveal-init', 'fx-reveal-sub');
    observeOnce(el, function (t) {
      requestAnimationFrame(function () {
        t.classList.add('fx-reveal-in');
      });
    });
  });

  document.querySelectorAll('[data-reveal-stagger="cards"]').forEach(function (wrap) {
    var kids = Array.prototype.slice.call(wrap.children);
    kids.forEach(function (k) {
      k.classList.add('fx-reveal-init', 'fx-reveal-card');
    });
    observeOnce(wrap, function () {
      kids.forEach(function (k, i) {
        setTimeout(function () {
          k.classList.add('fx-reveal-in');
        }, i * 120);
      });
    });
  });

  document.querySelectorAll('[data-reveal-stagger="rows"]').forEach(function (tbody) {
    var rows = tbody.querySelectorAll('tr');
    Array.prototype.forEach.call(rows, function (r) {
      r.classList.add('fx-reveal-init', 'fx-reveal-tr');
    });
    observeOnce(tbody, function () {
      Array.prototype.forEach.call(rows, function (r, i) {
        setTimeout(function () {
          r.classList.add('fx-reveal-in');
        }, i * 80);
      });
    });
  });

  document.querySelectorAll('[data-reveal="stats"]').forEach(function (box) {
    box.classList.add('fx-reveal-init', 'fx-reveal-stats-wrap');
    observeOnce(box, function (t) {
      requestAnimationFrame(function () {
        t.classList.add('fx-reveal-in');
      });
      setTimeout(function () {
        revealStatsNumbers(t);
      }, 350);
    });
  });
})();
