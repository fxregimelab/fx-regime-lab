(function (global) {
  'use strict';

  var PAIRS = {
    EURUSD: { key: 'eurusd', label: 'EUR/USD' },
    USDJPY: { key: 'usdjpy', label: 'USD/JPY' },
    USDINR: { key: 'usdinr', label: 'USD/INR' },
  };

  function todayUtc() {
    return new Date().toISOString().slice(0, 10);
  }

  function truncate(text, maxLen) {
    var t = String(text || '').trim();
    if (!t) return '—';
    if (t.length <= maxLen) return t;
    return t.slice(0, maxLen - 1).trim() + '…';
  }

  function directionClass(text) {
    var t = String(text || '').toLowerCase();
    if (t.indexOf('↑') >= 0 || t.indexOf(' up ') >= 0 || t.indexOf('bull') >= 0 || t.indexOf('increase') >= 0) {
      return 'term-intel-bar__item--up';
    }
    if (t.indexOf('↓') >= 0 || t.indexOf(' down ') >= 0 || t.indexOf('bear') >= 0 || t.indexOf('decrease') >= 0) {
      return 'term-intel-bar__item--down';
    }
    return '';
  }

  function syncCard(card) {
    if (!card) return;
    var pct = card.querySelector('.term-card__conf-pct');
    var confidence = card.querySelector('[data-card-confidence]');
    var badge = card.querySelector('.term-card__badge');
    var regime = card.querySelector('[data-card-regime]');

    if (pct && confidence) {
      confidence.textContent = String(pct.textContent || '').replace('%', '').trim() || '—';
      card.setAttribute('data-panel-confidence', String(pct.textContent || '').trim());
    }
    if (badge && regime) {
      regime.textContent = String(badge.textContent || '').trim() || '—';
      card.setAttribute('data-panel-regime', String(badge.textContent || '').trim());
    }
    var spot = card.querySelector('.term-card__spot');
    if (spot) card.setAttribute('data-panel-spot', String(spot.textContent || '').trim());
    var driver = card.querySelector('.term-card__driver');
    if (driver) card.setAttribute('data-panel-driver', String(driver.textContent || '').trim());
    var foot = card.querySelector('.term-card__foot');
    if (foot) card.setAttribute('data-panel-updated', String(foot.textContent || '').trim());
    if (global.FXRLTerminalMotion && typeof global.FXRLTerminalMotion.animateNumbers === 'function') {
      global.FXRLTerminalMotion.animateNumbers(card);
    }
  }

  function observeCards() {
    var cards = document.querySelectorAll('.term-card');
    cards.forEach(function (card) {
      syncCard(card);
      var observer = new MutationObserver(function () {
        syncCard(card);
      });
      observer.observe(card, { subtree: true, childList: true, characterData: true });
    });
  }

  function setIntelligence(signalChanges, isToday) {
    var list = document.getElementById('term-intel-list');
    if (!list) return;
    list.innerHTML = '';
    if (!isToday || !signalChanges || !signalChanges.length) {
      list.innerHTML = '<span class="term-intel-bar__empty">No material signal changes today</span>';
      return;
    }

    signalChanges.slice(0, 3).forEach(function (item) {
      var span = document.createElement('span');
      span.className = 'term-intel-bar__item ' + directionClass(item);
      span.textContent = item;
      list.appendChild(span);
    });
  }

  function applyAiArticle(ai) {
    var sections = (ai && ai.sections) || {};
    var pairs = document.querySelectorAll('.term-card[data-panel-pair]');
    pairs.forEach(function (card) {
      var pair = card.getAttribute('data-panel-pair');
      var map = PAIRS[pair];
      if (!map) return;
      var data = sections[map.key] || {};
      var driver = data.key_driver || data.narrative || '';
      if (driver) {
        var driverEl = card.querySelector('.term-card__driver');
        if (driverEl) driverEl.textContent = truncate(driver, 60);
      }
      card.setAttribute('data-panel-narrative', data.narrative || '');
      card.setAttribute('data-panel-watch', data.watch_for || '');
      syncCard(card);
    });

    var articleDate = String(ai.date || '').slice(0, 10);
    var generatedDate = String(ai.generated_at || '').slice(0, 10);
    var isToday = articleDate === todayUtc() || generatedDate === todayUtc();
    setIntelligence(sections.signal_changes || [], isToday);
  }

  function initAiLayer() {
    fetch('/data/ai_article.json')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (json) {
        if (!json) return;
        global.FXRLHomeIntel = json;
        applyAiArticle(json);
      })
      .catch(function () {
        setIntelligence([], false);
      });
  }

  function init() {
    observeCards();
    initAiLayer();
  }

  document.addEventListener('DOMContentLoaded', init);
})(typeof window !== 'undefined' ? window : this);
