
// ─── About Page — Full interactive methodology experience ─────────────────────

// Pipeline steps definition
const PIPELINE_STEPS = [
  {
    id: 'ingest',
    n: '01',
    title: 'Data Ingestion',
    label: 'RAW MARKET DATA',
    desc: 'Every trading day, a Python pipeline ingests public market data from multiple sources simultaneously. No proprietary feeds — only what is publicly available.',
    detail: 'Sources include: Yahoo Finance (FX spot, equity indices), FRED (2Y/10Y sovereign yields for G10), CFTC COT reports (weekly non-commercial positioning), Deribit / public vol surfaces (implied vol), open interest from exchange data, and RBI/SEBI releases for INR-specific series.',
    sources: ['FX Spot (Yahoo Finance)', 'Sovereign Yields (FRED)', 'CFTC COT Reports', 'Implied Volatility', 'Open Interest', 'INR-Specific (RBI)'],
    color: BRAND.eurusd,
    metric: { label: 'DATA SERIES', value: '40+' },
  },
  {
    id: 'normalize',
    n: '02',
    title: 'Signal Normalization',
    label: 'PERCENTILE RANKING',
    desc: 'Raw values carry no inherent comparability across pairs or time. Each signal series is normalized to a rolling percentile rank — converting absolute values into a 0-100 score.',
    detail: 'Rate differential of -0.45 means nothing without context. At the 22nd percentile of a 252-day lookback window, it signals meaningful USD weakness pressure. This normalization is the engine that makes regime calls consistent across pairs with vastly different scales.',
    sources: ['252-day lookback window', 'Cross-pair normalization', 'Rolling z-scores', 'Outlier winsorization'],
    color: BRAND.usdjpy,
    metric: { label: 'LOOKBACK', value: '252d' },
  },
  {
    id: 'composite',
    n: '03',
    title: 'Composite Construction',
    label: 'WEIGHTED COMPOSITE',
    desc: 'Normalized signals are combined into a single composite score using pair-specific weights. The composite runs from roughly -2 (strong bearish USD) to +2 (strong bullish USD).',
    detail: 'Rate differentials carry the heaviest weight as the structural anchor. COT positioning adds a sentiment/crowd overlay. Volatility signals gate the regime — if implied vol crosses the 90th percentile, the regime is forced to VOL_EXPANDING regardless of composite direction.',
    sources: ['Rate diff weight: ~40%', 'COT weight: ~30%', 'Vol weight: ~20%', 'OI/RR weight: ~10%'],
    color: BRAND.usdinr,
    metric: { label: 'COMPOSITE RANGE', value: '±2.0' },
  },
  {
    id: 'regime',
    n: '04',
    title: 'Regime Classification',
    label: 'LABEL ASSIGNMENT',
    desc: 'The composite score is mapped to a regime label via threshold bands. The label is the pipeline\'s read of the current equilibrium — not a price forecast.',
    detail: 'Labels are strings, not a fixed enum — the pipeline can emit new labels as strategies evolve. Each label carries a confidence score derived from the distance from band boundaries and signal agreement. VOL_EXPANDING overrides all other labels when the vol gate fires.',
    sources: ['Composite > 1.2: STRONG USD STRENGTH', 'Composite 0.6-1.2: MODERATE', 'Composite ±0.4: NEUTRAL', 'IV > P90: VOL_EXPANDING'],
    color: '#888',
    metric: { label: 'LABEL TYPES', value: '11+' },
  },
  {
    id: 'validate',
    n: '05',
    title: 'Call & Validation',
    label: 'PUBLIC RECORD',
    desc: 'The regime call is published before market open with the confidence score and primary driver. The following trading day, the outcome is logged — correct or incorrect, no revisions.',
    detail: 'Validation is directional: if the call was MODERATE USD WEAKNESS and EUR/USD closed higher the next day, it is marked correct. The return percentage is the next-day close-to-close spot move. This is the only performance metric that matters — everything else is noise.',
    sources: ['Published pre-market', 'Next-day close validation', 'No ex-post revisions', 'All outcomes public'],
    color: '#22c55e',
    metric: { label: '7D ACCURACY', value: '77.8%' },
  },
];

// Signal families for expandable cards
const SIGNAL_FAMILIES = [
  {
    id: 'rate',
    n: '01',
    label: 'Rate Differentials',
    color: BRAND.eurusd,
    summary: '2Y sovereign yield spreads. The structural anchor of the composite.',
    body: 'The 2-year government bond yield differential captures the forward-looking monetary policy divergence between two economies. A widening positive spread (e.g., USD 2Y > EUR 2Y) signals dollar strength pressure. The 2Y tenor is used — not 10Y — because it better reflects expected short-term policy paths rather than term premium and fiscal dynamics.',
    stats: [['Tenor', '2Y sovereign'], ['Pairs', 'G10 + INR'], ['Weight', '~40%'], ['Update', 'Daily FRED']],
  },
  {
    id: 'cot',
    n: '02',
    label: 'COT Positioning',
    color: BRAND.usdjpy,
    summary: 'CFTC weekly non-commercial net positions as percentile ranks.',
    body: 'The Commitment of Traders report reveals how speculative futures participants are positioned. Extreme readings (>85th or <15th percentile) signal crowded positioning and potential reversal risk. Moderate readings in the direction of the rate differential confirm the trend. The COT acts as a sentiment overlay — agreeing with the rate signal adds conviction, disagreeing reduces confidence.',
    stats: [['Source', 'CFTC weekly'], ['Lag', '3 days'], ['Weight', '~30%'], ['Pairs', 'EUR/USD, USD/JPY, USD/INR']],
  },
  {
    id: 'vol',
    n: '03',
    label: 'Realized Volatility',
    color: BRAND.usdinr,
    summary: '5d and 20d realized vs 30d implied. Vol gate at 90th percentile.',
    body: 'Two realized vol windows (5d short-term and 20d medium-term) are compared against the 30-day implied vol from options markets. When IV exceeds RV significantly, the market is pricing in uncertainty beyond what has been realized — this raises caution. When IV crosses the 90th percentile of its own lookback, the vol gate fires and forces the regime to VOL_EXPANDING, overriding the directional composite entirely.',
    stats: [['Short window', '5-day realized'], ['Medium window', '20-day realized'], ['Forward vol', '30-day implied'], ['Gate trigger', 'IV > P90']],
  },
  {
    id: 'oi',
    n: '04',
    label: 'OI and Risk Reversals',
    color: '#888',
    summary: '25-delta risk reversals and open interest flows for asymmetric reads.',
    body: 'Risk reversals measure the skew between call and put implied volatility — a positive RR means the market is pricing upside (calls more expensive than puts). Combined with open interest dynamics, this reveals whether positioning is asymmetric in a way that could accelerate a move. For USD/INR specifically, INR-specific series from RBI and SEBI publications are incorporated given the managed float regime.',
    stats: [['RR tenor', '25-delta, 1M'], ['OI source', 'Exchange data'], ['INR special', 'RBI/SEBI series'], ['Weight', '~10%']],
  },
];

// Composite simulator — maps score to regime label
function scoreToRegime(score) {
  if (score > 1.2) return { label: 'STRONG USD STRENGTH', color: '#f0f0f0' };
  if (score > 0.6) return { label: 'MODERATE USD STRENGTH', color: '#d4d4d4' };
  if (score > -0.4 && score < 0.4) return { label: 'NEUTRAL', color: '#888' };
  if (score < -1.2) return { label: 'STRONG USD WEAKNESS', color: BRAND.usdinr };
  if (score < -0.6) return { label: 'MODERATE USD WEAKNESS', color: BRAND.eurusd };
  return { label: 'MODERATE USD STRENGTH', color: '#d4d4d4' };
}

// ─── Pipeline Walkthrough Component ──────────────────────────────────────────
function PipelineWalkthrough() {
  const [activeStep, setActiveStep] = React.useState(0);
  const [animating, setAnimating] = React.useState(false);
  const step = PIPELINE_STEPS[activeStep];

  const goTo = (i) => {
    if (animating || i === activeStep) return;
    setAnimating(true);
    setTimeout(() => { setActiveStep(i); setAnimating(false); }, 180);
  };

  return (
    <div style={{ border: '1px solid #e5e5e5' }}>
      {/* Step progress bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid #e5e5e5', background: '#fafafa' }}>
        {PIPELINE_STEPS.map((s, i) => {
          const active = i === activeStep;
          const done = i < activeStep;
          return (
            <button key={s.id} onClick={() => goTo(i)}
              style={{ flex: 1, padding: '14px 12px', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, letterSpacing: '0.08em', color: active ? '#0a0a0a' : done ? '#888' : '#bbb', borderBottom: active ? `2px solid ${s.color}` : done ? '2px solid #e5e5e5' : '2px solid transparent', marginBottom: -1, background: 'none', transition: 'color 0.15s', fontWeight: active ? 700 : 400, textAlign: 'left', cursor: 'pointer', borderRight: i < 4 ? '1px solid #f0f0f0' : 'none' }}>
              <span style={{ display: 'block', color: done ? s.color : active ? s.color : '#ccc', marginBottom: 4 }}>{s.n}</span>
              {s.title}
            </button>
          );
        })}
      </div>

      {/* Step content */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: 320 }}>
        {/* Left: text */}
        <div style={{ padding: '32px', borderRight: '1px solid #f0f0f0', opacity: animating ? 0 : 1, transform: animating ? 'translateY(6px)' : 'translateY(0)', transition: 'opacity 0.18s ease, transform 0.18s ease' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: step.color, fontWeight: 700, letterSpacing: '0.1em' }}>{step.n}</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#bbb', letterSpacing: '0.12em' }}>{step.label}</span>
          </div>
          <h3 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 22, color: '#0a0a0a', letterSpacing: '-0.02em', margin: '0 0 14px' }}>{step.title}</h3>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#525252', lineHeight: 1.75, marginBottom: 16 }}>{step.desc}</p>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#888', lineHeight: 1.7 }}>{step.detail}</p>

          {/* Nav buttons */}
          <div style={{ display: 'flex', gap: 10, marginTop: 28 }}>
            <button onClick={() => goTo(Math.max(0, activeStep - 1))} disabled={activeStep === 0}
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '8px 16px', border: '1px solid #e5e5e5', color: activeStep === 0 ? '#ccc' : '#555', cursor: activeStep === 0 ? 'default' : 'pointer', background: 'none' }}>
              ← Prev
            </button>
            <button onClick={() => goTo(Math.min(4, activeStep + 1))} disabled={activeStep === 4}
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '8px 16px', background: activeStep === 4 ? '#f0f0f0' : '#0a0a0a', color: activeStep === 4 ? '#bbb' : '#fff', cursor: activeStep === 4 ? 'default' : 'pointer', border: 'none' }}>
              {activeStep === 4 ? 'Complete' : 'Next →'}
            </button>
          </div>
        </div>

        {/* Right: visual */}
        <div style={{ padding: '32px', background: '#fafafa', opacity: animating ? 0 : 1, transition: 'opacity 0.18s ease', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          {/* Large metric */}
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb', letterSpacing: '0.12em', marginBottom: 8 }}>{step.metric.label}</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 52, fontWeight: 700, color: step.color, letterSpacing: '-0.04em', lineHeight: 1, marginBottom: 24 }}>{step.metric.value}</p>
          </div>

          {/* Sources list */}
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb', letterSpacing: '0.12em', marginBottom: 12 }}>
              {activeStep === 0 ? 'DATA SOURCES' : activeStep === 1 ? 'METHODOLOGY' : activeStep === 2 ? 'WEIGHTS' : activeStep === 3 ? 'THRESHOLDS' : 'PROCESS'}
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {step.sources.map((s, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ width: 4, height: 4, background: step.color, flexShrink: 0, borderRadius: activeStep === 4 ? '50%' : 0 }} />
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#555' }}>{s}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Pipeline progress visual */}
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#ccc', letterSpacing: '0.1em', marginBottom: 10, marginTop: 24 }}>PIPELINE STAGE</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              {PIPELINE_STEPS.map((s, i) => (
                <React.Fragment key={s.id}>
                  <div style={{ width: 8, height: 8, background: i <= activeStep ? s.color : '#e5e5e5', transition: 'background 0.3s ease', flexShrink: 0, borderRadius: i === activeStep ? '50%' : 0 }} />
                  {i < 4 && <div style={{ flex: 1, height: 1, background: i < activeStep ? '#e5e5e5' : '#f0f0f0' }} />}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Signal Family Cards (expandable) ────────────────────────────────────────
function SignalFamilyCards() {
  const [expanded, setExpanded] = React.useState(null);

  return (
    <div style={{ border: '1px solid #e5e5e5' }}>
      {SIGNAL_FAMILIES.map((fam, i) => {
        const isOpen = expanded === fam.id;
        return (
          <div key={fam.id} style={{ borderBottom: i < SIGNAL_FAMILIES.length - 1 ? '1px solid #e5e5e5' : 'none' }}>
            {/* Header — always visible, clickable */}
            <button onClick={() => setExpanded(isOpen ? null : fam.id)}
              style={{ width: '100%', display: 'grid', gridTemplateColumns: '40px 1fr auto', gap: 20, alignItems: 'center', padding: '20px 24px', background: isOpen ? '#fafafa' : '#fff', cursor: 'pointer', textAlign: 'left', transition: 'background 0.15s' }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color: fam.color, fontWeight: 700 }}>{fam.n}</span>
              <div>
                <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 15, color: '#0a0a0a', margin: '0 0 3px' }}>{fam.label}</p>
                <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#888', margin: 0 }}>{fam.summary}</p>
              </div>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, color: '#bbb', transform: isOpen ? 'rotate(45deg)' : 'none', transition: 'transform 0.2s ease', display: 'block' }}>+</span>
            </button>

            {/* Expanded body */}
            <div style={{ maxHeight: isOpen ? 400 : 0, overflow: 'hidden', transition: 'max-height 0.3s ease' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 32, padding: '0 24px 24px 24px', paddingLeft: 84 }}>
                <div>
                  <div style={{ width: 32, height: 2, background: fam.color, marginBottom: 16 }} />
                  <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#444', lineHeight: 1.75 }}>{fam.body}</p>
                </div>
                <div style={{ minWidth: 160, flexShrink: 0 }}>
                  <div style={{ border: '1px solid #e5e5e5', borderTop: `2px solid ${fam.color}` }}>
                    {fam.stats.map(([label, val], j) => (
                      <div key={j} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: '10px 14px', borderBottom: j < fam.stats.length - 1 ? '1px solid #f5f5f5' : 'none' }}>
                        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', letterSpacing: '0.08em', whiteSpace: 'nowrap' }}>{label.toUpperCase()}</span>
                        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#111', fontWeight: 700, textAlign: 'right' }}>{val}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Live Composite Simulator ─────────────────────────────────────────────────
function CompositeSimulator() {
  const [weights, setWeights] = React.useState({ rate: -0.45, cot: 34, vol: 6.2, oi: 0.2 });

  // Normalize each to -1…+1 contribution
  const rateContrib = Math.max(-1, Math.min(1, weights.rate / 5));
  const cotContrib = (weights.cot - 50) / 50;
  const volContrib = weights.vol > 9 ? -0.5 : weights.vol > 7 ? -0.2 : 0.1;
  const oiContrib = weights.oi;

  const composite = (rateContrib * 0.4 + cotContrib * 0.3 + volContrib * 0.2 + oiContrib * 0.1) * 2;
  const clampedComp = Math.max(-2, Math.min(2, composite));
  const regime = scoreToRegime(clampedComp);
  const confidence = Math.min(0.95, Math.max(0.30, 0.5 + Math.abs(clampedComp) * 0.2));
  const compPct = ((clampedComp + 2) / 4 * 100);

  const Slider = ({ id, label, min, max, step, unit, value }) => (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.08em' }}>{label}</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#0a0a0a', fontWeight: 700 }}>{value.toFixed(step < 1 ? 2 : 0)}{unit}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => setWeights(w => ({ ...w, [id]: parseFloat(e.target.value) }))}
        style={{ width: '100%', accentColor: BRAND.usdjpy, height: 2, cursor: 'pointer' }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3 }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#ccc' }}>{min}{unit}</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#ccc' }}>{max}{unit}</span>
      </div>
    </div>
  );

  return (
    <div style={{ border: '1px solid #e5e5e5' }}>
      <div style={{ padding: '16px 24px', borderBottom: '1px solid #e5e5e5', background: '#fafafa', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', letterSpacing: '0.1em', marginBottom: 2 }}>COMPOSITE SIMULATOR</p>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#555' }}>Adjust signal inputs — watch regime and confidence update live.</p>
        </div>
        <button onClick={() => setWeights({ rate: -0.45, cot: 34, vol: 6.2, oi: 0.2 })}
          style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#888', border: '1px solid #e5e5e5', padding: '6px 12px', background: 'none', cursor: 'pointer' }}>Reset</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0 }}>
        {/* Left: sliders */}
        <div style={{ padding: '24px', borderRight: '1px solid #f0f0f0' }}>
          <Slider id="rate" label="RATE DIFF 2Y" min={-5} max={5} step={0.05} unit="" value={weights.rate} />
          <Slider id="cot" label="COT PERCENTILE" min={0} max={100} step={1} unit="" value={weights.cot} />
          <Slider id="vol" label="REALIZED VOL 20D" min={1} max={15} step={0.1} unit="" value={weights.vol} />
          <Slider id="oi" label="OI/RR SIGNAL" min={-1} max={1} step={0.1} unit="" value={weights.oi} />
        </div>

        {/* Right: live output */}
        <div style={{ padding: '24px', background: '#fafafa' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', letterSpacing: '0.12em', marginBottom: 20 }}>LIVE OUTPUT</p>

          {/* Composite score */}
          <div style={{ marginBottom: 24 }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb', letterSpacing: '0.1em', marginBottom: 8 }}>COMPOSITE SCORE</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 42, fontWeight: 700, color: clampedComp >= 0 ? '#16a34a' : BRAND.usdinr, letterSpacing: '-0.04em', lineHeight: 1, transition: 'color 0.3s' }}>
              {clampedComp >= 0 ? '+' : ''}{clampedComp.toFixed(2)}
            </p>
            {/* Composite bar */}
            <div style={{ position: 'relative', marginTop: 10, background: '#e5e5e5', height: 4 }}>
              <div style={{ position: 'absolute', left: '50%', top: -2, width: 2, height: 8, background: '#bbb' }} />
              <div style={{ position: 'absolute', left: `${compPct > 50 ? 50 : compPct}%`, width: `${Math.abs(compPct - 50)}%`, height: '100%', background: clampedComp >= 0 ? '#16a34a' : BRAND.usdinr, transition: 'all 0.2s ease' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#bbb' }}>BEAR -2.0</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#bbb' }}>BULL +2.0</span>
            </div>
          </div>

          {/* Regime label */}
          <div style={{ marginBottom: 20 }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb', letterSpacing: '0.1em', marginBottom: 8 }}>REGIME LABEL</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, fontWeight: 700, color: regime.color, letterSpacing: '0.04em', lineHeight: 1.4, transition: 'color 0.3s' }}>{regime.label}</p>
          </div>

          {/* Confidence */}
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb', letterSpacing: '0.1em', marginBottom: 8 }}>CONFIDENCE</p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 28, fontWeight: 700, color: '#0a0a0a', letterSpacing: '-0.03em', lineHeight: 1, marginBottom: 8 }}>
              {Math.round(confidence * 100)}<span style={{ fontSize: 14, color: '#bbb', fontWeight: 400 }}>%</span>
            </p>
            <div style={{ background: '#e5e5e5', height: 3 }}>
              <div style={{ width: `${Math.round(confidence * 100)}%`, height: '100%', background: BRAND.usdjpy, transition: 'width 0.25s ease' }} />
            </div>
          </div>

          {/* Signal contributions */}
          <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #ebebeb' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#bbb', letterSpacing: '0.1em', marginBottom: 10 }}>SIGNAL CONTRIBUTIONS</p>
            {[
              ['RATE DIFF', rateContrib * 0.4 * 2, BRAND.eurusd],
              ['COT', cotContrib * 0.3 * 2, BRAND.usdjpy],
              ['VOL', volContrib * 0.2 * 2, BRAND.usdinr],
              ['OI/RR', oiContrib * 0.1 * 2, '#888'],
            ].map(([lbl, contrib, color]) => (
              <div key={lbl} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 7 }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', minWidth: 50 }}>{lbl}</span>
                <div style={{ flex: 1, background: '#ebebeb', height: 2, position: 'relative' }}>
                  <div style={{ position: 'absolute', left: '50%', top: -1, width: 1, height: 4, background: '#ccc' }} />
                  <div style={{ position: 'absolute', left: contrib > 0 ? '50%' : `${50 + contrib / 2 * 100}%`, width: `${Math.abs(contrib) / 2 * 100}%`, height: '100%', background: color, transition: 'all 0.2s' }} />
                </div>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: contrib >= 0 ? '#16a34a' : BRAND.usdinr, fontWeight: 700, minWidth: 36, textAlign: 'right', transition: 'color 0.2s' }}>{contrib >= 0 ? '+' : ''}{contrib.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Full About Page ─────────────────────────────────────────────────────────
function AboutPage({ navigate }) {
  return (
    <div style={{ maxWidth: 1152, margin: '0 auto', padding: '56px 24px 80px' }}>

      {/* ── Section 1: Header ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 80, marginBottom: 80, paddingBottom: 64, borderBottom: '1px solid #e5e5e5' }}>
        <div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 20 }}>ABOUT</p>
          <h1 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 800, fontSize: 40, color: '#0a0a0a', letterSpacing: '-0.035em', lineHeight: 1.05, margin: '0 0 28px' }}>
            A research system.<br />Public by design.
          </h1>
          <div style={{ display: 'flex', gap: 8, marginBottom: 28 }}>
            {PAIRS.map(p => <span key={p.label} style={{ display: 'inline-block', width: 24, height: 3, background: p.pairColor }} />)}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button onClick={() => navigate('/brief')} style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, fontWeight: 600, color: '#ffffff', background: '#0a0a0a', border: 'none', padding: '10px 16px', cursor: 'pointer', textAlign: 'left' }}>Today's brief →</button>
            <button onClick={() => navigate('/terminal')} style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, fontWeight: 500, color: '#0a0a0a', background: 'none', border: '1px solid #e5e5e5', padding: '10px 16px', cursor: 'pointer', textAlign: 'left' }}>Open terminal →</button>
            <button onClick={() => navigate('/performance')} style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, fontWeight: 500, color: '#0a0a0a', background: 'none', border: '1px solid #e5e5e5', padding: '10px 16px', cursor: 'pointer', textAlign: 'left' }}>Track record →</button>
          </div>
        </div>
        <div>
          <h2 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 18, color: '#0a0a0a', letterSpacing: '-0.02em', margin: '0 0 16px' }}>Shreyash Sakhare</h2>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 15, color: '#525252', lineHeight: 1.8, marginBottom: 20 }}>
            EE undergrad. Studying how G10 FX regimes form and break using rate differentials, COT positioning, and volatility. This is not a learning journal or a student project in disguise. It is a discretionary macro research system that happens to be public.
          </p>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 15, color: '#525252', lineHeight: 1.8, marginBottom: 28 }}>
            The site is the public trace of that work — dated calls, validated outcomes, no narrative added after the fact. Credibility compounds through calendar discipline and honest validation, not marketing.
          </p>

          {/* This is / This is not */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, background: '#e5e5e5' }}>
            {[
              { title: 'THIS IS', color: '#16a34a', sign: '+', items: ['Daily regime calls for G10 pairs', 'Public validation trail', 'Composite signal from 4 families', 'Morning brief before market open', 'Terminal for dense monitoring'] },
              { title: 'THIS IS NOT', color: '#dc2626', sign: '-', items: ['A SaaS or subscription product', 'Investment advice', 'An automated trading system', 'Generic macro commentary'] },
            ].map(col => (
              <div key={col.title} style={{ background: '#fff', padding: '20px' }}>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: col.color, letterSpacing: '0.1em', marginBottom: 12 }}>{col.title}</p>
                <ul style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#525252', lineHeight: 1.8, paddingLeft: 0, listStyle: 'none', margin: 0 }}>
                  {col.items.map(t => (
                    <li key={t} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 6 }}>
                      <span style={{ color: col.color, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, paddingTop: 2, flexShrink: 0 }}>{col.sign}</span>{t}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Section 2: Pipeline Walkthrough ── */}
      <div style={{ marginBottom: 72 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 28 }}>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 10 }}>METHODOLOGY</p>
            <h2 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 26, color: '#0a0a0a', letterSpacing: '-0.025em', margin: 0 }}>How the pipeline works</h2>
          </div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#bbb' }}>Click each stage to explore</p>
        </div>
        <PipelineWalkthrough />
      </div>

      {/* ── Section 3: Signal Families ── */}
      <div style={{ marginBottom: 72 }}>
        <div style={{ marginBottom: 28 }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 10 }}>SIGNAL ARCHITECTURE</p>
          <h2 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 26, color: '#0a0a0a', letterSpacing: '-0.025em', margin: 0 }}>Four signal families</h2>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#737373', marginTop: 8 }}>Click any family to expand the full methodology.</p>
        </div>
        <SignalFamilyCards />
      </div>

      {/* ── Section 4: Composite Simulator ── */}
      <div style={{ marginBottom: 72 }}>
        <div style={{ marginBottom: 28 }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 10 }}>INTERACTIVE</p>
          <h2 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 26, color: '#0a0a0a', letterSpacing: '-0.025em', margin: 0 }}>Composite score simulator</h2>
          <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#737373', marginTop: 8 }}>Drag the sliders to see how signal inputs combine into a regime call.</p>
        </div>
        <CompositeSimulator />
      </div>

      {/* ── Section 5: Validation Philosophy ── */}
      <div style={{ borderTop: '1px solid #e5e5e5', paddingTop: 64 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 64 }}>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#a0a0a0', letterSpacing: '0.12em', marginBottom: 14 }}>VALIDATION</p>
            <h2 style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 24, color: '#0a0a0a', letterSpacing: '-0.025em', lineHeight: 1.2, margin: '0 0 16px' }}>Why public validation matters</h2>
            <button onClick={() => navigate('/performance')}
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#555', border: '1px solid #e5e5e5', padding: '9px 16px', background: 'none', cursor: 'pointer', marginTop: 16 }}>
              Full track record →
            </button>
          </div>
          <div>
            <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 15, color: '#525252', lineHeight: 1.8, marginBottom: 20 }}>
              Any discretionary framework can be constructed to look correct in hindsight. The discipline of publishing a call before the outcome is known — and logging the result without revision — is the only meaningful test.
            </p>
            <p style={{ fontFamily: 'Inter, sans-serif', fontSize: 15, color: '#525252', lineHeight: 1.8, marginBottom: 28 }}>
              Each call is validated on next-day close-to-close spot movement. If the regime was MODERATE USD WEAKNESS and EUR/USD closed higher, it is correct. If it closed lower, it is incorrect. There is no partial credit, no adjustments for vol regimes, no "context" that modifies the record.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1, background: '#e5e5e5' }}>
              {[
                { label: '7D ACCURACY', value: '77.8%', color: '#16a34a' },
                { label: 'CALLS LOGGED', value: '27', color: '#0a0a0a' },
                { label: 'PAIRS COVERED', value: `${PAIRS.length}`, color: BRAND.eurusd },
              ].map(m => (
                <div key={m.label} style={{ background: '#fff', padding: '18px' }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#aaa', letterSpacing: '0.1em', marginBottom: 8 }}>{m.label}</p>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 26, fontWeight: 700, color: m.color, letterSpacing: '-0.03em' }}>{m.value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div style={{ marginTop: 40, paddingTop: 24, borderTop: '1px solid #f0f0f0' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#c0c0c0', letterSpacing: '0.06em', lineHeight: 1.8 }}>
            RESEARCH AND LEARNING ONLY. NOT INVESTMENT ADVICE. ALL REGIME CALLS ARE RESEARCH OUTPUTS, NOT TRADING RECOMMENDATIONS.
          </p>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, {
  PIPELINE_STEPS, SIGNAL_FAMILIES, scoreToRegime,
  PipelineWalkthrough, SignalFamilyCards, CompositeSimulator,
  AboutPage,
});
