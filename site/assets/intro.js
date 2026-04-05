(function () {
  'use strict';

  // ─── CONFIG ──────────────────────────────────────

  var CONFIG = {
    stripes: [
      {
        id: 'blue',
        color: '#4A90D9',
        glow: 'rgba(74,144,217,0.6)',
        startX: 'right',
        startY: 0.38,
        direction: -1
      },
      {
        id: 'orange',
        color: '#F5962B',
        glow: 'rgba(245,150,43,0.6)',
        startX: 'left',
        startY: 0.50,
        direction: 1
      },
      {
        id: 'red',
        color: '#C94030',
        glow: 'rgba(201,64,48,0.6)',
        startX: 'left',
        startY: 0.62,
        direction: 1
      }
    ],

    logoWidthFraction: 0.40,
    stripeHeightFraction: 0.06,
    stripeGap: 8,
    skewAngle: -12,

    timeline: {
      pointsAppear: 0,
      streakStart: 200,
      streakDuration: 1200,
      barFormDuration: 600,
      tiltDuration: 400,
      logoHoldStart: 2200,
      logoLockDelay: 200,
      lockSeparate: 300,
      textStart: 3200,
      textStagger: 300,
      travelStart: 5500,
      travelDuration: 800,
      websiteFadeStart: 6800,
      websiteFadeDuration: 800,
      introRemoveDelay: 7800
    }
  };

  // ─── STATE ───────────────────────────────────────

  var canvas, ctx, overlay, brandText, skipBtn;
  var W, H, dpr, rafId;
  var completed = false;
  var stripeStates = [];
  // BUG FIX 1: initialize lastTime to -1 so first frame is skipped
  var lastTime = -1;

  // ─── UTILITY ─────────────────────────────────────

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  // BUG FIX 2: hex → rgba conversion (colors are hex, not rgb())
  function hexToRgba(hex, alpha) {
    var r = parseInt(hex.slice(1, 3), 16);
    var g = parseInt(hex.slice(3, 5), 16);
    var b = parseInt(hex.slice(5, 7), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }

  // ─── INIT ────────────────────────────────────────

  function init() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      completeIntro();
      return;
    }

    // BUG FIX 3: same-day skip using fxrl_intro_ymd localStorage key
    try {
      var dayKey = 'fxrl_intro_ymd';
      var todayYmd = new Date().toLocaleDateString('en-CA');
      if (localStorage.getItem(dayKey) === todayYmd) {
        completeIntro();
        return;
      }
    } catch (e) {}

    overlay = document.getElementById('fxrl-intro');
    canvas = document.getElementById('intro-canvas');
    brandText = document.getElementById('intro-brand-text');
    skipBtn = document.getElementById('intro-skip');

    if (!overlay || !canvas) {
      completeIntro();
      return;
    }

    ctx = canvas.getContext('2d');
    document.body.classList.add('intro-active');

    setupCanvas();
    setupSkip();
    setupBrandText();
    initStripeStates();

    rafId = requestAnimationFrame(animate);
    runTimeline();
  }

  // ─── CANVAS SETUP ────────────────────────────────

  function setupCanvas() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.scale(dpr, dpr);

    window.addEventListener('resize', function () {
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      canvas.style.width = W + 'px';
      canvas.style.height = H + 'px';
      ctx.scale(dpr, dpr);
      recalcStripeTargets();
    });
  }

  // ─── STRIPE STATE INIT ───────────────────────────

  function initStripeStates() {
    var logoW = W * CONFIG.logoWidthFraction;
    var stripeH = H * CONFIG.stripeHeightFraction;
    var totalH = stripeH * 3 + CONFIG.stripeGap * 2;
    var logoX = (W - logoW) / 2;
    var logoY = (H - totalH) / 2;

    stripeStates = CONFIG.stripes.map(function (cfg, i) {
      var targetY = logoY + i * (stripeH + CONFIG.stripeGap);
      var startX = cfg.startX === 'right' ? W + 20 : -20;

      return {
        cfg: cfg,
        pointX: startX,
        pointY: H * cfg.startY,
        pointOpacity: 0,
        pointSize: 0,
        trail: [],
        trailMaxLength: 60,
        barProgress: 0,
        barWidth: 0,
        barHeight: 0,
        barX: startX,
        barY: H * cfg.startY,
        skewProgress: 0,
        currentX: startX,
        currentY: H * cfg.startY,
        targetX: logoX,
        targetY: targetY,
        targetW: logoW,
        targetH: stripeH,
        glowIntensity: 0,
        lockOffset: 0,
        travelX: null,
        travelY: null,
        dissolveX: null,
        dissolveY: null,
        dissolveW: null,
        dissolveH: null,
        dissolveOpacity: null,
        dissolveStart: null,
        travelStartX: null,
        travelStartY: null,
        formingStart: null,
        formingStartX: null,
        formingStartY: null,
        phase: 'hidden'
      };
    });
  }

  function recalcStripeTargets() {
    var logoW = W * CONFIG.logoWidthFraction;
    var stripeH = H * CONFIG.stripeHeightFraction;
    var totalH = stripeH * 3 + CONFIG.stripeGap * 2;
    var logoX = (W - logoW) / 2;
    var logoY = (H - totalH) / 2;

    stripeStates.forEach(function (s, i) {
      s.targetX = logoX;
      s.targetY = logoY + i * (stripeH + CONFIG.stripeGap);
      s.targetW = logoW;
      s.targetH = stripeH;
    });
  }

  // ─── BRAND TEXT SETUP ────────────────────────────

  function setupBrandText() {
    brandText.innerHTML =
      ['FX', 'REGIME', 'LAB'].map(function (w) {
        return '<span class="word">' + w + '</span>';
      }).join('');

    var logoH = H * CONFIG.stripeHeightFraction * 3 + CONFIG.stripeGap * 2;
    var logoY = (H - logoH) / 2;
    brandText.style.top = (logoY + logoH + 40) + 'px';
    brandText.style.transform = 'translateX(-50%)';
    brandText.style.opacity = '1';
  }

  // ─── SKIP SETUP ──────────────────────────────────

  function setupSkip() {
    setTimeout(function () {
      if (skipBtn) skipBtn.classList.add('visible');
    }, 1000);

    var doSkip = function () {
      if (!completed) completeIntro();
    };

    if (skipBtn) skipBtn.addEventListener('click', doSkip);
    document.addEventListener('keydown', doSkip, { once: true });
    document.addEventListener('click', function (e) {
      if (e.target !== skipBtn) doSkip();
    }, { once: true });
  }

  // ─── TIMELINE ────────────────────────────────────

  function runTimeline() {
    var T = CONFIG.timeline;

    setTimeout(function () {
      stripeStates.forEach(function (s) {
        s.phase = 'streak';
        s.pointOpacity = 1;
        s.pointSize = 3;
      });
    }, T.streakStart);

    setTimeout(function () {
      stripeStates.forEach(function (s) {
        if (s.phase === 'streak') s.phase = 'forming';
      });
    }, T.streakStart + T.streakDuration);

    setTimeout(function () {
      stripeStates.forEach(function (s) {
        if (s.phase === 'forming') s.phase = 'logo';
      });
    }, T.streakStart + T.streakDuration + T.barFormDuration);

    setTimeout(function () {
      stripeStates.forEach(function (s) {
        s.phase = 'locking';
      });
      animateLock();
    }, T.logoHoldStart + T.logoLockDelay);

    setTimeout(function () {
      stripeStates.forEach(function (s) {
        s.phase = 'locked';
        s.glowIntensity = 1;
      });
      setTimeout(function () {
        stripeStates.forEach(function (s) {
          s.glowIntensity = 0;
        });
      }, 600);
    }, T.logoHoldStart + T.logoLockDelay + T.lockSeparate + 100);

    var words = brandText ? brandText.querySelectorAll('.word') : [];
    ['FX', 'REGIME', 'LAB'].forEach(function (_, i) {
      setTimeout(function () {
        if (words[i]) words[i].classList.add('visible');
      }, T.textStart + i * T.textStagger);
    });

    setTimeout(function () {
      stripeStates.forEach(function (s) {
        s.phase = 'dissolving';
      });
      startTravel();
    }, T.travelStart);

    setTimeout(function () {
      overlay.classList.add('dissolving');
      document.body.classList.remove('intro-active');
      document.body.classList.add('intro-complete');
      overlay.style.transition = 'opacity 800ms ease';
      overlay.style.opacity = '0';
    }, T.websiteFadeStart);

    setTimeout(function () {
      completeIntro();
    }, T.introRemoveDelay);
  }

  // ─── LOCK ANIMATION ──────────────────────────────

  function animateLock() {
    var separateDist = 6;
    var T = CONFIG.timeline;
    var start = performance.now();

    function lockFrame(now) {
      var elapsed = now - start;
      var progress = Math.min(elapsed / T.lockSeparate, 1);

      if (progress < 0.5) {
        var separateP = 2 * progress * progress;
        stripeStates[0].lockOffset = -separateDist * separateP * 2;
        stripeStates[1].lockOffset = 0;
        stripeStates[2].lockOffset = separateDist * separateP * 2;
      } else {
        var snapP = (progress - 0.5) * 2;
        stripeStates[0].lockOffset = -separateDist * (1 - snapP);
        stripeStates[1].lockOffset = 0;
        stripeStates[2].lockOffset = separateDist * (1 - snapP);
      }

      if (progress < 1) {
        requestAnimationFrame(lockFrame);
      } else {
        stripeStates.forEach(function (s) { s.lockOffset = 0; });
      }
    }

    requestAnimationFrame(lockFrame);
  }

  // ─── TRAVEL ANIMATION ────────────────────────────

  function startTravel() {
    var T = CONFIG.timeline;

    stripeStates.forEach(function (s, i) {
      s.travelStartX = s.currentX;
      s.travelStartY = s.currentY;
      s.travelProgress = 0;
      s.travelDelay = i * 30;
    });

    if (brandText) {
      brandText.style.transition =
        'all ' + T.travelDuration + 'ms cubic-bezier(0.4, 0, 0.2, 1)';
      brandText.style.fontSize = '13px';
      brandText.style.letterSpacing = '0.12em';
      brandText.style.left = '56px';
      brandText.style.top = '14px';
      brandText.style.transform = 'none';
      // BUG FIX 4: removed near-black color override — keep warm white during travel
    }
  }

  // ─── MAIN ANIMATION LOOP ─────────────────────────

  function animate(timestamp) {
    if (completed) return;

    // BUG FIX 1: guard against first-frame dt spike
    if (lastTime < 0) {
      lastTime = timestamp;
      rafId = requestAnimationFrame(animate);
      return;
    }

    var dt = timestamp - lastTime;
    lastTime = timestamp;

    ctx.clearRect(0, 0, W, H);

    stripeStates.forEach(function (s, i) {
      drawStripe(s, i, timestamp, dt);
    });

    rafId = requestAnimationFrame(animate);
  }

  function drawStripe(s, index, t, dt) {
    if (s.phase === 'hidden') return;

    if (s.phase === 'streak') {
      updateStreak(s, dt);
      drawTrail(s);
      drawPoint(s);
    }

    if (s.phase === 'forming') {
      updateForming(s, dt);
      drawTrail(s);
      drawFormingBar(s);
    }

    if (s.phase === 'logo' || s.phase === 'locking' || s.phase === 'locked') {
      drawLogoStripe(s);
    }

    if (s.phase === 'dissolving') {
      updateDissolving(s, dt, t);
      drawDissolvingStripe(s);
    }
  }

  // ─── DRAW: STREAK PHASE ──────────────────────────

  function updateStreak(s, dt) {
    var speed = W * 0.0035 * (dt / 16);

    if (s.cfg.startX === 'right') {
      s.currentX -= speed;
    } else {
      s.currentX += speed;
    }
    s.currentY = H * s.cfg.startY;

    s.trail.push({ x: s.currentX, y: s.currentY });
    if (s.trail.length > s.trailMaxLength) {
      s.trail.shift();
    }

    var center = W / 2;
    var reached = s.cfg.startX === 'right'
      ? s.currentX <= center + W * 0.05
      : s.currentX >= center - W * 0.05;

    if (reached) {
      s.phase = 'forming';
      s.formingStart = performance.now();
      s.formingStartX = s.currentX;
      s.formingStartY = s.currentY;
    }
  }

  function drawTrail(s) {
    var trail = s.trail;
    if (trail.length < 2) return;

    for (var i = 1; i < trail.length; i++) {
      var alpha = (i / trail.length) * 0.8;
      var width = (i / trail.length) * 3;

      ctx.beginPath();
      ctx.moveTo(trail[i - 1].x, trail[i - 1].y);
      ctx.lineTo(trail[i].x, trail[i].y);
      // BUG FIX 2: use hexToRgba instead of string replace on hex colors
      ctx.strokeStyle = hexToRgba(s.cfg.color, alpha);
      ctx.lineWidth = width;
      ctx.lineCap = 'round';
      ctx.stroke();
    }
  }

  function drawPoint(s) {
    ctx.beginPath();
    ctx.arc(s.currentX, s.currentY, 4, 0, Math.PI * 2);
    ctx.fillStyle = s.cfg.color;
    ctx.shadowBlur = 20;
    ctx.shadowColor = s.cfg.glow;
    ctx.fill();
    ctx.shadowBlur = 0;
  }

  // ─── DRAW: FORMING PHASE ─────────────────────────

  function updateForming(s, dt) {
    if (!s.formingStart) s.formingStart = performance.now();
    var elapsed = performance.now() - s.formingStart;
    var T = CONFIG.timeline;

    s.barProgress = Math.min(elapsed / T.barFormDuration, 1);

    var eased = 1 - Math.pow(1 - s.barProgress, 3);

    s.currentX = lerp(s.formingStartX, s.targetX, eased);
    s.currentY = lerp(s.formingStartY, s.targetY, eased);

    s.barWidth = lerp(0, s.targetW, eased);
    s.barHeight = lerp(0, s.targetH, eased);

    if (s.barProgress > 0.6) {
      s.skewProgress = (s.barProgress - 0.6) / 0.4;
    }

    if (s.barProgress >= 1) {
      s.phase = 'logo';
      s.currentX = s.targetX;
      s.currentY = s.targetY;
      s.barWidth = s.targetW;
      s.barHeight = s.targetH;
      s.skewProgress = 1;
    }
  }

  function drawFormingBar(s) {
    if (s.barWidth <= 0 || s.barHeight <= 0) return;

    ctx.save();
    ctx.translate(s.currentX + s.barWidth / 2, s.currentY + s.barHeight / 2);

    var skew = Math.tan(CONFIG.skewAngle * Math.PI / 180) * s.skewProgress;
    ctx.transform(1, 0, skew, 1, 0, 0);

    ctx.fillStyle = s.cfg.color;
    ctx.shadowBlur = 15 * (1 - s.barProgress);
    ctx.shadowColor = s.cfg.glow;

    ctx.fillRect(-s.barWidth / 2, -s.barHeight / 2, s.barWidth, s.barHeight);

    ctx.shadowBlur = 0;
    ctx.restore();
  }

  // ─── DRAW: LOGO PHASE ────────────────────────────

  function drawLogoStripe(s) {
    var x = s.targetX;
    var y = s.targetY + s.lockOffset;
    var w = s.targetW;
    var h = s.targetH;

    ctx.save();
    ctx.translate(x + w / 2, y + h / 2);

    var skew = Math.tan(CONFIG.skewAngle * Math.PI / 180);
    ctx.transform(1, 0, skew, 1, 0, 0);

    if (s.glowIntensity > 0) {
      ctx.shadowBlur = 30 * s.glowIntensity;
      ctx.shadowColor = s.cfg.glow;
    }

    ctx.fillStyle = s.cfg.color;
    ctx.fillRect(-w / 2, -h / 2, w, h);

    ctx.shadowBlur = 0;
    ctx.restore();

    if (s.glowIntensity > 0) {
      s.glowIntensity = Math.max(0, s.glowIntensity - 0.02);
    }
  }

  // ─── DRAW: DISSOLVING / TRAVEL PHASE ─────────────

  function updateDissolving(s, dt, t) {
    if (!s.dissolveStart) {
      s.dissolveStart = performance.now();
      s.travelStartX = s.targetX;
      s.travelStartY = s.targetY;
    }

    var elapsed = performance.now() - s.dissolveStart;
    var travelDur = CONFIG.timeline.travelDuration;
    var delay = s.cfg.id === 'blue' ? 0 : s.cfg.id === 'orange' ? 50 : 100;

    var progress = Math.max(0, Math.min((elapsed - delay) / travelDur, 1));
    var eased = progress * progress * progress;

    var navX = 14;
    var navY = 14;

    s.dissolveX = lerp(s.travelStartX, navX, eased);
    s.dissolveY = lerp(s.travelStartY, navY, eased);
    s.dissolveW = lerp(s.targetW, 24, eased);
    s.dissolveH = lerp(s.targetH, 5, eased);
    s.dissolveOpacity = 1 - eased * 0.8;
  }

  function drawDissolvingStripe(s) {
    // BUG FIX 5: null-check instead of falsy check (dissolveX could be 0)
    if (s.dissolveX == null) return;

    ctx.save();
    ctx.globalAlpha = s.dissolveOpacity || 1;
    ctx.translate(s.dissolveX + s.dissolveW / 2, s.dissolveY + s.dissolveH / 2);

    var skew = Math.tan(CONFIG.skewAngle * Math.PI / 180);
    ctx.transform(1, 0, skew, 1, 0, 0);

    ctx.fillStyle = s.cfg.color;
    ctx.fillRect(-s.dissolveW / 2, -s.dissolveH / 2, s.dissolveW, s.dissolveH);

    ctx.restore();

    if (s.dissolveOpacity > 0.3) {
      ctx.beginPath();
      ctx.moveTo(s.dissolveX, s.dissolveY);
      ctx.lineTo(s.dissolveX + s.dissolveW * 0.3, s.dissolveY);
      // BUG FIX 2: use hexToRgba for hex colors
      ctx.strokeStyle = hexToRgba(s.cfg.color, 0.3);
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }

  // ─── COMPLETE INTRO ──────────────────────────────

  function completeIntro() {
    if (completed) return;
    completed = true;

    // Record today's date so same-day revisits skip the intro
    try {
      localStorage.setItem('fxrl_intro_ymd', new Date().toLocaleDateString('en-CA'));
    } catch (e) {}

    cancelAnimationFrame(rafId);

    if (overlay) {
      overlay.style.transition = 'opacity 400ms ease';
      overlay.style.opacity = '0';
    }

    document.body.classList.remove('intro-active');
    document.body.classList.add('intro-complete');

    setTimeout(function () {
      if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
    }, 500);
  }

  // ─── START ───────────────────────────────────────

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
