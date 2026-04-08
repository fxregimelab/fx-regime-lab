/* pair-boot.js — shared pair page initialiser */
(function (global) {
  'use strict';

  var chartInitDone = {};

  function updateHero(pair, latest, regime) {
    var D = global.FXRLData;
    if (!D) return;

    var freshness = D.getFreshnessLabel(latest && latest.date);

    var badge = document.querySelector('[data-freshness-badge]');
    if (badge && freshness) {
      badge.textContent = freshness.text;
      badge.style.color = freshness.color;
      badge.style.borderColor = freshness.color;
    }

    var dateEl = document.querySelector('[data-last-updated]');
    if (dateEl && latest && latest.date) {
      dateEl.textContent = 'Last updated ' + String(latest.date).slice(0, 10);
    }

    var sigDate = document.querySelector('[data-signal-date]');
    if (sigDate && latest && latest.date) {
      sigDate.textContent = 'Signals ' + String(latest.date).slice(0, 10);
    }

    var regimeBadge = document.querySelector('[data-regime-badge]');
    var regimeClass =
      regime && regime.regime && String(regime.regime).toLowerCase().includes('bull')
        ? 'bullish'
        : regime && regime.regime && String(regime.regime).toLowerCase().includes('bear')
        ? 'bearish'
        : 'neutral';

    if (regimeBadge && regime && regime.regime) {
      regimeBadge.className = 'term-cmd-regime ' + regimeClass;
      regimeBadge.textContent = String(regime.regime).toUpperCase();
    } else if (regimeBadge) {
      regimeBadge.className = 'term-cmd-regime neutral';
      regimeBadge.textContent = '—';
    }

    var hdrBadge = document.getElementById('hdr-regime-badge');
    if (hdrBadge && regime && regime.regime) {
      hdrBadge.textContent = D.formatRegimeLabel ? D.formatRegimeLabel(regime.regime) : String(regime.regime);
    }

    var hdrScore = document.getElementById('hdr-score');
    if (hdrScore && regime && regime.confidence !== undefined && regime.confidence !== null) {
      var hpct = D.confidenceToPercent ? D.confidenceToPercent(regime.confidence) : NaN;
      hdrScore.textContent = isFinite(hpct) ? String(hpct) : '—';
    }

    var confEl = document.querySelector('[data-confidence]');
    if (confEl) {
      if (regime && regime.confidence !== undefined && regime.confidence !== null) {
        var pct = D.confidenceToPercent ? D.confidenceToPercent(regime.confidence) : NaN;
        confEl.textContent = isFinite(pct) ? pct + '%' : '—';
      } else {
        confEl.textContent = '—';
      }
    }

    var driverEl = document.querySelector('[data-driver]');
    if (driverEl && regime && regime.primary_driver) {
      driverEl.textContent = D.formatDriverLabel ? D.formatDriverLabel(regime.primary_driver) : String(regime.primary_driver);
    }

    var volEl = document.querySelector('[data-vol-regime]');
    if (volEl && latest && latest.realized_vol_20d != null) {
      var vol = Number(latest.realized_vol_20d);
      var label = vol < 5 ? 'LOW' : vol < 10 ? 'NORMAL' : vol < 15 ? 'HIGH' : 'EXTREME';
      volEl.textContent = label;
      volEl.style.color =
        vol < 5 ? '#2DD4A0' : vol < 10 ? '#8B9BB4' : vol < 15 ? '#F59E0B' : '#F87171';
    }
  }

  function renderSignalStack(stack) {
    var container = document.querySelector('[data-signal-stack]');
    if (!container || !stack) return;

    function dirIcon(d) {
      return d === 'bullish' ? '↑' : d === 'bearish' ? '↓' : '→';
    }

    function dirColor(d) {
      return d === 'bullish' ? '#2DD4A0' : d === 'bearish' ? '#F87171' : '#8B9BB4';
    }

    container.innerHTML =
      '<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:12px;">' +
      '<thead><tr style="border-bottom:1px solid rgba(255,255,255,0.08);">' +
      '<th style="text-align:left;padding:8px 0;color:#4A5568;font-weight:500;letter-spacing:0.08em;font-size:10px;">SIGNAL</th>' +
      '<th style="text-align:center;padding:8px 0;color:#4A5568;font-weight:500;letter-spacing:0.08em;font-size:10px;">DIRECTION</th>' +
      '<th style="text-align:right;padding:8px 0;color:#4A5568;font-weight:500;letter-spacing:0.08em;font-size:10px;">CONTRIBUTION</th>' +
      '</tr></thead><tbody>' +
      stack
        .map(function (s) {
          return (
            '<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">' +
            '<td style="padding:12px 0;color:#E8EDF2;">' +
            s.label +
            '</td>' +
            '<td style="padding:12px 0;text-align:center;color:' +
            dirColor(s.direction) +
            ';">' +
            dirIcon(s.direction) +
            ' ' +
            String(s.direction).toUpperCase() +
            '</td>' +
            '<td style="padding:12px 0;text-align:right;">' +
            '<div style="display:flex;align-items:center;gap:8px;justify-content:flex-end;">' +
            '<div style="width:80px;height:4px;background:rgba(255,255,255,0.08);border-radius:2px;overflow:hidden;">' +
            '<div style="width:' +
            s.contribution +
            '%;height:100%;background:' +
            dirColor(s.direction) +
            ';border-radius:2px;"></div>' +
            '</div>' +
            '<span style="color:#8B9BB4;min-width:32px;text-align:right;">' +
            Math.round(s.contribution) +
            '%</span>' +
            '</div></td></tr>'
          );
        })
        .join('') +
      '</tbody></table>';
    container.classList.add('term-fade-in');
  }

  function initTabCharts(tabName, rows, pair) {
    if (chartInitDone[tabName]) return;
    chartInitDone[tabName] = true;

    var FX = global.FXRLCharts;
    var D = global.FXRLData;
    if (!FX || !D || !D.SIGNAL_CHART_MAP) return;

    var color = FX.pairColor(pair);
    var map = D.SIGNAL_CHART_MAP;

    Object.keys(map).forEach(function (col) {
      var cfg = map[col];
      if (!cfg || cfg.tab !== tabName) return;

      var containerId = 'chart-' + col;
      var container = document.getElementById(containerId);
      if (!container) return;

      var data = [];
      for (var i = 0; i < (rows || []).length; i++) {
        var r = rows[i];
        if (!r || r[col] === null || r[col] === undefined) continue;
        var v = parseFloat(r[col]);
        if (!isFinite(v)) continue;
        data.push({ date: r.date, value: v });
      }

      var prec = cfg.precision != null ? cfg.precision : 2;
      var minMove = Math.pow(10, -prec);
      var opts = {
        color: cfg.color || color,
        precision: prec,
        skipRangeButtons: true,
        emptyMessage: (cfg.description || col) + ' — no data yet',
        priceFormat: {
          type: 'price',
          precision: prec,
          minMove: minMove,
        },
      };

      var chartPromise;
      if (cfg.chartType === 'histogram') {
        chartPromise = FX.histogram(containerId, data, opts);
      } else if (cfg.chartType === 'area') {
        chartPromise = FX.area(containerId, data, opts);
      } else {
        chartPromise = FX.line(containerId, data, opts);
      }

      chartPromise.then(function (instance) {
        if (instance && FX.register) {
          FX.register(containerId, instance);
        }
      });
    });
  }

  function wireTabs(rows, pair, pairConfig) {
    var tabs = document.querySelectorAll('[data-tab-btn]');

    tabs.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var tabName = btn.getAttribute('data-tab-btn');
        if (!tabName) return;

        document.querySelectorAll('[data-tab-panel]').forEach(function (p) {
          p.style.display = 'none';
        });

        var panel = document.querySelector('[data-tab-panel="' + tabName + '"]');
        if (panel) {
          panel.style.display = 'block';
          panel.classList.remove('term-fade-in');
          panel.offsetHeight;
          panel.classList.add('term-fade-in');
        }

        tabs.forEach(function (t) {
          t.classList.remove('tab-active');
        });
        btn.classList.add('tab-active');

        initTabCharts(tabName, rows, pair);
      });
    });
  }

  /**
   * @param {string} pair e.g. EURUSD
   * @param {{ defaultTab?: string }} pairConfig
   */
  function bootPairPage(pair, pairConfig) {
    pairConfig = pairConfig || {};
    var D = global.FXRLData;
    if (!D || typeof D.initDataClient !== 'function') {
      return Promise.resolve();
    }

    var normPair = String(pair || '')
      .replace(/\//g, '')
      .toUpperCase();

    return D.initDataClient()
      .then(function () {
        return D.fetchLatestSignalRow(normPair);
      })
      .then(function (latest) {
        return D.fetchRegimeCalls(normPair, 1).then(function (regimeCalls) {
          var regime = regimeCalls && regimeCalls.length ? regimeCalls[0] : null;
          updateHero(pair, latest, regime);

          var stack = D.computeSignalStack ? D.computeSignalStack(latest) : null;
          renderSignalStack(stack);

          return D.fetchSignalsFromSupabase(normPair, 730).then(function (rows) {
            var rowsArr = rows || [];
            if (D.showPairDataStatus) {
              var ld = latest && latest.date ? String(latest.date).slice(0, 10) : '';
              D.showPairDataStatus(rowsArr.length ? 'supabase' : 'none', ld, null, {
                supabaseFetchFailed: !rowsArr.length,
                supabaseClientMissing: !D.getSupabaseClient || !D.getSupabaseClient(),
              });
            }
            var defTab = pairConfig.defaultTab || 'fundamentals';
            initTabCharts(defTab, rowsArr, normPair);
            wireTabs(rowsArr, normPair, pairConfig);

            if (global.FXRLTerminalMotion && typeof global.FXRLTerminalMotion.initPageMotion === 'function') {
              var main = document.getElementById('term-pair-main');
              if (main) global.FXRLTerminalMotion.initPageMotion(main);
            }

            if (typeof global.__clearInitGuard === 'function') global.__clearInitGuard();
          });
        });
      })
      .catch(function (e) {
        if (typeof console !== 'undefined' && console.warn) {
          console.warn('[pair-boot]', e && e.message ? e.message : e);
        }
        if (typeof global.__clearInitGuard === 'function') global.__clearInitGuard();
      });
  }

  global.FXRLPairBoot = {
    bootPairPage: bootPairPage,
  };
})(window);
