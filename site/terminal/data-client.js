/**
 * Terminal data: Supabase `signals` + `regime_calls` (Worker-injected anon key).
 * Pipeline: core/signal_write._row_to_signal → Supabase. Pair pages use DB column names.
 */
(function (global) {
  'use strict';

  var QUERY_TIMEOUT = 8000;

  /**
   * @param {number} [timeout]
   * @returns {Promise<boolean>}
   */
  function waitForSupabase(timeout) {
    var ms = timeout != null ? timeout : QUERY_TIMEOUT;
    if (global.__supabaseReady && supabaseLibReady()) {
      return Promise.resolve(true);
    }
    return new Promise(function (resolve) {
      var t = setTimeout(function () {
        resolve(false);
      }, ms);
      if (typeof document === 'undefined') {
        resolve(false);
        return;
      }
      document.addEventListener(
        'supabase-ready',
        function () {
          clearTimeout(t);
          resolve(true);
        },
        { once: true }
      );
    });
  }

  /** PostgREST builder (thenable) — race with timeout. */
  function queryWithTimeout(queryBuilder) {
    var timeout = new Promise(function (_resolve, reject) {
      setTimeout(function () {
        reject(new Error('Supabase query timeout'));
      }, QUERY_TIMEOUT);
    });
    return Promise.race([queryBuilder, timeout]);
  }

  var DATA_UPDATING_MESSAGE = 'Data updating — pipeline runs daily at 23:00 UTC';
  /** PostgREST page size (avoid default row cap truncation). */
  var SUPABASE_PAGE_SIZE = 1000;
  var _signalsColumnProbeDone = false;

  var _supabaseClient = null;
  var _initPromise = null;

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

  /**
   * Resolves when the Supabase JS client is created (or null if unavailable).
   * Safe to call from every data entry point; concurrent calls share one wait.
   */
  function initDataClient() {
    if (_supabaseClient) return Promise.resolve(_supabaseClient);
    if (_initPromise) return _initPromise;
    _initPromise = waitForSupabase(8000)
      .then(function (ready) {
        if (!ready) {
          if (typeof console !== 'undefined' && console.warn) {
            console.warn('Supabase client library not ready');
          }
          return null;
        }
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
          tryProbeSignalsColumns(_supabaseClient);
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

  function tryProbeSignalsColumns(client) {
    if (_signalsColumnProbeDone || !client) return;
    _signalsColumnProbeDone = true;
    queryWithTimeout(client.from('signals').select('*').limit(1))
      .then(function (res) {
        if (res && res.error) return;
        var row = res.data && res.data[0];
        if (row && typeof console !== 'undefined' && console.log) {
          console.log('signals columns:', Object.keys(row));
        }
      })
      .catch(function () {
        /* ignore */
      });
  }

  /**
   * @param {string} pair
   * @param {number} [days]
   * @returns {Promise<object[]>}
   */
  function fetchSignalsFromSupabase(pair, days) {
    var d = days != null ? days : 365;
    var normPair = normalisePair(pair);
    var fromDate = new Date();
    fromDate.setDate(fromDate.getDate() - d);
    var dateStr = fromDate.toISOString().split('T')[0];
    return initDataClient()
      .then(function (client) {
        if (!client) return [];
        return queryWithTimeout(
          client
            .from('signals')
            .select('*')
            .eq('pair', normPair)
            .gte('date', dateStr)
            .order('date', { ascending: true })
        ).then(function (result) {
          if (result.error) throw result.error;
          return result.data || [];
        });
      })
      .catch(function (err) {
        if (typeof console !== 'undefined' && console.warn) {
          console.warn('fetchSignalsFromSupabase failed:', err && err.message ? err.message : err);
        }
        return [];
      });
  }

  /**
   * @param {string} pair
   * @returns {Promise<object|null>}
   */
  function fetchLatestSignalRow(pair) {
    var normPair = normalisePair(pair);
    return initDataClient()
      .then(function (client) {
        if (!client) return null;
        return queryWithTimeout(
          client
            .from('signals')
            .select('*')
            .eq('pair', normPair)
            .order('date', { ascending: false })
            .limit(1)
        ).then(function (result) {
          if (result.error) throw result.error;
          return result.data && result.data[0] ? result.data[0] : null;
        });
      })
      .catch(function (err) {
        if (typeof console !== 'undefined' && console.warn) {
          console.warn('fetchLatestSignalRow failed:', err && err.message ? err.message : err);
        }
        return null;
      });
  }

  function getDataFreshness(dateStr) {
    if (!dateStr) return 'no-data';
    var dataDate = new Date(String(dateStr).slice(0, 10) + 'T12:00:00Z');
    var now = new Date();
    var diffDays = Math.floor((now - dataDate) / (1000 * 60 * 60 * 24));
    if (diffDays <= 3) return 'live';
    if (diffDays <= 7) return 'stale';
    return 'no-data';
  }

  function getFreshnessLabel(dateStr) {
    var status = getDataFreshness(dateStr);
    var map = {
      live: { text: 'LIVE', color: '#2DD4A0' },
      stale: { text: 'STALE', color: '#F59E0B' },
      'no-data': { text: 'NO DATA', color: '#F87171' },
    };
    return map[status];
  }

  var SIGNAL_CHART_MAP = {
    rate_diff_2y: {
      label: '2Y Rate Differential',
      tab: 'fundamentals',
      chartType: 'line',
      unit: '%',
      precision: 3,
      description: 'US minus foreign 2Y yield spread',
      bullishAbove: 0,
    },
    rate_diff_10y: {
      label: '10Y Rate Differential',
      tab: 'fundamentals',
      chartType: 'line',
      unit: '%',
      precision: 3,
      description: 'US minus foreign 10Y yield spread',
      bullishAbove: 0,
    },
    rate_diff_zscore: {
      label: 'Rate Diff Z-Score',
      tab: 'fundamentals',
      chartType: 'line',
      unit: '',
      precision: 2,
      description: '52-week normalised z-score of rate diff',
      bullishAbove: 0,
    },
    cot_lev_money_net: {
      label: 'Leveraged Money Net',
      tab: 'positioning',
      chartType: 'histogram',
      unit: 'contracts',
      precision: 0,
      description: 'CFTC leveraged money net position',
    },
    cot_asset_mgr_net: {
      label: 'Asset Manager Net',
      tab: 'positioning',
      chartType: 'histogram',
      unit: 'contracts',
      precision: 0,
      description: 'CFTC asset manager net position',
    },
    cot_percentile: {
      label: 'COT Percentile Rank',
      tab: 'positioning',
      chartType: 'line',
      unit: '%',
      precision: 1,
      description: '52-week percentile rank of net position',
      warningAbove: 90,
      warningBelow: 10,
    },
    realized_vol_5d: {
      label: '5D Realized Vol',
      tab: 'vol',
      chartType: 'line',
      unit: '%',
      precision: 2,
      description: '5-day annualised realized volatility',
    },
    realized_vol_20d: {
      label: '20D Realized Vol',
      tab: 'vol',
      chartType: 'line',
      unit: '%',
      precision: 2,
      description: '20-day annualised realized volatility',
    },
    implied_vol_30d: {
      label: '30D Implied Vol',
      tab: 'vol',
      chartType: 'line',
      unit: '%',
      precision: 2,
      description: '30-day implied volatility from options',
    },
    vol_skew: {
      label: 'Vol Skew',
      tab: 'vol',
      chartType: 'line',
      unit: '%',
      precision: 2,
      description: 'Implied vol skew — put vs call premium',
    },
    atm_vol: {
      label: 'ATM Vol',
      tab: 'vol',
      chartType: 'line',
      unit: '%',
      precision: 2,
      description: 'At-the-money implied volatility',
    },
    risk_reversal_25d: {
      label: '25D Risk Reversal',
      tab: 'vol',
      chartType: 'line',
      unit: '%',
      precision: 2,
      description: '25-delta risk reversal — directional skew',
    },
    oi_delta: {
      label: 'OI Delta',
      tab: 'cross_asset',
      chartType: 'histogram',
      unit: '',
      precision: 0,
      description: 'Open interest change — positioning pressure',
    },
    oi_price_alignment: {
      label: 'OI / Price Alignment',
      tab: 'cross_asset',
      chartType: 'line',
      unit: '',
      precision: 2,
      description: 'OI and price direction alignment score',
    },
    cross_asset_vix: {
      label: 'VIX',
      tab: 'cross_asset',
      chartType: 'area',
      unit: '',
      precision: 2,
      description: 'VIX as USD risk-off regime input',
      color: '#F59E0B',
    },
    cross_asset_dxy: {
      label: 'DXY',
      tab: 'cross_asset',
      chartType: 'area',
      unit: '',
      precision: 3,
      description: 'Dollar index as cross-pair context',
      color: '#4D8EFF',
    },
    cross_asset_oil: {
      label: 'Brent Oil',
      tab: 'cross_asset',
      chartType: 'line',
      unit: 'USD',
      precision: 2,
      description: 'Brent crude as terms-of-trade input',
      color: '#F59E0B',
    },
  };

  function computeSignalStack(latestRow) {
    if (!latestRow) return null;

    function dir(value, bullishAbove) {
      var thr = bullishAbove != null ? bullishAbove : 0;
      if (value === null || value === undefined) return 'neutral';
      return value > thr ? 'bullish' : 'bearish';
    }

    var rateScore = latestRow.rate_diff_zscore || 0;
    var volScore =
      -((latestRow.realized_vol_20d || 0) - (latestRow.implied_vol_30d || 0));
    var crossScore = -((latestRow.cross_asset_vix || 20) - 20) / 20;

    return [
      {
        label: 'Rate Differentials',
        direction: dir(rateScore),
        contribution: Math.min(100, Math.abs(rateScore) * 30),
        value: latestRow.rate_diff_2y,
        unit: '%',
      },
      {
        label: 'COT Positioning',
        direction:
          (latestRow.cot_percentile || 50) > 75
            ? 'bullish'
            : (latestRow.cot_percentile || 50) < 25
              ? 'bearish'
              : 'neutral',
        contribution: Math.abs((latestRow.cot_percentile || 50) - 50) * 2,
        value: latestRow.cot_percentile,
        unit: 'th pct',
      },
      {
        label: 'Vol & Correlation',
        direction: dir(volScore),
        contribution: Math.min(100, Math.abs(volScore) * 20),
        value: latestRow.realized_vol_20d,
        unit: '%',
      },
      {
        label: 'Cross Asset',
        direction: dir(crossScore),
        contribution: Math.min(100, Math.abs(crossScore) * 100),
        value: latestRow.cross_asset_vix,
        unit: '',
      },
    ];
  }

  function fetchPipelineStatus() {
    return initDataClient()
      .then(function (client) {
        if (!client) return { last_run: null, status: 'unknown' };
        return queryWithTimeout(
          client.from('signals').select('date, pair').order('date', { ascending: false }).limit(1)
        ).then(function (result) {
          if (result.error) throw result.error;
          var latest = result.data && result.data[0];
          return {
            last_run: latest && latest.date ? String(latest.date).slice(0, 10) : null,
            status: latest ? 'live' : 'unknown',
          };
        });
      })
      .catch(function (err) {
        if (typeof console !== 'undefined' && console.warn) {
          console.warn('fetchPipelineStatus failed:', err && err.message ? err.message : err);
        }
        return { last_run: null, status: 'unknown' };
      });
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

  function num(x) {
    if (x === '' || x == null) return NaN;
    var n = parseFloat(String(x).replace(/,/g, ''));
    return isFinite(n) ? n : NaN;
  }

  var _lastPipelineStatus = null;
  var _inFlightSignals = new Map();
  var CACHE_TTL = 5 * 60 * 1000; // 5 minutes
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

  function fetchJsonWithTimeout(url, timeoutMs) {
    var ms = timeoutMs || FETCH_TIMEOUT_MS;
    var options = {};
    var timer = null;
    if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
      options.signal = AbortSignal.timeout(ms);
    } else {
      var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
      timer = setTimeout(function () {
        if (controller) controller.abort();
      }, ms);
      if (controller) options.signal = controller.signal;
    }
    return fetch(url, options)
      .then(function (r) {
        if (!r.ok) throw new Error('fetch ' + url);
        return r.json();
      })
      .finally(function () {
        if (timer) clearTimeout(timer);
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

  function emptyColsObject(cols) {
    var empty = {};
    cols.forEach(function (c) {
      empty[c] = [];
    });
    return empty;
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
        return emptyColsObject(cols);
      }
      var sel = ['date']
        .concat(cols)
        .filter(function (c, i, a) {
          return c && a.indexOf(c) === i;
        });
      var selStr = sel.join(',');
      var allRows = [];
      var offset = 0;
      function fetchNextPage() {
        return queryWithTimeout(
          client
            .from('signals')
            .select(selStr)
            .eq('pair', np)
            .gte('date', start)
            .order('date', { ascending: true })
            .range(offset, offset + SUPABASE_PAGE_SIZE - 1)
        ).then(function (res) {
          if (res.error) {
            if (typeof console !== 'undefined' && console.error) {
              console.error('[DataClient] Supabase error:', res.error.message || String(res.error));
            }
            return emptyColsObject(cols);
          }
          var chunk = res.data || [];
          for (var i = 0; i < chunk.length; i++) allRows.push(chunk[i]);
          if (chunk.length < SUPABASE_PAGE_SIZE) {
            if (allRows.length > 0) {
              var built = buildTimeSeriesResult(allRows, cols);
              setCached(cacheKey, built);
              return built;
            }
            if (typeof console !== 'undefined' && console.warn) {
              console.warn('[DataClient] No data for ' + np);
            }
            return emptyColsObject(cols);
          }
          offset += SUPABASE_PAGE_SIZE;
          return fetchNextPage();
        });
      }
      return fetchNextPage().catch(function (e) {
        if (typeof console !== 'undefined' && console.error) {
          console.error('[DataClient] Supabase fetch threw:', e && e.message ? e.message : e);
        }
        return emptyColsObject(cols);
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
  function fetchFromSupabase(pair, client, startDate) {
    var np = normalisePair(pair);
    var start = startDate || '2020-01-01';
    var all = [];
    var offset = 0;
    function fetchNextPage() {
      return queryWithTimeout(
        client
          .from('signals')
          .select('*')
          .eq('pair', np)
          .gte('date', start)
          .order('date', { ascending: true })
          .range(offset, offset + SUPABASE_PAGE_SIZE - 1)
      ).then(function (res) {
        if (res.error) throw res.error;
        var chunk = res.data || [];
        for (var i = 0; i < chunk.length; i++) all.push(chunk[i]);
        if (chunk.length < SUPABASE_PAGE_SIZE) return all;
        offset += SUPABASE_PAGE_SIZE;
        return fetchNextPage();
      });
    }
    return fetchNextPage();
  }

  function fetchSignalRows(pair, startDate) {
    return initDataClient().then(function (client) {
      if (!client) return null;
      var np = normalisePair(pair);
      return fetchFromSupabase(np, client, startDate || '2020-01-01').catch(function (e) {
        if (typeof console !== 'undefined' && console.error) console.error('FXRLData: signals fetch', e);
        return null;
      });
    });
  }

  function loadData(pair, startDate) {
    var np = normalisePair(pair);
    return initDataClient().then(function (client) {
      if (!client) return null;
      return fetchFromSupabase(np, client, startDate || '2020-01-01').catch(function (e) {
        if (typeof console !== 'undefined' && console.warn) {
          console.warn('[DataClient] Supabase failed:', e && e.message ? e.message : e);
        }
        return null;
      });
    });
  }

  /** ~3Y window for pair charts (range buttons up to 2Y). */
  var PAIR_SIGNALS_WINDOW_DAYS = 1095;

  function loadPairDataset(pair, startDate) {
    void startDate;
    var np = normalisePair(pair);
    return initDataClient().then(function (client) {
      if (!client) {
        return {
          sbRows: null,
          latestDate: null,
          dataSource: 'none',
          supabaseFetchFailed: true,
          supabaseClientMissing: true,
          masterText: null,
          cotText: null,
        };
      }
      return fetchSignalsFromSupabase(np, PAIR_SIGNALS_WINDOW_DAYS).then(function (rows) {
        var sbRows = rows && rows.length ? rows : null;
        var latestDate = null;
        if (sbRows && sbRows.length) {
          latestDate = String(sbRows[sbRows.length - 1].date || '').slice(0, 10);
        }
        if (latestDate) setDataDate(latestDate);
        return {
          sbRows: sbRows,
          masterText: null,
          cotText: null,
          latestDate: latestDate,
          dataSource: sbRows ? 'supabase' : 'none',
          supabaseFetchFailed: !sbRows,
          supabaseClientMissing: false,
        };
      });
    });
  }

  /**
   * @param {string} pair
   * @param {number} days
   */
  function fetchRegimeCalls(pair, days) {
    var n = Math.max(1, Math.min(500, days != null ? days : 1));
    return initDataClient().then(function (client) {
      if (!client) return [];
      var np = normalisePair(pair);
      return queryWithTimeout(
        client
          .from('regime_calls')
          .select('pair, date, regime, confidence, primary_driver')
          .eq('pair', np)
          .order('date', { ascending: false })
          .limit(n)
      )
        .then(function (res) {
          if (res.error) throw res.error;
          var rows = res.data || [];
          return rows.map(function (r) {
            return {
              date: String(r.date || '').slice(0, 10),
              regime: r.regime || '',
              confidence: r.confidence != null ? Number(r.confidence) : NaN,
              primary_driver: r.primary_driver || '',
            };
          });
        })
        .catch(function (err) {
          if (typeof console !== 'undefined' && console.warn) {
            console.warn('fetchRegimeCalls failed:', err && err.message ? err.message : err);
          }
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
          .limit(1)
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
          .order('date', { ascending: false })
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
          .limit(5)
      )
        .then(function (res) {
          if (res && res.error) return;
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

  function fetchLatestPrices() {
    return initDataClient().then(function (client) {
      if (!client) return null;
      return queryWithTimeout(
        client
          .from('signals')
          .select('date,pair,cross_asset_dxy,cross_asset_oil,cross_asset_vix,realized_vol_5d')
          .in('pair', ['EURUSD', 'USDJPY', 'USDINR'])
          .order('date', { ascending: false })
          .limit(90)
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

  /** Canonical labels for regime_calls.primary_driver-style tokens (legacy export). */
  var DRIVER_LABELS = {
    eurusd_composite: 'EUR/USD Composite',
    usdjpy_composite: 'USD/JPY Composite',
    usdinr_composite: 'USD/INR Composite',
    rate_differential: 'Rate Differential',
    rate_diff: 'Rate Differential',
    cot_positioning: 'COT Positioning',
    cot_position: 'COT Positioning',
    realized_vol: 'Realized Volatility',
    realized_volatility: 'Realized Volatility',
    vol_regime: 'Vol Regime',
    cross_asset: 'Cross-Asset Context',
    cross_asset_correlation: 'Cross-Asset Context',
    dxy_momentum: 'DXY Momentum',
    vix_regime: 'VIX Regime',
    carry: 'Carry Signal',
    momentum: 'Momentum',
    mean_reversion: 'Mean Reversion',
    inr_composite: 'USD/INR Composite',
  };

  /**
   * Human-readable driver for UI (HOME cards, panel).
   * @param {string} raw
   * @returns {string}
   */
  function formatDriverLabel(raw) {
    if (!raw) return '—';
    var s0 = String(raw).trim();
    if (!s0) return '—';
    if (s0.indexOf(' ') >= 0 && s0.indexOf('_') < 0) return s0;
    var map = {
      eurusd_composite: 'EUR/USD Composite',
      usdjpy_composite: 'USD/JPY Composite',
      usdinr_composite: 'USD/INR Composite',
      rate_differential: 'Rate Differential',
      rate_diff: 'Rate Differential',
      cot_positioning: 'COT Positioning',
      cot_position: 'COT Positioning',
      realized_vol: 'Realized Volatility',
      realized_volatility: 'Realized Volatility',
      vol_regime: 'Vol Regime',
      cross_asset: 'Cross-Asset Context',
      cross_asset_correlation: 'Cross-Asset Context',
      dxy_momentum: 'DXY Momentum',
      vix_regime: 'VIX Regime',
      carry: 'Carry Signal',
      momentum: 'Momentum',
      mean_reversion: 'Mean Reversion',
      inr_composite: 'USD/INR Composite',
    };
    var key = s0.toLowerCase();
    if (map[key]) return map[key];
    return s0
      .replace(/_/g, ' ')
      .replace(/\b\w/g, function (c) {
        return c.toUpperCase();
      });
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
   * Pair terminal strip: Live + date (Supabase-only).
   * @param {string} source loadPairDataset dataSource: supabase | none
   * @param {string} latestDate YYYY-MM-DD
   * @param {ParentNode} [root] default document
   * @param {{ supabaseFetchFailed?: boolean, supabaseClientMissing?: boolean }} [meta]
   */
  function showPairDataStatus(source, latestDate, root, meta) {
    meta = meta || {};
    var doc = root && root.querySelector ? root : document;
    var statusEl = doc.querySelector ? doc.querySelector('.pair-data-status') : null;
    if (!statusEl) return;
    var ymd = String(latestDate || '').slice(0, 10);
    var dateFmt = _fmtDataDate(ymd);
    var prefix = '—';
    var warnTitle = '';
    var sbDown = !!(meta.supabaseFetchFailed || meta.supabaseClientMissing);
    if (source === 'supabase') {
      prefix = 'Live';
    }
    if (sbDown) {
      warnTitle = 'Supabase unavailable — check connection and credentials.';
    }
    statusEl.textContent = dateFmt ? prefix + ' · ' + dateFmt : prefix;
    statusEl.setAttribute('title', warnTitle);
    statusEl.setAttribute('data-term-source', source || 'none');
    if (source === 'supabase') {
      statusEl.style.color = sbDown ? '#f59e0b' : 'var(--bullish)';
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
    return fetchJsonWithTimeout('/static/ai_article.json', 4000)
      .then(function (j) {
        return j && typeof j === 'object' ? j : null;
      })
      .catch(function () {
        return null;
      });
  }

  /**
   * HOME brief card: brief_log → /static/ai_article.json → placeholder.
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
      .then(function (j) {
        if (j && j.last_supabase_write) {
          applyPipelineNavStatus(j);
          return;
        }
        return fetchPipelineStatus().then(function (sb) {
          if (sb && sb.last_run) {
            applyPipelineNavStatus({
              supabase_write_status: sb.status === 'live' ? 'ok' : 'unknown',
              last_supabase_write: sb.last_run + 'T12:00:00Z',
              last_run_utc: sb.last_run + 'T12:00:00Z',
            });
          } else {
            applyPipelineNavStatus(null);
          }
        });
      })
      .catch(function () {
        return fetchPipelineStatus().then(function (sb) {
          if (sb && sb.last_run) {
            applyPipelineNavStatus({
              supabase_write_status: sb.status === 'live' ? 'ok' : 'unknown',
              last_supabase_write: sb.last_run + 'T12:00:00Z',
              last_run_utc: sb.last_run + 'T12:00:00Z',
            });
          } else {
            applyPipelineNavStatus(null);
          }
        });
      });

    var pairs = [
      { pair: 'EURUSD', card: '.term-card--eur' },
      { pair: 'USDJPY', card: '.term-card--jpy' },
      { pair: 'USDINR', card: '.term-card--inr' },
    ];

    var pRegime = pairs.map(function (x) {
      return fetchRegimeCalls(x.pair, 1).then(function (rows) {
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
          var latest = pack.rows.length ? pack.rows[0] : null;
          if (hasSb && (!latest || !latest.regime)) stale = true;
          if (!hasSb) return;

          var badge = card.querySelector('.term-card__badge');
          var regimeLine = card.querySelector('[data-card-regime]');
          var pctEl = card.querySelector('.term-card__conf-pct');
          var fill = card.querySelector('.term-card__conf-fill');
          var driver = card.querySelector('.term-card__driver');
          var confCenter = card.querySelector('.term-card__confidence');
          var lowNote = card.querySelector('.term-card__conf-note');
          if (badge) badge.textContent = latest ? formatRegimeLabel(latest.regime) : '—';
          if (regimeLine) regimeLine.textContent = latest ? formatRegimeLabel(latest.regime) : '—';
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
              var r = pack.rows && pack.rows.length ? pack.rows[0] : null;
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
        if (typeof global.__clearInitGuard === 'function') global.__clearInitGuard();
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
    fetchSignals: fetchSignals,
    fetchSignalsFromSupabase: fetchSignalsFromSupabase,
    fetchLatestSignalRow: fetchLatestSignalRow,
    getDataFreshness: getDataFreshness,
    getFreshnessLabel: getFreshnessLabel,
    SIGNAL_CHART_MAP: SIGNAL_CHART_MAP,
    computeSignalStack: computeSignalStack,
    fetchPipelineStatus: fetchPipelineStatus,
    fetchRegimeCalls: fetchRegimeCalls,
    fetchLatestBrief: fetchLatestBrief,
    fetchBriefPreview: fetchBriefPreview,
    fetchValidationLog: fetchValidationLog,
    checkPipelineErrors: checkPipelineErrors,
    fetchSignalRows: fetchSignalRows,
    fetchFromSupabase: fetchFromSupabase,
    loadData: loadData,
    loadPairDataset: loadPairDataset,
    setDataDate: setDataDate,
    getDataDate: getDataDate,
    DATA_UPDATING_MESSAGE: DATA_UPDATING_MESSAGE,
    initTerminalHome: initTerminalHome,
    fetchLatestPrices: fetchLatestPrices,
    buildCotArraysFromSignals: buildCotArraysFromSignals,
    DRIVER_LABELS: DRIVER_LABELS,
    formatDriverLabel: formatDriverLabel,
    formatRegimeLabel: formatRegimeLabel,
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
            client.from('signals').select('date,pair,rate_diff_2y').order('date', { ascending: false }).limit(1)
          );
          if (q.error) throw q.error;
          console.info('Supabase signals query:', q.data && q.data.length > 0 ? 'OK - latest: ' + q.data[0].date : 'EMPTY');
        } catch (e) {
          console.info('Supabase signals query: FAILED -', e && e.message ? e.message : e);
        }
      }

      if (global.FXRLData && typeof global.FXRLData.fetchSignalsFromSupabase === 'function') {
        var rows = await global.FXRLData.fetchSignalsFromSupabase('EURUSD', 30);
        console.info('fetchSignalsFromSupabase(EURUSD, 30):', rows && rows.length ? rows.length + ' rows' : 'empty');
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