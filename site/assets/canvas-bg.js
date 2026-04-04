/**
 * FX Regime Lab — vanilla canvas background (UI v2).
 * Layers: slow pair lines, sine pulses, sparse ambient dots.
 * pointer-events: none; mobile = layer 1 only at reduced opacity.
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
  var mobile = typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 768px)').matches;
  var dots = [];
  var lastDot = 0;

  var colors = {
    eur: 'rgba(37, 99, 168, 0.07)',
    jpy: 'rgba(184, 107, 42, 0.07)',
    inr: 'rgba(166, 48, 48, 0.07)',
    navy: 'rgba(27, 58, 107, 0.05)',
    dotEur: 'rgba(37, 99, 168, 0.3)',
    dotJpy: 'rgba(184, 107, 42, 0.3)',
    dotInr: 'rgba(166, 48, 48, 0.3)',
  };

  function resize() {
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

  function drawLines(now) {
    var sec = (now - t0) / 1000;
    var speed = w / 28;
    var offset = (sec * speed) % w;

    ctx.lineWidth = 1.5;
    var bases = [h * 0.35, h * 0.42, h * 0.5];
    var lineColors = [colors.eur, colors.jpy, colors.inr];
    for (var L = 0; L < 3; L++) {
      ctx.beginPath();
      ctx.strokeStyle = mobile ? lineColors[L].replace('0.07', '0.035') : lineColors[L];
      for (var x = -offset; x < w + 40; x += 6) {
        var y = smoothY(bases[L], x + offset, sec * 0.15 + L, 22 + L * 6);
        if (x === -offset) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
  }

  function drawWaves(now) {
    if (mobile) return;
    var sec = (now - t0) / 1000;
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

  function drawDots(now) {
    if (mobile) return;
    if (now - lastDot > 2000) {
      spawnDot();
      lastDot = now;
    }
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
  }

  function frame(now) {
    ctx.clearRect(0, 0, w, h);
    drawLines(now);
    drawWaves(now);
    drawDots(now);
    requestAnimationFrame(frame);
  }

  resize();
  window.addEventListener('resize', resize);
  requestAnimationFrame(frame);
})();
