/**
 * Terminal data: Supabase when Worker injects URL/key; CSV fallback for local dev.
 * Production: prefer Supabase for mapped signal columns; CSV still used for full master series on site/data/.
 */
(function (global) {
  'use strict';

  var MASTER_CSV = '/data/latest_with_cot.csv';
  var COT_CSV = '/data/cot_latest.csv';

  /** DB column -> master CSV column per pair (matches core/signal_write._row_to_signal). */
  var SIGNAL_TO_CSV = {
    EURUSD: {
      rate_diff_2y: 'US_DE_2Y_spread',
      rate_diff_10y: 'US_DE_10Y_spread',
      rate_diff_zscore: 'US_DE_2Y_spread_zscore',
      cot_lev_money_net: 'EUR_lev_net',
      cot_asset_mgr_net: 'EUR_assetmgr_net',
      cot_percentile: 'EUR_lev_percentile',
      realized_vol_5d: 'EURUSD_vol5',
      realized_vol_20d: 'EURUSD_vol30',
      cross_asset_dxy: 'DXY',
      cross_asset_oil: 'Brent',
      cross_asset_vix: 'VIX',
    },
    USDJPY: {
      rate_diff_2y: 'US_JP_2Y_spread',
      rate_diff_10y: 'US_JP_10Y_spread',
      rate_diff_zscore: 'US_JP_2Y_spread_zscore',
      cot_lev_money_net: 'JPY_lev_net',
      cot_asset_mgr_net: 'JPY_assetmgr_net',
      cot_percentile: 'JPY_lev_percentile',
      realized_vol_5d: 'USDJPY_vol5',
      realized_vol_20d: 'USDJPY_vol30',
      cross_asset_dxy: 'DXY',
      cross_asset_oil: 'Brent',
      cross_asset_vix: 'VIX',
    },
    USDINR: {
      rate_diff_2y: 'US_IN_policy_spread',
      rate_diff_10y: 'US_IN_10Y_spread',
      rate_diff_zscore: 'US_IN_policy_spread_zscore',
      realized_vol_5d: 'USDINR_vol5',
      realized_vol_20d: 'USDINR_vol30',
      cross_asset_dxy: 'DXY',
      cross_asset_oil: 'Brent',
      cross_asset_vix: 'VIX',
    },
  };

  function metaContent(name) {
    var m = document.querySelector('meta[name="' + name + '"]');
    return m && m.getAttribute('content') ? String(m.getAttribute('content')).trim() : '';
  }

  function getSupabaseClient() {
    var url =
      (global.__SUPABASE_URL__ && String(global.__SUPABASE_URL__).trim()) ||
      metaContent('supabase-url');
    var key =
      (global.__SUPABASE_ANON_KEY__ && String(global.__SUPABASE_ANON_KEY__).trim()) ||
      metaContent('supabase-anon-key');
    if (!url || !key || !global.supabase || typeof global.supabase.createClient !== 'function') {
      if (typeof console !== 'undefined' && console.warn) {
        console.warn('[DataClient] Supabase not available — using CSV fallback where applicable');
      }
      return null;
    }
    try {
      return global.supabase.createClient(url, key);
    } catch (e) {
      if (typeof console !== 'undefined' && console.error) console.error('FXRLData: createClient failed', e);
      return null;
    }
  }

  function tsFromDate(dateStr) {
    var iso = String(dateStr || '').trim() + 'T12:00:00Z';
    var U = global.FXUtils;
    if (U && typeof U.timestampToMs === 'function') {
      var t0 = U.timestampToMs(iso);
      return isFinite(t0) ? t0 : NaN;
    }
    var t1 = new Date(iso).getTime();
    return isFinite(t1) ? t1 : NaN;
  }

  function num(x) {
    if (x === '' || x == null) return NaN;
    var n = parseFloat(String(x).replace(/,/g, ''));
    return isFinite(n) ? n : NaN;
  }

  var _csvCache = {};

  function fetchTextCached(url) {
    if (_csvCache[url]) return Promise.resolve(_csvCache[url]);
    return fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error('fetch ' + url);
        return r.text();
      })
      .then(function (t) {
        _csvCache[url] = t;
        return t;
      });
  }

  function splitCsvLine(line) {
    var out = [];
    var cur = '';
    var inQ = false;
    for (var i = 0; i < line.length; i++) {
      var c = line[i];
      if (inQ) {
        if (c === '"') {
          if (line[i + 1] === '"') {
            cur += '"';
            i++;
          } else inQ = false;
        } else cur += c;
      } else {
        if (c === '"') inQ = true;
        else if (c === ',') {
          out.push(cur);
          cur = '';
        } else cur += c;
      }
    }
    out.push(cur);
    return out;
  }

  function parseMasterCsv(text) {
    var lines = text.split(/\r?\n/).filter(function (l) {
      return l.trim().length;
    });
    if (!lines.length) return { rows: [] };
    var headers = splitCsvLine(lines[0]).map(function (h, i) {
      var t = h.trim();
      if (!t && i === 0) return 'date';
      return t || 'col_' + i;
    });
    var rows = [];
    for (var r = 1; r < lines.length; r++) {
      var cells = splitCsvLine(lines[r]);
      var o = {};
      for (var c = 0; c < headers.length; c++) {
        o[headers[c]] = cells[c] != null ? cells[c].trim() : '';
      }
      rows.push(o);
    }
    return { rows: rows };
  }

  /**
   * @param {string} pair EURUSD | USDJPY | USDINR
   * @param {string[]} dbColumns signals table column names
   * @param {string} startDate YYYY-MM-DD
   * @returns {Promise<Record<string, [number, number][]>>}
   */
  function fetchSignalsFromCSV(pair, dbColumns, startDate) {
    var start = startDate || '2020-01-01';
    var map = SIGNAL_TO_CSV[pair] || {};
    return fetchTextCached(MASTER_CSV).then(function (text) {
      var parsed = parseMasterCsv(text);
      var rows = parsed.rows.filter(function (row) {
        return String(row.date || '') >= start;
      });
      var out = {};
      dbColumns.forEach(function (dbCol) {
        out[dbCol] = [];
      });
      for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var t = tsFromDate(row.date);
        if (!isFinite(t)) continue;
        dbColumns.forEach(function (dbCol) {
          var csvKey = map[dbCol];
          if (!csvKey) return;
          var v = num(row[csvKey]);
          if (isFinite(v)) out[dbCol].push([t, v]);
        });
      }
      return out;
    });
  }

  /**
   * @param {string} pair
   * @param {string[]} dbColumns
   * @param {string} startDate
   */
  function fetchSignals(pair, dbColumns, startDate) {
    var start = startDate || '2020-01-01';
    var client = getSupabaseClient();
    if (client) {
      var sel = ['date']
        .concat(dbColumns || [])
        .filter(function (c, i, a) {
          return c && a.indexOf(c) === i;
        });
      return client
        .from('signals')
        .select(sel.join(','))
        .eq('pair', pair)
        .gte('date', start)
        .order('date', { ascending: true })
        .then(function (res) {
          if (res.error) throw res.error;
          var data = res.data || [];
          if (!data.length) return fetchSignalsFromCSV(pair, dbColumns, start);
          var out = {};
          dbColumns.forEach(function (col) {
            out[col] = [];
          });
          for (var i = 0; i < data.length; i++) {
            var r = data[i];
            var tx = tsFromDate(r.date);
            if (!isFinite(tx)) continue;
            dbColumns.forEach(function (col) {
              var v = r[col];
              if (v == null || v === '') return;
              var n = typeof v === 'number' ? v : parseFloat(v);
              if (!isFinite(n)) return;
              out[col].push([tx, n]);
            });
          }
          return out;
        })
        .catch(function (e) {
          if (typeof console !== 'undefined' && console.error) console.error('[DataClient] Supabase fetch failed:', e);
          return fetchSignalsFromCSV(pair, dbColumns, start);
        });
    }
    return fetchSignalsFromCSV(pair, dbColumns, start).catch(function () {
      var empty = {};
      (dbColumns || []).forEach(function (c) {
        empty[c] = [];
      });
      return empty;
    });
  }

  /**
   * @param {string} pair
   * @param {string} startDate
   * @returns {Promise<object[]|null>}
   */
  function fetchSignalRows(pair, startDate) {
    var client = getSupabaseClient();
    if (!client) return Promise.resolve(null);
    return client
      .from('signals')
      .select('*')
      .eq('pair', pair)
      .gte('date', startDate || '2020-01-01')
      .order('date', { ascending: true })
      .then(function (res) {
        if (res.error) throw res.error;
        return res.data || [];
      })
      .catch(function (e) {
        if (typeof console !== 'undefined' && console.error) console.error('FXRLData: signals fetch', e);
        return null;
      });
  }

  function patchMasterRowsFromSignals(masterRows, sbRows, pair) {
    if (!masterRows || !sbRows || !sbRows.length) return;
    var cmap = SIGNAL_TO_CSV[pair];
    if (!cmap) return;
    var byDate = {};
    for (var i = 0; i < sbRows.length; i++) {
      var r = sbRows[i];
      if (r.date) byDate[String(r.date).slice(0, 10)] = r;
    }
    for (var j = 0; j < masterRows.length; j++) {
      var row = masterRows[j];
      var d = String(row.date || '').slice(0, 10);
      var sr = byDate[d];
      if (!sr) continue;
      Object.keys(cmap).forEach(function (dbKey) {
        var csvKey = cmap[dbKey];
        var v = sr[dbKey];
        if (v == null || v === '') return;
        row[csvKey] = typeof v === 'number' ? String(v) : String(v);
      });
    }
  }

  /**
   * @param {string} pair
   * @param {number} days
   */
  function fetchRegimeCalls(pair, days) {
    var n = Math.max(1, Math.min(500, days || 30));
    var client = getSupabaseClient();
    if (!client) return Promise.resolve([]);
    var start = new Date();
    start.setDate(start.getDate() - n);
    var startStr = start.toISOString().split('T')[0];
    return client
      .from('regime_calls')
      .select('date, regime, confidence, primary_driver')
      .eq('pair', pair)
      .gte('date', startStr)
      .order('date', { ascending: false })
      .limit(n)
      .then(function (res) {
        if (res.error) throw res.error;
        var rows = res.data || [];
        return rows
          .map(function (r) {
            return {
              date: String(r.date || '').slice(0, 10),
              regime: r.regime || '',
              confidence: r.confidence != null ? Number(r.confidence) : NaN,
              primary_driver: r.primary_driver || '',
            };
          })
          .reverse();
      })
      .catch(function (e) {
        if (typeof console !== 'undefined' && console.error) console.error('FXRLData: regime_calls', e);
        return [];
      });
  }

  function fetchLatestBrief() {
    return fetchBriefPreview();
  }

  function fetchBriefPreview() {
    var client = getSupabaseClient();
    if (!client) return Promise.resolve(null);
    return client
      .from('brief_log')
      .select('date, brief_text, eurusd_regime, usdjpy_regime, usdinr_regime, macro_context')
      .order('date', { ascending: false })
      .limit(1)
      .then(function (res) {
        if (res.error) throw res.error;
        var rows = res.data || [];
        return rows[0] || null;
      })
      .catch(function (e) {
        if (typeof console !== 'undefined' && console.error) console.error('FXRLData: brief_log', e);
        return null;
      });
  }

  /**
   * @param {string} pair
   * @param {number} days
   */
  function fetchValidationLog(pair, days) {
    var client = getSupabaseClient();
    if (!client) return Promise.resolve([]);
    var n = Math.max(1, Math.min(500, days || 30));
    var start = new Date();
    start.setDate(start.getDate() - n);
    var startStr = start.toISOString().split('T')[0];
    return client
      .from('validation_log')
      .select(
        'date,pair,predicted_direction,predicted_regime,confidence,actual_direction,actual_return_1d,correct_1d'
      )
      .eq('pair', pair)
      .gte('date', startStr)
      .order('date', { ascending: false })
      .then(function (res) {
        if (res.error) throw res.error;
        return res.data || [];
      })
      .catch(function (e) {
        if (typeof console !== 'undefined' && console.error) console.error('[DataClient] Validation log fetch failed:', e);
        return [];
      });
  }

  function checkPipelineErrors() {
    var client = getSupabaseClient();
    if (!client) return Promise.resolve();
    var today = new Date().toISOString().split('T')[0];
    return client
      .from('pipeline_errors')
      .select('source,error_message')
      .eq('date', today)
      .limit(5)
      .then(function (res) {
        var data = res.data;
        if (data && data.length && typeof console !== 'undefined' && console.warn) {
          console.warn('[Pipeline] Errors today:', data);
        }
      })
      .catch(function () {
        /* monitoring only */
      });
  }

  function latestMasterRow() {
    return fetchTextCached(MASTER_CSV)
      .then(parseMasterCsv)
      .then(function (p) {
        return p.rows.length ? p.rows[p.rows.length - 1] : null;
      })
      .catch(function () {
        return null;
      });
  }

  function formatRegimeLabel(raw) {
    if (!raw) return '—';
    return String(raw)
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, function (c) {
        return c.toUpperCase();
      });
  }

  function setStale(show) {
    var el = document.getElementById('term-data-stale');
    if (!el) return;
    el.hidden = !show;
  }

  function setSkel(root, on) {
    if (!root) return;
    var els = root.querySelectorAll('.term-skel-target');
    for (var i = 0; i < els.length; i++) {
      els[i].classList.toggle('term-skel-pulse', !!on);
    }
  }

  function _hoursSinceIso(iso) {
    if (!iso) return NaN;
    var t = new Date(String(iso)).getTime();
    if (!isFinite(t)) return NaN;
    return (Date.now() - t) / 3600000;
  }

  function applyPipelineNavStatus(json) {
    var dot = document.getElementById('term-pipeline-health-dot');
    var label = document.getElementById('term-pipeline-health-label');
    if (!dot || !label) return;
    dot.classList.remove('term-nav__live-dot--amber', 'term-nav__live-dot--grey');
    if (!json) {
      label.textContent = 'Status unknown';
      dot.classList.add('term-nav__live-dot--grey');
      return;
    }
    var st = json.supabase_write_status;
    var lastW = json.last_supabase_write;
    var staleHours = _hoursSinceIso(lastW);
    if (st === 'failed' || (isFinite(staleHours) && staleHours > 25)) {
      label.textContent = 'Data stale';
      dot.classList.add('term-nav__live-dot--amber');
      return;
    }
    if (st === 'ok') {
      label.textContent = 'Live';
      return;
    }
    label.textContent = 'Status unknown';
    dot.classList.add('term-nav__live-dot--grey');
  }

  function initTerminalHome() {
    var root = document.querySelector('.term-main');
    if (!root) return;
    setSkel(root, true);
    setStale(false);

    document.querySelectorAll('.term-card--eur, .term-card--jpy, .term-card--inr').forEach(function (card) {
      card.classList.add('loading');
    });

    checkPipelineErrors();

    fetch('/static/pipeline_status.json')
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(applyPipelineNavStatus)
      .catch(function () {
        applyPipelineNavStatus(null);
      });

    var pairs = [
      { pair: 'EURUSD', card: '.term-card--eur' },
      { pair: 'USDJPY', card: '.term-card--jpy' },
      { pair: 'USDINR', card: '.term-card--inr' },
    ];

    var pRegime = pairs.map(function (x) {
      return fetchRegimeCalls(x.pair, 120).then(function (rows) {
        return { pair: x.pair, card: x.card, rows: rows };
      });
    });

    var pLatest = latestMasterRow();

    var pBrief = fetchBriefPreview();

    Promise.all([Promise.all(pRegime), pLatest, pBrief])
      .then(function (all) {
        var regimeResults = all[0];
        var lastRow = all[1];
        var brief = all[2];
        var stale = false;
        var hasSb = !!getSupabaseClient();

        pairs.forEach(function (x) {
          var c = document.querySelector(x.card);
          if (c) c.classList.remove('loading');
        });

        regimeResults.forEach(function (pack) {
          var card = document.querySelector(pack.card);
          if (!card) return;
          var latest = pack.rows.length ? pack.rows[pack.rows.length - 1] : null;
          if (hasSb && (!latest || !latest.regime)) stale = true;
          if (!hasSb) return;

          var badge = card.querySelector('.term-card__badge');
          var pctEl = card.querySelector('.term-card__conf-pct');
          var fill = card.querySelector('.term-card__conf-fill');
          var driver = card.querySelector('.term-card__driver');
          if (badge) badge.textContent = latest ? formatRegimeLabel(latest.regime) : '—';
          if (pctEl) {
            var c = latest && isFinite(latest.confidence) ? Math.round(latest.confidence * 100) : NaN;
            pctEl.textContent = isFinite(c) ? c + '%' : '—';
            if (!isFinite(c)) pctEl.style.color = 'var(--text-muted)';
          }
          if (fill) {
            var w = latest && isFinite(latest.confidence) ? Math.max(0, Math.min(100, latest.confidence * 100)) : 0;
            fill.style.width = w + '%';
          }
          if (driver) {
            var pd = latest && latest.primary_driver ? String(latest.primary_driver).trim() : '';
            if (!pd) {
              driver.textContent = 'Driver: —';
              driver.style.color = 'var(--text-muted)';
            } else if (pd.indexOf('Driver:') === 0) {
              driver.textContent = pd;
              driver.style.color = '';
            } else {
              driver.textContent = 'Driver: ' + pd;
              driver.style.color = '';
            }
          }
        });

        if (lastRow) {
          pairs.forEach(function (x) {
            var card = document.querySelector(x.card);
            if (!card) return;
            var spotEl = card.querySelector('.term-card__spot');
            var foot = card.querySelector('.term-card__foot');
            var spotKey = x.pair === 'EURUSD' ? 'EURUSD' : x.pair === 'USDJPY' ? 'USDJPY' : 'USDINR';
            var sp = num(lastRow[spotKey]);
            if (spotEl) {
              spotEl.style.color = '';
              if (x.pair === 'USDJPY' || x.pair === 'USDINR') {
                spotEl.textContent = isFinite(sp) ? sp.toFixed(2) : '—';
              } else {
                spotEl.textContent = isFinite(sp) ? sp.toFixed(4) : '—';
              }
              if (!isFinite(sp)) spotEl.style.color = 'var(--text-muted)';
            }
            if (foot) foot.textContent = lastRow.date ? 'As of ' + lastRow.date + ' · data' : 'Updated —';
          });

          var ticker = document.querySelector('[data-term-ticker]');
          if (ticker) {
            function fmtChg(k) {
              var v = num(lastRow[k]);
              if (!isFinite(v)) return { t: '—', cls: 'muted' };
              var cls = v > 0 ? 'bullish' : v < 0 ? 'bearish' : 'muted';
              return { t: (v >= 0 ? '+' : '') + v.toFixed(2) + '%', cls: cls };
            }
            var dxy = num(lastRow.DXY_chg_1D);
            var e1 = num(lastRow.EURUSD_chg_1D);
            var j1 = num(lastRow.USDJPY_chg_1D);
            var i1 = num(lastRow.USDINR_chg_1D);
            var b1 = num(lastRow.Brent_chg_1D);
            var g1 = num(lastRow.Gold_chg_1D);
            function span(label, v, isPct) {
              var cls = !isFinite(v) ? 'muted' : v > 0 ? 'bullish' : v < 0 ? 'bearish' : 'muted';
              var t = !isFinite(v) ? '—' : (v >= 0 ? '+' : '') + v.toFixed(2) + (isPct ? '%' : '');
              return (
                '<span class="muted">' +
                label +
                '</span> <span class="' +
                cls +
                '">' +
                t +
                '</span>'
              );
            }
            ticker.innerHTML =
              span('DXY', dxy, true) +
              '<span class="sep">·</span>' +
              span('EUR/USD', e1, true) +
              '<span class="sep">·</span>' +
              span('USD/JPY', j1, true) +
              '<span class="sep">·</span>' +
              span('USD/INR', i1, true) +
              '<span class="sep">·</span>' +
              span('Brent', b1, true) +
              '<span class="sep">·</span>' +
              span('Gold', g1, true);
          }

          var items = document.querySelectorAll('.term-cross .term-cross__item');
          if (items.length >= 4) {
            function setItem(idx, label, valStr, chgKey, chgIsPp) {
              var it = items[idx];
              if (!it) return;
              var l = it.querySelector('.term-cross__label');
              var v = it.querySelector('.term-cross__val');
              var c = it.querySelector('.term-cross__chg');
              if (l) l.textContent = label;
              if (v) v.textContent = valStr != null && valStr !== '' ? valStr : '—';
              if (c) {
                var ch = num(lastRow[chgKey]);
                var suffix = chgIsPp ? 'pp' : '%';
                c.textContent = isFinite(ch) ? (ch >= 0 ? '+' : '') + ch.toFixed(2) + suffix : '—';
                c.className =
                  'term-cross__chg ' +
                  (isFinite(ch) ? (ch >= 0 ? 'term-cross__chg--up' : 'term-cross__chg--down') : '');
              }
            }
            var u10 = num(lastRow.US_10Y);
            setItem(
              0,
              'US 10Y',
              isFinite(u10) ? u10.toFixed(2) + '%' : '—',
              'US_10Y_chg_1D',
              true
            );
            var spr = num(lastRow.US_DE_10Y_spread);
            setItem(
              1,
              'US–DE 10Y',
              isFinite(spr) ? spr.toFixed(2) + '%' : '—',
              'US_DE_10Y_spread_chg_1D',
              true
            );
            var br = num(lastRow.Brent);
            setItem(2, 'Brent', isFinite(br) ? br.toFixed(2) : '—', 'Brent_chg_1D', false);
            var gd = num(lastRow.Gold);
            setItem(3, 'Gold', isFinite(gd) ? gd.toLocaleString('en-US', { maximumFractionDigits: 0 }) : '—', 'Gold_chg_1D', false);
          }
        } else {
          stale = true;
        }

        if (hasSb && brief && brief.brief_text) {
          var body = document.querySelector('.term-brief__body');
          var title = document.querySelector('.term-brief__title');
          if (body) {
            var t = brief.brief_text.trim();
            body.textContent = t.length > 400 ? t.slice(0, 397) + '…' : t;
            body.style.color = '';
          }
          if (title && brief.date) {
            title.textContent = 'Regime read — ' + String(brief.date).slice(0, 10);
          }
        } else if (hasSb) {
          var body2 = document.querySelector('.term-brief__body');
          if (body2) {
            body2.textContent = '—';
            body2.style.color = 'var(--text-muted)';
          }
        }

        var tsEl = document.getElementById('term-pipeline-ts');
        if (tsEl && lastRow && lastRow.date) {
          tsEl.textContent = 'As of ' + lastRow.date + ' · data';
        }

        setStale(stale);
        setSkel(root, false);
      })
      .catch(function () {
        pairs.forEach(function (x) {
          var c = document.querySelector(x.card);
          if (c) c.classList.remove('loading');
        });
        setStale(true);
        setSkel(root, false);
      });
  }

  global.FXRLData = {
    getSupabaseClient: getSupabaseClient,
    fetchSignals: fetchSignals,
    fetchSignalsFromCSV: fetchSignalsFromCSV,
    fetchRegimeCalls: fetchRegimeCalls,
    fetchLatestBrief: fetchLatestBrief,
    fetchBriefPreview: fetchBriefPreview,
    fetchValidationLog: fetchValidationLog,
    checkPipelineErrors: checkPipelineErrors,
    fetchSignalRows: fetchSignalRows,
    patchMasterRowsFromSignals: patchMasterRowsFromSignals,
    fetchTextCached: fetchTextCached,
    parseMasterCsv: parseMasterCsv,
    initTerminalHome: initTerminalHome,
    MASTER_CSV: MASTER_CSV,
    COT_CSV: COT_CSV,
  };
})(typeof window !== 'undefined' ? window : this);
