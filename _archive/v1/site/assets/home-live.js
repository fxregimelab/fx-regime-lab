/**
 * Home page: pipeline timestamp, EUR hero card, three pair cards, validation track strip.
 */
(function (global) {
  'use strict';

  var PAIRS = [
    { code: 'EURUSD', prefix: 'eur', terminal: '/terminal/eurusd.html', cardClass: 'card-light--eur', pairColor: 'var(--pair-eur)' },
    { code: 'USDJPY', prefix: 'jpy', terminal: '/terminal/usdjpy.html', cardClass: 'card-light--jpy', pairColor: 'var(--pair-jpy)' },
    { code: 'USDINR', prefix: 'inr', terminal: '/terminal/usdinr.html', cardClass: 'card-light--inr', pairColor: 'var(--pair-inr)' },
  ];

  function getClient() {
    var url = global.__SUPABASE_URL__;
    var key = global.__SUPABASE_ANON_KEY__;
    if (!url || !key || !global.supabase || typeof global.supabase.createClient !== 'function') return null;
    return global.supabase.createClient(url, key);
  }

  function confToPct(c) {
    if (c == null || !isFinite(Number(c))) return null;
    var x = Number(c);
    if (x >= 0 && x <= 1) return Math.round(x * 100);
    if (x > 1 && x <= 100) return Math.round(x);
    return null;
  }

  function fmtBp(x) {
    if (x == null || !isFinite(Number(x))) return '—';
    var v = Math.round(Number(x));
    return (v >= 0 ? '▲ +' : '▼ ') + Math.abs(v) + ' bp';
  }

  function fmtPctile(x) {
    if (x == null || !isFinite(Number(x))) return '—';
    return Math.round(Number(x)) + 'th';
  }

  function fmtVol(x) {
    if (x == null || !isFinite(Number(x))) return '—';
    return Number(x).toFixed(1) + '%';
  }

  function spreadField(sig) {
    if (!sig) return null;
    if (sig.rate_diff_10y != null && isFinite(Number(sig.rate_diff_10y))) return Number(sig.rate_diff_10y);
    if (sig.rate_diff_2y != null && isFinite(Number(sig.rate_diff_2y))) return Number(sig.rate_diff_2y);
    return null;
  }

  function fmtSpreadDelta(prev, cur) {
    if (prev == null || cur == null || !isFinite(prev) || !isFinite(cur)) return { text: '—', pos: false };
    var d = cur - prev;
    var v = Math.round(d);
    var text = (v >= 0 ? '▲ +' : '▼ ') + Math.abs(v) + ' bp vs prior row';
    return { text: text, pos: v > 0 };
  }

  function regimeStreakLine(rows) {
    if (!rows || !rows.length) return '';
    var cur = String(rows[0].regime || 'UNKNOWN').trim();
    var streak = 0;
    for (var i = 0; i < rows.length; i++) {
      if (String(rows[i].regime || '').trim() === cur) streak += 1;
      else break;
    }
    var prev = streak < rows.length ? String(rows[streak].regime || '').trim() : '';
    if (!prev) return cur + ' · ' + streak + ' day(s) at this label';
    return cur + ' · ' + streak + ' day(s) · previously ' + prev;
  }

  function fmtComposite(sc) {
    if (sc == null || !isFinite(Number(sc))) return '—';
    var x = Number(sc);
    return (x >= 0 ? '+' : '') + x.toFixed(2);
  }

  function setPipelineTs() {
    var el = document.getElementById('home-pipeline-ts');
    if (!el || !global.FXRegimeSite) return;
    global.FXRegimeSite.loadPipelineStatus().then(function (st) {
      if (st && st.last_run_utc) el.textContent = global.FXRegimeSite.formatTs(st.last_run_utc);
      else el.textContent = '—';
    });
  }

  function clearSkel(root) {
    if (root) root.classList.remove('home-card--skeleton');
  }

  function applyHeroEur(regimeRow, sigRow) {
    var root = document.getElementById('home-hero-card');
    var badge = document.getElementById('home-hero-badge');
    var confNum = document.getElementById('home-hero-conf');
    var bar = document.getElementById('home-hero-conf-bar');
    var rd = document.getElementById('home-hero-rd');
    var cot = document.getElementById('home-hero-cot');
    var vol = document.getElementById('home-hero-vol');
    var sc = document.getElementById('home-hero-sc');
    var ts = document.getElementById('home-hero-ts');
    clearSkel(root);
    if (badge && regimeRow) badge.textContent = regimeRow.regime || '—';
    var pct = regimeRow ? confToPct(regimeRow.confidence) : null;
    if (confNum) confNum.textContent = pct != null ? String(pct) : '—';
    if (bar) bar.style.width = pct != null ? Math.min(100, Math.max(0, pct)) + '%' : '0%';
    if (rd && sigRow) rd.textContent = fmtBp(spreadField(sigRow));
    if (cot && sigRow) cot.textContent = sigRow.cot_percentile != null ? fmtPctile(sigRow.cot_percentile) : '—';
    if (vol && sigRow) vol.textContent = fmtVol(sigRow.realized_vol_20d);
    if (sc && regimeRow) sc.textContent = fmtComposite(regimeRow.signal_composite);
    if (ts && regimeRow && regimeRow.date) ts.textContent = 'As of ' + String(regimeRow.date).slice(0, 10) + ' UTC';
  }

  function applyPairCard(prefix, regimeRow, sigLatest, sigPrev, historyRows) {
    var badge = document.getElementById('home-' + prefix + '-badge');
    var hist = document.getElementById('home-' + prefix + '-history');
    var confNum = document.getElementById('home-' + prefix + '-conf-pct');
    var bar = document.getElementById('home-' + prefix + '-conf-bar');
    var rd = document.getElementById('home-' + prefix + '-rd');
    var cot = document.getElementById('home-' + prefix + '-cot');
    var vol = document.getElementById('home-' + prefix + '-vol');
    var chg = document.getElementById('home-' + prefix + '-chg');
    var card = document.getElementById('home-pair-' + prefix);
    clearSkel(card);
    if (badge && regimeRow) badge.textContent = regimeRow.regime || '—';
    if (hist) hist.textContent = historyRows && historyRows.length ? regimeStreakLine(historyRows) : '';
    var pct = regimeRow ? confToPct(regimeRow.confidence) : null;
    if (confNum) confNum.textContent = pct != null ? pct + '%' : '—';
    if (bar) bar.style.width = pct != null ? Math.min(100, Math.max(0, pct)) + '%' : '0%';
    if (prefix === 'inr') {
      if (rd && sigLatest) {
        var v10 = sigLatest.rate_diff_10y;
        rd.textContent = v10 != null && isFinite(Number(v10)) ? fmtBp(Number(v10)) : '—';
      }
    } else {
      if (rd && sigLatest) rd.textContent = fmtBp(spreadField(sigLatest));
      if (cot && sigLatest) cot.textContent = sigLatest.cot_percentile != null ? fmtPctile(sigLatest.cot_percentile) : '—';
    }
    if (vol && sigLatest) vol.textContent = fmtVol(sigLatest.realized_vol_20d);
    if (chg) {
      var curS = spreadField(sigLatest);
      var prevS = spreadField(sigPrev);
      var d = fmtSpreadDelta(prevS, curS);
      chg.textContent = d.text;
      chg.style.color = d.pos ? 'var(--positive)' : d.text === '—' ? 'var(--text-muted)' : 'var(--text-sec)';
    }
  }

  function loadHeroAndPairs(client) {
    if (!client) return Promise.resolve();
    return Promise.all(
      PAIRS.map(function (p) {
        return Promise.all([
          client
            .from('regime_calls')
            .select('pair,date,regime,confidence,primary_driver,rate_signal,cot_signal,vol_signal,signal_composite')
            .eq('pair', p.code)
            .order('date', { ascending: false })
            .limit(120)
            .then(function (res) {
              if (res.error) throw res.error;
              return res.data || [];
            }),
          client
            .from('signals')
            .select('date,pair,rate_diff_2y,rate_diff_10y,cot_percentile,realized_vol_20d')
            .eq('pair', p.code)
            .order('date', { ascending: false })
            .limit(2)
            .then(function (res) {
              if (res.error) throw res.error;
              var d = res.data || [];
              return { latest: d[0] || null, prev: d[1] || null };
            }),
        ]).then(function (arr) {
          return { code: p.code, prefix: p.prefix, regimes: arr[0], signals: arr[1] };
        });
      })
    ).then(function (packs) {
      packs.forEach(function (pack) {
        var latestReg = pack.regimes && pack.regimes.length ? pack.regimes[0] : null;
        var sigL = pack.signals && pack.signals.latest;
        var sigP = pack.signals && pack.signals.prev;
        applyPairCard(pack.prefix, latestReg, sigL, sigP, pack.regimes);
      });
      var eurPack = packs.filter(function (x) {
        return x.prefix === 'eur';
      })[0];
      if (eurPack) {
        var lr = eurPack.regimes && eurPack.regimes.length ? eurPack.regimes[0] : null;
        var sl = eurPack.signals && eurPack.signals.latest;
        applyHeroEur(lr, sl);
      }
    });
  }

  function loadTrackStrip(client) {
    var elDays = document.getElementById('home-track-days');
    var elPred = document.getElementById('home-track-predictions');
    var elAcc = document.getElementById('home-track-accuracy');
    if (!elDays || !elPred || !elAcc) return Promise.resolve();
    if (!client) {
      elDays.textContent = '—';
      elPred.textContent = '—';
      elAcc.textContent = '—';
      return Promise.resolve();
    }
    return Promise.all([
      client
        .from('validation_log')
        .select('*', { count: 'exact', head: true })
        .then(function (res) {
          if (res.error) throw res.error;
          return res.count != null ? res.count : 0;
        }),
      client
        .from('validation_log')
        .select('*', { count: 'exact', head: true })
        .not('correct_1d', 'is', null)
        .then(function (res) {
          if (res.error) throw res.error;
          return res.count != null ? res.count : 0;
        }),
      client
        .from('validation_log')
        .select('date')
        .order('date', { ascending: false })
        .limit(4000)
        .then(function (res) {
          if (res.error) throw res.error;
          var set = {};
          (res.data || []).forEach(function (r) {
            if (r.date) set[String(r.date).slice(0, 10)] = 1;
          });
          return Object.keys(set).length;
        }),
    ]).then(function (counts) {
      var totalPred = counts[0];
      var scoredTotal = counts[1];
      var distinctDays = counts[2];
      elPred.textContent = String(totalPred);
      elDays.textContent = String(distinctDays);
      if (scoredTotal < 5) {
        elAcc.innerHTML = '<span class="home-track-accumulating">Accumulating</span>';
        return null;
      }
      var start = new Date();
      start.setDate(start.getDate() - 20);
      var startStr = start.toISOString().split('T')[0];
      return client
        .from('validation_log')
        .select('date,correct_1d')
        .gte('date', startStr)
        .then(function (res2) {
          if (res2.error) throw res2.error;
          var rows = (res2.data || []).filter(function (r) {
            return r.correct_1d === true || r.correct_1d === false;
          });
          if (!rows.length) {
            elAcc.innerHTML = '<span class="home-track-accumulating">Accumulating</span>';
            return;
          }
          var ok = rows.filter(function (r) {
            return r.correct_1d === true;
          }).length;
          elAcc.textContent = Math.round((ok / rows.length) * 100) + '%';
        });
    });
  }

  function run() {
    setPipelineTs();
    var client = getClient();
    if (!client) {
      ['eur', 'jpy', 'inr'].forEach(function (pfx) {
        var c = document.getElementById('home-pair-' + pfx);
        if (c) c.classList.add('home-card--skeleton');
      });
      var hc = document.getElementById('home-hero-card');
      if (hc) hc.classList.add('home-card--skeleton');
      return;
    }
    loadHeroAndPairs(client).catch(function () {
      var hc = document.getElementById('home-hero-card');
      if (hc) hc.classList.add('home-card--skeleton');
    });
    loadTrackStrip(client).catch(function () {
      var elAcc = document.getElementById('home-track-accuracy');
      if (elAcc) elAcc.textContent = '—';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})(typeof window !== 'undefined' ? window : this);
