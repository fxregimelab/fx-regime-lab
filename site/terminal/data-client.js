/**
 * Terminal data: Supabase when Worker injects URL/key; CSV fallback for local dev.
 * Production: prefer Supabase for mapped signal columns; CSV still used for full master series on site/data/.
 */
(function (global) {
  'use strict';

  var MASTER_CSV = '/data/latest_with_cot.csv';
  var COT_CSV = '/data/cot_latest.csv';
  var DATA_UPDATING_MESSAGE = 'Data updating — pipeline runs daily at 23:00 UTC';

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

  var _supabaseClient = null;
  var _initPromise = null;
  var SUPABASE_LIB_WAIT_MS = 15000;

  function metaContent(name) {
    var m = document.querySelector('meta[name="' + name + '"]');
    return m && m.getAttribute('content') ? String(m.getAttribute('content')).trim() : '';
  }

  function getSupabaseUrl() {
    return (
      (global.__SUPABASE_URL__ && String(global.__SUPABASE_URL__).trim()) ||
      metaContent('supabase-url')
    );
  }

  function getSupabaseAnonKey() {
    return (
      (global.__SUPABASE_ANON_KEY__ && String(global.__SUPABASE_ANON_KEY__).trim()) ||
      metaContent('supabase-anon-key')
    );
  }

  function supabaseLibReady() {
    return !!(global.supabase && typeof global.supabase.createClient === 'function');
  }

  function supabaseCredsReady() {
    return !!(getSupabaseUrl() && getSupabaseAnonKey());
  }

  function waitForSupabase() {
    return new Promise(function (resolve, reject) {
      if (supabaseCredsReady() && supabaseLibReady()) {
        resolve();
        return;
      }
      var settled = false;
      var poll = null;
      var timer = null;
      function done(ok, err) {
        if (settled) return;
        settled = true;
        if (timer) clearTimeout(timer);
        if (poll) clearInterval(poll);
        if (ok) resolve();
        else reject(err || new Error('Supabase unavailable'));
      }
      poll = setInterval(function () {
        if (supabaseCredsReady() && supabaseLibReady()) done(true);
      }, 50);
      if (typeof document !== 'undefined') {
        document.addEventListener(
          'supabase-ready',
          function () {
            if (supabaseCredsReady() && supabaseLibReady()) done(true);
          },
          { once: true }
        );
      }
      timer = setTimeout(function () {
        if (!supabaseCredsReady() || !supabaseLibReady()) {
          done(false, new Error('Supabase library or credentials timeout'));
        }
      }, SUPABASE_LIB_WAIT_MS);
    });
  }

  /**
   * Resolves when the Supabase JS client is created (or null if unavailable).
   * Safe to call from every data entry point; concurrent calls share one wait.
   */
  function initDataClient() {
    if (_supabaseClient) return Promise.resolve(_supabaseClient);
    if (_initPromise) return _initPromise;
    _initPromise = waitForSupabase()
      .then(function () {
        var url = getSupabaseUrl();
        var key = getSupabaseAnonKey();
        if (!url || !key || !supabaseLibReady()) {
          if (typeof console !== 'undefined' && console.warn) {
            console.warn('[DataClient] Supabase credentials not available');
          }
          return null;
        }
        if (_supabaseClient) return _supabaseClient;
        try {
          _supabaseClient = global.supabase.createClient(url, key, {
            auth: {
              persistSession: false,
              autoRefreshToken: false,
            },
          });
          return _supabaseClient;
        } catch (e) {
          if (typeof console !== 'undefined' && console.error) console.error('FXRLData: createClient failed', e);
          return null;
        }
      })
      .catch(function (e) {
        if (typeof console !== 'undefined' && console.warn) {
          console.warn('[DataClient] initDataClient:', e && e.message ? e.message : e);
        }
        return null;
      })
      .finally(function () {
        if (!_supabaseClient) _initPromise = null;
      });
    return _initPromise;
  }

  function getSupabaseClient() {
    return _supabaseClient;
  }

  function isLocalDev() {
    var h = (global.location && global.location.hostname) || '';
    return h === 'localhost' || h === '127.0.0.1' || (h.indexOf && h.indexOf('.local') !== -1);
  }

  function normalisePair(pair) {
    return String(pair || '')
      .trim()
      .toUpperCase()
      .replace(/\//g, '');
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

  function buildTimeSeriesResult(data, columns) {
    var result = {};
    var cols = columns || [];
    cols.forEach(function (col) {
      result[col] = [];
    });
    for (var i = 0; i < (data || []).length; i++) {
      var row = data[i];
      var tx = tsFromDate(row.date);
      if (!isFinite(tx)) continue;
      cols.forEach(function (col) {
        var v = row[col];
        if (v == null || v === '') return;
        var n = typeof v === 'number' ? v : parseFloat(v);
        if (isFinite(n)) result[col].push([tx, n]);
      });
    }
    return result;
  }

  function buildMasterRowsFromSignals(sbRows, pair) {
    var p = normalisePair(pair);
    var cmap = SIGNAL_TO_CSV[p];
    if (!cmap || !sbRows || !sbRows.length) return [];
    var out = [];
    for (var i = 0; i < sbRows.length; i++) {
      var r = sbRows[i];
      var row = { date: String(r.date || '').slice(0, 10) };
      Object.keys(cmap).forEach(function (dbKey) {
        var csvKey = cmap[dbKey];
        var v = r[dbKey];
        if (v == null || v === '') return;
        row[csvKey] = typeof v === 'number' ? String(v) : String(v);
      });
      out.push(row);
    }
    return out;
  }

  function num(x) {
    if (x === '' || x == null) return NaN;
    var n = parseFloat(String(x).replace(/,/g, ''));
    return isFinite(n) ? n : NaN;
  }

  var _csvCache = {};
  var _lastPipelineStatus = null;
  var _inFlightSignals = new Map();
  var CACHE_TTL = 5 * 60 * 1000; // 5 minutes
  var SUPABASE_QUERY_TIMEOUT_MS = 8000;
  var FETCH_TIMEOUT_MS = 12000;
  var _fetchQueue = {
    running: 0,
    maxConcurrent: 3,
    queue: [],
    add: function (fn) {
      var self = this;
      if (self.running < self.maxConcurrent) {
        self.running += 1;
        return Promise.resolve()
          .then(fn)
          .finally(function () {
            self.running -= 1;
            if (self.queue.length > 0) {
              var next = self.queue.shift();
              self.add(next.fn).then(next.resolve, next.reject);
            }
          });
      }
      return new Promise(function (resolve, reject) {
        self.queue.push({ fn: fn, resolve: resolve, reject: reject });
      });
    },
  };

  function fetchWithTimeout(promise, ms) {
    var timeoutMs = ms || SUPABASE_QUERY_TIMEOUT_MS;
    var timer = null;
    var timeout = new Promise(function (_resolve, reject) {
      timer = setTimeout(function () {
        reject(new Error('Query timeout'));
      }, timeoutMs);
    });
    return Promise.race([promise, timeout]).finally(function () {
      if (timer) clearTimeout(timer);
    });
  }

  /** Postgrest builder (thenable) or Promise — race with timeout */
  function queryWithTimeout(queryPromise, ms) {
    return fetchWithTimeout(queryPromise, ms);
  }

  function fetchTextWithTimeout(url, timeoutMs) {
    var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (controller) controller.abort();
    }, timeoutMs || FETCH_TIMEOUT_MS);
    var options = controller ? { signal: controller.signal } : {};
    return fetch(url, options)
      .then(function (r) {
        if (!r.ok) throw new Error('fetch ' + url);
        return r.text();
      })
      .finally(function () {
        clearTimeout(timer);
      });
  }

  function fetchJsonWithTimeout(url, timeoutMs) {
    var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (controller) controller.abort();
    }, timeoutMs || FETCH_TIMEOUT_MS);
    var options = controller ? { signal: controller.signal } : {};
    return fetch(url, options)
      .then(function (r) {
        if (!r.ok) throw new Error('fetch ' + url);
        return r.json();
      })
      .finally(function () {
        clearTimeout(timer);
      });
  }

  function getCached(key) {
    try {
      var item = sessionStorage.getItem(key);
      if (!item) return null;
      var parsed = JSON.parse(item);
      if (!parsed || typeof parsed !== 'object') return null;
      if (Date.now() - parsed.timestamp > CACHE_TTL) {
        sessionStorage.removeItem(key);
        return null;
      }
      return parsed.data;
    } catch (_e) {
      return null;
    }
  }

  function setCached(key, data) {
    try {
      sessionStorage.setItem(
        key,
        JSON.stringify({
          data: data,
          timestamp: Date.now(),
        })
      );
    } catch (_e) {
      // storage full/unavailable: ignore and continue without cache
    }
  }

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
    if (!isLocalDev()) {
      if (typeof console !== 'undefined' && console.warn) {
        console.warn('[DataClient] CSV not available on production');
      }
      return Promise.resolve(null);
    }
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

  function emptyColsObject(cols) {
    var empty = {};
    cols.forEach(function (c) {
      empty[c] = [];
    });
    return empty;
  }

  function tryCsvFallback(np, cols, start, cacheKey) {
    if (!isLocalDev()) {
      if (typeof console !== 'undefined' && console.warn) {
        console.warn('[DataClient] No data source available (CSV disabled on production)');
      }
      return Promise.resolve(emptyColsObject(cols));
    }
    return fetchSignalsFromCSV(np, cols, start).then(function (csvOut) {
      if (csvOut) setCached(cacheKey, csvOut);
      return csvOut || emptyColsObject(cols);
    });
  }

  /**
   * @param {string} pair
   * @param {string[]} dbColumns
   * @param {string} startDate
   */
  function _fetchSignalsImpl(pair, dbColumns, startDate) {
    var start = startDate || '2020-01-01';
    var cols = (dbColumns || []).filter(function (c, i, a) {
      return c && a.indexOf(c) === i;
    });
    var np = normalisePair(pair);
    var cacheKey = 'fxrl:signals:' + np + ':' + cols.join(',') + ':' + start;
    var cached = getCached(cacheKey);
    if (cached) {
      return Promise.resolve(cached);
    }
    return initDataClient().then(function (client) {
      if (!client) {
        return tryCsvFallback(np, cols, start, cacheKey).catch(function () {
          return emptyColsObject(cols);
        });
      }
      var sel = ['date']
        .concat(cols)
        .filter(function (c, i, a) {
          return c && a.indexOf(c) === i;
        });
      return queryWithTimeout(
        client
          .from('signals')
          .select(sel.join(','))
          .eq('pair', np)
          .gte('date', start)
          .order('date', { ascending: true }),
        SUPABASE_QUERY_TIMEOUT_MS
      )
        .then(function (res) {
          if (res.error) {
            if (typeof console !== 'undefined' && console.error) {
              console.error('[DataClient] Supabase error:', res.error.message || String(res.error));
            }
            return tryCsvFallback(np, cols, start, cacheKey);
          }
          var data = res.data || [];
          if (data.length > 0) {
            var out = buildTimeSeriesResult(data, cols);
            setCached(cacheKey, out);
            return out;
          }
          if (typeof console !== 'undefined' && console.warn) {
            console.warn('[DataClient] No data for ' + np);
          }
          return tryCsvFallback(np, cols, start, cacheKey);
        })
        .catch(function (e) {
          if (typeof console !== 'undefined' && console.error) {
            console.error('[DataClient] Supabase fetch threw:', e && e.message ? e.message : e);
          }
          return tryCsvFallback(np, cols, start, cacheKey);
        });
    });
  }

  /**
   * @param {string} pair
   * @param {string[]} dbColumns
   * @param {string} startDate
   */
  function fetchSignals(pair, dbColumns, startDate) {
    var start = startDate || '2020-01-01';
    var cols = (dbColumns || []).filter(function (c, i, a) {
      return c && a.indexOf(c) === i;
    });
    var np = normalisePair(pair);
    var key = np + ':' + cols.join(',') + ':' + start;
    if (_inFlightSignals.has(key)) return _inFlightSignals.get(key);

    var promise = _fetchQueue.add(function () {
      return _fetchSignalsImpl(np, cols, start);
    })
      .finally(function () {
        _inFlightSignals.delete(key);
      });
    _inFlightSignals.set(key, promise);
    return promise;
  }

  /**
   * @param {string} pair
   * @param {string} startDate
   * @returns {Promise<object[]|null>}
   */
  function fetchSignalRows(pair, startDate) {
    return initDataClient().then(function (client) {
      if (!client) return null;
      var np = normalisePair(pair);
      return queryWithTimeout(
        client
          .from('signals')
          .select('*')
          .eq('pair', np)
          .gte('date', startDate || '2020-01-01')
          .order('date', { ascending: true }),
        SUPABASE_QUERY_TIMEOUT_MS
      )
        .then(function (res) {
          if (res.error) throw res.error;
          return res.data || [];
        })
        .catch(function (e) {
          if (typeof console !== 'undefined' && console.error) console.error('FXRLData: signals fetch', e);
          return null;
        });
    });
  }

  function fetchFromSupabase(pair, client, startDate) {
    var np = normalisePair(pair);
    return queryWithTimeout(
      client
        .from('signals')
        .select('*')
        .eq('pair', np)
        .gte('date', startDate || '2020-01-01')
        .order('date', { ascending: true }),
      SUPABASE_QUERY_TIMEOUT_MS
    )
      .then(function (res) {
        if (res.error) throw res.error;
        return res.data || [];
      });
  }

  function fetchFromCSV(pair, startDate) {
    if (!isLocalDev()) return Promise.resolve(null);
    var start = startDate || '2020-01-01';
    var np = normalisePair(pair);
    return fetchTextCached(MASTER_CSV).then(function (text) {
      var parsed = parseMasterCsv(text);
      return (parsed.rows || []).filter(function (row) {
        var d = String(row.date || '').slice(0, 10);
        return d && d >= start;
      });
    });
  }

  function loadData(pair, startDate) {
    var np = normalisePair(pair);
    return initDataClient().then(function (client) {
      if (client) {
        return fetchFromSupabase(np, client, startDate)
          .then(function (data) {
            if (data && data.length) return data;
            return fetchFromCSV(np, startDate)
              .then(function (csvRows) {
                return csvRows && csvRows.length ? csvRows : null;
              })
              .catch(function (e) {
                if (typeof console !== 'undefined' && console.warn) {
                  console.warn('[DataClient] CSV failed:', e && e.message ? e.message : e);
                }
                return null;
              });
          })
          .catch(function (e) {
            if (typeof console !== 'undefined' && console.warn) {
              console.warn('[DataClient] Supabase failed, trying CSV:', e);
            }
            return fetchFromCSV(np, startDate)
              .then(function (csvRows) {
                return csvRows && csvRows.length ? csvRows : null;
              })
              .catch(function (csvErr) {
                if (typeof console !== 'undefined' && console.warn) {
                  console.warn('[DataClient] CSV failed:', csvErr && csvErr.message ? csvErr.message : csvErr);
                }
                return null;
              });
          });
      }
      return fetchFromCSV(np, startDate)
        .then(function (csvRows) {
          return csvRows && csvRows.length ? csvRows : null;
        })
        .catch(function (e) {
          if (typeof console !== 'undefined' && console.warn) {
            console.warn('[DataClient] CSV failed:', e && e.message ? e.message : e);
          }
          return null;
        });
    });
  }

  function loadPairDataset(pair, startDate) {
    var start = startDate || '2020-01-01';
    var np = normalisePair(pair);
    return initDataClient().then(function (client) {
      var supabaseRowsP = client
        ? fetchFromSupabase(np, client, start).catch(function (e) {
            if (typeof console !== 'undefined' && console.warn) {
              console.warn('[DataClient] Supabase failed:', e);
            }
            return null;
          })
        : Promise.resolve(null);
      var masterP = isLocalDev()
      ? fetchTextCached(MASTER_CSV).catch(function (e) {
          if (typeof console !== 'undefined' && console.warn) {
            console.warn('[DataClient] CSV failed:', e && e.message ? e.message : e);
          }
          return null;
        })
      : Promise.resolve(null);
    var cotP = isLocalDev()
      ? fetchTextCached(COT_CSV).catch(function (e) {
          if (typeof console !== 'undefined' && console.warn) {
            console.warn('[DataClient] CSV failed:', e && e.message ? e.message : e);
          }
          return null;
        })
      : Promise.resolve(null);
    return Promise.all([supabaseRowsP, masterP, cotP]).then(function (pack) {
      var sbRows = pack[0];
      var masterText = pack[1];
      var cotText = pack[2];
      var latestDate = null;
      if (sbRows && sbRows.length) {
        latestDate = String(sbRows[sbRows.length - 1].date || '').slice(0, 10);
      }
      if (!latestDate && masterText) {
        var parsed = parseMasterCsv(masterText);
        var rows = parsed.rows || [];
        if (rows.length) {
          latestDate = String(rows[rows.length - 1].date || '').slice(0, 10);
        }
      }
      if (latestDate) setDataDate(latestDate);
      var dataSource = 'none';
      if (masterText) dataSource = 'csv';
      if (sbRows && sbRows.length) dataSource = masterText ? 'hybrid' : 'supabase';
      return {
        sbRows: sbRows && sbRows.length ? sbRows : null,
        masterText: masterText,
        cotText: cotText,
        latestDate: latestDate,
        dataSource: dataSource,
      };
    });
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
    return initDataClient().then(function (client) {
      if (!client) return [];
      var np = normalisePair(pair);
      var start = new Date();
      start.setDate(start.getDate() - n);
      var startStr = start.toISOString().split('T')[0];
      return queryWithTimeout(
        client
          .from('regime_calls')
          .select('date, regime, confidence, primary_driver')
          .eq('pair', np)
          .gte('date', startStr)
          .order('date', { ascending: false })
          .limit(n),
        SUPABASE_QUERY_TIMEOUT_MS
      )
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
    });
  }

  function fetchLatestBrief() {
    return fetchBriefPreview();
  }

  function fetchBriefPreview() {
    return initDataClient().then(function (client) {
      if (!client) return null;
      return queryWithTimeout(
        client
          .from('brief_log')
          .select('date, brief_text, eurusd_regime, usdjpy_regime, usdinr_regime, macro_context')
          .order('date', { ascending: false })
          .limit(1),
        SUPABASE_QUERY_TIMEOUT_MS
      )
        .then(function (res) {
          if (res.error) throw res.error;
          var rows = res.data || [];
          return rows[0] || null;
        })
        .catch(function (e) {
          if (typeof console !== 'undefined' && console.error) console.error('FXRLData: brief_log', e);
          return null;
        });
    });
  }

  /**
   * @param {string} pair
   * @param {number} days
   */
  function fetchValidationLog(pair, days) {
    return initDataClient().then(function (client) {
      if (!client) return [];
      var np = normalisePair(pair);
      var n = Math.max(1, Math.min(500, days || 30));
      var start = new Date();
      start.setDate(start.getDate() - n);
      var startStr = start.toISOString().split('T')[0];
      return queryWithTimeout(
        client
          .from('validation_log')
          .select(
            'date,pair,predicted_direction,predicted_regime,confidence,actual_direction,actual_return_1d,correct_1d'
          )
          .eq('pair', np)
          .gte('date', startStr)
          .order('date', { ascending: false }),
        SUPABASE_QUERY_TIMEOUT_MS
      )
        .then(function (res) {
          if (res.error) throw res.error;
          return res.data || [];
        })
        .catch(function (e) {
          if (typeof console !== 'undefined' && console.error) console.error('[DataClient] Validation log fetch failed:', e);
          return [];
        });
    });
  }

  function checkPipelineErrors() {
    return initDataClient().then(function (client) {
      if (!client) return;
      var today = new Date().toISOString().split('T')[0];
      return queryWithTimeout(
        client
          .from('pipeline_errors')
          .select('source,error_message')
          .eq('date', today)
          .limit(5),
        SUPABASE_QUERY_TIMEOUT_MS
      )
        .then(function (res) {
          var data = res.data;
          if (data && data.length && typeof console !== 'undefined' && console.warn) {
            console.warn('[Pipeline] Errors today:', data);
          }
        })
        .catch(function () {
          /* monitoring only */
        });
    });
  }

  function latestMasterRow() {
    if (!isLocalDev()) return Promise.resolve(null);
    return fetchTextCached(MASTER_CSV)
      .then(parseMasterCsv)
      .then(function (p) {
        return p.rows.length ? p.rows[p.rows.length - 1] : null;
      })
      .catch(function () {
        return null;
      });
  }

  function fetchLatestPrices() {
    return initDataClient().then(function (client) {
      if (!client) return null;
      return queryWithTimeout(
        client
          .from('signals')
          .select('date,pair,cross_asset_dxy,cross_asset_oil,cross_asset_vix,realized_vol_5d')
          .in('pair', ['EURUSD', 'USDJPY', 'USDINR'])
          .order('date', { ascending: false })
          .limit(90),
        SUPABASE_QUERY_TIMEOUT_MS
      )
        .then(function (res) {
          if (res.error) throw res.error;
          var data = res.data || [];
          var byPair = {};
          for (var i = 0; i < data.length; i++) {
            var row = data[i];
            var pr = row.pair;
            if (!pr) continue;
            var pNorm = String(pr).toUpperCase();
            if (!byPair[pNorm]) byPair[pNorm] = row;
          }
          var want = ['EURUSD', 'USDJPY', 'USDINR'];
          var latestDate = '';
          for (var w = 0; w < want.length; w++) {
            var r = byPair[want[w]];
            if (r && r.date) {
              var ds = String(r.date).slice(0, 10);
              if (ds > latestDate) latestDate = ds;
            }
          }
          return { byPair: byPair, latestDate: latestDate };
        })
        .catch(function (e) {
          if (typeof console !== 'undefined' && console.error) {
            console.error('[Home] Failed to fetch latest prices:', e);
          }
          return null;
        });
    });
  }

  function buildCotArraysFromSignals(pair, startDate) {
    var p = normalisePair(pair);
    return fetchSignals(
      p,
      ['cot_lev_money_net', 'cot_asset_mgr_net', 'cot_percentile'],
      startDate || '2023-01-01'
    ).then(function (series) {
      if (!series) return { ok: false };
      var lev = series.cot_lev_money_net || [];
      var mgr = series.cot_asset_mgr_net || [];
      var pct = series.cot_percentile || [];
      var byDate = {};
      function ingest(arr, key) {
        for (var i = 0; i < arr.length; i++) {
          var pt = arr[i];
          if (!pt || !isFinite(pt[0])) continue;
          var d = new Date(pt[0]).toISOString().slice(0, 10);
          if (!byDate[d]) byDate[d] = {};
          var v = pt[1];
          if (v == null || v === '') continue;
          var n = typeof v === 'number' ? v : parseFloat(String(v));
          if (isFinite(n)) byDate[d][key] = n;
        }
      }
      ingest(lev, 'lev');
      ingest(mgr, 'mgr');
      ingest(pct, 'pct');
      var dates = Object.keys(byDate).sort();
      var cotLevNet = [];
      var cotAssetNet = [];
      var cotPctArr = [];
      var hasLev = false;
      var hasMgr = false;
      for (var j = 0; j < dates.length; j++) {
        var o = byDate[dates[j]];
        var ln = o.lev;
        var an = o.mgr;
        var pc = o.pct;
        if (isFinite(ln)) hasLev = true;
        if (isFinite(an)) hasMgr = true;
        cotLevNet.push(isFinite(ln) ? ln : NaN);
        cotAssetNet.push(isFinite(an) ? an : NaN);
        cotPctArr.push(isFinite(pc) ? pc : NaN);
      }
      if (!hasLev && !hasMgr) return { ok: false };
      return {
        ok: true,
        cotDates: dates,
        cotLevNet: cotLevNet,
        cotAssetNet: cotAssetNet,
        cotPctArr: cotPctArr,
      };
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

  /** Canonical labels for regime_calls.primary_driver-style tokens */
  var DRIVER_LABELS = {
    rate_differential: 'Rate differential',
    rate_spread: 'Rate spread',
    yield_differential: 'Yield differential',
    cot_positioning: 'COT positioning',
    policy_divergence: 'Policy divergence',
    risk_sentiment: 'Risk sentiment',
    carry: 'Carry',
    liquidity: 'Liquidity',
    intervention: 'Intervention',
    oil: 'Oil / commodities',
    volatility: 'Volatility',
    real_rates: 'Real rates',
    terms_of_trade: 'Terms of trade',
    positioning: 'Positioning',
    flow: 'Flow',
  };

  function normaliseDriverKey(raw) {
    return String(raw || '')
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '_')
      .replace(/[^a-z0-9_]/g, '');
  }

  /**
   * Human-readable driver for UI (HOME cards, panel). Keeps free-text sentences as-is.
   * @param {string} raw
   * @returns {string}
   */
  function formatDriverLabel(raw) {
    var t = String(raw || '').trim();
    if (!t) return '';
    if (t.indexOf(' ') >= 0 && t.indexOf('_') < 0) return t;
    var nk = normaliseDriverKey(t);
    if (DRIVER_LABELS[nk]) return DRIVER_LABELS[nk];
    if (t.indexOf('_') >= 0 || nk === t) return formatRegimeLabel(t);
    return t;
  }

  /**
   * regime_calls.confidence may be 0–1 or already 0–100.
   * @returns {number} NaN if missing
   */
  function confidenceToPercent(raw) {
    var c = raw == null ? NaN : Number(raw);
    if (!isFinite(c)) return NaN;
    if (c >= 0 && c <= 1) return Math.round(c * 100);
    if (c > 1 && c <= 100) return Math.round(c);
    if (c > 100) return 100;
    return NaN;
  }

  /**
   * Pair terminal strip: "Live · 5 Apr 2026" (Supabase) or "Local · …" (CSV / dev).
   * @param {string} source loadPairDataset dataSource
   * @param {string} latestDate YYYY-MM-DD
   * @param {ParentNode} [root] default document
   */
  function showPairDataStatus(source, latestDate, root) {
    var doc = root && root.querySelector ? root : document;
    var statusEl = doc.querySelector ? doc.querySelector('.pair-data-status') : null;
    if (!statusEl) return;
    var ymd = String(latestDate || '').slice(0, 10);
    var dateFmt = _fmtDataDate(ymd);
    var prefix = '—';
    if (source === 'csv') prefix = 'Local';
    else if (source === 'supabase' || source === 'hybrid') prefix = 'Live';
    statusEl.textContent = dateFmt ? prefix + ' · ' + dateFmt : prefix;
    if (source === 'csv') {
      statusEl.style.color = 'var(--text-muted)';
    } else if (source === 'supabase' || source === 'hybrid') {
      statusEl.style.color = 'var(--bullish)';
    } else {
      statusEl.style.color = 'var(--text-muted)';
    }
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

  function _hoursSinceDate(dateStr) {
    if (!dateStr) return NaN;
    return _hoursSinceIso(String(dateStr).slice(0, 10) + 'T12:00:00Z');
  }

  function _fmtDataDate(dateStr) {
    if (!dateStr) return '';
    var d = String(dateStr).slice(0, 10).split('-');
    if (d.length !== 3) return '';
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var mm = Number(d[1]) - 1;
    if (!isFinite(mm) || mm < 0 || mm > 11) return '';
    return d[2] + ' ' + months[mm] + ' ' + d[0];
  }

  function _fmtPipelineTime(iso) {
    if (!iso) return 'Pipeline —';
    var dt = new Date(String(iso));
    if (!isFinite(dt.getTime())) return 'Pipeline —';
    var hh = String(dt.getUTCHours()).padStart(2, '0');
    var mm = String(dt.getUTCMinutes()).padStart(2, '0');
    return 'Pipeline ' + hh + ':' + mm + ' UTC';
  }

  /**
   * Strip common markdown from brief_log / AI snippets for plain-text HOME preview.
   * @param {string} raw
   * @returns {string}
   */
  function cleanBriefText(raw) {
    var t = String(raw || '')
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n');
    t = t.replace(/\*\*([^*]+)\*\*/g, '$1');
    t = t.replace(/__([^_]+)__/g, '$1');
    t = t.replace(/#{1,6}\s*/gm, '');
    t = t.replace(/[ \t]+/g, ' ');
    t = t.replace(/\n{3,}/g, '\n\n');
    return t.trim();
  }

  function fetchAiArticleJson() {
    return fetchJsonWithTimeout('/data/ai_article.json', FETCH_TIMEOUT_MS)
      .then(function (j) {
        return j && typeof j === 'object' ? j : null;
      })
      .catch(function () {
        return null;
      });
  }

  /**
   * HOME brief card: brief_log → /data/ai_article.json → placeholder.
   * @param {object|null} brief from fetchBriefPreview
   * @param {object|null} aiArticle from fetchAiArticleJson
   */
  function applyHomeBrief(brief, aiArticle) {
    var briefSec = document.querySelector('.term-brief');
    var body = document.querySelector('.term-brief__body');
    var title = document.querySelector('.term-brief__title');
    var fromSb = brief && String(brief.brief_text || '').trim();
    var sec = aiArticle && aiArticle.sections && typeof aiArticle.sections === 'object' ? aiArticle.sections : null;
    var macro = sec && sec.macro_context != null ? String(sec.macro_context).trim() : '';
    var headline = aiArticle && aiArticle.headline != null ? String(aiArticle.headline).trim() : '';
    var maxBody = 420;

    if (briefSec) {
      briefSec.classList.remove('term-brief--from-db', 'term-brief--from-ai');
      if (fromSb) briefSec.classList.add('term-brief--from-db');
      else if (macro || headline) briefSec.classList.add('term-brief--from-ai');
    }

    if (fromSb) {
      var t = cleanBriefText(brief.brief_text);
      if (body) {
        body.textContent = t.length > maxBody ? t.slice(0, maxBody - 3) + '…' : t;
        body.style.color = '';
      }
      if (title && brief.date) {
        title.textContent = 'Regime read — ' + String(brief.date).slice(0, 10);
      }
      return;
    }

    var rawBody = macro || headline;
    var snippet = rawBody ? cleanBriefText(rawBody) : '';
    if (snippet) {
      if (body) {
        body.textContent = snippet.length > maxBody ? snippet.slice(0, maxBody - 3) + '…' : snippet;
        body.style.color = '';
      }
      if (title) {
        var ht = headline ? cleanBriefText(headline) : '';
        if (ht) {
          title.textContent = ht.length > 120 ? ht.slice(0, 117) + '…' : ht;
        } else {
          var ad =
            (aiArticle.date && String(aiArticle.date).slice(0, 10)) ||
            (aiArticle.generated_at && String(aiArticle.generated_at).slice(0, 10)) ||
            '';
          title.textContent = ad ? 'Morning read — ' + ad : 'Morning brief';
        }
      }
      return;
    }

    if (body) {
      body.textContent =
        'Brief preview updates after the daily pipeline. Open the full brief for tables and charts.';
      body.style.color = 'var(--text-muted)';
    }
    if (title) title.textContent = 'Regime read — G10 snapshot';
  }

  function getDataDate() {
    try {
      var v = sessionStorage.getItem('fxrl_data_date');
      return v ? String(v).slice(0, 10) : '';
    } catch (e) {
      return '';
    }
  }

  function setDataDate(dateStr) {
    var v = String(dateStr || '').slice(0, 10);
    if (!v) return;
    try {
      sessionStorage.setItem('fxrl_data_date', v);
    } catch (e) {
      /* storage unavailable */
    }
  }

  function updatePipelineTimestamp(json) {
    var tsEl = document.getElementById('term-pipeline-ts');
    if (!tsEl) return;
    var lhs = _fmtPipelineTime(json && json.last_run_utc);
    var d = getDataDate();
    var rhs = _fmtDataDate(d);
    tsEl.textContent = rhs ? lhs + ' · ' + rhs : lhs;
  }

  function applyPipelineNavStatus(json) {
    var dot = document.getElementById('term-pipeline-health-dot');
    var label = document.getElementById('term-pipeline-health-label');
    if (!dot || !label) return;
    _lastPipelineStatus = json || null;
    dot.classList.remove('term-nav__live-dot--amber', 'term-nav__live-dot--grey');
    if (!json) {
      label.textContent = 'UNKNOWN';
      dot.classList.add('term-nav__live-dot--grey');
      updatePipelineTimestamp(null);
      return;
    }
    var st = json.supabase_write_status;
    var lastW = json.last_supabase_write;
    var staleHours = _hoursSinceIso(lastW);
    if (st === 'failed' || (isFinite(staleHours) && staleHours > 25)) {
      label.textContent = 'STALE';
      dot.classList.add('term-nav__live-dot--amber');
    } else if (st === 'ok') {
      label.textContent = 'LIVE';
    } else {
      label.textContent = 'UNKNOWN';
      dot.classList.add('term-nav__live-dot--grey');
    }
    var dataAgeHours = _hoursSinceDate(getDataDate());
    if (isFinite(dataAgeHours) && dataAgeHours > 48) {
      label.textContent = 'STALE';
      dot.classList.remove('term-nav__live-dot--grey');
      dot.classList.add('term-nav__live-dot--amber');
    }
    updatePipelineTimestamp(json);
  }

  function initTerminalHome() {
    var root = document.querySelector('.term-main');
    if (!root) return Promise.resolve();
    setSkel(root, true);
    setStale(false);

    document.querySelectorAll('.term-card--eur, .term-card--jpy, .term-card--inr').forEach(function (card) {
      card.classList.add('loading');
    });

    checkPipelineErrors();

    fetchJsonWithTimeout('/static/pipeline_status.json', FETCH_TIMEOUT_MS)
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

    var pLatest = fetchLatestPrices();

    var pBrief = fetchBriefPreview();
    var pAi = fetchAiArticleJson();

    return Promise.all([Promise.all(pRegime), pLatest, pBrief, pAi])
      .then(function (all) {
        var regimeResults = all[0];
        var lastBundle = all[1];
        var brief = all[2];
        var aiArticle = all[3];
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
          var confCenter = card.querySelector('.term-card__confidence');
          var lowNote = card.querySelector('.term-card__conf-note');
          if (badge) badge.textContent = latest ? formatRegimeLabel(latest.regime) : '—';
          var cPct = latest ? confidenceToPercent(latest.confidence) : NaN;
          if (pctEl) {
            pctEl.textContent = isFinite(cPct) ? cPct + '%' : '—';
            if (!isFinite(cPct)) pctEl.style.color = 'var(--text-muted)';
            else pctEl.style.color = '';
          }
          if (confCenter) {
            confCenter.textContent = isFinite(cPct) ? String(cPct) : '—';
          }
          if (fill) {
            var w = isFinite(cPct) ? Math.max(0, Math.min(100, cPct)) : 0;
            fill.style.width = w + '%';
          }
          if (lowNote) {
            var showLow = isFinite(cPct) && cPct < 35;
            lowNote.hidden = !showLow;
            if (showLow) {
              lowNote.textContent = 'Low confidence — interpret as context, not a hard signal.';
            }
          }
          if (driver) {
            var pd = latest && latest.primary_driver ? String(latest.primary_driver).trim() : '';
            if (!pd) {
              driver.textContent = 'Driver: —';
              driver.style.color = 'var(--text-muted)';
            } else if (pd.indexOf('Driver:') === 0) {
              var rest = pd.slice(7).trim();
              driver.textContent = rest ? 'Driver: ' + formatDriverLabel(rest) : 'Driver: —';
              driver.style.color = rest ? '' : 'var(--text-muted)';
            } else {
              driver.textContent = 'Driver: ' + formatDriverLabel(pd);
              driver.style.color = '';
            }
          }
        });

        var footDate =
          (lastBundle && lastBundle.latestDate) ||
          (function () {
            var mx = '';
            regimeResults.forEach(function (pack) {
              var r = pack.rows && pack.rows.length ? pack.rows[pack.rows.length - 1] : null;
              if (r && r.date && String(r.date).slice(0, 10) > mx) mx = String(r.date).slice(0, 10);
            });
            return mx;
          })();

        pairs.forEach(function (x) {
          var card = document.querySelector(x.card);
          if (!card) return;
          var foot = card.querySelector('.term-card__foot');
          if (foot) {
            if (!footDate) {
              foot.textContent = 'Updated —';
            } else {
              var pretty = _fmtDataDate(footDate);
              foot.textContent = pretty
                ? 'As of ' + pretty + (hasSb ? ' · Live' : isLocalDev() ? ' · Local' : '')
                : 'Updated —';
            }
          }
        });

        var ref =
          lastBundle && lastBundle.byPair
            ? lastBundle.byPair.EURUSD || lastBundle.byPair.USDJPY || lastBundle.byPair.USDINR
            : null;
        var items = document.querySelectorAll('.term-cross .term-cross__item');
        if (items.length >= 4) {
          function setCrossItem(idx, label, valStr) {
            var it = items[idx];
            if (!it) return;
            var l = it.querySelector('.term-cross__label');
            var v = it.querySelector('.term-cross__val');
            var c = it.querySelector('.term-cross__chg');
            if (l) l.textContent = label;
            if (v) v.textContent = valStr != null && valStr !== '' ? valStr : '—';
            if (c) {
              c.textContent = '—';
              c.className = 'term-cross__chg';
            }
          }
          setCrossItem(0, 'US 10Y', '—');
          setCrossItem(1, 'US–DE 10Y', '—');
          var br = ref ? num(ref.cross_asset_oil) : NaN;
          setCrossItem(2, 'Brent', isFinite(br) ? br.toFixed(2) : '—');
          setCrossItem(3, 'Gold', '—');
        }

        applyHomeBrief(brief, aiArticle);

        if (footDate) {
          setDataDate(footDate);
          applyPipelineNavStatus(_lastPipelineStatus);
        } else {
          updatePipelineTimestamp(_lastPipelineStatus);
        }

        setStale(stale);
        setSkel(root, false);
      })
      .catch(function () {
        pairs.forEach(function (x) {
          var c = document.querySelector(x.card);
          if (c) c.classList.remove('loading');
        });
        applyHomeBrief(null, null);
        updatePipelineTimestamp(_lastPipelineStatus);
        setStale(true);
        setSkel(root, false);
      });
  }

  global.FXRLData = {
    initDataClient: initDataClient,
    getSupabaseClient: getSupabaseClient,
    isLocalDev: isLocalDev,
    normalisePair: normalisePair,
    buildMasterRowsFromSignals: buildMasterRowsFromSignals,
    fetchSignals: fetchSignals,
    fetchSignalsFromCSV: fetchSignalsFromCSV,
    fetchRegimeCalls: fetchRegimeCalls,
    fetchLatestBrief: fetchLatestBrief,
    fetchBriefPreview: fetchBriefPreview,
    fetchValidationLog: fetchValidationLog,
    checkPipelineErrors: checkPipelineErrors,
    fetchSignalRows: fetchSignalRows,
    fetchFromSupabase: fetchFromSupabase,
    fetchFromCSV: fetchFromCSV,
    loadData: loadData,
    loadPairDataset: loadPairDataset,
    patchMasterRowsFromSignals: patchMasterRowsFromSignals,
    fetchTextCached: fetchTextCached,
    parseMasterCsv: parseMasterCsv,
    setDataDate: setDataDate,
    getDataDate: getDataDate,
    DATA_UPDATING_MESSAGE: DATA_UPDATING_MESSAGE,
    initTerminalHome: initTerminalHome,
    fetchLatestPrices: fetchLatestPrices,
    buildCotArraysFromSignals: buildCotArraysFromSignals,
    MASTER_CSV: MASTER_CSV,
    COT_CSV: COT_CSV,
    DRIVER_LABELS: DRIVER_LABELS,
    formatDriverLabel: formatDriverLabel,
    confidenceToPercent: confidenceToPercent,
    showPairDataStatus: showPairDataStatus,
    fmtDataDate: function (ymd) {
      return _fmtDataDate(String(ymd || '').slice(0, 10));
    },
    cleanBriefText: cleanBriefText,
  };

  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function () {
      void initDataClient();
    });
    document.addEventListener('supabase-ready', function () {
      void initDataClient();
    });
  }

  global.FXRLTest = {
    testDataPath: async function () {
      console.group('FX Regime Lab - Data Path Test');
      var supabaseUrl = global.__SUPABASE_URL__;
      var supabaseKey = global.__SUPABASE_ANON_KEY__;
      console.info('supabase-env.js loaded:', !!supabaseUrl && supabaseUrl.length > 10 ? 'YES' : 'NO');
      console.info('SUPABASE_URL set:', !!supabaseUrl);
      console.info('SUPABASE_ANON_KEY set:', !!supabaseKey);

      if (global.FXRLData && typeof global.FXRLData.initDataClient === 'function') {
        await global.FXRLData.initDataClient();
      }

      var client = global.FXRLData && typeof global.FXRLData.getSupabaseClient === 'function'
        ? global.FXRLData.getSupabaseClient()
        : null;
      console.info('Supabase client:', client ? 'OK' : 'NULL');

      if (client) {
        try {
          var q = await queryWithTimeout(
            client.from('signals').select('date,pair,rate_diff_2y').order('date', { ascending: false }).limit(1),
            SUPABASE_QUERY_TIMEOUT_MS
          );
          if (q.error) throw q.error;
          console.info('Supabase signals query:', q.data && q.data.length > 0 ? 'OK - latest: ' + q.data[0].date : 'EMPTY');
        } catch (e) {
          console.info('Supabase signals query: FAILED -', e && e.message ? e.message : e);
        }
      }

      try {
        var isLoc =
          global.FXRLData && typeof global.FXRLData.isLocalDev === 'function' && global.FXRLData.isLocalDev();
        if (!isLoc) {
          console.info(
            'CSV fallback /data/latest_with_cot.csv: SKIP (production — CSV not in repo deploy; use Supabase)'
          );
        } else {
          var csvResp = await fetch('/data/latest_with_cot.csv');
          var len = csvResp.headers.get('content-length');
          console.info(
            'CSV fallback /data/latest_with_cot.csv:',
            csvResp.ok ? 'OK (' + (len || 'unknown') + ' bytes)' : 'FAIL (' + csvResp.status + ')'
          );
        }
      } catch (e2) {
        console.info('CSV fallback: FAILED -', e2 && e2.message ? e2.message : e2);
      }

      try {
        var psResp = await fetch('/static/pipeline_status.json');
        var psJson = await psResp.json();
        console.info('pipeline_status.json:', psResp.ok ? 'OK - last run: ' + (psJson.last_run || 'unknown') : 'FAIL');
      } catch (e3) {
        console.info('pipeline_status.json: FAILED -', e3 && e3.message ? e3.message : e3);
      }

      console.groupEnd();
      return 'Test complete - check console output above';
    },
  };
})(typeof window !== 'undefined' ? window : this);