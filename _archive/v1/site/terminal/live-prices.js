(function (global) {
  'use strict';

  var SYMBOLS = {
    'EUR/USD': 'EURUSD=X',
    'USD/JPY': 'USDJPY=X',
    'USD/INR': 'USDINR=X',
    DXY: 'DX-Y.NYB',
    Brent: 'BZ=F',
    Gold: 'GC=F',
  };

  var PRICE_API_PRIMARY = '/api/fx-price?symbol=';
  var PRICE_API_FALLBACK = '/proxy/yahoo/v8/finance/chart/';
  var CARD_MAP = {
    'EUR/USD': '.term-card--eur',
    'USD/JPY': '.term-card--jpy',
    'USD/INR': '.term-card--inr',
  };

  var priceInterval = null;
  var firstPollTimeout = null;
  var tickerObserver = null;
  var lastObserverKick = 0;
  var MIN_INTERVAL = 30000; // 30 seconds
  var lastFetch = 0;

  function fmtPct(v) {
    if (global.FXUtils && typeof global.FXUtils.formatPct === 'function') {
      return global.FXUtils.formatPct(v);
    }
    var sign = v >= 0 ? '+' : '';
    return sign + Number(v || 0).toFixed(2) + '%';
  }

  function formatPrice(price, name) {
    if (!isFinite(price)) return '—';
    if (name === 'EUR/USD') return Number(price).toFixed(4);
    if (name === 'USD/JPY' || name === 'USD/INR' || name === 'Brent') return Number(price).toFixed(2);
    if (name === 'Gold') return Number(price).toLocaleString('en-US', { maximumFractionDigits: 0 });
    if (name === 'DXY') return Number(price).toFixed(2);
    return String(price);
  }

  function fetchJsonWithTimeout(url, timeoutMs) {
    var ms = timeoutMs || 4000;
    var timer = null;
    var signal = null;
    try {
      if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
        signal = AbortSignal.timeout(ms);
      }
    } catch (_e) {
      signal = null;
    }
    if (!signal && typeof AbortController !== 'undefined') {
      var controller = new AbortController();
      signal = controller.signal;
      timer = setTimeout(function () {
        try {
          controller.abort();
        } catch (_a) {}
      }, ms);
    }
    var options = {
      headers: { Accept: 'application/json' },
    };
    if (signal) options.signal = signal;
    try {
      return fetch(url, options)
        .then(function (resp) {
          if (!resp.ok) throw new Error('HTTP ' + resp.status);
          return resp.json();
        })
        .catch(function (err) {
          if (typeof console !== 'undefined' && console.warn) {
            console.warn('[LivePrices] fetch failed:', err && err.message ? err.message : err);
          }
          return null;
        })
        .finally(function () {
          if (timer) clearTimeout(timer);
        });
    } catch (err) {
      if (typeof console !== 'undefined' && console.warn) {
        console.warn('[LivePrices] fetch failed:', err && err.message ? err.message : err);
      }
      return Promise.resolve(null);
    }
  }

  // Live spot path uses Worker / Yahoo only; api.frankfurter.app is not used in this file.

  function parseYahooPrice(data) {
    var chart = data && data.chart;
    var result = chart && chart.result && chart.result[0];
    var meta = result && result.meta;
    var price = meta ? Number(meta.regularMarketPrice) : NaN;
    var prevClose = meta ? Number(meta.previousClose) : NaN;
    if (!isFinite(price) || !isFinite(prevClose) || prevClose === 0) {
      throw new Error('price_shape');
    }
    var change = price - prevClose;
    var changePct = (change / prevClose) * 100;
    return { price: price, change: change, changePct: changePct };
  }

  function fetchYahoo(base, symbol) {
    // Primary path uses Worker proxy (/api/fx-price?symbol=X) — no extra params needed.
    // Fallback path uses direct Yahoo URL with query string appended.
    var url = base === PRICE_API_PRIMARY
      ? base + encodeURIComponent(symbol)
      : base + symbol + '?interval=1m&range=1d';
    return fetchJsonWithTimeout(url, 4000).then(function (data) {
      if (data == null) throw new Error('no_json');
      return parseYahooPrice(data);
    });
  }

  async function fetchPrice(name, symbol) {
    try {
      return await fetchYahoo(PRICE_API_PRIMARY, symbol);
    } catch (_e) {
      try {
        return await fetchYahoo(PRICE_API_FALLBACK, symbol);
      } catch (e2) {
        if (typeof console !== 'undefined' && console.warn) {
          console.warn('[LivePrices] ' + symbol + ' fetch failed:', e2 && e2.message ? e2.message : e2);
        }
        return null;
      }
    }
  }

  function tickerItemHtml(name) {
    return (
      '<span class="ticker-item" data-ticker="' +
      name +
      '">' +
      '<span class="muted ticker-label">' +
      name +
      '</span> ' +
      '<span class="ticker-price">—</span> ' +
      '<span class="ticker-change muted">—</span>' +
      '</span>'
    );
  }

  function ensureTickerStructure() {
    var roots = document.querySelectorAll('[data-term-ticker]');
    if (!roots.length) return false;
    for (var i = 0; i < roots.length; i++) {
      var cell = roots[i];
      var name = (cell.getAttribute('data-term-ticker') || '').trim();
      if (!name || !SYMBOLS[name]) continue;
      if (cell.querySelector('[data-ticker="' + name + '"]')) continue;
      cell.innerHTML = tickerItemHtml(name);
    }
    return true;
  }

  function updateTickerItem(name, data) {
    var el = document.querySelector('[data-ticker="' + name + '"]');
    if (!el) return;
    var price = Number(data.price);
    var changePct = Number(data.changePct);
    var priceEl = el.querySelector('.ticker-price');
    var changeEl = el.querySelector('.ticker-change');
    if (!priceEl || !changeEl) return;

    priceEl.textContent = formatPrice(price, name);
    changeEl.textContent = isFinite(changePct) ? fmtPct(changePct) : '—';
    changeEl.className = 'ticker-change ' + (changePct >= 0 ? 'positive' : 'negative');

    priceEl.classList.remove('price-flash', 'price-flash--up', 'price-flash--down');
    void priceEl.offsetWidth;
    priceEl.classList.add('price-flash', changePct >= 0 ? 'price-flash--up' : 'price-flash--down');
    setTimeout(function () {
      priceEl.classList.remove('price-flash', 'price-flash--up', 'price-flash--down');
    }, 650);
  }

  function updateHomeCard(name, data) {
    var selector = CARD_MAP[name];
    if (!selector) return;
    var card = document.querySelector(selector);
    if (!card) return;
    var spotEl = card.querySelector('.term-card__spot');
    if (!spotEl) return;
    var changePct = Number(data.changePct);
    spotEl.textContent = formatPrice(Number(data.price), name);
    spotEl.classList.remove('price-flash', 'price-flash--up', 'price-flash--down');
    void spotEl.offsetWidth;
    spotEl.classList.add('price-flash', changePct >= 0 ? 'price-flash--up' : 'price-flash--down');
    setTimeout(function () {
      spotEl.classList.remove('price-flash', 'price-flash--up', 'price-flash--down');
    }, 650);
  }

  /** Pair terminal pages: [data-pair-page][data-live-pair="EUR/USD"] etc. */
  function updatePairPageHero(name, data) {
    var root = document.querySelector('[data-pair-page][data-live-pair="' + name + '"]');
    if (!root) return;
    var price = Number(data.price);
    var changePct = Number(data.changePct);
    var hdrSpot = root.querySelector('#hdr-spot');
    var hdrD1 = root.querySelector('#hdr-d1');
    var heroSpot = root.querySelector('#hero-spot');
    var heroD1 = root.querySelector('#hero-d1');
    if (hdrSpot) hdrSpot.textContent = formatPrice(price, name);
    if (heroSpot) heroSpot.textContent = formatPrice(price, name);
    if (hdrD1) {
      hdrD1.textContent = isFinite(changePct) ? fmtPct(changePct) : '—';
      hdrD1.className =
        'term-pair-head__d1 ' +
        (changePct > 0 ? 'term-pair-head__d1--up' : changePct < 0 ? 'term-pair-head__d1--down' : '');
    }
    if (heroD1) {
      heroD1.textContent = isFinite(changePct) ? fmtPct(changePct) : '—';
    }
  }

  function updateAllPrices() {
    var now = Date.now();
    if (now - lastFetch < MIN_INTERVAL) return;
    lastFetch = now;
    var hasTicker = !!document.querySelector('[data-term-ticker]');
    if (hasTicker) ensureTickerStructure();
    Promise.allSettled(
      Object.keys(SYMBOLS).map(function (name) {
        return fetchPrice(name, SYMBOLS[name]).then(function (data) {
          return { name: name, data: data };
        });
      })
    ).then(function (updates) {
      updates.forEach(function (result) {
        if (result.status === 'fulfilled' && result.value && result.value.data) {
          var n = result.value.name;
          var d = result.value.data;
          if (hasTicker) updateTickerItem(n, d);
          updateHomeCard(n, d);
          updatePairPageHero(n, d);
        }
      });
    });
  }

  function stopPolling() {
    if (firstPollTimeout) {
      clearTimeout(firstPollTimeout);
      firstPollTimeout = null;
    }
    if (priceInterval) {
      clearInterval(priceInterval);
      priceInterval = null;
    }
  }

  function startPolling() {
    stopPolling();
    if (document.hidden) return;
    firstPollTimeout = setTimeout(function () {
      updateAllPrices();
    }, 2000);
    priceInterval = setInterval(updateAllPrices, 30000);
  }

  function onVisibilityChange() {
    if (document.hidden) {
      stopPolling();
    } else {
      lastFetch = 0;
      startPolling();
    }
  }

  function initObserver() {
    var bar = document.querySelector('.term-ticker');
    if (!bar) return;
    if (tickerObserver) tickerObserver.disconnect();
    tickerObserver = new MutationObserver(function () {
      var cells = bar.querySelectorAll('[data-term-ticker]');
      var missing = false;
      for (var i = 0; i < cells.length; i++) {
        var name = (cells[i].getAttribute('data-term-ticker') || '').trim();
        if (name && SYMBOLS[name] && !cells[i].querySelector('[data-ticker="' + name + '"]')) {
          missing = true;
          break;
        }
      }
      if (!missing) return;
      ensureTickerStructure();
      var now = Date.now();
      if (!document.hidden && now - lastObserverKick > 10000) {
        lastObserverKick = now;
        setTimeout(function () {
          updateAllPrices();
        }, 250);
      }
    });
    tickerObserver.observe(bar, { childList: true, subtree: true });
  }

  var visibilityHooked = false;

  function init() {
    if (document.querySelector('[data-term-ticker]')) {
      ensureTickerStructure();
      initObserver();
    }
    if (!visibilityHooked) {
      visibilityHooked = true;
      document.addEventListener('visibilitychange', onVisibilityChange);
    }
    if (!document.hidden) startPolling();
    else stopPolling();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(typeof window !== 'undefined' ? window : this);
