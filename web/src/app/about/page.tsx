'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Nav } from '@/components/layout/nav';
import { Footer } from '@/components/layout/footer';
import { MacroPulseBar, PULSE_BAR_H } from '@/components/ui/macro-pulse-bar';
import { BRAND, PAIRS } from '@/lib/mockData';

const SHELL_NAV_H = 54;
const SHELL_TOP_OFFSET = PULSE_BAR_H + SHELL_NAV_H;

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
    desc: "The composite score is mapped to a regime label via threshold bands. The label is the pipeline's read of the current equilibrium — not a price forecast.",
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

function scoreToRegime(score: number) {
  if (score > 1.2) return { label: 'STRONG USD STRENGTH', color: '#f0f0f0' };
  if (score > 0.6) return { label: 'MODERATE USD STRENGTH', color: '#d4d4d4' };
  if (score > -0.4 && score < 0.4) return { label: 'NEUTRAL', color: '#888' };
  if (score < -1.2) return { label: 'STRONG USD WEAKNESS', color: BRAND.usdinr };
  if (score < -0.6) return { label: 'MODERATE USD WEAKNESS', color: BRAND.eurusd };
  return { label: 'MODERATE USD STRENGTH', color: '#d4d4d4' };
}

export default function About() {
  const router = useRouter();
  const [activeStep, setActiveStep] = React.useState(0);
  const [animating, setAnimating] = React.useState(false);
  const [expanded, setExpanded] = React.useState<string | null>(null);
  const [weights, setWeights] = React.useState({ rate: -0.45, cot: 34, vol: 6.2, oi: 0.2 });

  const goTo = (i: number) => {
    if (animating || i === activeStep) return;
    setAnimating(true);
    setTimeout(() => { setActiveStep(i); setAnimating(false); }, 180);
  };

  const step = PIPELINE_STEPS[activeStep];

  // Composite calc
  const rateContrib = Math.max(-1, Math.min(1, weights.rate / 5));
  const cotContrib = (weights.cot - 50) / 50;
  const volContrib = weights.vol > 9 ? -0.5 : weights.vol > 7 ? -0.2 : 0.1;
  const oiContrib = weights.oi;
  const composite = (rateContrib * 0.4 + cotContrib * 0.3 + volContrib * 0.2 + oiContrib * 0.1) * 2;
  const clampedComp = Math.max(-2, Math.min(2, composite));
  const regime = scoreToRegime(clampedComp);
  const confidence = Math.min(0.95, Math.max(0.30, 0.5 + Math.abs(clampedComp) * 0.2));
  const compPct = ((clampedComp + 2) / 4 * 100);

  return (
    <>
      <MacroPulseBar />
      <Nav />
      <main className="flex-1 bg-white" style={{ marginTop: `${SHELL_TOP_OFFSET}px` }}>
        <div className="w-full px-6 md:px-8 pt-14 pb-20">
          
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-16 lg:gap-20 mb-20 pb-16 border-b border-[#e5e5e5]">
            <div>
              <p className="font-mono text-[10px] text-[#a0a0a0] tracking-widest mb-5">ABOUT</p>
              <h1 className="font-sans font-extrabold text-[40px] leading-[1.05] text-[#0a0a0a] tracking-tight mb-7">
                A research system.
                <br />
                Public by design.
              </h1>
              <div className="flex gap-2 mb-7">
                {PAIRS.map(p => (
                  <span key={p.label} className="w-6 h-[3px]" style={{ backgroundColor: p.pairColor }} />
                ))}
              </div>
              <div className="flex flex-col gap-2">
                <button onClick={() => router.push('/brief')} className="bg-[#0a0a0a] text-white font-sans font-semibold text-[13px] px-5 py-2.5 transition-opacity hover:opacity-90 text-left">
                  Today&apos;s brief →
                </button>
                <button onClick={() => router.push('/terminal')} className="bg-transparent border border-[#e5e5e5] text-[#0a0a0a] font-sans font-medium text-[13px] px-5 py-2.5 hover:bg-[#fafafa] transition-colors text-left">
                  Open terminal →
                </button>
                <button onClick={() => router.push('/performance')} className="bg-transparent border border-[#e5e5e5] text-[#0a0a0a] font-sans font-medium text-[13px] px-5 py-2.5 hover:bg-[#fafafa] transition-colors text-left">
                  Track record →
                </button>
              </div>
            </div>
            <div>
              <h2 className="font-sans font-bold text-lg text-[#0a0a0a] tracking-tight mb-4">Shreyash Sakhare</h2>
              <p className="font-sans text-[15px] text-[#525252] leading-relaxed mb-5">
                EE undergrad. Studying how G10 FX regimes form and break using rate differentials, COT positioning, and volatility. This is not a learning journal or a student project in disguise. It is a discretionary macro research system that happens to be public.
              </p>
              <p className="font-sans text-[15px] text-[#525252] leading-relaxed mb-7">
                The site is the public trace of that work — dated calls, validated outcomes, no narrative added after the fact. Credibility compounds through calendar discipline and honest validation, not marketing.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-[1px] bg-[#e5e5e5]">
                <div className="bg-white p-5">
                  <p className="font-mono text-[10px] text-[#16a34a] tracking-widest mb-3">THIS IS</p>
                  <ul className="space-y-1.5">
                    {['Daily regime calls for G10 pairs', 'Public validation trail', 'Composite signal from 4 families', 'Morning brief before market open', 'Terminal for dense monitoring'].map(t => (
                      <li key={t} className="flex gap-2.5 items-start font-sans text-[13px] text-[#525252]">
                        <span className="text-[#16a34a] font-mono font-bold">+</span>{t}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="bg-white p-5">
                  <p className="font-mono text-[10px] text-[#dc2626] tracking-widest mb-3">THIS IS NOT</p>
                  <ul className="space-y-1.5">
                    {['A SaaS or subscription product', 'Investment advice', 'An automated trading system', 'Generic macro commentary'].map(t => (
                      <li key={t} className="flex gap-2.5 items-start font-sans text-[13px] text-[#525252]">
                        <span className="text-[#dc2626] font-mono font-bold">-</span>{t}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <section className="mb-20">
            <div className="flex items-baseline justify-between mb-7">
              <div>
                <p className="font-mono text-[10px] text-[#a0a0a0] tracking-widest mb-2.5">METHODOLOGY</p>
                <h2 className="font-sans font-bold text-[26px] text-[#0a0a0a] tracking-tight">How the pipeline works</h2>
              </div>
              <p className="font-mono text-[11px] text-[#bbb]">Click each stage to explore</p>
            </div>
            
            <div className="border border-[#e5e5e5]">
              <div className="flex bg-[#fafafa] border-b border-[#e5e5e5]">
                {PIPELINE_STEPS.map((s, i) => {
                  const active = i === activeStep;
                  const done = i < activeStep;
                  return (
                    <button key={s.id} onClick={() => goTo(i)} className={`flex-1 p-3.5 text-left border-r border-[#f0f0f0] transition-colors last:border-r-0 ${active ? 'bg-white' : ''}`}>
                      <span className={`block font-mono text-[10px] mb-1 ${active || done ? '' : 'text-[#ccc]'}`} style={{ color: active || done ? s.color : undefined }}>{s.n}</span>
                      <span className={`font-mono text-[10px] tracking-tight uppercase ${active ? 'font-bold text-[#0a0a0a]' : done ? 'text-[#888]' : 'text-[#bbb]'}`}>{s.title}</span>
                      <div className={`h-0.5 mt-2 transition-all duration-300 ${active ? 'w-full' : 'w-0'}`} style={{ backgroundColor: s.color }} />
                    </button>
                  );
                })}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 min-h-[320px]">
                <div className={`p-8 border-r border-[#f0f0f0] transition-all duration-200 ${animating ? 'opacity-0 translate-y-2' : 'opacity-100 translate-y-0'}`}>
                  <div className="flex items-center gap-2.5 mb-5">
                    <span className="font-mono text-[10px] font-bold" style={{ color: step.color }}>{step.n}</span>
                    <span className="font-mono text-[10px] text-[#bbb] tracking-widest uppercase">{step.label}</span>
                  </div>
                  <h3 className="font-sans font-bold text-[22px] text-[#0a0a0a] tracking-tight mb-3.5">{step.title}</h3>
                  <p className="font-sans text-sm text-[#525252] leading-relaxed mb-4">{step.desc}</p>
                  <p className="font-sans text-[13px] text-[#888] leading-relaxed">{step.detail}</p>
                  
                  <div className="flex gap-2.5 mt-7">
                    <button onClick={() => goTo(Math.max(0, activeStep - 1))} disabled={activeStep === 0}
                      className="font-mono text-[10px] px-4 py-2 border border-[#e5e5e5] transition-colors hover:bg-[#fafafa] disabled:text-[#ccc] disabled:hover:bg-transparent">
                      ← PREV
                    </button>
                    <button onClick={() => goTo(Math.min(4, activeStep + 1))} disabled={activeStep === 4}
                      className="font-mono text-[10px] px-4 py-2 bg-[#0a0a0a] text-white transition-opacity hover:opacity-90 disabled:bg-[#f0f0f0] disabled:text-[#bbb]">
                      {activeStep === 4 ? 'COMPLETE' : 'NEXT →'}
                    </button>
                  </div>
                </div>
                <div className={`p-8 bg-[#fafafa] flex flex-col justify-between transition-opacity duration-200 ${animating ? 'opacity-0' : 'opacity-100'}`}>
                  <div>
                    <p className="font-mono text-[9px] text-[#bbb] tracking-widest mb-2 uppercase">{step.metric.label}</p>
                    <p className="font-mono text-[52px] font-bold leading-none tracking-tighter" style={{ color: step.color }}>{step.metric.value}</p>
                  </div>
                  <div>
                    <p className="font-mono text-[9px] text-[#bbb] tracking-widest mb-3 uppercase">
                      {activeStep === 0 ? 'Data Sources' : activeStep === 1 ? 'Methodology' : activeStep === 2 ? 'Weights' : activeStep === 3 ? 'Thresholds' : 'Process'}
                    </p>
                    <div className="grid grid-cols-1 gap-2">
                      {step.sources.map((s, i) => (
                        <div key={i} className="flex items-center gap-2.5">
                          <span className="w-1 h-1 shrink-0" style={{ backgroundColor: step.color }} />
                          <span className="font-mono text-[11px] text-[#555]">{s}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="mt-6">
                    <p className="font-mono text-[9px] text-[#ccc] tracking-widest mb-2.5">PIPELINE STAGE</p>
                    <div className="flex items-center gap-1">
                      {PIPELINE_STEPS.map((s, i) => (
                        <React.Fragment key={s.id}>
                          <div className={`w-2 h-2 transition-colors duration-300 ${i <= activeStep ? '' : 'bg-[#e5e5e5]'}`} 
                            style={{ backgroundColor: i <= activeStep ? s.color : undefined, borderRadius: i === activeStep ? '50%' : '0' }} />
                          {i < 4 && <div className={`flex-1 h-[1px] ${i < activeStep ? 'bg-[#e5e5e5]' : 'bg-[#f0f0f0]'}`} />}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="mb-20">
            <div className="mb-7">
              <p className="font-mono text-[10px] text-[#a0a0a0] tracking-widest mb-2.5">SIGNAL ARCHITECTURE</p>
              <h2 className="font-sans font-bold text-[26px] text-[#0a0a0a] tracking-tight">Four signal families</h2>
              <p className="font-sans text-sm text-[#737373] mt-2">Click any family to expand the full methodology.</p>
            </div>
            
            <div className="border border-[#e5e5e5]">
              {SIGNAL_FAMILIES.map((fam, i) => {
                const isOpen = expanded === fam.id;
                return (
                  <div key={fam.id} className={`${i < SIGNAL_FAMILIES.length - 1 ? 'border-b border-[#e5e5e5]' : ''}`}>
                    <button onClick={() => setExpanded(isOpen ? null : fam.id)}
                      className={`w-full grid grid-cols-[40px_1fr_auto] gap-5 items-center p-5 lg:px-6 transition-colors text-left ${isOpen ? 'bg-[#fafafa]' : 'bg-white hover:bg-[#fafafa]'}`}>
                      <span className="font-mono text-[13px] font-bold" style={{ color: fam.color }}>{fam.n}</span>
                      <div>
                        <p className="font-sans font-semibold text-[15px] text-[#0a0a0a] mb-0.5">{fam.label}</p>
                        <p className="font-sans text-[13px] text-[#888]">{fam.summary}</p>
                      </div>
                      <span className={`font-mono text-sm text-[#bbb] transition-transform duration-200 ${isOpen ? 'rotate-45' : ''}`}>+</span>
                    </button>
                    <div className={`overflow-hidden transition-all duration-300 ease-in-out ${isOpen ? 'max-height-[500px] border-t border-[#f0f0f0]' : 'max-height-0'}`}>
                      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-8 p-6 pl-[60px] lg:pl-[84px]">
                        <div>
                          <div className="w-8 h-0.5 mb-4" style={{ backgroundColor: fam.color }} />
                          <p className="font-sans text-sm text-[#444] leading-relaxed">{fam.body}</p>
                        </div>
                        <div className="min-w-[160px]">
                          <div className="border border-[#e5e5e5]" style={{ borderTop: `2px solid ${fam.color}` }}>
                            {fam.stats.map(([label, val], j) => (
                              <div key={j} className={`flex justify-between gap-4 p-2.5 px-3.5 ${j < fam.stats.length - 1 ? 'border-b border-[#f5f5f5]' : ''}`}>
                                <span className="font-mono text-[9px] text-[#aaa] tracking-widest uppercase">{label}</span>
                                <span className="font-mono text-[10px] text-[#111] font-bold text-right uppercase">{val}</span>
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
          </section>

          <section className="mb-20">
            <div className="mb-7">
              <p className="font-mono text-[10px] text-[#a0a0a0] tracking-widest mb-2.5 uppercase">Interactive</p>
              <h2 className="font-sans font-bold text-[26px] text-[#0a0a0a] tracking-tight">Composite score simulator</h2>
              <p className="font-sans text-sm text-[#737373] mt-2">Drag the sliders to see how signal inputs combine into a regime call.</p>
            </div>
            
            <div className="border border-[#e5e5e5]">
              <div className="p-4 px-6 bg-[#fafafa] border-b border-[#e5e5e5] flex items-center justify-between">
                <div>
                  <p className="font-mono text-[10px] text-[#888] tracking-widest mb-0.5 uppercase">COMPOSITE SIMULATOR</p>
                  <p className="font-sans text-[13px] text-[#555]">Adjust signal inputs — watch regime and confidence update live.</p>
                </div>
                <button onClick={() => setWeights({ rate: -0.45, cot: 34, vol: 6.2, oi: 0.2 })}
                  className="font-mono text-[10px] text-[#888] border border-[#e5e5e5] px-3 py-1.5 transition-colors hover:bg-white">RESET</button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2">
                <div className="p-6 border-r border-[#f0f0f0]">
                  {[
                    { id: 'rate', label: 'RATE DIFF 2Y', min: -5, max: 5, step: 0.05, unit: '', val: weights.rate },
                    { id: 'cot', label: 'COT PERCENTILE', min: 0, max: 100, step: 1, unit: '', val: weights.cot },
                    { id: 'vol', label: 'REALIZED VOL 20D', min: 1, max: 15, step: 0.1, unit: '', val: weights.vol },
                    { id: 'oi', label: 'OI/RR SIGNAL', min: -1, max: 1, step: 0.1, unit: '', val: weights.oi },
                  ].map(s => (
                    <div key={s.id} className="mb-5 last:mb-0">
                      <div className="flex justify-between mb-2">
                        <span className="font-mono text-[10px] text-[#888] tracking-widest">{s.label}</span>
                        <span className="font-mono text-[11px] text-[#0a0a0a] font-bold">{s.val.toFixed(s.step < 1 ? 2 : 0)}{s.unit}</span>
                      </div>
                      <input type="range" min={s.min} max={s.max} step={s.step} value={s.val}
                        onChange={e => setWeights(w => ({ ...w, [s.id]: parseFloat(e.target.value) }))}
                        className="w-full h-0.5 bg-[#e5e5e5] appearance-none cursor-pointer accent-[#0a0a0a]" />
                      <div className="flex justify-between mt-1.5">
                        <span className="font-mono text-[9px] text-[#ccc]">{s.min}{s.unit}</span>
                        <span className="font-mono text-[9px] text-[#ccc]">{s.max}{s.unit}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="p-6 bg-[#fafafa]">
                  <p className="font-mono text-[9px] text-[#aaa] tracking-widest mb-5 uppercase">LIVE OUTPUT</p>
                  
                  <div className="mb-6">
                    <p className="font-mono text-[9px] text-[#bbb] tracking-widest mb-2.5 uppercase">COMPOSITE SCORE</p>
                    <p className={`font-mono text-[42px] font-bold leading-none tracking-tighter transition-colors duration-300`} 
                      style={{ color: clampedComp >= 0 ? '#16a34a' : BRAND.usdinr }}>
                      {clampedComp >= 0 ? '+' : ''}{clampedComp.toFixed(2)}
                    </p>
                    <div className="relative mt-2.5 bg-[#e5e5e5] h-1">
                      <div className="absolute left-1/2 -top-0.5 w-[1px] h-2 bg-[#bbb]" />
                      <div className="absolute h-full transition-all duration-200"
                        style={{ 
                          left: compPct > 50 ? '50%' : `${compPct}%`, 
                          width: `${Math.abs(compPct - 50)}%`, 
                          backgroundColor: clampedComp >= 0 ? '#16a34a' : BRAND.usdinr 
                        }} />
                    </div>
                    <div className="flex justify-between mt-1">
                      <span className="font-mono text-[8px] text-[#bbb]">BEAR -2.0</span>
                      <span className="font-mono text-[8px] text-[#bbb]">BULL +2.0</span>
                    </div>
                  </div>

                  <div className="mb-5">
                    <p className="font-mono text-[9px] text-[#bbb] tracking-widest mb-2 uppercase">REGIME LABEL</p>
                    <p className="font-mono text-[12px] font-bold uppercase tracking-widest transition-colors duration-300" style={{ color: regime.color }}>{regime.label}</p>
                  </div>

                  <div className="mb-5">
                    <p className="font-mono text-[9px] text-[#bbb] tracking-widest mb-2 uppercase">CONFIDENCE</p>
                    <p className="font-mono text-[28px] font-bold leading-none tracking-tight">
                      {Math.round(confidence * 100)}<span className="text-sm font-normal text-[#bbb] ml-0.5">%</span>
                    </p>
                    <div className="bg-[#e5e5e5] h-1 mt-2.5">
                      <div className="h-full bg-[#0a0a0a] transition-all duration-300" style={{ width: `${Math.round(confidence * 100)}%` }} />
                    </div>
                  </div>

                  <div className="mt-5 pt-4 border-t border-[#ebebeb]">
                    <p className="font-mono text-[9px] text-[#bbb] tracking-widest mb-2.5 uppercase">SIGNAL CONTRIBUTIONS</p>
                    {[
                      { lbl: 'RATE DIFF', val: rateContrib * 0.4 * 2, color: BRAND.eurusd },
                      { lbl: 'COT', val: cotContrib * 0.3 * 2, color: BRAND.usdjpy },
                      { lbl: 'VOL', val: volContrib * 0.2 * 2, color: BRAND.usdinr },
                      { lbl: 'OI/RR', val: oiContrib * 0.1 * 2, color: '#888' },
                    ].map(c => (
                      <div key={c.lbl} className="flex items-center gap-2.5 mb-2 last:mb-0">
                        <span className="font-mono text-[9px] text-[#aaa] min-w-[48px] uppercase">{c.lbl}</span>
                        <div className="flex-1 bg-[#ebebeb] h-[1px] relative">
                          <div className="absolute left-1/2 -top-[1.5px] w-[1px] h-1 bg-[#ccc]" />
                          <div className="absolute h-[2px] -top-[0.5px] transition-all duration-200"
                            style={{ 
                              left: c.val > 0 ? '50%' : `${50 + c.val / 2 * 100}%`, 
                              width: `${Math.abs(c.val) / 2 * 100}%`, 
                              backgroundColor: c.color 
                            }} />
                        </div>
                        <span className={`font-mono text-[10px] font-bold min-w-[36px] text-right transition-colors duration-200`} 
                          style={{ color: c.val >= 0 ? '#16a34a' : BRAND.usdinr }}>
                          {c.val >= 0 ? '+' : ''}{c.val.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="pt-16 border-t border-[#e5e5e5]">
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-12 lg:gap-16">
              <div>
                <p className="font-mono text-[10px] text-[#a0a0a0] tracking-widest mb-3.5 uppercase">Validation</p>
                <h2 className="font-sans font-bold text-2xl text-[#0a0a0a] tracking-tight leading-tight mb-4">Why public validation matters</h2>
                <button onClick={() => router.push('/performance')}
                  className="font-mono text-[11px] text-[#555] border border-[#e5e5e5] px-4 py-2 hover:bg-[#fafafa] transition-colors mt-2">
                  FULL TRACK RECORD →
                </button>
              </div>
              <div>
                <p className="font-sans text-[15px] text-[#525252] leading-relaxed mb-5">
                  Any discretionary framework can be constructed to look correct in hindsight. The discipline of publishing a call before the outcome is known — and logging the result without revision — is the only meaningful test.
                </p>
                <p className="font-sans text-[15px] text-[#525252] leading-relaxed mb-7">
                  Each call is validated on next-day close-to-close spot movement. If the regime was MODERATE USD WEAKNESS and EUR/USD closed higher, it is correct. If it closed lower, it is incorrect. There is no partial credit, no adjustments for vol regimes, no &quot;context&quot; that modifies the record.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-[1px] bg-[#e5e5e5]">
                  {[
                    { label: 'CALENDAR ACCURACY', value: '78.2%', color: '#16a34a' },
                    { label: 'CALLS LOGGED', value: '250+', color: '#0a0a0a' },
                    { label: 'PAIRS COVERED', value: '7', color: BRAND.eurusd },
                  ].map(m => (
                    <div key={m.label} className="bg-white p-5">
                      <p className="font-mono text-[9px] text-[#aaa] tracking-widest mb-2 uppercase">{m.label}</p>
                      <p className="font-mono text-[26px] font-bold tracking-tighter" style={{ color: m.color }}>{m.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-10 pt-6 border-t border-[#f0f0f0]">
              <p className="font-mono text-[10px] text-[#c0c0c0] tracking-widest leading-relaxed uppercase">
                Research and learning only. Not investment advice. All regime calls are research outputs, not trading recommendations.
              </p>
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
}
