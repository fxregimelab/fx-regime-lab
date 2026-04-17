/**
 * Public /dashboard/: live regime_calls + signals + validation_log (Supabase anon).
 */
(function (global) {
  'use strict';

  var PAIRS = [
    { code: 'EURUSD', prefix: 'eur' },
    { code: 'USDJPY', prefix: 'jpy' },
    { code: 'USDINR', prefix: 'inr' },
  ];

  function getClient() {
    var url = global.__SUPABASE_URL__;
    var key = global.__SUPABASE_ANON_KEY__;
    if (!url || !key || !global.supabase || typeof global.supabase.createClient !== 'function') {
      return null;
    }
    return global.supabase.createClient(url, key);
  }

  function confToPct(c) {
    if (c == null || !isFinite(Number(c))) return null;
    var x = Number(c);
    // 0 is valid (must use >=); match terminal confidenceToPercent semantics
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

  function regimeStreakLine(rows) {
    if (!rows || !rows.length) return '';
    var cur = String(rows[0].regime || 'UNKNOWN').trim();
    var streak = 0;
    for (var i = 0; i < rows.length; i++) {
      if (String(rows[i].regime || '').trim() === cur) streak += 1;
      else break;
    }
    var prev =
      streak < rows.length ? String(rows[streak].regime || '').trim() : '';
    if (!prev) return cur + ' · ' + streak + ' day(s) at this label';
    return cur + ' · ' + streak + ' day(s) · previously ' + prev;
  }

  function outcomeCell(r) {
    if (r.correct_1d === true) return '✓';
    if (r.correct_1d === false) return '✗';
    return '—';
  }

  function pairDisplay(code) {
    if (code === 'EURUSD') return 'EUR/USD';
    if (code === 'USDJPY') return 'USD/JPY';
    if (code === 'USDINR') return 'USD/INR';
    return code;
  }

  function applyPairCard(prefix, regimeRow, sigRow, historyRows) {
    var badge = document.getElementById('dash-' + prefix + '-badge');
    var hist = document.getElementById('dash-' + prefix + '-history');
    var confNum = document.getElementById('dash-' + prefix + '-conf-pct');
    var bar = document.getElementById('dash-' + prefix + '-conf-bar');
    var rd = document.getElementById('dash-' + prefix + '-rd');
    var cot = document.getElementById('dash-' + prefix + '-cot');
    var vol = document.getElementById('dash-' + prefix + '-vol');
    if (badge && regimeRow) {
      badge.textContent = regimeRow.regime || '—';
    }
    if (hist) {
      hist.textContent = historyRows && historyRows.length ? regimeStreakLine(historyRows) : '';
    }
    var pct = regimeRow ? confToPct(regimeRow.confidence) : null;
    if (confNum) {
      confNum.textContent = pct != null ? pct + '%' : '—';
    }
    if (bar) {
      bar.style.width = pct != null ? Math.min(100, Math.max(0, pct)) + '%' : '0%';
    }
    if (rd && sigRow) {
      var rdv = sigRow.rate_diff_10y != null ? sigRow.rate_diff_10y : sigRow.rate_diff_2y;
      rd.textContent = fmtBp(rdv);
    }
    if (cot && sigRow) {
      cot.textContent = sigRow.cot_percentile != null ? fmtPctile(sigRow.cot_percentile) : '—';
    }
    if (vol && sigRow) {
      vol.textContent = fmtVol(sigRow.realized_vol_20d);
    }
  }

  function renderValidationRows(rows) {
    var tb = document.getElementById('dash-validation-tbody');
    if (!tb) return;
    tb.innerHTML = '';
    if (!rows || !rows.length) {
      var tr0 = document.createElement('tr');
      tr0.innerHTML =
        '<td colspan="5" style="text-align:center;color:var(--text-muted)">No validation rows yet</td>';
      tb.appendChild(tr0);
      return;
    }
    rows.forEach(function (r) {
      var tr = document.createElement('tr');
      var ok = r.correct_1d === true;
      var bad = r.correct_1d === false;
      tr.className = ok ? 'row-ok' : bad ? 'row-bad' : '';
      var conf =
        r.confidence != null && isFinite(Number(r.confidence))
          ? Math.round(Number(r.confidence) <= 1 ? Number(r.confidence) * 100 : Number(r.confidence)) + '%'
          : '—';
      tr.innerHTML =
        '<td class="cell-date">' +
        String(r.date || '').slice(0, 10) +
        '</td><td>' +
        pairDisplay(r.pair) +
        '</td><td>' +
        (r.predicted_direction || '—') +
        '</td><td class="cell-mono">' +
        conf +
        '</td><td>' +
        outcomeCell(r) +
        '</td>';
      tb.appendChild(tr);
    });
  }

  function loadDashboard() {
    var client = getClient();
    var note = document.querySelector('.dash-placeholder-note');
    if (!client) {
      if (note) {
        note.innerHTML =
          'Supabase env not injected — pair cards stay static. Configure Cloudflare Worker env for live reads.';
      }
      return Promise.resolve();
    }
    return Promise.all(
      PAIRS.map(function (p) {
        return Promise.all([
          client
            .from('regime_calls')
            .select('pair,date,regime,confidence,primary_driver')
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
            .limit(1)
            .then(function (res) {
              if (res.error) throw res.error;
              var d = res.data || [];
              return d[0] || null;
            }),
        ]).then(function (arr) {
          return { code: p.code, prefix: p.prefix, regimes: arr[0], signal: arr[1] };
        });
      })
    )
      .then(function (packs) {
        packs.forEach(function (pack) {
          var latestReg = pack.regimes && pack.regimes.length ? pack.regimes[0] : null;
          applyPairCard(pack.prefix, latestReg, pack.signal, pack.regimes);
        });
        if (note) {
          note.innerHTML =
            'Live regime and signal rows from Supabase. Charts below remain illustrative; use the <a href="/terminal/">Research terminal</a> for full desks.';
        }
        return client
          .from('validation_log')
          .select(
            'date,pair,predicted_direction,confidence,actual_direction,correct_1d'
          )
          .order('date', { ascending: false })
          .limit(30)
          .then(function (res) {
            if (res.error) throw res.error;
            renderValidationRows(res.data || []);
          });
      })
      .catch(function (e) {
        if (note) {
          note.textContent =
            'Live read failed: ' + (e && e.message ? e.message : String(e)) + ' — try the terminal.';
        }
      });
  }

  global.FXRLDashboardLive = {
    load: loadDashboard,
  };
})(typeof window !== 'undefined' ? window : this);
