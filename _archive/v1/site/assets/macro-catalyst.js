/**
 * Next macro catalyst from /data/macro_cal.json (HIGH then MED, nearest future date).
 */
(function (global) {
  'use strict';

  function asYmd(d) {
    if (!d || !(d instanceof Date) || isNaN(d.getTime())) return '';
    return d.toISOString().slice(0, 10);
  }

  function daysFromToday(ymdStr) {
    var today = asYmd(new Date());
    var a = new Date(today + 'T12:00:00Z').getTime();
    var b = new Date(String(ymdStr).slice(0, 10) + 'T12:00:00Z').getTime();
    return Math.round((b - a) / 86400000);
  }

  function score(ev) {
    var imp = String((ev && ev.impact) || '').toUpperCase();
    if (imp === 'HIGH') return 0;
    if (imp === 'MED' || imp === 'MEDIUM') return 1;
    return 2;
  }

  /**
   * @returns {{ text: string } | null}
   */
  function pickNextCatalyst(events, refYmd) {
    if (!Array.isArray(events) || !events.length) return null;
    var floor = String(refYmd || asYmd(new Date())).slice(0, 10);
    var candidates = [];
    for (var i = 0; i < events.length; i++) {
      var ev = events[i];
      var ds = String(ev && ev.date ? ev.date : '').slice(0, 10);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(ds)) continue;
      if (ds < floor) continue;
      candidates.push(ev);
    }
    if (!candidates.length) return null;
    candidates.sort(function (a, b) {
      var da = String(a.date || '').slice(0, 10);
      var db = String(b.date || '').slice(0, 10);
      if (da !== db) return da.localeCompare(db);
      var sa = score(a);
      var sb = score(b);
      if (sa !== sb) return sa - sb;
      return String(a.event || '').localeCompare(String(b.event || ''));
    });
    var best = candidates[0];
    var ymd = String(best.date || '').slice(0, 10);
    var days = daysFromToday(ymd);
    var name = String(best.event || 'Event').trim().slice(0, 72);
    var cc = best.country ? String(best.country) + ' · ' : '';
    var tim = best.time ? ' ' + String(best.time) : '';
    var dayWord =
      days === 0 ? 'today' : days === 1 ? 'tomorrow' : 'in ' + days + ' days';
    var text =
      'Next catalyst: ' +
      cc +
      name +
      (tim ? ' (' + tim.trim() + ' UTC)' : '') +
      ' — ' +
      dayWord +
      ' (' +
      ymd +
      ').';
    return { text: text, days: days, impact: best.impact };
  }

  function fillElement(el, refYmd) {
    if (!el) return Promise.resolve(null);
    el.textContent = 'Loading calendar…';
    return fetch('/data/macro_cal.json', { cache: 'no-store' })
      .then(function (r) {
        return r.ok ? r.json() : [];
      })
      .then(function (json) {
        var picked = pickNextCatalyst(Array.isArray(json) ? json : [], refYmd);
        if (!picked) {
          el.textContent = 'No upcoming high-impact events in the published window.';
          return null;
        }
        el.textContent = picked.text;
        return picked;
      })
      .catch(function () {
        el.textContent = 'Macro calendar unavailable (offline or not yet published).';
        return null;
      });
  }

  global.FXRLMacroCatalyst = {
    pickNextCatalyst: pickNextCatalyst,
    fillElement: fillElement,
  };
})(typeof window !== 'undefined' ? window : this);
