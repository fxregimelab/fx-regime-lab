
// ─── Shared SVG Sparkline (used across shell pages) ──────────────────────────
function Sparkline({ values, color = '#4BA3E3', height = 48, width = 120, showDots = false, showZeroLine = false }) {
  if (!values || values.length < 2) return <div style={{ height }} />;
  const mn = Math.min(...values), mx = Math.max(...values);
  const range = mx - mn || 0.01;
  const n = values.length;
  const pts = values.map((v, i) => [i / (n - 1) * width, (height - 4) - ((v - mn) / range) * (height - 8)]);
  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const area = `${line} L${width},${height} L0,${height} Z`;
  const zeroY = (height - 4) - ((0 - mn) / range) * (height - 8);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ display: 'block' }}>
      {showZeroLine && <line x1="0" y1={zeroY} x2={width} y2={zeroY} stroke="#e5e5e5" strokeWidth="1" strokeDasharray="3,2" />}
      <path d={area} fill={`${color}18`} />
      <path d={line} fill="none" stroke={color} strokeWidth="1.5" />
      {showDots && pts.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="2.5" fill={color} stroke="#fff" strokeWidth="1" />)}
    </svg>
  );
}

// ─── Mock equity data ─────────────────────────────────────────────────────────
const MOCK_EQUITY = {
  dates: ['Apr 7','Apr 8','Apr 9','Apr 10','Apr 11','Apr 14','Apr 15','Apr 16','Apr 17','Apr 22','Apr 23','Apr 24','Apr 25','Apr 26'],
  EURUSD: [0, 0.18, 0.04, -0.14, 0.04, 0.22, 0.48, 0.30, -0.18, -0.14, 0.04, 0.35, 0.66, 0.97],
  USDJPY: [0, 0.31, 0.55, 0.48, 0.62, 0.87, 0.61, 0.55, 0.72, 1.11, 1.50, 2.02, 2.54, 3.02],
  USDINR: [0, 0.04, 0.04, 0.04, 0.04, 0.12, 0.12, 0.02, 0.02, 0.14, 0.16, 0.28, 0.21, 0.21],
};
// composite
MOCK_EQUITY.ALL = MOCK_EQUITY.dates.map((_, i) =>
  (MOCK_EQUITY.EURUSD[i] + MOCK_EQUITY.USDJPY[i] + MOCK_EQUITY.USDINR[i]) / 3
);

// Per pair brief text content
const BRIEF_SECTIONS = {
  EURUSD: {
    regime: 'MODERATE USD WEAKNESS',
    confidence: 0.72,
    composite: -0.81,
    analysis: `Rate differential continued to compress (-0.45 spread vs -0.38 last week). CFTC positioning shows net EUR longs at 34th percentile - room to extend. Realized vol 6.2 annualized, below the 30d implied of 7.1 suggesting vol-sellers favor the range.\n\nCall: Bias EUR/USD higher into 1.0820 resistance. Stop on daily close below 1.0690.`,
    primaryDriver: 'Rate differential compressing; COT short-cover underway',
  },
  USDJPY: {
    regime: 'STRONG USD STRENGTH',
    confidence: 0.84,
    composite: 1.43,
    analysis: `BoJ maintained YCC at 1.0% cap. 2Y rate spread widened to 3.82, cycle high. COT at 78th percentile - positioning extended but momentum intact. Vol at 8.1 realized vs 9.3 implied - tail risk premium building.\n\nCall: USD/JPY constructive above 153.80. Target 155.50. Risk: BoJ jawboning or surprise pivot.`,
    primaryDriver: 'BoJ YCC intact; rate spread at cycle high',
  },
  USDINR: {
    regime: 'MODERATE DEPRECIATION PRESSURE',
    confidence: 0.63,
    composite: 0.61,
    analysis: `RBI cap limiting moves. 4.1 rate differential supports dollar demand vs rupee. COT at 52nd percentile - neutral positioning. Realized vol contained at 3.1 - regime likely range-bound near term.\n\nCall: USD/INR mild upside bias. Range 83.75-84.20 likely to contain near-term move.`,
    primaryDriver: 'RBI intervention cap; DXY correlation elevated',
  },
};

// ─── Home Page ───────────────────────────────────────────────────────────────
function HomePage({ navigate }) {
  return (
    <div style={{ background: '#ffffff' }}>
      {/* Hero */}
      <section style={{ maxWidth: 1152, margin: '0 auto', padding: '72px 24px 64px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 64, alignItems: 'start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#737373', letterSpacing: '0.1em' }}>LIVE · G10 FX · DAILY CALLS</span>
          </div>
          <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 52, lineHeight: 1.05, color: '#0a0a0a', letterSpacing: '-0.035em', margin: '0 0 24px' }}>
            Daily regime<br />calls. On the<br />record.
          </h1>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 16, color: '#525252', lineHeight: 1.7, maxWidth: 440, margin: '0 0 32px' }}>
            G10 FX regime classification across EUR/USD, USD/JPY, and USD/INR. Composite signal from rate differentials, COT positioning, realized volatility, and open interest. Every call public before market open. Every outcome validated.
          </p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <button onClick={() => navigate('/brief')} style={{ background: '#0a0a0a', color: '#ffffff', fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 13, padding: '10px 20px', border: 'none', cursor: 'pointer' }}>
              Read today's brief
            </button>
            <button onClick={() => navigate('/performance')} style={{ background: 'none', color: '#0a0a0a', fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 13, padding: '10px 0', border: 'none', cursor: 'pointer', textDecoration: 'underline', textDecorationColor: '#d0d0d0', textUnderlineOffset: 4 }}>
              Validation log →
            </button>
          </div>
          <div style={{ marginTop: 36, display: 'flex', alignItems: 'center', gap: 8, paddingTop: 24, borderTop: '1px solid #f0f0f0' }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.06em' }}>PIPELINE · {TODAY} 07:12 UTC · 3 pairs updated</span>
          </div>
        </div>
        <div><HeroRegimeCard call={MOCK_REGIME_CALLS.EURUSD} signals={MOCK_SIGNALS.EURUSD} /></div>
      </section>

      <div style={{ borderTop: '1px solid #e5e5e5' }} />

      {/* Stats bar */}
      <section style={{ borderBottom: '1px solid #e5e5e5' }}>
        <div style={{ maxWidth: 1152, margin: '0 auto', padding: '0 24px', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)' }}>
          {[
            { label: 'Pairs tracked', value: '3' },
            { label: 'Calls since April 2026', value: '27' },
            { label: '7-day accuracy', value: '77.8%' },
            { label: 'Signal families', value: '4' },
          ].map((s, i) => (
            <div key={s.label} style={{ padding: '22px 0', paddingRight: 24, borderRight: i < 3 ? '1px solid #e5e5e5' : 'none', paddingLeft: i > 0 ? 24 : 0 }}>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 26, fontWeight: 700, color: '#0a0a0a', letterSpacing: '-0.03em', marginBottom: 4 }}>{s.value}</p>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.08em' }}>{s.label.toUpperCase()}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pair snapshot */}
      <section style={{ maxWidth: 1152, margin: '0 auto', padding: '64px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 24 }}>
          <div>
            <h2 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 20, color: '#0a0a0a', letterSpacing: '-0.02em', margin: 0 }}>Live Regime Snapshot</h2>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#a0a0a0', marginTop: 6 }}>{TODAY} · Updated 07:12 UTC</p>
          </div>
          <button onClick={() => navigate('/terminal')} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#737373', background: 'none', border: '1px solid #e5e5e5', padding: '7px 14px', cursor: 'pointer' }}>Open terminal →</button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: `repeat(${PAIRS.length}, 1fr)`, gap: 1, background: '#e5e5e5', boxShadow: '0 0 0 1px #e5e5e5' }}>
          {PAIRS.map(p => <PairCard key={p.label} pair={p} call={MOCK_REGIME_CALLS[p.label]} signals={MOCK_SIGNALS[p.label]} navigate={navigate} />)}
        </div>
      </section>


      {/* Regime heatmap */}
      <section style={{ maxWidth: 1152, margin: '0 auto', padding: '0 24px 48px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 20 }}>
          <div>
            <h2 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 20, color: '#0a0a0a', letterSpacing: '-0.02em', margin: 0 }}>30-Day Regime View</h2>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#a0a0a0', marginTop: 6 }}>Cross-pair regime at a glance. Click a pair for detail.</p>
          </div>
        </div>
        <RegimeHeatmap navigate={navigate} />
      </section>
      {/* Validation strip */}
      <section style={{ background: '#0a0a0a', borderTop: '1px solid #111', borderBottom: '1px solid #111' }}>
        <div style={{ maxWidth: 1152, margin: '0 auto', padding: '56px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 28, flexWrap: 'wrap', gap: 20 }}>
            <div>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#444', letterSpacing: '0.12em', marginBottom: 8 }}>VALIDATION LOG</p>
              <h2 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 20, color: '#f2f2f2', letterSpacing: '-0.02em', margin: 0 }}>Next-day outcome, on the record.</h2>
              <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#525252', marginTop: 8 }}>Every call validated the following trading day. No revisions, no ex-post edits.</p>
            </div>
            <div style={{ textAlign: 'right' }}>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 36, fontWeight: 700, color: '#22c55e', letterSpacing: '-0.04em', lineHeight: 1 }}>77.8%</p>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#444', letterSpacing: '0.1em', marginTop: 4 }}>7-DAY ACCURACY</p>
            </div>
          </div>
          <ValidationTable rows={MOCK_VALIDATION.slice(0, 6)} tone="dark" />
          <button onClick={() => navigate('/performance')} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#555', background: 'none', border: '1px solid #1f1f1f', padding: '9px 16px', marginTop: 16, cursor: 'pointer' }}>Full validation log →</button>
        </div>
      </section>

      {/* Signal Architecture */}
      <section style={{ maxWidth: 1152, margin: '0 auto', padding: '64px 24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 64, alignItems: 'start' }}>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 14 }}>SIGNAL ARCHITECTURE</p>
            <h2 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 28, color: '#0a0a0a', letterSpacing: '-0.025em', lineHeight: 1.2, margin: '0 0 16px' }}>Four signal<br />families. One<br />composite.</h2>
            <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#737373', lineHeight: 1.7 }}>Each family is normalized to a percentile rank before weighting. The composite drives the regime label.</p>
          </div>
          <div style={{ border: '1px solid #e5e5e5' }}>
            {[
              { n: '01', label: 'Rate Differentials', desc: '2Y sovereign yield spreads. Primary driver of medium-term FX regime direction.', color: BRAND.eurusd },
              { n: '02', label: 'COT Positioning', desc: 'CFTC weekly non-commercial net positions as percentile ranks. Crowd and reversal signals.', color: BRAND.usdjpy },
              { n: '03', label: 'Realized Volatility', desc: '5d and 20d realized vs 30d implied. Vol gate forces VOL_EXPANDING above 90th pctile.', color: BRAND.usdinr },
              { n: '04', label: 'OI and Risk Reversals', desc: 'Open interest flows and 25-delta risk reversals. INR-specific series included.', color: '#888' },
            ].map((s, i) => (
              <div key={s.n} style={{ display: 'flex', alignItems: 'flex-start', gap: 20, padding: '20px 22px', borderBottom: i < 3 ? '1px solid #e5e5e5' : 'none' }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: s.color, fontWeight: 700, minWidth: 24, paddingTop: 2 }}>{s.n}</span>
                <div>
                  <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 14, color: '#0a0a0a', marginBottom: 4 }}>{s.label}</p>
                  <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#737373', lineHeight: 1.6 }}>{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* About strip */}
      <section style={{ borderTop: '1px solid #e5e5e5', borderBottom: '1px solid #e5e5e5' }}>
        <div style={{ maxWidth: 1152, margin: '0 auto', padding: '48px 24px', display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 64, alignItems: 'start' }}>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 14 }}>ABOUT</p>
            <h2 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 22, color: '#0a0a0a', letterSpacing: '-0.02em', margin: 0 }}>Shreyash Sakhare</h2>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#a0a0a0', marginTop: 6 }}>EE Undergrad · Discretionary Macro Research</p>
          </div>
          <div>
            <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 15, color: '#525252', lineHeight: 1.75, maxWidth: 580, margin: '0 0 20px' }}>
              Studying how G10 FX regimes form and break using rate differentials, COT positioning, and volatility. This site is the public trace of that work — dated calls, validated outcomes, no narrative added after the fact.
            </p>
            <div style={{ display: 'flex', gap: 20 }}>
              <button onClick={() => navigate('/about')} style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, fontWeight: 500, color: '#0a0a0a', background: 'none', border: '1px solid #e5e5e5', padding: '8px 16px', cursor: 'pointer' }}>About this project</button>
              <button onClick={() => navigate('/brief')} style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, fontWeight: 500, color: '#737373', background: 'none', border: 'none', padding: '8px 0', cursor: 'pointer', textDecoration: 'underline', textDecorationColor: '#d0d0d0', textUnderlineOffset: 4 }}>Today's brief →</button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

// ─── Brief Page (upgraded) ────────────────────────────────────────────────────
function BriefPage({ navigate }) {
  const [activePair, setActivePair] = React.useState('ALL');

  const macroContext = "Dollar index softening into month-end rebalancing flows. Fed speaker today (14:00 ET). Risk-on tone with equities bid. UST 2Y at 4.82%, 10Y at 4.41. DXY -0.18%.";

  return (
    <div style={{ maxWidth: 1152, margin: '0 auto', padding: '48px 24px' }}>
      {/* Header */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'start', gap: 32, marginBottom: 40, paddingBottom: 24, borderBottom: '1px solid #e5e5e5' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }} />
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#888', letterSpacing: '0.1em' }}>MORNING BRIEF</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#ccc' }}>{TODAY}</span>
          </div>
          <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 32, color: '#0a0a0a', letterSpacing: '-0.03em', margin: 0 }}>Daily Brief — {TODAY}</h1>
        </div>
        <button onClick={() => navigate('/terminal')}
          style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#555', background: 'none', border: '1px solid #e5e5e5', padding: '9px 16px', cursor: 'pointer', whiteSpace: 'nowrap' }}>
          Open terminal →
        </button>
      </div>

      {/* Macro context */}
      <div style={{ background: '#fafafa', border: '1px solid #e5e5e5', borderLeft: '3px solid #0a0a0a', padding: '16px 20px', marginBottom: 40 }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em', marginBottom: 8 }}>MACRO CONTEXT</p>
        <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#333', lineHeight: 1.7 }}>{macroContext}</p>
      </div>

      {/* Pair filter tabs */}
      <div style={{ display: 'flex', gap: 1, marginBottom: 32, borderBottom: '1px solid #e5e5e5' }}>
        {['ALL', ...PAIRS.map(p => p.display)].map(label => {
          const active = activePair === label;
          const pairMeta = PAIRS.find(p => p.display === label);
          return (
            <button key={label} onClick={() => setActivePair(label)}
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, padding: '10px 18px', color: active ? '#0a0a0a' : '#999', borderBottom: active ? `2px solid ${pairMeta?.pairColor ?? '#0a0a0a'}` : '2px solid transparent', marginBottom: -1, fontWeight: active ? 700 : 400, transition: 'color 0.1s', letterSpacing: '0.04em' }}>
              {label}
            </button>
          );
        })}
      </div>

      {/* Pair sections */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {PAIRS.filter(p => activePair === 'ALL' || activePair === p.display).map(p => {
          const call = MOCK_REGIME_CALLS[p.label];
          const sig = MOCK_SIGNALS[p.label];
          const section = BRIEF_SECTIONS[p.label];
          const pct = call ? Math.round(call.confidence * 100) : null;

          return (
            <div key={p.label} style={{ border: '1px solid #e5e5e5', borderTop: `3px solid ${p.pairColor}`, marginBottom: 16 }}>
              {/* Pair header */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'start', gap: 24, padding: '20px 24px', borderBottom: '1px solid #f0f0f0', background: '#fafafa' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, fontWeight: 700, color: p.pairColor }}>{p.display}</span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 700, color: '#0a0a0a', background: '#f0f0f0', padding: '2px 8px', letterSpacing: '0.04em' }}>{section?.regime}</span>
                  </div>
                  <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#737373', lineHeight: 1.5 }}>{section?.primaryDriver}</p>
                </div>
                {/* Confidence + quick stats */}
                <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, fontWeight: 700, color: p.pairColor, letterSpacing: '-0.03em', lineHeight: 1 }}>{pct ?? '—'}<span style={{ fontSize: 12, color: '#aaa', fontWeight: 400 }}>{pct != null ? '%' : ''}</span></p>
                    <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', letterSpacing: '0.1em', marginTop: 4 }}>CONFIDENCE</p>
                    <div style={{ marginTop: 6, width: 80 }}>
                      <div style={{ background: '#ebebeb', height: 2 }}>
                        <div style={{ width: `${pct ?? 0}%`, height: '100%', background: p.pairColor }} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Signal snapshot row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', borderBottom: '1px solid #f0f0f0' }}>
                {[
                  ['SPOT', sig?.spot?.toFixed(p.label === 'USDJPY' ? 2 : 4)],
                  ['RATE DIFF 2Y', fmt2(sig?.rate_diff_2y)],
                  ['COT PCTILE', fmtInt(sig?.cot_percentile)],
                  ['RVOL 20D', fmt2(sig?.realized_vol_20d)],
                  ['COMPOSITE', fmt2(call?.signal_composite)],
                ].map(([label, value], i) => (
                  <div key={label} style={{ padding: '14px 18px', borderRight: i < 4 ? '1px solid #f0f0f0' : 'none' }}>
                    <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', letterSpacing: '0.1em', marginBottom: 6 }}>{label}</p>
                    <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, fontWeight: 700, color: '#0a0a0a' }}>{value ?? '—'}</p>
                  </div>
                ))}
              </div>

              {/* Analysis text */}
              <div style={{ padding: '22px 24px' }}>
                {section?.analysis.split('\n\n').map((para, i) => (
                  <p key={i} style={{ fontFamily: 'Inter, sans-serif', fontSize: 15, color: i === 1 ? '#111' : '#444', lineHeight: 1.75, marginBottom: 12, fontWeight: i === 1 ? 500 : 400 }}>{para}</p>
                ))}
                <button onClick={() => navigate(`/terminal/fx-regime/${p.urlSlug}`)}
                  style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: p.pairColor, background: 'none', border: `1px solid ${p.pairColor}40`, padding: '7px 14px', cursor: 'pointer', marginTop: 8 }}>
                  Open {p.display} desk →
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 40, paddingTop: 24, borderTop: '1px solid #e5e5e5' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#c0c0c0', letterSpacing: '0.06em', lineHeight: 1.8 }}>
          RESEARCH AND LEARNING ONLY. NOT INVESTMENT ADVICE. ALL CALLS LOGGED PRIOR TO MARKET OPEN. OUTCOMES VALIDATED NEXT TRADING DAY.
        </p>
      </div>
    </div>
  );
}

// ─── Performance Page (upgraded) ─────────────────────────────────────────────
function PerformancePage({ navigate }) {
  const [filterPair, setFilterPair] = React.useState('ALL');

  const correct = MOCK_VALIDATION.filter(r => r.outcome === 'correct').length;
  const total = MOCK_VALIDATION.length;
  const accuracy = ((correct / total) * 100).toFixed(1);
  const avgReturn = (MOCK_VALIDATION.reduce((s, r) => s + r.return_pct, 0) / total).toFixed(2);
  const totalReturn = MOCK_EQUITY.ALL[MOCK_EQUITY.ALL.length - 1].toFixed(2);

  const filtered = filterPair === 'ALL' ? MOCK_VALIDATION : MOCK_VALIDATION.filter(r => r.pair === filterPair);

  return (
    <div style={{ maxWidth: 1152, margin: '0 auto', padding: '48px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 40, paddingBottom: 24, borderBottom: '1px solid #e5e5e5' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 10 }}>TRACK RECORD</p>
        <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 32, color: '#0a0a0a', letterSpacing: '-0.03em', margin: 0 }}>Performance</h1>
        <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#737373', marginTop: 8 }}>Next-day directional validation. Updated daily after market close.</p>
      </div>

      {/* Top metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: '#e5e5e5', boxShadow: '0 0 0 1px #e5e5e5', marginBottom: 32 }}>
        {[
          { label: '7D ACCURACY', value: `${accuracy}%`, color: '#16a34a', sub: `${correct}/${total} correct` },
          { label: 'AVG NEXT-DAY RET', value: `${Number(avgReturn) >= 0 ? '+' : ''}${avgReturn}%`, color: BRAND.usdjpy, sub: 'Per call directional' },
          { label: 'CUMULATIVE RET', value: `+${totalReturn}%`, color: BRAND.eurusd, sub: 'Since Apr 2026' },
          { label: 'CALLS VALIDATED', value: `${total}`, color: '#0a0a0a', sub: `${PAIRS.length} pairs` },
        ].map(m => (
          <div key={m.label} style={{ background: '#fff', padding: '22px 20px' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#999', letterSpacing: '0.12em', marginBottom: 10 }}>{m.label}</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 30, fontWeight: 700, color: m.color, letterSpacing: '-0.03em', lineHeight: 1 }}>{m.value}</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#bbb', marginTop: 6 }}>{m.sub}</p>
          </div>
        ))}
      </div>

      {/* Equity curve — composite */}
      <div style={{ border: '1px solid #e5e5e5', marginBottom: 24 }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em', marginBottom: 4 }}>CUMULATIVE RETURN — ALL PAIRS</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#aaa' }}>Apr 7 — {TODAY} · Next-day spot move in call direction</p>
          </div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 22, fontWeight: 700, color: '#16a34a', letterSpacing: '-0.03em' }}>+{totalReturn}%</p>
        </div>
        <div style={{ padding: '16px 20px 8px' }}>
          {/* Main equity curve */}
          <svg width="100%" height="120" viewBox="0 0 800 120" preserveAspectRatio="none" style={{ display: 'block' }}>
            <defs>
              <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#16a34a" stopOpacity="0.2" />
                <stop offset="100%" stopColor="#16a34a" stopOpacity="0" />
              </linearGradient>
            </defs>
            {(() => {
              const vals = MOCK_EQUITY.ALL;
              const mn = Math.min(...vals) - 0.05, mx = Math.max(...vals) + 0.05;
              const n = vals.length;
              const pts = vals.map((v, i) => [i / (n - 1) * 800, 112 - (v - mn) / (mx - mn) * 104]);
              const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
              return <>
                <path d={`${line} L800,120 L0,120 Z`} fill="url(#equityGrad)" />
                <path d={line} fill="none" stroke="#16a34a" strokeWidth="2" />
                {pts.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="3" fill="#16a34a" stroke="#fff" strokeWidth="1.5" />)}
              </>;
            })()}
          </svg>
          {/* X-axis labels */}
          <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: 6, paddingBottom: 8 }}>
            {MOCK_EQUITY.dates.filter((_, i) => i % 3 === 0 || i === MOCK_EQUITY.dates.length - 1).map((d, i) => (
              <span key={i} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb' }}>{d}</span>
            ))}
          </div>
        </div>
        {/* Per-pair mini equity curves */}
        <div style={{ display: 'grid', gridTemplateColumns: `repeat(${PAIRS.length}, 1fr)`, borderTop: '1px solid #f0f0f0' }}>
          {PAIRS.map((p, i) => {
            const vals = MOCK_EQUITY[p.label];
            const finalVal = vals[vals.length - 1];
            return (
              <div key={p.label} style={{ padding: '14px 18px', borderRight: i < PAIRS.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: p.pairColor, fontWeight: 700 }}>{p.display}</span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 700, color: finalVal >= 0 ? '#16a34a' : '#dc2626' }}>
                    {finalVal >= 0 ? '+' : ''}{finalVal.toFixed(2)}%
                  </span>
                </div>
                <Sparkline values={vals} color={p.pairColor} height={40} width={200} showDots={false} showZeroLine={true} />
              </div>
            );
          })}
        </div>
      </div>

      {/* Accuracy over time chart */}
      <div style={{ border: '1px solid #e5e5e5', marginBottom: 24 }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #f0f0f0' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em' }}>ROLLING 7-DAY ACCURACY</p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: `repeat(${PAIRS.length}, 1fr)`, borderBottom: '1px solid #f0f0f0' }}>
          {PAIRS.map((p, i) => {
            const pRows = MOCK_VALIDATION.filter(r => r.pair === p.display);
            const acc = pRows.length ? ((pRows.filter(r => r.outcome === 'correct').length / pRows.length) * 100).toFixed(0) : '—';
            return (
              <div key={p.label} style={{ padding: '16px 20px', borderRight: i < PAIRS.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: p.pairColor, fontWeight: 700, marginBottom: 4 }}>{p.display}</p>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 26, fontWeight: 700, color: '#0a0a0a', letterSpacing: '-0.03em' }}>{acc}%</p>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#bbb', marginTop: 2 }}>{pRows.length} calls</p>
                {/* Mini accuracy bar */}
                <div style={{ marginTop: 10, background: '#f0f0f0', height: 3 }}>
                  <div style={{ width: `${acc}%`, height: '100%', background: p.pairColor }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Filter + validation table */}
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 1, borderBottom: '1px solid #e5e5e5' }}>
        {['ALL', ...PAIRS.map(p => p.display)].map(label => {
          const active = filterPair === label;
          const pairMeta = PAIRS.find(p => p.display === label);
          return (
            <button key={label} onClick={() => setFilterPair(label)}
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '9px 16px', color: active ? '#0a0a0a' : '#999', borderBottom: active ? `2px solid ${pairMeta?.pairColor ?? '#0a0a0a'}` : '2px solid transparent', marginBottom: -1, fontWeight: active ? 700 : 400, letterSpacing: '0.06em' }}>
              {label}
            </button>
          );
        })}
        <span style={{ marginLeft: 'auto', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#bbb' }}>{filtered.length} calls shown</span>
      </div>

      <ValidationTable rows={filtered} tone="light" />


      {/* Regime transition matrix */}
      <div style={{ border: '1px solid #e5e5e5', marginBottom: 24 }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #f0f0f0' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em', marginBottom: 4 }}>REGIME TRANSITION MATRIX</p>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#aaa' }}>How often each regime transitions to another (based on available history)</p>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'JetBrains Mono, monospace', fontSize: 10 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                <th style={{ padding: '10px 14px', textAlign: 'left', color: '#aaa', fontWeight: 500, minWidth: 180 }}>FROM \ TO</th>
                {['STRONG STR', 'MOD STR', 'NEUTRAL', 'MOD WEAK', 'VOL EXP'].map(h => (
                  <th key={h} style={{ padding: '10px 10px', textAlign: 'center', color: '#aaa', fontWeight: 500, minWidth: 80 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                ['STRONG USD STRENGTH', [null, '72%', '18%', '8%', '2%']],
                ['MODERATE USD STRENGTH', ['24%', null, '51%', '20%', '5%']],
                ['NEUTRAL', ['12%', '38%', null, '41%', '9%']],
                ['MODERATE USD WEAKNESS', ['8%', '22%', '52%', null, '18%']],
                ['VOL_EXPANDING', ['15%', '30%', '35%', '20%', null]],
              ].map(([regime, probs], ri) => (
                <tr key={regime} style={{ borderBottom: '1px solid #f8f8f8' }}>
                  <td style={{ padding: '10px 14px', color: '#555', fontSize: 10 }}>{regime}</td>
                  {probs.map((p, ci) => (
                    <td key={ci} style={{ padding: '10px 10px', textAlign: 'center', color: p === null ? '#f0f0f0' : parseInt(p) > 50 ? '#0a0a0a' : '#888', fontWeight: p && parseInt(p) > 40 ? 700 : 400, background: p === null ? '#f8f8f8' : `rgba(75,163,227,${parseInt(p)/200})` }}>
                      {p ?? '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#c0c0c0', letterSpacing: '0.06em', lineHeight: 1.8, paddingTop: 20, marginTop: 20, borderTop: '1px solid #e5e5e5' }}>
        NEXT-DAY DIRECTIONAL OUTCOME. RETURN % IS NEXT-DAY CLOSE-TO-CLOSE SPOT MOVE IN DIRECTION OF CALL. RESEARCH ONLY - NOT INVESTMENT ADVICE.
      </p>
    </div>
  );
}

// ─── FX Regime Page ───────────────────────────────────────────────────────────
function FxRegimePage({ navigate }) {
  return (
    <div style={{ maxWidth: 1152, margin: '0 auto', padding: '64px 24px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 80 }}>
        <div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 14 }}>STRATEGY</p>
          <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 36, color: '#0a0a0a', letterSpacing: '-0.03em', lineHeight: 1.1, margin: '0 0 20px' }}>FX Regime</h1>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#737373', lineHeight: 1.7, marginBottom: 28 }}>
            Classifies each pair's current market environment using a composite of four signal families. Calls are made once daily before market open.
          </p>
          <button onClick={() => navigate('/terminal/fx-regime')} style={{ background: '#0a0a0a', color: '#ffffff', fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 13, padding: '10px 18px', border: 'none', cursor: 'pointer' }}>Open pair desks →</button>
        </div>
        <div>
          <div style={{ border: '1px solid #e5e5e5', marginBottom: 32 }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e5e5', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.1em' }}>CURRENT CALLS</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0' }}>{TODAY}</span>
            </div>
            {PAIRS.map((p, i) => {
              const call = MOCK_REGIME_CALLS[p.label];
              return (
                <div key={p.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: i < PAIRS.length - 1 ? '1px solid #f0f0f0' : 'none', gap: 16 }}>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: p.pairColor, fontWeight: 700, minWidth: 60 }}>{p.display}</span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#0a0a0a', fontWeight: 700, flex: 1 }}>{call?.regime}</span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#737373' }}>{fmtPct(call?.confidence)}</span>
                  <button onClick={() => navigate(`/terminal/fx-regime/${p.urlSlug}`)} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: p.pairColor, background: 'none', border: `1px solid ${p.pairColor}40`, padding: '5px 10px', cursor: 'pointer' }}>→</button>
                </div>
              );
            })}
          </div>
          <div style={{ border: '1px solid #e5e5e5' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e5e5' }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.1em' }}>REGIME TAXONOMY</span>
            </div>
            {[
              ['STRONG/MODERATE USD STRENGTH', 'Composite strongly or moderately favors USD. Confidence above 60%.'],
              ['NEUTRAL', 'Composite near neutral band. No clear directional bias.'],
              ['STRONG/MODERATE USD WEAKNESS', 'Composite favors USD selling pressure at varying conviction.'],
              ['VOL_EXPANDING', 'Implied vol above 90th pctile. Vol gate applied. Regime forced.'],
              ['DEPRECIATION/APPRECIATION PRESSURE', 'INR-specific. Composite drives USD/INR direction.'],
            ].map(([regime, desc], i) => (
              <div key={regime} style={{ display: 'flex', gap: 20, padding: '14px 20px', borderBottom: i < 4 ? '1px solid #f0f0f0' : 'none' }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 700, color: '#0a0a0a', minWidth: 200, flexShrink: 0, lineHeight: 1.5 }}>{regime}</span>
                <span style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#737373', lineHeight: 1.6 }}>{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── 404 ─────────────────────────────────────────────────────────────────────
function NotFoundPage({ navigate }) {
  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: '120px 24px', textAlign: 'center' }}>
      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 80, fontWeight: 700, color: '#f0f0f0', lineHeight: 1, letterSpacing: '-0.05em' }}>404</p>
      <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 22, color: '#0a0a0a', letterSpacing: '-0.02em', margin: '16px 0 10px' }}>Page not found.</h1>
      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#737373', marginBottom: 32 }}>This route does not exist in the current build.</p>
      <button onClick={() => navigate('/')} style={{ background: '#0a0a0a', color: '#fff', fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 13, padding: '10px 20px', border: 'none', cursor: 'pointer' }}>Back to home</button>
    </div>
  );
}

Object.assign(window, {
  Sparkline, MOCK_EQUITY, BRIEF_SECTIONS,
  HomePage, BriefPage, PerformancePage, FxRegimePage, NotFoundPage,
});
