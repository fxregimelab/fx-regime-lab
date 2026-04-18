/**
 * FX Regime Lab — canvas background (UI v3).
 * Layers: pair lines, sine waves, legacy ambient dots, sparse data particles + connectors, static grid.
 * Section multiplier from [data-canvas-opacity]; readability band (left ~55%) dims motion to 8% alpha.
 * prefers-reduced-motion: static grid only.
 */
(function () {
  'use strict';

  var canvas = document.getElementById('fx-canvas-bg');
  if (!canvas) return;

  var ctx = canvas.getContext('2d');
  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var w = 0;
  var h = 0;
  var t0 = performance.now();
  var mobile =
    typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 768px)').matches;
  var reduceMotion =
    typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var dots = [];
  var lastDot = 0;
  var particles = [];
  var lastParticle = 0;

  var sectionMul = 1;
  var READ_BAND = 0.55;
  var READ_ALPHA = 0.08;

  var colors = {
    eur: 'rgba(37, 99, 168, 0.07)',
    jpy: 'rgba(184, 107, 42, 0.07)',
    inr: 'rgba(166, 48, 48, 0.07)',
    navy: 'rgba(27, 58, 107, 0.05)',
    dotEur: 'rgba(37, 99, 168, 0.3)',
    dotJpy: 'rgba(184, 107, 42, 0.3)',
    dotInr: 'rgba(166, 48, 48, 0.3)',
    particleEur: 'rgba(37, 99, 168, 0.5)',
    particleJpy: 'rgba(184, 107, 42, 0.5)',
    particleInr: 'rgba(166, 48, 48, 0.5)',
  };

  var particlePalette = [colors.particleEur, colors.particleJpy, colors.particleInr];

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    mobile =
      typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 768px)').matches;
    w = window.innerWidth;
    h = Math.max(document.documentElement.scrollHeight, window.innerHeight);
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function smoothY(base, x, phase, amp) {
    return base + Math.sin(x * 0.004 + phase) * amp + Math.sin(x * 0.0017 + phase * 0.5) * (amp * 0.4);
  }

  function lineYAt(L, xWorld, now) {
    var sec = (now - t0) / 1000;
    var speed = w / 28;
    var offset = (sec * speed) % w;
    var bases = [h * 0.35, h * 0.42, h * 0.5];
    return smoothY(bases[L], xWorld + offset, sec * 0.15 + L, 22 + L * 6);
  }

  function nearestLinePoint(px, py, now) {
    var bestD2 = Infinity;
    var best = { x: px, y: py };
    var x0 = Math.max(0, px - 120);
    var x1 = Math.min(w, px + 120);
    for (var L = 0; L < 3; L++) {
      for (var x = x0; x <= x1; x += 4) {
        var ly = lineYAt(L, x, now);
        var dx = x - px;
        var dy = ly - py;
        var d2 = dx * dx + dy * dy;
        if (d2 < bestD2) {
          bestD2 = d2;
          best.x = x;
          best.y = ly;
        }
      }
    }
    return best;
  }

  function drawStaticGrid() {
    ctx.strokeStyle = 'rgba(27, 58, 107, 0.05)';
    ctx.lineWidth = 1;
    for (var y = 0; y < h; y += 80) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
  }

  function drawLinesInClip(now, x0, x1, alphaScale) {
    var sec = (now - t0) / 1000;
    var speed = w / 28;
    var offset = (sec * speed) % w;
    ctx.save();
    ctx.beginPath();
    ctx.rect(x0, 0, x1 - x0, h);
    ctx.clip();
    ctx.globalAlpha = alphaScale * sectionMul;
    ctx.lineWidth = 1.5;
    var bases = [h * 0.35, h * 0.42, h * 0.5];
    var lineColors = [colors.eur, colors.jpy, colors.inr];
    for (var L = 0; L < 3; L++) {
      ctx.beginPath();
      var col = mobile ? lineColors[L].replace('0.07', '0.035') : lineColors[L];
      ctx.strokeStyle = col;
      for (var x = -offset; x < w + 40; x += 6) {
        var y = smoothY(bases[L], x + offset, sec * 0.15 + L, 22 + L * 6);
        if (x === -offset) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawWavesInClip(now, x0, x1, alphaScale) {
    if (mobile) return;
    var sec = (now - t0) / 1000;
    ctx.save();
    ctx.beginPath();
    ctx.rect(x0, 0, x1 - x0, h);
    ctx.clip();
    ctx.globalAlpha = alphaScale * sectionMul;
    ctx.strokeStyle = colors.navy;
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (var x = 0; x < w; x += 4) {
      var y = h * 0.62 + Math.sin(x * 0.012 + sec * 1.8) * 18 + Math.sin(x * 0.005 + sec * 0.9) * 10;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.beginPath();
    for (var x2 = 0; x2 < w; x2 += 4) {
      var y2 = h * 0.7 + Math.sin(x2 * 0.01 - sec * 1.4) * 14;
      if (x2 === 0) ctx.moveTo(x2, y2);
      else ctx.lineTo(x2, y2);
    }
    ctx.stroke();
    ctx.restore();
  }

  function spawnDot() {
    dots.push({
      x: Math.random() * w,
      y: Math.random() * h * 0.85,
      r: 2,
      life: 1,
      c: [colors.dotEur, colors.dotJpy, colors.dotInr][(Math.random() * 3) | 0],
    });
  }

  function drawDotsInClip(now, x0, x1, alphaScale) {
    if (mobile) return;
    if (now - lastDot > 2000) {
      spawnDot();
      lastDot = now;
    }
    ctx.save();
    ctx.beginPath();
    ctx.rect(x0, 0, x1 - x0, h);
    ctx.clip();
    ctx.globalAlpha = alphaScale * sectionMul;
    for (var i = dots.length - 1; i >= 0; i--) {
      var d = dots[i];
      d.life -= 0.008;
      if (d.life <= 0) {
        dots.splice(i, 1);
        continue;
      }
      ctx.fillStyle = d.c.replace('0.3', String(0.35 * d.life));
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function spawnParticle() {
    particles.push({
      x: Math.random() * w,
      y: Math.random() * h * 0.92,
      born: performance.now(),
      c: particlePalette[(Math.random() * 3) | 0],
    });
  }

  function drawParticles(now) {
    if (mobile) return;
    if (now - lastParticle > 800) {
      spawnParticle();
      lastParticle = now;
    }
    var i;
    for (i = particles.length - 1; i >= 0; i--) {
      var p = particles[i];
      var age = now - p.born;
      if (age > 1500) {
        particles.splice(i, 1);
        continue;
      }
      var life = 1 - age / 1500;
      var nx = nearestLinePoint(p.x, p.y, now);
      var bandLeft = p.x < w * READ_BAND;
      var pa = (bandLeft ? READ_ALPHA : 1) * sectionMul * life;

      ctx.save();
      if (age < 300) {
        ctx.strokeStyle = p.c.replace('0.5', String(0.35 * (1 - age / 300)));
        ctx.lineWidth = 1;
        ctx.globalAlpha = pa;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(nx.x, nx.y);
        ctx.stroke();
      }
      ctx.globalAlpha = pa;
      ctx.fillStyle = p.c;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 1.25, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }

  function drawMotionLayers(now) {
    var split = w * READ_BAND;
    drawLinesInClip(now, 0, split, READ_ALPHA);
    drawLinesInClip(now, split, w, 1);
    drawWavesInClip(now, 0, split, READ_ALPHA);
    drawWavesInClip(now, split, w, 1);
    drawDotsInClip(now, 0, split, READ_ALPHA);
    drawDotsInClip(now, split, w, 1);
    drawParticles(now);
  }

  var rafId = null;
  function introActive() {
    var body = document.body;
    return !!(body && body.classList.contains('intro-active'));
  }

  function frame(now) {
    ctx.clearRect(0, 0, w, h);
    drawMotionLayers(now);
    drawStaticGrid();
    rafId = requestAnimationFrame(frame);
  }

  function stopLoop() {
    if (rafId != null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function startLoop() {
    if (reduceMotion || rafId != null || introActive()) return;
    rafId = requestAnimationFrame(frame);
  }

  function syncIntroPause() {
    if (introActive()) {
      stopLoop();
      ctx.clearRect(0, 0, w, h);
      drawStaticGrid();
      return;
    }
    if (!document.hidden && !reduceMotion) startLoop();
  }

  function wireSectionOpacity() {
    var els = document.querySelectorAll('[data-canvas-opacity]');
    if (!els.length) return;
    var ratios = [];
    function update() {
      var best = 1;
      var maxR = 0;
      for (var i = 0; i < els.length; i++) {
        var el = els[i];
        var want = parseFloat(el.getAttribute('data-canvas-opacity') || '1');
        if (isNaN(want)) want = 1;
        var r = ratios[i] || 0;
        if (r > maxR) {
          maxR = r;
          best = want;
        }
      }
      if (maxR < 0.05) best = 1;
      sectionMul = best;
    }
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          var idx = e.target._fxCanvasIdx;
          if (typeof idx === 'number') ratios[idx] = e.intersectionRatio;
        });
        update();
      },
      { threshold: [0, 0.05, 0.15, 0.35, 0.55, 0.75, 1] }
    );
    for (var j = 0; j < els.length; j++) {
      els[j]._fxCanvasIdx = j;
      ratios[j] = 0;
      io.observe(els[j]);
    }
  }

  function onResize() {
    resize();
    if (reduceMotion) drawStaticGrid();
  }

  var resizeTimer = null;
  function debouncedResize() {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      resizeTimer = null;
      onResize();
    }, 50);
  }

  resize();
  window.addEventListener('resize', debouncedResize);
  wireSectionOpacity();

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      stopLoop();
    } else if (!reduceMotion && !introActive()) {
      startLoop();
    }
  });

  var introObserver = new MutationObserver(syncIntroPause);
  introObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  if (document.body) {
    introObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] });
  }

  if (reduceMotion) {
    drawStaticGrid();
    return;
  }

  syncIntroPause();
})();
