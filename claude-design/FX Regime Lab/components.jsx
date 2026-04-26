
// ─── Brand colors from logo ──────────────────────────────────────────────────
const BRAND = {
  eurusd: '#4BA3E3',   // logo blue
  usdjpy: '#F5923A',   // logo orange — also site accent
  usdinr: '#D94030',   // logo red
  accent: '#F5923A',
};

const TODAY = '2026-04-26';

const PAIRS = [
  { label: 'EURUSD', display: 'EUR/USD', urlSlug: 'eurusd', pairColor: BRAND.eurusd },
  { label: 'USDJPY', display: 'USD/JPY', urlSlug: 'usdjpy', pairColor: BRAND.usdjpy },
  { label: 'USDINR', display: 'USD/INR', urlSlug: 'usdinr', pairColor: BRAND.usdinr },
];

const MOCK_REGIME_CALLS = {
  EURUSD: {
    pair: 'EURUSD', date: TODAY, regime: 'MODERATE USD WEAKNESS',
    confidence: 0.72, signal_composite: -0.81,
    rate_signal: 'BEARISH', primary_driver: 'Rate differential compressing; COT short-cover underway',
    created_at: `${TODAY}T07:12:34Z`,
  },
  USDJPY: {
    pair: 'USDJPY', date: TODAY, regime: 'STRONG USD STRENGTH',
    confidence: 0.84, signal_composite: 1.43,
    rate_signal: 'BULLISH', primary_driver: 'BoJ YCC intact; rate spread at cycle high',
    created_at: `${TODAY}T07:12:34Z`,
  },
  USDINR: {
    pair: 'USDINR', date: TODAY, regime: 'MODERATE DEPRECIATION PRESSURE',
    confidence: 0.63, signal_composite: 0.61,
    rate_signal: 'BULLISH', primary_driver: 'RBI intervention cap; DXY correlation elevated',
    created_at: `${TODAY}T07:12:34Z`,
  },
};

const MOCK_SIGNALS = {
  EURUSD: {
    pair: 'EURUSD', date: TODAY,
    rate_diff_2y: -0.45, cot_percentile: 34,
    realized_vol_20d: 6.21, realized_vol_5d: 5.88,
    implied_vol_30d: 7.14, spot: 1.0731,
    day_change: -0.0021, day_change_pct: -0.20,
    created_at: `${TODAY}T07:12:34Z`,
  },
  USDJPY: {
    pair: 'USDJPY', date: TODAY,
    rate_diff_2y: 3.82, cot_percentile: 78,
    realized_vol_20d: 8.13, realized_vol_5d: 7.94,
    implied_vol_30d: 9.32, spot: 154.62,
    day_change: 0.84, day_change_pct: 0.55,
    created_at: `${TODAY}T07:12:34Z`,
  },
  USDINR: {
    pair: 'USDINR', date: TODAY,
    rate_diff_2y: 4.10, cot_percentile: 52,
    realized_vol_20d: 3.07, realized_vol_5d: 3.21,
    implied_vol_30d: null, spot: 83.94,
    day_change: 0.06, day_change_pct: 0.07,
    created_at: `${TODAY}T07:12:34Z`,
  },
};

const MOCK_HISTORY = {
  EURUSD: [
    { date: '2026-04-25', regime: 'MODERATE USD WEAKNESS', confidence: 0.68 },
    { date: '2026-04-24', regime: 'NEUTRAL', confidence: 0.51 },
    { date: '2026-04-23', regime: 'NEUTRAL', confidence: 0.48 },
    { date: '2026-04-22', regime: 'MODERATE USD STRENGTH', confidence: 0.59 },
    { date: '2026-04-17', regime: 'MODERATE USD STRENGTH', confidence: 0.61 },
    { date: '2026-04-16', regime: 'STRONG USD STRENGTH', confidence: 0.77 },
    { date: '2026-04-15', regime: 'STRONG USD STRENGTH', confidence: 0.80 },
  ],
  USDJPY: [
    { date: '2026-04-25', regime: 'STRONG USD STRENGTH', confidence: 0.82 },
    { date: '2026-04-24', regime: 'STRONG USD STRENGTH', confidence: 0.79 },
    { date: '2026-04-23', regime: 'STRONG USD STRENGTH', confidence: 0.75 },
    { date: '2026-04-22', regime: 'MODERATE USD STRENGTH', confidence: 0.66 },
    { date: '2026-04-17', regime: 'MODERATE USD STRENGTH', confidence: 0.63 },
    { date: '2026-04-16', regime: 'VOL_EXPANDING', confidence: 0.55 },
    { date: '2026-04-15', regime: 'MODERATE USD STRENGTH', confidence: 0.61 },
  ],
  USDINR: [
    { date: '2026-04-25', regime: 'MODERATE DEPRECIATION PRESSURE', confidence: 0.60 },
    { date: '2026-04-24', regime: 'MODERATE DEPRECIATION PRESSURE', confidence: 0.58 },
    { date: '2026-04-23', regime: 'NEUTRAL', confidence: 0.46 },
    { date: '2026-04-22', regime: 'NEUTRAL', confidence: 0.49 },
    { date: '2026-04-17', regime: 'MODERATE APPRECIATION PRESSURE', confidence: 0.55 },
    { date: '2026-04-16', regime: 'MODERATE APPRECIATION PRESSURE', confidence: 0.57 },
    { date: '2026-04-15', regime: 'MODERATE APPRECIATION PRESSURE', confidence: 0.62 },
  ],
};

const MOCK_VALIDATION = [
  { date: '2026-04-25', pair: 'EUR/USD', call: 'MODERATE USD WEAKNESS', outcome: 'correct', return_pct: 0.31 },
  { date: '2026-04-25', pair: 'USD/JPY', call: 'STRONG USD STRENGTH', outcome: 'correct', return_pct: 0.48 },
  { date: '2026-04-25', pair: 'USD/INR', call: 'MODERATE DEPRECIATION PRESSURE', outcome: 'incorrect', return_pct: -0.07 },
  { date: '2026-04-24', pair: 'EUR/USD', call: 'NEUTRAL', outcome: 'correct', return_pct: 0.04 },
  { date: '2026-04-24', pair: 'USD/JPY', call: 'STRONG USD STRENGTH', outcome: 'correct', return_pct: 0.52 },
  { date: '2026-04-24', pair: 'USD/INR', call: 'MODERATE DEPRECIATION PRESSURE', outcome: 'correct', return_pct: 0.12 },
  { date: '2026-04-23', pair: 'EUR/USD', call: 'NEUTRAL', outcome: 'incorrect', return_pct: -0.18 },
  { date: '2026-04-23', pair: 'USD/JPY', call: 'STRONG USD STRENGTH', outcome: 'correct', return_pct: 0.39 },
  { date: '2026-04-23', pair: 'USD/INR', call: 'NEUTRAL', outcome: 'correct', return_pct: 0.02 },
];

const MOCK_BRIEF = `# Morning Brief — ${TODAY}

**Macro context:** Dollar index softening into month-end rebalancing flows. Fed speaker today (14:00 ET). Risk-on tone with equities bid.

## EUR/USD

Regime: **Moderate USD Weakness** | Confidence 72%

Rate differential continued to compress (-0.45 spread vs -0.38 last week). CFTC positioning shows net EUR longs at 34th percentile - room to extend. Realized vol 6.2 annualized, below the 30d implied of 7.1 suggesting vol-sellers favor range.

Call: Bias EUR/USD higher into 1.0820 resistance. Stop on daily close below 1.0690.

## USD/JPY

Regime: **Strong USD Strength** | Confidence 84%

BoJ maintained YCC at 1.0% cap. 2y rate spread widened to 3.82, cycle high. COT at 78th percentile - positioning extended but momentum intact.

Call: USD/JPY constructive above 153.80. Target 155.50. Risk: BoJ jawboning.

## USD/INR

Regime: **Moderate Depreciation Pressure** | Confidence 63%

RBI cap limiting moves. 4.1 rate differential supports dollar demand vs rupee. Realized vol contained at 3.1.

Call: USD/INR mild upside bias. Range 83.75-84.20 likely to contain near-term move.

---

*Research and learning only. Not investment advice.*`;


// ─── Mock macro calendar ─────────────────────────────────────────────────────
const MOCK_CALENDAR = [
  { date: '2026-04-29', event: 'US GDP Q1 (Advance)', impact: 'HIGH', pairs: ['EURUSD', 'USDJPY'], category: 'US' },
  { date: '2026-04-30', event: 'FOMC Rate Decision', impact: 'HIGH', pairs: ['EURUSD', 'USDJPY', 'USDINR'], category: 'US' },
  { date: '2026-04-30', event: 'Eurozone CPI Flash', impact: 'HIGH', pairs: ['EURUSD'], category: 'EU' },
  { date: '2026-05-01', event: 'BoJ Press Conference', impact: 'HIGH', pairs: ['USDJPY'], category: 'JP' },
  { date: '2026-05-02', event: 'US NFP (Non-Farm Payrolls)', impact: 'HIGH', pairs: ['EURUSD', 'USDJPY', 'USDINR'], category: 'US' },
  { date: '2026-05-06', event: 'RBI Monetary Policy Meeting', impact: 'HIGH', pairs: ['USDINR'], category: 'IN' },
  { date: '2026-05-07', event: 'US ISM Services PMI', impact: 'MEDIUM', pairs: ['EURUSD', 'USDJPY'], category: 'US' },
  { date: '2026-05-08', event: 'ECB Minutes', impact: 'MEDIUM', pairs: ['EURUSD'], category: 'EU' },
  { date: '2026-05-13', event: 'US CPI (April)', impact: 'HIGH', pairs: ['EURUSD', 'USDJPY', 'USDINR'], category: 'US' },
  { date: '2026-05-15', event: 'US Retail Sales', impact: 'MEDIUM', pairs: ['EURUSD', 'USDJPY'], category: 'US' },
  { date: '2026-05-20', event: 'FOMC Minutes', impact: 'MEDIUM', pairs: ['EURUSD', 'USDJPY'], category: 'US' },
  { date: '2026-05-22', event: 'UK CPI (April)', impact: 'MEDIUM', pairs: [], category: 'UK' },
];

// ─── Mock regime heatmap (30 days × 3 pairs) ─────────────────────────────────
const REGIME_HEATMAP_COLORS = {
  'STRONG USD STRENGTH': '#1e3a5f',
  'MODERATE USD STRENGTH': '#2d5a8e',
  'NEUTRAL': '#3a3a3a',
  'MODERATE USD WEAKNESS': '#7a3f1f',
  'STRONG USD WEAKNESS': '#a0522d',
  'VOL_EXPANDING': '#7a5c00',
  'STRONG DEPRECIATION PRESSURE': '#6b1a1a',
  'MODERATE DEPRECIATION PRESSURE': '#8b2a2a',
  'MODERATE APPRECIATION PRESSURE': '#1a5a2a',
  'STRONG APPRECIATION PRESSURE': '#0d3a1a',
  'DIRECTIONAL_ONLY': '#333',
  'UNKNOWN': '#1a1a1a',
};

const MOCK_HEATMAP = (() => {
  const regimes = {
    EURUSD: ['STRONG USD STRENGTH','STRONG USD STRENGTH','MODERATE USD STRENGTH','MODERATE USD STRENGTH','NEUTRAL','NEUTRAL','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','NEUTRAL','NEUTRAL','MODERATE USD STRENGTH','MODERATE USD STRENGTH','NEUTRAL','NEUTRAL','NEUTRAL','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','NEUTRAL','NEUTRAL','NEUTRAL','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','NEUTRAL','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS'],
    USDJPY: ['STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','VOL_EXPANDING','MODERATE USD STRENGTH','MODERATE USD STRENGTH','MODERATE USD STRENGTH','MODERATE USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','MODERATE USD STRENGTH','MODERATE USD STRENGTH','MODERATE USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH'],
    USDINR: ['MODERATE APPRECIATION PRESSURE','MODERATE APPRECIATION PRESSURE','MODERATE APPRECIATION PRESSURE','MODERATE APPRECIATION PRESSURE','NEUTRAL','NEUTRAL','NEUTRAL','NEUTRAL','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','NEUTRAL','NEUTRAL','NEUTRAL','NEUTRAL','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','NEUTRAL','NEUTRAL','NEUTRAL','NEUTRAL','NEUTRAL','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','NEUTRAL','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE'],
  };
  const dates = Array.from({length: 30}, (_, i) => {
    const d = new Date('2026-04-26');
    d.setDate(d.getDate() - (29 - i));
    return d.toISOString().slice(0, 10);
  });
  return { dates, regimes };
})();

// ─── Utilities ───────────────────────────────────────────────────────────────
function fmt2(v) { return v == null || isNaN(v) ? '—' : v.toFixed(2); }
function fmt4(v) { return v == null || isNaN(v) ? '—' : v.toFixed(4); }
function fmtPct(v) { return v == null || isNaN(v) ? '—' : `${Math.round(v * 100)}%`; }
function fmtInt(v) { return v == null || isNaN(v) ? '—' : v.toFixed(0); }
function fmtChg(v) {
  if (v == null || isNaN(v)) return { str: '—', color: '#666' };
  const sign = v >= 0 ? '+' : '';
  const color = v >= 0 ? '#4ade80' : '#f87171';
  return { str: `${sign}${v.toFixed(2)}%`, color };
}

// ─── Logo ──────────────────────────────────────────────────────────────────────
function LogoMark({ size = 24 }) {
  return <img src="logo.png" alt="FX Regime Lab" style={{ height: size, width: 'auto', display: 'block', flexShrink: 0 }} />;
}

// ─── ConfidenceBar ────────────────────────────────────────────────────────────
function ConfidenceBar({ value, tone = 'dark', color }) {
  const pct = value == null ? 0 : Math.round(value * 100);
  const barColor = color || BRAND.accent;
  const trackColor = tone === 'dark' ? '#1e1e1e' : '#ebebeb';
  return (
    <div style={{ background: trackColor, height: tone === 'dark' ? 3 : 2, width: '100%' }}>
      <div style={{ width: `${pct}%`, height: '100%', background: barColor, transition: 'width 0.5s ease' }} />
    </div>
  );
}

// ─── Nav (Shell) ──────────────────────────────────────────────────────────────
function Nav({ currentRoute, navigate }) {
  const [open, setOpen] = React.useState(false);
  React.useEffect(() => {
    const h = () => setOpen(false);
    document.addEventListener('click', h);
    return () => document.removeEventListener('click', h);
  }, []);
  const isActive = href => href === '/' ? currentRoute === '/' : currentRoute.startsWith(href);

  return (
    <header style={{ borderBottom: '1px solid #e5e5e5', background: '#fff', position: 'sticky', top: 0, zIndex: 50 }}>
      <nav style={{ maxWidth: 1152, margin: '0 auto', padding: '0 24px', height: 54, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {/* Brand */}
        <button onClick={() => navigate('/')} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <LogoMark size={22} />
          <span style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 15, color: '#0a0a0a', letterSpacing: '-0.02em' }}>FX Regime Lab</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
          {[['/', 'Home'], ['/brief', 'Brief']].map(([href, label]) => (
            <button key={href} onClick={() => navigate(href)}
              style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, fontWeight: 500, color: isActive(href) ? '#0a0a0a' : '#555', padding: '0 14px', height: 54, display: 'flex', alignItems: 'center', borderBottom: isActive(href) ? `2px solid ${BRAND.accent}` : '2px solid transparent', transition: 'color 0.1s' }}>
              {label}
            </button>
          ))}

          <div style={{ position: 'relative' }} onClick={e => e.stopPropagation()}>
            <button onClick={() => setOpen(v => !v)}
              style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, fontWeight: 500, color: '#555', padding: '0 14px', height: 54, display: 'flex', alignItems: 'center', gap: 5, borderBottom: '2px solid transparent' }}>
              Research
              <svg width="10" height="6" viewBox="0 0 10 6" fill="none" style={{ opacity: 0.5, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>
                <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            {open && (
              <div style={{ position: 'absolute', right: 0, top: 54, background: '#fff', border: '1px solid #e5e5e5', minWidth: 180, boxShadow: '0 8px 24px rgba(0,0,0,0.08)', zIndex: 100 }}>
                {[['/performance', 'Performance'], ['/fx-regime', 'FX Regime'], ['/calendar', 'Calendar']].map(([href, label]) => (
                  <button key={href} onClick={() => { navigate(href); setOpen(false); }}
                    style={{ display: 'flex', alignItems: 'center', width: '100%', padding: '11px 16px', fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#0a0a0a', borderBottom: '1px solid #f5f5f5', transition: 'background 0.1s' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#fafafa'}
                    onMouseLeave={e => e.currentTarget.style.background = 'none'}>
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button onClick={() => navigate('/about')}
            style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, fontWeight: 500, color: isActive('/about') ? '#0a0a0a' : '#555', padding: '0 14px', height: 54, display: 'flex', alignItems: 'center', borderBottom: isActive('/about') ? `2px solid ${BRAND.accent}` : '2px solid transparent' }}>
            About
          </button>

          <button onClick={() => navigate('/terminal')}
            style={{ marginLeft: 14, background: '#0a0a0a', color: '#fff', fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 12, padding: '8px 16px', letterSpacing: '0.01em', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4ade80', flexShrink: 0 }} />
            Terminal
          </button>
        </div>
      </nav>
    </header>
  );
}

// ─── TerminalNav ──────────────────────────────────────────────────────────────
function TerminalNav({ currentRoute, navigate }) {
  const pair = PAIRS.find(p => currentRoute.includes(p.urlSlug));
  return (
    <header style={{ borderBottom: '1px solid #1e1e1e', background: '#080808', position: 'sticky', top: 0, zIndex: 50 }}>
      {/* Brand bar */}
      <div style={{ borderBottom: '1px solid #141414', padding: '0 24px', height: 38, display: 'flex', alignItems: 'center', justifyContent: 'space-between', maxWidth: 1152, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <LogoMark size={16} />
          <span style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 13, color: '#e8e8e8', letterSpacing: '-0.02em' }}>FX Regime Lab</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#333', marginLeft: 4 }}>/ Terminal</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#4ade80' }} />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888' }}>LIVE · {TODAY} 07:12 UTC</span>
        </div>
      </div>
      {/* Breadcrumb + pair tabs */}
      <div style={{ maxWidth: 1152, margin: '0 auto', padding: '0 24px', height: 38, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'JetBrains Mono, monospace', fontSize: 10 }}>
          <button onClick={() => navigate('/')} style={{ color: '#888', fontFamily: 'inherit', fontSize: 'inherit' }}>shell</button>
          <span style={{ color: '#555' }}>/</span>
          <button onClick={() => navigate('/terminal')} style={{ color: currentRoute === '/terminal' ? '#ddd' : '#777', fontFamily: 'inherit', fontSize: 'inherit' }}>terminal</button>
          {currentRoute.includes('/fx-regime') && <>
            <span style={{ color: '#555' }}>/</span>
            <button onClick={() => navigate('/terminal/fx-regime')} style={{ color: currentRoute === '/terminal/fx-regime' ? '#ddd' : '#777', fontFamily: 'inherit', fontSize: 'inherit' }}>fx-regime</button>
          </>}
          {pair && <>
            <span style={{ color: '#555' }}>/</span>
            <span style={{ color: pair.pairColor, fontWeight: 600, fontFamily: 'inherit' }}>{pair.urlSlug}</span>
          </>}
        </div>
        <div style={{ display: 'flex', gap: 2 }}>
          {PAIRS.map(p => {
            const active = currentRoute.includes(p.urlSlug);
            const sig = MOCK_SIGNALS[p.label];
            const chgPct = sig?.day_change_pct;
            return (
              <button key={p.label} onClick={() => navigate(`/terminal/fx-regime/${p.urlSlug}`)}
                style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 12px', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, background: active ? '#141414' : 'transparent', borderBottom: active ? `2px solid ${p.pairColor}` : '2px solid transparent', transition: 'all 0.1s', marginBottom: -1 }}>
                <span style={{ color: p.pairColor, fontWeight: 700 }}>{p.display}</span>
                {sig && <span style={{ color: chgPct >= 0 ? '#4ade80' : '#f87171' }}>{chgPct >= 0 ? '+' : ''}{chgPct?.toFixed(2)}%</span>}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}

// ─── Footer ───────────────────────────────────────────────────────────────────
function Footer({ navigate }) {
  return (
    <footer style={{ borderTop: '1px solid #e5e5e5', background: '#fff', marginTop: 80 }}>
      <div style={{ maxWidth: 1152, margin: '0 auto', padding: '48px 24px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 40 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <LogoMark size={20} />
            <span style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 14, color: '#0a0a0a' }}>FX Regime Lab</span>
          </div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#888', maxWidth: 260, lineHeight: 1.7 }}>
            Daily G10 FX regime research.<br />Every call logged. Every outcome public.
          </p>
          <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
            {PAIRS.map(p => <span key={p.label} style={{ display: 'inline-block', width: 18, height: 4, background: p.pairColor }} />)}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 48 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[['/', 'Home'], ['/brief', 'Brief'], ['/performance', 'Performance']].map(([href, label]) => (
              <button key={href} onClick={() => navigate(href)} style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#555', textAlign: 'left' }}>{label}</button>
            ))}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[['/fx-regime', 'FX Regime'], ['/about', 'About'], ['/terminal', 'Terminal']].map(([href, label]) => (
              <button key={href} onClick={() => navigate(href)} style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#555', textAlign: 'left' }}>{label}</button>
            ))}
          </div>
        </div>
      </div>
      <div style={{ borderTop: '1px solid #f0f0f0', padding: '14px 24px' }}>
        <p style={{ maxWidth: 1152, margin: '0 auto', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#aaa' }}>
          Research and learning only. Not investment advice. Shreyash Sakhare — Discretionary Macro Research.
        </p>
      </div>
    </footer>
  );
}

// ─── HeroRegimeCard ───────────────────────────────────────────────────────────
function HeroRegimeCard({ call, signals }) {
  const pct = call ? Math.round(call.confidence * 100) : null;
  const chg = signals?.day_change_pct;
  return (
    <div style={{ background: '#080808', border: '1px solid #1e1e1e' }}>
      {/* Card header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '1px solid #1a1a1a' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 8, height: 8, background: BRAND.eurusd, display: 'inline-block', flexShrink: 0 }} />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: BRAND.eurusd, fontWeight: 700, letterSpacing: '0.04em' }}>EUR/USD</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {chg != null && <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: chg >= 0 ? '#4ade80' : '#f87171', fontWeight: 600 }}>{chg >= 0 ? '+' : ''}{chg.toFixed(2)}%</span>}
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#4ade80' }} />
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#555' }}>LIVE</span>
          </div>
        </div>
      </div>

      <div style={{ padding: '20px' }}>
        {/* Spot price */}
        <div style={{ marginBottom: 20 }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#999', letterSpacing: '0.12em', marginBottom: 4 }}>SPOT</p>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 32, fontWeight: 700, color: '#ffffff', letterSpacing: '-0.02em', lineHeight: 1 }}>
            {signals?.spot?.toFixed(4) ?? '—'}
          </p>
        </div>

        {/* Regime label */}
        <div style={{ marginBottom: 20, paddingBottom: 16, borderBottom: '1px solid #1a1a1a' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#999', letterSpacing: '0.12em', marginBottom: 6 }}>REGIME</p>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 700, color: '#ffffff', letterSpacing: '0.04em', lineHeight: 1.4 }}>{call?.regime ?? '—'}</p>
        </div>

        {/* Confidence */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#444', letterSpacing: '0.12em' }}>CONFIDENCE</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 28, fontWeight: 700, color: BRAND.eurusd, letterSpacing: '-0.03em', lineHeight: 1 }}>
              {pct ?? '—'}<span style={{ fontSize: 14, fontWeight: 400, color: '#555' }}>{pct != null ? '%' : ''}</span>
            </p>
          </div>
          <ConfidenceBar value={call?.confidence} tone="dark" color={BRAND.eurusd} />
        </div>

        {/* Signal rows */}
        <div style={{ borderTop: '1px solid #141414' }}>
          {[
            ['RATE DIFF 2Y', fmt2(signals?.rate_diff_2y)],
            ['COT PERCENTILE', fmtInt(signals?.cot_percentile)],
            ['REALIZED VOL 20D', fmt2(signals?.realized_vol_20d)],
            ['IMPLIED VOL 30D', fmt2(signals?.implied_vol_30d)],
            ['SIGNAL COMPOSITE', fmt2(call?.signal_composite)],
          ].map(([label, value]) => (
            <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 0', borderBottom: '1px solid #111' }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#aaa', letterSpacing: '0.06em' }}>{label}</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#ffffff', fontWeight: 700 }}>{value}</span>
            </div>
          ))}
        </div>

        {call?.primary_driver && (
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#999', marginTop: 14, lineHeight: 1.7, paddingTop: 12, borderTop: '1px solid #141414' }}>
            {call.primary_driver}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── PairCard (shell) ─────────────────────────────────────────────────────────
function PairCard({ pair, call, signals, navigate }) {
  const [hov, setHov] = React.useState(false);
  const pct = call ? Math.round(call.confidence * 100) : null;
  const chg = signals?.day_change_pct;
  return (
    <div
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      onClick={() => navigate(`/pairs/${pair.urlSlug}`)}
      style={{ border: `1px solid ${hov ? '#bbb' : '#e5e5e5'}`, background: hov ? '#fafafa' : '#fff', cursor: 'pointer', transition: 'all 0.12s', padding: '20px 20px', borderTop: `3px solid ${pair.pairColor}` }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 15, color: '#0a0a0a', marginBottom: 2 }}>{pair.display}</p>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 20, fontWeight: 700, color: '#0a0a0a', letterSpacing: '-0.02em' }}>{signals?.spot?.toFixed(pair.label === 'USDJPY' ? 2 : 4) ?? '—'}</p>
        </div>
        {chg != null && (
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, fontWeight: 600, color: chg >= 0 ? '#16a34a' : '#dc2626', background: chg >= 0 ? '#f0fdf4' : '#fff5f5', padding: '3px 8px' }}>
            {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
          </span>
        )}
      </div>

      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 700, color: '#111', letterSpacing: '0.03em', lineHeight: 1.4, marginBottom: 12 }}>
        {call?.regime ?? '—'}
      </p>

      <div style={{ marginBottom: 14 }}>
        <ConfidenceBar value={call?.confidence} tone="light" color={pair.pairColor} />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#888', letterSpacing: '0.1em' }}>CONFIDENCE</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#0a0a0a', fontWeight: 700 }}>{pct != null ? `${pct}%` : '—'}</span>
        </div>
      </div>

      <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 7 }}>
        {[['Rate diff 2Y', fmt2(signals?.rate_diff_2y)], ['COT pctile', fmtInt(signals?.cot_percentile)], ['Rvol 20d', fmt2(signals?.realized_vol_20d)]].map(([lbl, val]) => (
          <div key={lbl} style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888' }}>{lbl}</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#111', fontWeight: 600 }}>{val}</span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 14, paddingTop: 10, borderTop: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', letterSpacing: '0.08em' }}>OPEN DESK</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: pair.pairColor, fontWeight: 700 }} onClick={(e) => { e.stopPropagation(); navigate(`/terminal/fx-regime/${pair.urlSlug}`); }}>→</span>
      </div>
    </div>
  );
}

// ─── RegimeCard (compact, terminal) ──────────────────────────────────────────
function RegimeCard({ call, signals, pairDisplay }) {
  const pairMeta = PAIRS.find(p => p.display === pairDisplay || p.label === call?.pair);
  const regimeAccent = call && call.confidence >= 0.55 &&
    (call.regime.includes('STRENGTH') || call.regime.includes('WEAKNESS') || call.regime.includes('PRESSURE') || call.regime === 'VOL_EXPANDING');
  const sig = signals || MOCK_SIGNALS[pairMeta?.label];
  const chg = sig?.day_change_pct;

  return (
    <div style={{ background: '#0e0e0e', border: '1px solid #1e1e1e', borderLeft: `3px solid ${pairMeta?.pairColor ?? '#333'}`, padding: '14px 16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: pairMeta?.pairColor ?? '#ccc', fontWeight: 700 }}>{pairDisplay ?? call?.pair}</span>
        {chg != null && <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fontWeight: 600, color: chg >= 0 ? '#4ade80' : '#f87171' }}>{chg >= 0 ? '+' : ''}{chg.toFixed(2)}%</span>}
      </div>
      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 18, fontWeight: 700, color: '#e8e8e8', letterSpacing: '-0.01em', marginBottom: 8 }}>
        {sig?.spot?.toFixed(pairMeta?.label === 'USDJPY' ? 2 : 4) ?? '—'}
      </p>
      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fontWeight: 700, color: regimeAccent ? BRAND.accent : '#c0c0c0', letterSpacing: '0.04em', lineHeight: 1.4, marginBottom: 10 }}>
        {call?.regime ?? '—'}
      </p>
      <ConfidenceBar value={call?.confidence} tone="dark" color={pairMeta?.pairColor} />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5 }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.1em' }}>CONF</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#ccc', fontWeight: 700 }}>{fmtPct(call?.confidence)}</span>
      </div>
      <div style={{ borderTop: '1px solid #1a1a1a', marginTop: 10, paddingTop: 10, display: 'flex', flexDirection: 'column', gap: 5 }}>
        {[['RATE DIFF', fmt2(sig?.rate_diff_2y)], ['COT PCT', fmtInt(sig?.cot_percentile)], ['RVOL 20D', fmt2(sig?.realized_vol_20d)]].map(([lbl, val]) => (
          <div key={lbl} style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#777', letterSpacing: '0.06em' }}>{lbl}</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#e0e0e0', fontWeight: 600 }}>{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── ValidationTable ──────────────────────────────────────────────────────────
function ValidationTable({ rows, tone = 'light' }) {
  const isD = tone === 'dark';
  const bg = isD ? '#0a0a0a' : '#fff';
  const border = isD ? '#1e1e1e' : '#e5e5e5';
  const hdr = isD ? '#888' : '#999';
  const text = isD ? '#ffffff' : '#111';
  const muted = isD ? '#aaa' : '#555';
  const stripe = isD ? '#0d0d0d' : '#fafafa';

  return (
    <div style={{ border: `1px solid ${border}`, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'JetBrains Mono, monospace' }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${border}`, background: isD ? '#0d0d0d' : '#fafafa' }}>
            {['DATE', 'PAIR', 'CALL', 'OUTCOME', 'RET %'].map(h => (
              <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 10, color: hdr, letterSpacing: '0.1em', fontWeight: 600 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: i < rows.length - 1 ? `1px solid ${border}` : 'none', background: i % 2 === 1 ? stripe : bg }}>
              <td style={{ padding: '9px 16px', fontSize: 11, color: muted }}>{row.date}</td>
              <td style={{ padding: '9px 16px', fontSize: 11, color: text, fontWeight: 700 }}>{row.pair}</td>
              <td style={{ padding: '9px 16px', fontSize: 10, color: muted, maxWidth: 200 }}>{row.call}</td>
              <td style={{ padding: '9px 16px', fontSize: 11, fontWeight: 700, color: row.outcome === 'correct' ? '#16a34a' : '#dc2626' }}>
                {row.outcome === 'correct' ? '✓ correct' : '✗ incorrect'}
              </td>
              <td style={{ padding: '9px 16px', fontSize: 12, fontWeight: 700, color: row.return_pct >= 0 ? '#16a34a' : '#dc2626' }}>
                {row.return_pct >= 0 ? '+' : ''}{row.return_pct.toFixed(2)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

Object.assign(window, {
  BRAND, PAIRS, MOCK_REGIME_CALLS, MOCK_SIGNALS, MOCK_HISTORY, MOCK_VALIDATION, MOCK_BRIEF,
  MOCK_CALENDAR, MOCK_HEATMAP, REGIME_HEATMAP_COLORS,
  TODAY, fmt2, fmt4, fmtPct, fmtInt, fmtChg,
  LogoMark, ConfidenceBar, RegimeCard, HeroRegimeCard, PairCard, ValidationTable,
  Nav, TerminalNav, Footer,
});
