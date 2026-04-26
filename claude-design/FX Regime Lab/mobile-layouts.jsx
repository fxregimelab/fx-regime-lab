
// ─── Local fmtSpot (not exported from components.jsx) ────────────────────────
function fmtSpot(v, pair) {
  if (v == null) return '—';
  return v.toFixed(pair === 'USDJPY' ? 2 : 4);
}

// ─── Mobile wrapper (375px container) ────────────────────────────────────────
function MobileFrame({ children, label, bg = '#fff' }) {
  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', verticalAlign: 'top' }}>
      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', letterSpacing: '0.1em', marginBottom: 8, textAlign: 'center' }}>{label}</div>
      <div style={{ width: 375, background: bg, border: '1px solid #e5e5e5', overflow: 'hidden', boxShadow: '0 4px 24px rgba(0,0,0,0.08)', position: 'relative', maxHeight: 812, overflowY: 'auto' }}>
        {children}
      </div>
      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#ccc', textAlign: 'center', marginTop: 6 }}>375 × 812 — iPhone 14</div>
    </div>
  );
}

// ─── MobileNav ────────────────────────────────────────────────────────────────
function MobileNav({ currentPage = 'home', onNavigate }) {
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const navLinks = [
    ['home', 'Home'], ['brief', 'Brief'], ['performance', 'Performance'],
    ['fx-regime', 'FX Regime'], ['calendar', 'Calendar'], ['about', 'About'],
  ];
  return (
    <>
      <header style={{ position: 'sticky', top: 0, zIndex: 100, background: '#fff', borderBottom: '1px solid #e5e5e5', height: 54, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <img src="logo.png" alt="" style={{ height: 20, width: 'auto' }} />
          <span style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 14, color: '#0a0a0a', letterSpacing: '-0.02em' }}>FX Regime Lab</span>
        </div>
        <button onClick={() => setDrawerOpen(true)} style={{ display: 'flex', flexDirection: 'column', gap: 5, padding: 4, background: 'none', border: 'none', cursor: 'pointer' }}>
          {[0,1,2].map(i => <div key={i} style={{ width: 22, height: 1.5, background: '#0a0a0a' }} />)}
        </button>
      </header>

      {/* Overlay */}
      {drawerOpen && (
        <div onClick={() => setDrawerOpen(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 200 }} />
      )}

      {/* Drawer */}
      <div style={{ position: 'fixed', top: 0, right: drawerOpen ? 0 : -300, width: 280, height: '100%', background: '#fff', borderLeft: '1px solid #e5e5e5', zIndex: 300, transition: 'right 0.25s ease', display: 'flex', flexDirection: 'column', padding: '16px 0' }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '0 16px 16px', borderBottom: '1px solid #f0f0f0' }}>
          <button onClick={() => setDrawerOpen(false)} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 18, color: '#aaa', lineHeight: 1, cursor: 'pointer' }}>×</button>
        </div>
        {navLinks.map(([slug, label]) => (
          <button key={slug} onClick={() => { onNavigate?.(slug); setDrawerOpen(false); }}
            style={{ fontFamily: 'Inter, sans-serif', fontSize: 15, color: currentPage === slug ? '#0a0a0a' : '#737373', fontWeight: currentPage === slug ? 600 : 400, padding: '14px 20px', textAlign: 'left', borderBottom: '1px solid #f8f8f8', background: 'none', cursor: 'pointer', borderLeft: currentPage === slug ? `3px solid ${BRAND.accent}` : '3px solid transparent' }}>
            {label}
          </button>
        ))}
        <div style={{ marginTop: 'auto', padding: '16px 20px', borderTop: '1px solid #f0f0f0' }}>
          <button onClick={() => { onNavigate?.('terminal'); setDrawerOpen(false); }}
            style={{ width: '100%', background: '#0a0a0a', color: '#fff', fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 13, padding: '12px 0', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, cursor: 'pointer', border: 'none' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4ade80' }} />
            Terminal
          </button>
        </div>
      </div>
    </>
  );
}

// ─── MobileHomePage ───────────────────────────────────────────────────────────
function MobileHomePage({ navigate }) {
  return (
    <div style={{ background: '#fff' }}>
      <MobileNav currentPage="home" onNavigate={navigate} />
      {/* Hero */}
      <div style={{ padding: '40px 16px 32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#22c55e' }} />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#737373', letterSpacing: '0.1em' }}>LIVE · G10 FX · DAILY CALLS</span>
        </div>
        <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 36, lineHeight: 1.1, color: '#0a0a0a', letterSpacing: '-0.03em', margin: '0 0 18px' }}>
          Daily regime<br />calls. On the<br />record.
        </h1>
        <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#525252', lineHeight: 1.7, marginBottom: 24 }}>
          G10 FX regime classification across EUR/USD, USD/JPY, and USD/INR. Every call public before market open. Every outcome validated.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <button onClick={() => navigate?.('brief')} style={{ background: '#0a0a0a', color: '#fff', fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 13, padding: '12px 20px', border: 'none', cursor: 'pointer', textAlign: 'center' }}>
            Read today's brief
          </button>
          <button onClick={() => navigate?.('performance')} style={{ background: 'none', color: '#0a0a0a', fontFamily: 'Inter, sans-serif', fontSize: 13, padding: '12px 0', border: 'none', cursor: 'pointer', textDecoration: 'underline', textDecorationColor: '#d0d0d0', textUnderlineOffset: 4 }}>
            Validation log →
          </button>
        </div>
        <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 7, paddingTop: 20, borderTop: '1px solid #f0f0f0' }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#22c55e' }} />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#a0a0a0', letterSpacing: '0.06em' }}>PIPELINE · {TODAY} 07:12 UTC</span>
        </div>
      </div>

      {/* HeroRegimeCard full width */}
      <div style={{ margin: '0 16px 32px', background: '#080808', border: '1px solid #1e1e1e', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, borderBottom: '1px solid #1a1a1a', paddingBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 7, height: 7, background: BRAND.eurusd }} />
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: BRAND.eurusd, fontWeight: 700 }}>EUR/USD</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#4ade80' }} />
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#555' }}>LIVE</span>
          </div>
        </div>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#999', letterSpacing: '0.12em', marginBottom: 4 }}>SPOT</p>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 28, fontWeight: 700, color: '#fff', letterSpacing: '-0.02em', marginBottom: 14 }}>1.0731</p>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 700, color: '#fff', marginBottom: 12 }}>MODERATE USD WEAKNESS</p>
        <ConfidenceBar value={0.72} tone="dark" color={BRAND.eurusd} />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5 }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#444' }}>CONFIDENCE</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: BRAND.eurusd, fontWeight: 700 }}>72%</span>
        </div>
      </div>

      {/* Stats bar — 2x2 */}
      <div style={{ borderTop: '1px solid #e5e5e5', borderBottom: '1px solid #e5e5e5', margin: '0 0 32px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
          {[['3', 'PAIRS TRACKED'], ['27', 'CALLS LOGGED'], ['77.8%', '7D ACCURACY'], ['4', 'SIGNAL FAMILIES']].map(([val, label], i) => (
            <div key={i} style={{ padding: '20px 16px', borderRight: i % 2 === 0 ? '1px solid #e5e5e5' : 'none', borderBottom: i < 2 ? '1px solid #e5e5e5' : 'none' }}>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 22, fontWeight: 700, color: '#0a0a0a', letterSpacing: '-0.03em', marginBottom: 4 }}>{val}</p>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#a0a0a0', letterSpacing: '0.08em' }}>{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Pair cards — single column */}
      <div style={{ padding: '0 16px 32px' }}>
        <h2 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 18, color: '#0a0a0a', letterSpacing: '-0.02em', marginBottom: 16 }}>Live Regime Snapshot</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, background: '#e5e5e5' }}>
          {PAIRS.map(p => {
            const call = MOCK_REGIME_CALLS[p.label];
            const sig = MOCK_SIGNALS[p.label];
            const chg = sig?.day_change_pct;
            return (
              <div key={p.label} onClick={() => navigate?.(`pairs/${p.urlSlug}`)}
                style={{ background: '#fff', padding: '16px', borderTop: `3px solid ${p.pairColor}`, cursor: 'pointer' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div>
                    <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 14, color: '#0a0a0a', marginBottom: 2 }}>{p.display}</p>
                    <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 18, fontWeight: 700, color: '#0a0a0a' }}>{fmtSpot(sig?.spot, p.label)}</p>
                  </div>
                  {chg != null && <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: chg >= 0 ? '#16a34a' : '#dc2626', background: chg >= 0 ? '#f0fdf4' : '#fff5f5', padding: '3px 7px' }}>{chg >= 0 ? '+' : ''}{chg.toFixed(2)}%</span>}
                </div>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fontWeight: 700, color: '#111', marginBottom: 10 }}>{call?.regime}</p>
                <ConfidenceBar value={call?.confidence} tone="light" color={p.pairColor} />
              </div>
            );
          })}
        </div>
      </div>

      {/* Regime heatmap — horizontal scroll */}
      <div style={{ borderTop: '1px solid #e5e5e5', borderBottom: '1px solid #e5e5e5', marginBottom: 32 }}>
        <div style={{ padding: '14px 16px', background: '#fafafa', borderBottom: '1px solid #e5e5e5' }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em' }}>30-DAY REGIME VIEW</span>
        </div>
        {PAIRS.map(p => (
          <div key={p.label} style={{ display: 'grid', gridTemplateColumns: '60px 1fr', borderBottom: '1px solid #f0f0f0' }}>
            <div style={{ padding: '10px 12px', borderRight: '1px solid #f0f0f0', display: 'flex', alignItems: 'center' }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: p.pairColor, fontWeight: 700 }}>{p.urlSlug.toUpperCase().slice(0, 6)}</span>
            </div>
            <div style={{ overflowX: 'auto', padding: '10px 12px', display: 'flex', gap: 2 }}>
              {MOCK_HEATMAP.dates.map((date, i) => (
                <div key={date} style={{ width: 12, height: 24, background: REGIME_HEATMAP_COLORS[MOCK_HEATMAP.regimes[p.label]?.[i]] ?? '#1a1a1a', flexShrink: 0 }} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{ padding: '24px 16px', borderTop: '1px solid #e5e5e5', background: '#fafafa' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', lineHeight: 1.8 }}>Research and learning only. Not investment advice. Shreyash Sakhare — Discretionary Macro Research.</p>
      </div>
    </div>
  );
}

// ─── MobileBriefPage ──────────────────────────────────────────────────────────
function MobileBriefPage({ navigate }) {
  const [activePair, setActivePair] = React.useState('ALL');
  return (
    <div>
      <MobileNav currentPage="brief" onNavigate={navigate} />
      <div style={{ padding: '24px 16px' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em', marginBottom: 8 }}>MORNING BRIEF · {TODAY}</p>
        <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 24, color: '#0a0a0a', letterSpacing: '-0.025em', marginBottom: 20 }}>Daily Brief</h1>
        {/* Macro context */}
        <div style={{ background: '#fafafa', border: '1px solid #e5e5e5', borderLeft: '3px solid #0a0a0a', padding: '14px 16px', marginBottom: 20 }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#888', letterSpacing: '0.1em', marginBottom: 6 }}>MACRO CONTEXT</p>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#333', lineHeight: 1.7 }}>Dollar index softening into month-end. Fed speaker today (14:00 ET). Risk-on tone with equities bid. DXY -0.18%.</p>
        </div>
      </div>
      {/* Scrollable pair tabs */}
      <div style={{ display: 'flex', overflowX: 'auto', borderBottom: '1px solid #e5e5e5', padding: '0 16px', gap: 0 }}>
        {['ALL', ...PAIRS.map(p => p.display)].map(label => {
          const active = activePair === label;
          const pm = PAIRS.find(p => p.display === label);
          return (
            <button key={label} onClick={() => setActivePair(label)}
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '10px 14px', color: active ? '#0a0a0a' : '#999', borderBottom: active ? `2px solid ${pm?.pairColor ?? '#0a0a0a'}` : '2px solid transparent', marginBottom: -1, whiteSpace: 'nowrap', fontWeight: active ? 700 : 400, background: 'none', cursor: 'pointer' }}>
              {label}
            </button>
          );
        })}
      </div>
      <div style={{ padding: '16px 16px 32px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {PAIRS.filter(p => activePair === 'ALL' || activePair === p.display).map(p => {
          const call = MOCK_REGIME_CALLS[p.label];
          const sig = MOCK_SIGNALS[p.label];
          const section = BRIEF_SECTIONS[p.label];
          return (
            <div key={p.label} style={{ border: '1px solid #e5e5e5', borderTop: `3px solid ${p.pairColor}` }}>
              {/* Pair header */}
              <div style={{ padding: '14px 16px', background: '#fafafa', borderBottom: '1px solid #f0f0f0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 700, color: p.pairColor }}>{p.display}</span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 18, fontWeight: 700, color: p.pairColor }}>{call ? Math.round(call.confidence * 100) : '—'}<span style={{ fontSize: 11, color: '#aaa', fontWeight: 400 }}>%</span></span>
                </div>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fontWeight: 700, color: '#0a0a0a', background: '#f0f0f0', display: 'inline-block', padding: '2px 7px', marginBottom: 6 }}>{section?.regime}</p>
                <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#737373', lineHeight: 1.5 }}>{section?.primaryDriver}</p>
              </div>
              {/* Signal snapshot — 2+3 layout */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', borderBottom: '1px solid #f0f0f0' }}>
                {[['SPOT', fmtSpot(sig?.spot, p.label)], ['RATE DIFF', fmt2(sig?.rate_diff_2y)], ['COT PCT', fmtInt(sig?.cot_percentile)], ['RVOL 20D', fmt2(sig?.realized_vol_20d)]].map(([lbl, val], i) => (
                  <div key={lbl} style={{ padding: '12px 14px', borderRight: i % 2 === 0 ? '1px solid #f0f0f0' : 'none', borderBottom: i < 2 ? '1px solid #f0f0f0' : 'none' }}>
                    <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', letterSpacing: '0.1em', marginBottom: 4 }}>{lbl}</p>
                    <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 700, color: '#0a0a0a' }}>{val}</p>
                  </div>
                ))}
              </div>
              {/* Analysis */}
              <div style={{ padding: '14px 16px' }}>
                {section?.analysis.split('\n\n').map((para, i) => (
                  <p key={i} style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: i === 1 ? '#111' : '#444', lineHeight: 1.75, marginBottom: 10, fontWeight: i === 1 ? 500 : 400 }}>{para}</p>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── MobilePerformancePage ────────────────────────────────────────────────────
function MobilePerformancePage({ navigate }) {
  const [filterPair, setFilterPair] = React.useState('ALL');
  const correct = MOCK_VALIDATION.filter(r => r.outcome === 'correct').length;
  const total = MOCK_VALIDATION.length;
  const accuracy = ((correct / total) * 100).toFixed(1);
  const avgReturn = (MOCK_VALIDATION.reduce((s, r) => s + r.return_pct, 0) / total).toFixed(2);
  const totalReturn = MOCK_EQUITY.ALL[MOCK_EQUITY.ALL.length - 1].toFixed(2);

  return (
    <div>
      <MobileNav currentPage="performance" onNavigate={navigate} />
      <div style={{ padding: '24px 16px 32px' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 8 }}>TRACK RECORD</p>
        <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 24, color: '#0a0a0a', letterSpacing: '-0.025em', marginBottom: 20 }}>Performance</h1>
        {/* 2x2 metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, background: '#e5e5e5', marginBottom: 20 }}>
          {[
            { label: '7D ACCURACY', value: `${accuracy}%`, color: '#16a34a' },
            { label: 'AVG RET', value: `${Number(avgReturn) >= 0 ? '+' : ''}${avgReturn}%`, color: BRAND.usdjpy },
            { label: 'CUMULATIVE', value: `+${totalReturn}%`, color: BRAND.eurusd },
            { label: 'CALLS', value: `${total}`, color: '#0a0a0a' },
          ].map(m => (
            <div key={m.label} style={{ background: '#fff', padding: '16px' }}>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#999', letterSpacing: '0.12em', marginBottom: 8 }}>{m.label}</p>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, fontWeight: 700, color: m.color, letterSpacing: '-0.03em' }}>{m.value}</p>
            </div>
          ))}
        </div>
        {/* Equity curve */}
        <div style={{ border: '1px solid #e5e5e5', marginBottom: 20 }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888' }}>CUMULATIVE RETURN</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, fontWeight: 700, color: '#16a34a' }}>+{totalReturn}%</p>
          </div>
          <div style={{ padding: '12px 16px 8px' }}>
            <svg width="100%" height="80" viewBox="0 0 340 80" preserveAspectRatio="none" style={{ display: 'block' }}>
              <defs><linearGradient id="mEqG" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#16a34a" stopOpacity="0.2" /><stop offset="100%" stopColor="#16a34a" stopOpacity="0" /></linearGradient></defs>
              {(() => {
                const vals = MOCK_EQUITY.ALL;
                const mn = Math.min(...vals) - 0.05, mx = Math.max(...vals) + 0.05;
                const n = vals.length;
                const pts = vals.map((v, i) => [i / (n - 1) * 340, 74 - (v - mn) / (mx - mn) * 66]);
                const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
                return (<><path d={`${line} L340,80 L0,80 Z`} fill="url(#mEqG)" /><path d={line} fill="none" stroke="#16a34a" strokeWidth="1.5" /></>);
              })()}
            </svg>
          </div>
        </div>
        {/* Pair filter */}
        <div style={{ display: 'flex', overflowX: 'auto', borderBottom: '1px solid #e5e5e5', marginBottom: 12, gap: 0 }}>
          {['ALL', ...PAIRS.map(p => p.display)].map(label => {
            const active = filterPair === label;
            const pm = PAIRS.find(p => p.display === label);
            return (
              <button key={label} onClick={() => setFilterPair(label)}
                style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '9px 12px', color: active ? '#0a0a0a' : '#999', borderBottom: active ? `2px solid ${pm?.pairColor ?? '#0a0a0a'}` : '2px solid transparent', marginBottom: -1, whiteSpace: 'nowrap', fontWeight: active ? 700 : 400, background: 'none', cursor: 'pointer' }}>
              {label}
            </button>
          );})}
        </div>
        {/* Table — horizontal scroll */}
        <div style={{ overflowX: 'auto', border: '1px solid #e5e5e5' }}>
          <table style={{ width: 500, borderCollapse: 'collapse', fontFamily: 'JetBrains Mono, monospace' }}>
            <thead>
              <tr style={{ background: '#fafafa', borderBottom: '1px solid #e5e5e5' }}>
                {['DATE','PAIR','OUTCOME','RET %'].map(h => <th key={h} style={{ padding: '9px 12px', textAlign: 'left', fontSize: 9, color: '#999', letterSpacing: '0.1em' }}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {MOCK_VALIDATION.filter(r => filterPair === 'ALL' || r.pair === filterPair).map((row, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #f5f5f5' }}>
                  <td style={{ padding: '9px 12px', fontSize: 10, color: '#555' }}>{row.date}</td>
                  <td style={{ padding: '9px 12px', fontSize: 10, fontWeight: 700, color: '#111' }}>{row.pair}</td>
                  <td style={{ padding: '9px 12px', fontSize: 10, fontWeight: 700, color: row.outcome === 'correct' ? '#16a34a' : '#dc2626' }}>{row.outcome === 'correct' ? '✓' : '✗'}</td>
                  <td style={{ padding: '9px 12px', fontSize: 11, fontWeight: 700, color: row.return_pct >= 0 ? '#16a34a' : '#dc2626' }}>{row.return_pct >= 0 ? '+' : ''}{row.return_pct.toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── MobileTerminalPairDeskPage ───────────────────────────────────────────────
function MobileTerminalPairDeskPage({ pairSlug = 'eurusd', navigate }) {
  const pair = PAIRS.find(p => p.urlSlug === pairSlug) ?? PAIRS[0];
  const call = MOCK_REGIME_CALLS[pair.label];
  const sig = MOCK_SIGNALS[pair.label];
  const [activeTab, setActiveTab] = React.useState('signals');
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const chg = sig?.day_change_pct;
  const composite = call?.signal_composite ?? 0;

  return (
    <div style={{ minHeight: '100vh', background: '#080808', color: '#e8e8e8' }}>
      {/* Terminal header */}
      <header style={{ background: '#080808', borderBottom: '1px solid #1e1e1e', padding: '10px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <img src="logo.png" alt="" style={{ height: 16, width: 'auto' }} />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#e8e8e8', fontWeight: 700 }}>Terminal</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333' }}>/ {pair.urlSlug}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#4ade80' }} />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#555' }}>LIVE</span>
        </div>
      </header>
      {/* Pair tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid #1e1e1e', overflowX: 'auto' }}>
        {PAIRS.map(p => (
          <button key={p.label} onClick={() => navigate?.(`terminal/${p.urlSlug}`)}
            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '8px 14px', color: p.label === pair.label ? p.pairColor : '#555', borderBottom: p.label === pair.label ? `2px solid ${p.pairColor}` : '2px solid transparent', whiteSpace: 'nowrap', background: p.label === pair.label ? '#0d0d0d' : 'transparent', cursor: 'pointer', marginBottom: -1, fontWeight: p.label === pair.label ? 700 : 400 }}>
            {p.display}
            {MOCK_SIGNALS[p.label]?.day_change_pct != null && (
              <span style={{ marginLeft: 6, color: MOCK_SIGNALS[p.label].day_change_pct >= 0 ? '#4ade80' : '#f87171' }}>
                {MOCK_SIGNALS[p.label].day_change_pct >= 0 ? '+' : ''}{MOCK_SIGNALS[p.label].day_change_pct.toFixed(2)}%
              </span>
            )}
          </button>
        ))}
      </div>

      {/* 2x2 top strip */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, padding: '2px', background: '#141414' }}>
        {[
          { label: 'SPOT', value: fmtSpot(sig?.spot, pair.label), sub: chg != null ? `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}% today` : null, subColor: chg >= 0 ? '#4ade80' : '#f87171', valueSize: 22 },
          { label: 'REGIME', value: call?.regime ?? '—', sub: call?.primary_driver?.slice(0, 30) + '…', subColor: '#888', valueSize: 11 },
          { label: 'CONFIDENCE', value: call ? `${Math.round(call.confidence * 100)}%` : '—', sub: null, subColor: pair.pairColor, valueSize: 28 },
          { label: 'COMPOSITE', value: composite >= 0 ? `+${fmt2(composite)}` : fmt2(composite), sub: null, subColor: composite >= 0 ? '#4ade80' : '#f87171', valueSize: 28 },
        ].map((item, i) => (
          <div key={i} style={{ background: '#0d0d0d', padding: '14px 16px' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#555', letterSpacing: '0.12em', marginBottom: 6 }}>{item.label}</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: item.valueSize, fontWeight: 700, color: item.subColor ?? '#fff', letterSpacing: '-0.02em', lineHeight: 1.2 }}>{item.value}</p>
            {item.sub && <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: item.subColor ?? '#888', marginTop: 5 }}>{item.sub}</p>}
          </div>
        ))}
      </div>

      {/* Tab strip — horizontal scroll */}
      <div style={{ display: 'flex', background: '#0a0a0a', borderBottom: '1px solid #1a1a1a', overflowX: 'auto' }}>
        {['signals','history','charts','attribution','calendar','ai'].map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, letterSpacing: '0.1em', padding: '10px 14px', color: activeTab === tab ? '#f0f0f0' : '#333', borderBottom: activeTab === tab ? `2px solid ${pair.pairColor}` : '2px solid transparent', marginBottom: -1, whiteSpace: 'nowrap', background: 'transparent', cursor: 'pointer' }}>
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ border: '1px solid #1a1a1a', borderTop: 'none', minHeight: 300 }}>
        {activeTab === 'signals' && (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'JetBrains Mono, monospace' }}>
            <tbody>
              {[
                ['Rate diff 2Y', fmt2(sig?.rate_diff_2y), call?.rate_signal === 'BULLISH' ? '↑' : '↓'],
                ['COT percentile', fmtInt(sig?.cot_percentile), sig?.cot_percentile > 60 ? '↑' : '↓'],
                ['Realized vol 20d', fmt2(sig?.realized_vol_20d), ''],
                ['Implied vol 30d', sig?.implied_vol_30d != null ? fmt2(sig?.implied_vol_30d) : '—', ''],
                ['Signal composite', fmt2(composite), composite >= 0 ? '↑' : '↓'],
              ].map(([label, value, dir], i) => (
                <tr key={label} style={{ borderBottom: '1px solid #0f0f0f', background: i % 2 === 0 ? '#0a0a0a' : '#0c0c0c' }}>
                  <td style={{ padding: '11px 16px', fontSize: 10, color: '#aaa' }}>{label}</td>
                  <td style={{ padding: '11px 16px', fontSize: 12, color: '#fff', fontWeight: 700 }}>{value}</td>
                  <td style={{ padding: '11px 16px', fontSize: 12, color: dir === '↑' ? '#4ade80' : dir === '↓' ? '#f87171' : '#555', fontWeight: 700 }}>{dir}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {activeTab !== 'signals' && (
          <div style={{ padding: '24px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333', letterSpacing: '0.1em' }}>{activeTab.toUpperCase()} TAB CONTENT</p>
            <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#2a2a2a', textAlign: 'center' }}>Tap to view {activeTab} data for {pair.display}</p>
          </div>
        )}
      </div>

      {/* Fixed bottom drawer trigger */}
      <button onClick={() => setDrawerOpen(true)}
        style={{ position: 'fixed', bottom: 20, right: 16, background: '#0a0a0a', color: '#e8e8e8', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, padding: '10px 18px', border: '1px solid #2a2a2a', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, boxShadow: '0 4px 20px rgba(0,0,0,0.6)', zIndex: 50 }}>
        ≡ More
      </button>

      {/* Bottom drawer overlay */}
      {drawerOpen && <div onClick={() => setDrawerOpen(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 100 }} />}

      {/* Bottom drawer */}
      <div style={{ position: 'fixed', bottom: drawerOpen ? 0 : '-100%', left: 0, right: 0, background: '#0c0c0c', border: '1px solid #1e1e1e', zIndex: 200, transition: 'bottom 0.3s ease', maxHeight: '75%', overflowY: 'auto' }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #141414', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#777', letterSpacing: '0.1em' }}>SIDEBAR</span>
          <button onClick={() => setDrawerOpen(false)} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 16, color: '#444', cursor: 'pointer' }}>×</button>
        </div>
        {/* Other Desks */}
        <div style={{ padding: '14px 16px', borderBottom: '1px solid #111' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em', marginBottom: 10 }}>OTHER DESKS</p>
          {PAIRS.filter(p => p.label !== pair.label).map(p => {
            const oc = MOCK_REGIME_CALLS[p.label];
            const os = MOCK_SIGNALS[p.label];
            return (
              <div key={p.label} onClick={() => { setDrawerOpen(false); navigate?.(`terminal/${p.urlSlug}`); }}
                style={{ background: '#0e0e0e', border: '1px solid #1e1e1e', borderLeft: `3px solid ${p.pairColor}`, padding: '10px 12px', marginBottom: 4, cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: p.pairColor, fontWeight: 700, marginBottom: 3 }}>{p.display}</p>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#888' }}>{oc?.regime}</p>
                </div>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 16, fontWeight: 700, color: '#e8e8e8' }}>{fmtSpot(os?.spot, p.label)}</p>
              </div>
            );
          })}
        </div>
        {/* Validation */}
        <div style={{ padding: '14px 16px', borderBottom: '1px solid #111' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.12em', marginBottom: 10 }}>RECENT VALIDATION</p>
          {MOCK_VALIDATION.filter(r => r.pair === pair.display).slice(0, 3).map((r, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: i < 2 ? '1px solid #111' : 'none' }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#777' }}>{r.date}</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: r.outcome === 'correct' ? '#4ade80' : '#f87171', fontWeight: 700 }}>{r.outcome === 'correct' ? '✓' : '✗'} {r.return_pct >= 0 ? '+' : ''}{r.return_pct.toFixed(2)}%</span>
            </div>
          ))}
        </div>
        {/* Pipeline */}
        <div style={{ padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4ade80' }} />
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#aaa' }}>PIPELINE LIVE · {TODAY}</span>
          </div>
          {[['SIGNALS','OK'],['REGIME CALLS','OK'],['VALIDATION','OK']].map(([l, s]) => (
            <div key={l} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #0f0f0f' }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#888' }}>{l}</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#4ade80', fontWeight: 700 }}>{s}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── MobileCalendarPage ───────────────────────────────────────────────────────
function MobileCalendarPage({ navigate }) {
  const [filterPair, setFilterPair] = React.useState('ALL');
  const [expandedEvent, setExpandedEvent] = React.useState(null);
  const today = new Date(TODAY);
  const daysUntil = (d) => Math.ceil((new Date(d) - today) / 86400000);
  const impactColor = (i) => i === 'HIGH' ? '#D94030' : '#F5923A';
  const filtered = filterPair === 'ALL' ? MOCK_CALENDAR : MOCK_CALENDAR.filter(e => e.pairs.includes(filterPair));

  return (
    <div>
      <MobileNav currentPage="calendar" onNavigate={navigate} />
      <div style={{ padding: '24px 16px 16px' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 8 }}>MACRO CALENDAR</p>
        <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 24, color: '#0a0a0a', letterSpacing: '-0.025em', marginBottom: 6 }}>Event Calendar</h1>
        <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#737373', marginBottom: 16 }}>Click any event for AI brief.</p>
        {/* FOMC banner — stacked */}
        {(() => {
          const fomc = MOCK_CALENDAR.find(e => e.event.includes('FOMC Rate'));
          if (!fomc) return null;
          const days = daysUntil(fomc.date);
          return (
            <div style={{ background: '#0a0a0a', border: '1px solid #1a1a1a', padding: '14px 16px', marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{ background: '#D94030', width: 3, height: 36, flexShrink: 0 }} />
                <div>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#444', letterSpacing: '0.1em', marginBottom: 4 }}>NEXT MAJOR EVENT</p>
                  <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 14, color: '#f0f0f0' }}>{fomc.event}</p>
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 8, borderTop: '1px solid #1a1a1a' }}>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#444' }}>{fomc.date}</p>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 20, fontWeight: 700, color: '#D94030' }}>{days}d</p>
              </div>
            </div>
          );
        })()}
      </div>
      {/* Pair filter — scroll */}
      <div style={{ display: 'flex', overflowX: 'auto', borderBottom: '1px solid #e5e5e5', padding: '0 16px', gap: 0, marginBottom: 8 }}>
        {['ALL', ...PAIRS.map(p => p.display)].map(label => {
          const pm = PAIRS.find(p => p.display === label);
          const active = filterPair === (label === 'ALL' ? 'ALL' : pm?.label ?? label);
          return (
            <button key={label} onClick={() => setFilterPair(label === 'ALL' ? 'ALL' : pm?.label ?? label)}
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '9px 12px', color: active ? '#0a0a0a' : '#999', borderBottom: active ? `2px solid ${pm?.pairColor ?? '#0a0a0a'}` : '2px solid transparent', marginBottom: -1, whiteSpace: 'nowrap', fontWeight: active ? 700 : 400, background: 'none', cursor: 'pointer' }}>
              {label}
            </button>
          );
        })}
      </div>
      {/* Events — date embedded in header */}
      <div style={{ padding: '8px 16px 32px', display: 'flex', flexDirection: 'column', gap: 1 }}>
        {filtered.map((e, i) => {
          const key = `${e.date}-${e.event}`;
          const isOpen = expandedEvent === key;
          const days = daysUntil(e.date);
          const dateObj = new Date(e.date + 'T00:00:00Z');
          const dayStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
          const impactPairs = e.pairs.map(lbl => PAIRS.find(p => p.label === lbl)).filter(Boolean);
          return (
            <div key={key} style={{ border: '1px solid #e5e5e5', borderTop: `2px solid ${impactColor(e.impact)}` }}>
              <button onClick={() => setExpandedEvent(isOpen ? null : key)}
                style={{ width: '100%', padding: '12px 14px', display: 'flex', alignItems: 'flex-start', gap: 10, background: isOpen ? '#fafafa' : '#fff', cursor: 'pointer', textAlign: 'left' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 44, paddingTop: 2 }}>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fontWeight: 700, color: '#0a0a0a' }}>{dayStr}</span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: days <= 2 ? '#D94030' : '#bbb', marginTop: 2, fontWeight: days <= 2 ? 700 : 400 }}>{days === 0 ? 'TODAY' : days === 1 ? 'TMRW' : `${days}d`}</span>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 13, color: '#0a0a0a', marginBottom: 4, textWrap: 'pretty' }}>{e.event}</p>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: impactColor(e.impact), fontWeight: 700 }}>{e.impact}</span>
                    {impactPairs.map(pm => <span key={pm.label} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: pm.pairColor }}>· {pm.display}</span>)}
                  </div>
                </div>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, color: '#bbb', transform: isOpen ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s', flexShrink: 0, display: 'inline-block', marginTop: 2 }}>›</span>
              </button>
              {isOpen && (
                <div style={{ background: '#fafafa', borderTop: '1px solid #ebebeb', padding: '14px 14px 16px' }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: impactColor(e.impact), letterSpacing: '0.1em', marginBottom: 8 }}>✦ AI BRIEF (MOCK)</p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#bbb', letterSpacing: '0.1em', marginBottom: 4 }}>OVERVIEW</p>
                      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#444', lineHeight: 1.65 }}>Key economic release tracked by FX participants for policy signals. Historically drives 20-40 pip moves in relevant pairs on surprise.</p>
                    </div>
                    <div style={{ background: '#fff', border: '1px solid #e5e5e5', padding: '10px 12px' }}>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: impactColor(e.impact), letterSpacing: '0.1em', marginBottom: 4 }}>EXPECTATIONS</p>
                      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#111', lineHeight: 1.65, fontWeight: 500 }}>Consensus and prior data would appear here in production. AI generation connects to Claude in Phase 5.</p>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {[['BEAT', 35, '#16a34a'], ['IN LINE', 45, '#737373'], ['MISS', 20, '#dc2626']].map(([type, prob, color]) => (
                        <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color, fontWeight: 700, minWidth: 50 }}>{type}</span>
                          <div style={{ flex: 1, background: '#ebebeb', height: 3 }}><div style={{ width: `${prob}%`, height: '100%', background: color }} /></div>
                          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color, fontWeight: 700, minWidth: 30, textAlign: 'right' }}>{prob}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── MobileAboutPage ──────────────────────────────────────────────────────────
function MobileAboutPage({ navigate }) {
  const [activeStep, setActiveStep] = React.useState(0);
  const steps = ['Ingest', 'Normalize', 'Composite', 'Regime', 'Validate'];
  const [expanded, setExpanded] = React.useState(null);
  const families = [
    { n: '01', label: 'Rate Differentials', color: BRAND.eurusd, summary: '2Y sovereign yield spreads. Structural anchor.' },
    { n: '02', label: 'COT Positioning', color: BRAND.usdjpy, summary: 'CFTC weekly non-commercial net positions.' },
    { n: '03', label: 'Realized Volatility', color: BRAND.usdinr, summary: '5d and 20d realized vs 30d implied. Vol gate at P90.' },
    { n: '04', label: 'OI and Risk Reversals', color: '#888', summary: '25-delta RR and open interest flows.' },
  ];

  return (
    <div>
      <MobileNav currentPage="about" onNavigate={navigate} />
      <div style={{ padding: '32px 16px' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 14 }}>ABOUT</p>
        <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 28, color: '#0a0a0a', letterSpacing: '-0.03em', lineHeight: 1.1, marginBottom: 20 }}>A research system.<br />Public by design.</h1>
        <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#525252', lineHeight: 1.8, marginBottom: 24 }}>EE undergrad studying how G10 FX regimes form and break. Dated calls, validated outcomes, no narrative after the fact.</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 32 }}>
          <button onClick={() => navigate?.('brief')} style={{ background: '#0a0a0a', color: '#fff', fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 13, padding: '12px', border: 'none', cursor: 'pointer' }}>Today's brief →</button>
          <button onClick={() => navigate?.('terminal')} style={{ background: 'none', color: '#0a0a0a', fontFamily: 'Inter, sans-serif', fontSize: 13, padding: '12px', border: '1px solid #e5e5e5', cursor: 'pointer' }}>Open terminal →</button>
        </div>
        {/* Pipeline steps — scroll strip */}
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 14 }}>METHODOLOGY</p>
        <div style={{ display: 'flex', overflowX: 'auto', gap: 1, marginBottom: 0, borderBottom: '1px solid #e5e5e5' }}>
          {steps.map((s, i) => (
            <button key={i} onClick={() => setActiveStep(i)}
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, padding: '10px 12px', color: activeStep === i ? '#0a0a0a' : '#bbb', borderBottom: activeStep === i ? `2px solid ${BRAND.accent}` : '2px solid transparent', whiteSpace: 'nowrap', marginBottom: -1, fontWeight: activeStep === i ? 700 : 400, background: 'none', cursor: 'pointer', letterSpacing: '0.06em' }}>
              {String(i+1).padStart(2,'0')} {s.toUpperCase()}
            </button>
          ))}
        </div>
        <div style={{ border: '1px solid #e5e5e5', borderTop: 'none', padding: '18px 16px', marginBottom: 32 }}>
          <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 16, color: '#0a0a0a', marginBottom: 8 }}>{steps[activeStep]}</p>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#737373', lineHeight: 1.7 }}>Pipeline step {activeStep + 1} of 5. Click steps above to explore each stage of the daily regime classification process.</p>
        </div>
        {/* Signal families */}
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 14 }}>SIGNAL ARCHITECTURE</p>
        <div style={{ border: '1px solid #e5e5e5', marginBottom: 32 }}>
          {families.map((fam, i) => (
            <div key={fam.id} style={{ borderBottom: i < families.length - 1 ? '1px solid #e5e5e5' : 'none' }}>
              <button onClick={() => setExpanded(expanded === i ? null : i)}
                style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 14, padding: '16px', background: expanded === i ? '#fafafa' : '#fff', cursor: 'pointer', textAlign: 'left' }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: fam.color, fontWeight: 700, minWidth: 24 }}>{fam.n}</span>
                <div style={{ flex: 1 }}>
                  <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 14, color: '#0a0a0a', marginBottom: 2 }}>{fam.label}</p>
                  <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#888' }}>{fam.summary}</p>
                </div>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, color: '#bbb', transform: expanded === i ? 'rotate(45deg)' : 'none', transition: 'transform 0.2s', flexShrink: 0 }}>+</span>
              </button>
              {expanded === i && (
                <div style={{ padding: '0 16px 16px 54px', background: '#fafafa', borderTop: '1px solid #ebebeb' }}>
                  <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#444', lineHeight: 1.75, paddingTop: 12 }}>Full signal family methodology appears here. This is the expanded body text for {fam.label.toLowerCase()} explaining how it feeds into the composite score.</p>
                </div>
              )}
            </div>
          ))}
        </div>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#ccc', lineHeight: 1.8 }}>RESEARCH AND LEARNING ONLY. NOT INVESTMENT ADVICE.</p>
      </div>
    </div>
  );
}

// ─── MobilePreviewGallery ─────────────────────────────────────────────────────
function MobilePreviewGallery({ navigate: rootNavigate }) {
  const [activePage, setActivePage] = React.useState('home');
  const pages = [
    { id: 'home', label: 'Home', component: <MobileHomePage navigate={() => {}} /> },
    { id: 'brief', label: 'Brief', component: <MobileBriefPage navigate={() => {}} /> },
    { id: 'performance', label: 'Performance', component: <MobilePerformancePage navigate={() => {}} /> },
    { id: 'calendar', label: 'Calendar', component: <MobileCalendarPage navigate={() => {}} /> },
    { id: 'terminal', label: 'Terminal Pair Desk', component: <MobileTerminalPairDeskPage pairSlug="eurusd" navigate={() => {}} /> },
    { id: 'about', label: 'About', component: <MobileAboutPage navigate={() => {}} /> },
  ];
  const current = pages.find(p => p.id === activePage);

  return (
    <div style={{ minHeight: '100vh', background: '#fafafa' }}>
      <div style={{ background: '#0a0a0a', padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#555', letterSpacing: '0.1em' }}>MOBILE LAYOUTS PREVIEW</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#333' }}>375px · iPhone 14</span>
        </div>
        {rootNavigate && (
          <button onClick={() => rootNavigate('/')} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#555', border: '1px solid #1e1e1e', padding: '6px 12px', background: 'none', cursor: 'pointer' }}>← Shell</button>
        )}
      </div>
      {/* Page selector */}
      <div style={{ display: 'flex', overflowX: 'auto', background: '#fff', borderBottom: '1px solid #e5e5e5' }}>
        {pages.map(p => (
          <button key={p.id} onClick={() => setActivePage(p.id)}
            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '12px 16px', color: activePage === p.id ? '#0a0a0a' : '#aaa', borderBottom: activePage === p.id ? `2px solid ${BRAND.accent}` : '2px solid transparent', marginBottom: -1, whiteSpace: 'nowrap', fontWeight: activePage === p.id ? 700 : 400, letterSpacing: '0.06em', background: 'none', cursor: 'pointer' }}>
            {p.label.toUpperCase()}
          </button>
        ))}
      </div>
      {/* Phone frame */}
      <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 24px 60px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <div style={{ background: '#1a1a1a', borderRadius: 44, padding: 12, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
            <div style={{ width: 375, height: 812, background: '#fff', overflow: 'hidden', borderRadius: 32, position: 'relative' }}>
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, overflowY: 'auto' }}>
                {current?.component}
              </div>
            </div>
          </div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#aaa', letterSpacing: '0.08em' }}>{current?.label.toUpperCase()} — 375 × 812</p>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, {
  MobileFrame, MobileNav,
  MobileHomePage, MobileBriefPage, MobilePerformancePage,
  MobileTerminalPairDeskPage, MobileCalendarPage, MobileAboutPage,
  MobilePreviewGallery,
});
