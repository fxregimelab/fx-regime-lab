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

  var PRICE_API_PRIMARY = 'https://query1.finance.yahoo.com/v8/finance/chart/';
  var PRICE_API_FALLBACK = 'https://query2.finance.yahoo.com/v8/finance/chart/';
  var FX_FALLBACK = {
    'EUR/USD': { from: 'EUR', to: 'USD' },
    'USD/JPY': { from: 'USD', to: 'JPY' },
    'USD/INR': { from: 'USD', to: 'INR' },
  };
  var CARD_MAP = {
    'EUR/USD': '.term-card--eur',
    'USD/JPY': '.term-card--jpy',
    'USD/INR': '.term-card--inr',
  };

  var priceInterval = null;
  var tickerObserver = null;
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

  function ymd(d) {
    return d.toISOString().slice(0, 10);
  }

  function fetchFrankfurterPair(name) {
    var map = FX_FALLBACK[name];
    if (!map) return Promise.resolve(null);
    var now = new Date();
    var yday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    var latestUrl = 'https://api.frankfurter.app/latest?from=' + map.from + '&to=' + map.to;
    var prevUrl = 'https://api.frankfurter.app/' + ymd(yday) + '?from=' + map.from + '&to=' + map.to;
    return Promise.all([
      fetch(latestUrl, { headers: { Accept: 'application/json' } }),
      fetch(prevUrl, { headers: { Accept: 'application/json' } }),
    ])
      .then(function (resps) {
        return Promise.all(
          resps.map(function (r) {
            return r.ok ? r.json() : null;
          })
        );
      })
      .then(function (rows) {
        var latest = rows[0];
        var prev = rows[1];
        var price = latest && latest.rates ? Number(latest.rates[map.to]) : NaN;
        var prevClose = prev && prev.rates ? Number(prev.rates[map.to]) : NaN;
        if (!isFinite(price)) return null;
        if (!isFinite(prevClose) || prevClose === 0) prevClose = price;
        var change = price - prevClose;
        var changePct = prevClose !== 0 ? (change / prevClose) * 100 : 0;
        return { price: price, change: change, changePct: changePct };
      })
      .catch(function () {
        return null;
      });
  }

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
    return fetch(base + symbol + '?interval=1m&range=1d', {
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(5000),
    }).then(function (resp) {
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      return resp.json();
    }).then(parseYahooPrice);
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
    var ticker = document.querySelector('[data-term-ticker]');
    if (!ticker) return false;
    if (ticker.querySelector('[data-ticker]')) return true;
    var names = Object.keys(SYMBOLS);
    ticker.innerHTML = names
      .map(function (name, idx) {
        return (idx ? '<span class="sep">·</span>' : '') + tickerItemHtml(name);
      })
      .join('');
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

  function updateAllPrices() {
    var now = Date.now();
    if (now - lastFetch < MIN_INTERVAL) return;
    lastFetch = now;
    if (!ensureTickerStructure()) return;
    Promise.allSettled(
      Object.keys(SYMBOLS).map(function (name) {
        return fetchPrice(name, SYMBOLS[name]).then(function (data) {
          return { name: name, data: data };
        });
      })
    ).then(function (updates) {
      updates.forEach(function (result) {
        if (result.status === 'fulfilled' && result.value && result.value.data) {
          updateTickerItem(result.value.name, result.value.data);
          updateHomeCard(result.value.name, result.value.data);
        }
      });
    });
  }

  function startPolling() {
    if (priceInterval) {
      clearInterval(priceInterval);
      priceInterval = null;
    }
    if (document.hidden) return;
    updateAllPrices();
    priceInterval = setInterval(updateAllPrices, 30000);
  }

  function initObserver() {
    var ticker = document.querySelector('[data-term-ticker]');
    if (!ticker) return;
    if (tickerObserver) tickerObserver.disconnect();
    tickerObserver = new MutationObserver(function () {
      if (!ticker.querySelector('[data-ticker]')) {
        ensureTickerStructure();
        updateAllPrices();
      }
    });
    tickerObserver.observe(ticker, { childList: true, subtree: true });
  }

  function init() {
    ensureTickerStructure();
    initObserver();
    startPolling();
    document.addEventListener('visibilitychange', startPolling);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(typeof window !== 'undefined' ? window : this);
