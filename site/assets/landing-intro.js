(function () {
  'use strict';

  if (window.location.pathname !== '/' && window.location.pathname !== '/index.html') return;

  var introRoot = document.getElementById('landing-intro');
  var introHero = document.getElementById('intro-hero');
  var introMark = document.getElementById('intro-mark');
  var introTitle = document.getElementById('intro-title');
  var titleBits = introTitle ? introTitle.querySelectorAll('.landing-intro__title-bit') : [];
  var introSkip = document.getElementById('intro-skip');
  var introMute = document.getElementById('intro-mute');
  var navSlot = document.getElementById('nav-mark-slot');
  var appWrap = document.querySelector('.v2-wrap');
  var html = document.documentElement;
  var body = document.body;

  if (!introRoot || !introHero || !introMark || !introTitle || !introSkip || !introMute || !navSlot) return;

  var dayKey = 'fxrl_intro_ymd';
  var soundOffKey = 'fxrl_intro_sound_off';
  var todayLocalYmd = new Date().toLocaleDateString('en-CA');
  var seenYmd = localStorage.getItem(dayKey);
  var soundOff = localStorage.getItem(soundOffKey) === '1';
  var hasWhooshPlayed = false;
  var stopped = false;
  var audioCtx = null;
  var whooshBuffers = {};
  var tl = null;
  var reducedCalls = null;
  var hasFlip = !!(window.gsap && window.Flip && typeof window.Flip.getState === 'function');
  var reduceMotion =
    typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function syncMuteLabel() {
    introMute.textContent = soundOff ? 'Sound: Off' : 'Sound: On';
  }

  function buildAudioContext() {
    if (audioCtx) return audioCtx;
    try {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      audioCtx = new AC();
    } catch (err) {
      audioCtx = null;
    }
    return audioCtx;
  }

  function fillWhooshBuffer(buffer) {
    var data = buffer.getChannelData(0);
    var frameCount = data.length;
    var attack = Math.floor(frameCount * 0.08);
    var releaseStart = Math.floor(frameCount * 0.62);
    var i;
    for (i = 0; i < frameCount; i++) {
      var t = i / frameCount;
      var noise = Math.random() * 2 - 1;
      var shaped = noise * (1 - t);
      var env = 1;
      if (i < attack) env = i / Math.max(1, attack);
      else if (i > releaseStart) env = (frameCount - i) / Math.max(1, frameCount - releaseStart);
      data[i] = shaped * env * 0.28;
    }
  }

  function getWhooshBuffer(ctx) {
    var rate = ctx.sampleRate | 0;
    if (whooshBuffers[rate]) return whooshBuffers[rate];
    var dur = 0.42;
    var frameCount = Math.floor(rate * dur);
    var buffer = ctx.createBuffer(1, frameCount, rate);
    fillWhooshBuffer(buffer);
    whooshBuffers[rate] = buffer;
    return buffer;
  }

  function synthWhoosh(ctx) {
    var dur = 0.42;
    var buffer = getWhooshBuffer(ctx);
    var src = ctx.createBufferSource();
    var hp = ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 550;
    var lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 5600;
    var gain = ctx.createGain();
    gain.gain.setValueAtTime(0.01, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.23, ctx.currentTime + 0.035);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);
    src.buffer = buffer;
    src.connect(hp);
    hp.connect(lp);
    lp.connect(gain);
    gain.connect(ctx.destination);
    src.start();
    src.stop(ctx.currentTime + dur + 0.02);
  }

  function wireIntroControls() {
    introRoot.addEventListener(
      'pointerdown',
      function () {
        playWhoosh();
      },
      { passive: true }
    );
    introMute.addEventListener('click', function () {
      soundOff = !soundOff;
      localStorage.setItem(soundOffKey, soundOff ? '1' : '0');
      syncMuteLabel();
    });
    introSkip.addEventListener('click', function () {
      playWhoosh();
      exitIntro(true);
    });
    document.addEventListener('keydown', function (evt) {
      if (evt.key === 'Escape') {
        evt.preventDefault();
        playWhoosh();
        exitIntro(true);
      }
    });
  }

  function playWhoosh() {
    if (hasWhooshPlayed || soundOff) return;
    var ctx = buildAudioContext();
    if (!ctx) return;
    hasWhooshPlayed = true;
    try {
      if (ctx.state === 'suspended') {
        ctx.resume().then(function () {
          synthWhoosh(ctx);
        });
      } else {
        synthWhoosh(ctx);
      }
    } catch (err) {}
  }

  function tweenToPromise(tween) {
    if (!tween) return Promise.resolve();
    return new Promise(function (resolve) {
      tween.eventCallback('onComplete', resolve);
    });
  }

  function teardownA11yState() {
    if (!appWrap) return;
    appWrap.removeAttribute('inert');
    appWrap.removeAttribute('aria-hidden');
  }

  function setSeenToday() {
    try {
      localStorage.setItem(dayKey, todayLocalYmd);
    } catch (err) {}
  }

  function completeCleanup() {
    stopped = true;
    teardownA11yState();
    html.classList.remove('landing-intro-active');
    html.classList.remove('hero-site-anim-paused');
    html.classList.add('landing-intro-ready');
    setTimeout(function () {
      html.classList.remove('landing-intro-ready');
    }, 900);
    if (introHero && window.gsap) {
      window.gsap.set(introHero, { clearProps: 'transform,willChange' });
    }
    if (introMark && window.gsap) {
      window.gsap.set(introMark, { clearProps: 'willChange' });
    }
    if (introTitle && window.gsap) {
      window.gsap.set(introTitle, { clearProps: 'willChange' });
    }
    if (titleBits.length && window.gsap) {
      window.gsap.set(titleBits, { clearProps: 'willChange' });
    }
    var brand = document.querySelector('.v2-nav__brand');
    if (brand && typeof brand.focus === 'function') {
      try {
        brand.focus({ preventScroll: true });
      } catch (err) {
        brand.focus();
      }
    }
    if (introRoot && introRoot.parentNode) introRoot.parentNode.removeChild(introRoot);
  }

  function fallbackMerge(duration) {
    var markRect = introMark.getBoundingClientRect();
    var navRect = navSlot.getBoundingClientRect();
    var dx = navRect.left + navRect.width / 2 - (markRect.left + markRect.width / 2);
    var dy = navRect.top + navRect.height / 2 - (markRect.top + markRect.height / 2);
    var scale = navRect.width / Math.max(1, markRect.width);

    return tweenToPromise(
      window.gsap.to(introMark, {
        duration: duration,
        x: '+=' + dx,
        y: '+=' + dy,
        scale: scale,
        ease: 'power3.inOut',
      })
    ).then(function () {
      var oldStatic = navSlot.querySelector('.v2-nav__mark-static');
      if (oldStatic) oldStatic.remove();
      introMark.classList.add('landing-intro__mark--nav');
      introMark.style.transform = '';
      navSlot.appendChild(introMark);
    });
  }

  function mergeToNav(duration) {
    var oldStatic = navSlot.querySelector('.v2-nav__mark-static');
    if (!hasFlip || !window.gsap || !window.Flip) return fallbackMerge(duration);

    try {
      var state = window.Flip.getState(introMark);
      if (oldStatic) oldStatic.remove();
      introMark.classList.add('landing-intro__mark--nav');
      navSlot.appendChild(introMark);
      return tweenToPromise(
        window.Flip.from(state, {
          duration: duration,
          ease: 'power3.inOut',
          absolute: true,
          scale: true,
        })
      );
    } catch (err) {
      return fallbackMerge(duration);
    }
  }

  function exitIntro(isSkip) {
    if (stopped) return;
    stopped = true;
    setSeenToday();
    if (tl) tl.kill();
    if (reducedCalls && reducedCalls.length) {
      reducedCalls.forEach(function (c) {
        if (c && typeof c.kill === 'function') c.kill();
      });
      reducedCalls = null;
    }

    Promise.resolve()
      .then(function () {
        var fast = isSkip || reduceMotion;
        return mergeToNav(fast ? 0.28 : 0.75);
      })
      .then(function () {
        return tweenToPromise(
          window.gsap.to(introRoot, {
            duration: isSkip ? 0.25 : reduceMotion ? 0.32 : 0.52,
            opacity: 0,
            ease: 'power2.out',
          })
        );
      })
      .then(function () {
        completeCleanup();
      });
  }

  if (seenYmd === todayLocalYmd) {
    if (introRoot.parentNode) introRoot.parentNode.removeChild(introRoot);
    return;
  }

  if (!window.gsap) {
    if (introRoot.parentNode) introRoot.parentNode.removeChild(introRoot);
    return;
  }

  if (window.Flip && hasFlip) window.gsap.registerPlugin(window.Flip);

  html.classList.add('landing-intro-active');
  html.classList.add('hero-site-anim-paused');
  if (appWrap) {
    appWrap.setAttribute('inert', '');
    appWrap.setAttribute('aria-hidden', 'true');
  }
  syncMuteLabel();
  introRoot.classList.add('is-visible');

  var bars = introMark.querySelectorAll('.landing-intro__bar');
  var blue = introMark.querySelector('.landing-intro__bar--blue');
  var orange = introMark.querySelector('.landing-intro__bar--orange');
  var red = introMark.querySelector('.landing-intro__bar--red');

  if (reduceMotion) {
    window.gsap.set(introRoot, { opacity: 1 });
    window.gsap.set([introSkip, introMute], { autoAlpha: 1 });
    window.gsap.set(blue, { x: 0, y: 0, scaleX: 1, scaleY: 1, transformOrigin: '100% 50%' });
    window.gsap.set(orange, { x: 0, y: 0, scaleX: 1, scaleY: 1, transformOrigin: '0% 50%' });
    window.gsap.set(red, { x: 0, y: 0, scaleX: 1, scaleY: 1, transformOrigin: '50% 100%' });
    window.gsap.set(introMark, { scale: 1, x: 0, y: 0, opacity: 1 });
    window.gsap.set(introHero, { x: '-11vw', y: 0, scale: 1 });
    window.gsap.set(introTitle, { autoAlpha: 1, y: 0 });
    if (titleBits.length) {
      window.gsap.set(titleBits, { autoAlpha: 1, y: 0 });
    }
    try {
      introSkip.focus({ preventScroll: true });
    } catch (err) {
      introSkip.focus();
    }
    reducedCalls = [
      window.gsap.delayedCall(0.32, function () {
        body.classList.remove('nav-open');
        html.classList.add('landing-intro-ready');
      }),
      window.gsap.delayedCall(0.72, function () {
        exitIntro(false);
      }),
    ];
    wireIntroControls();
    return;
  }

  window.gsap.set(introRoot, { opacity: 0 });
  window.gsap.set(introHero, { x: 0, y: 0, scale: 1 });
  window.gsap.set([introSkip, introMute], { autoAlpha: 0 });
  window.gsap.set(introTitle, { autoAlpha: 0, y: 10 });
  if (titleBits.length) {
    window.gsap.set(titleBits, { autoAlpha: 0, y: 16 });
  }
  window.gsap.set(introMark, { scale: 0.94, x: 0, y: 0, opacity: 1 });

  window.gsap.set(blue, {
    transformOrigin: '100% 50%',
    scaleX: 0.05,
    scaleY: 0.12,
    x: 160,
    y: 0,
  });
  window.gsap.set(orange, {
    transformOrigin: '0% 50%',
    scaleX: 0.05,
    scaleY: 0.12,
    x: -160,
    y: 0,
  });
  window.gsap.set(red, {
    transformOrigin: '50% 100%',
    scaleX: 0.05,
    scaleY: 0.12,
    x: -55,
    y: 72,
  });

  tl = window.gsap.timeline();
  tl.to(introRoot, { opacity: 1, duration: 0.28, ease: 'power1.out' }, 0);
  tl.to(introSkip, { autoAlpha: 1, duration: 0.26, ease: 'power1.out' }, 0.32);
  tl.to(introMute, { autoAlpha: 1, duration: 0.26, ease: 'power1.out' }, 0.32);
  tl.call(
    function () {
      try {
        introSkip.focus({ preventScroll: true });
      } catch (err) {
        introSkip.focus();
      }
    },
    [],
    0.58
  );
  tl.to(
    blue,
    {
      duration: 0.58,
      x: 0,
      scaleX: 1,
      scaleY: 1,
      ease: 'power3.out',
    },
    0.14
  );
  tl.to(
    orange,
    {
      duration: 0.58,
      x: 0,
      scaleX: 1,
      scaleY: 1,
      ease: 'power3.out',
    },
    0.26
  );
  tl.to(
    red,
    {
      duration: 0.58,
      x: 0,
      y: 0,
      scaleX: 1,
      scaleY: 1,
      ease: 'power3.out',
    },
    0.38
  );
  tl.to(introMark, { duration: 0.32, scale: 1, ease: 'back.out(1.05)' }, 0.94);
  tl.to(introHero, { duration: 0.58, x: '-11vw', ease: 'power2.inOut' }, 1.42);
  tl.to(introTitle, { autoAlpha: 1, y: 0, duration: 0.2, ease: 'power2.out' }, 1.78);
  tl.to(
    titleBits.length ? titleBits : introTitle,
    {
      autoAlpha: 1,
      y: 0,
      duration: 0.55,
      stagger: 0.08,
      ease: 'power2.out',
    },
    1.82
  );
  tl.to({}, { duration: 0.52 }, 2.55);
  tl.call(function () {
    body.classList.remove('nav-open');
    html.classList.add('landing-intro-ready');
  }, [], 2.92);
  tl.to(
    titleBits.length ? titleBits : introTitle,
    {
      autoAlpha: 0,
      y: -8,
      duration: 0.38,
      stagger: 0.04,
      ease: 'power2.in',
    },
    3.08
  );
  tl.call(
    function () {
      exitIntro(false);
    },
    [],
    3.52
  );

  wireIntroControls();
})();
