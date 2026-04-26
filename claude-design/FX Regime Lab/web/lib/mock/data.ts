import type { PairMeta, RegimeCall, SignalRow, ValidationRow, MacroEvent, HistoryRow, HeatmapData, BriefSection } from '../types';

export const TODAY = '2026-04-26';

export const BRAND = {
  eurusd: '#4BA3E3',
  usdjpy: '#F5923A',
  usdinr: '#D94030',
  accent: '#F5923A',
} as const;

export const PAIRS: PairMeta[] = [
  { label: 'EURUSD', display: 'EUR/USD', urlSlug: 'eurusd', pairColor: BRAND.eurusd },
  { label: 'USDJPY', display: 'USD/JPY', urlSlug: 'usdjpy', pairColor: BRAND.usdjpy },
  { label: 'USDINR', display: 'USD/INR', urlSlug: 'usdinr', pairColor: BRAND.usdinr },
];

export const MOCK_REGIME_CALLS: Record<string, RegimeCall> = {
  EURUSD: { pair: 'EURUSD', date: TODAY, regime: 'MODERATE USD WEAKNESS', confidence: 0.72, signal_composite: -0.81, rate_signal: 'BEARISH', primary_driver: 'Rate differential compressing; COT short-cover underway', created_at: `${TODAY}T07:12:34Z` },
  USDJPY: { pair: 'USDJPY', date: TODAY, regime: 'STRONG USD STRENGTH', confidence: 0.84, signal_composite: 1.43, rate_signal: 'BULLISH', primary_driver: 'BoJ YCC intact; rate spread at cycle high', created_at: `${TODAY}T07:12:34Z` },
  USDINR: { pair: 'USDINR', date: TODAY, regime: 'MODERATE DEPRECIATION PRESSURE', confidence: 0.63, signal_composite: 0.61, rate_signal: 'BULLISH', primary_driver: 'RBI intervention cap; DXY correlation elevated', created_at: `${TODAY}T07:12:34Z` },
};

export const MOCK_SIGNALS: Record<string, SignalRow> = {
  EURUSD: { pair: 'EURUSD', date: TODAY, rate_diff_2y: -0.45, cot_percentile: 34, realized_vol_20d: 6.21, realized_vol_5d: 5.88, implied_vol_30d: 7.14, spot: 1.0731, day_change: -0.0021, day_change_pct: -0.20, created_at: `${TODAY}T07:12:34Z` },
  USDJPY: { pair: 'USDJPY', date: TODAY, rate_diff_2y: 3.82, cot_percentile: 78, realized_vol_20d: 8.13, realized_vol_5d: 7.94, implied_vol_30d: 9.32, spot: 154.62, day_change: 0.84, day_change_pct: 0.55, created_at: `${TODAY}T07:12:34Z` },
  USDINR: { pair: 'USDINR', date: TODAY, rate_diff_2y: 4.10, cot_percentile: 52, realized_vol_20d: 3.07, realized_vol_5d: 3.21, implied_vol_30d: null, spot: 83.94, day_change: 0.06, day_change_pct: 0.07, created_at: `${TODAY}T07:12:34Z` },
};

export const MOCK_HISTORY: Record<string, HistoryRow[]> = {
  EURUSD: [
    { date: '2026-04-26', regime: 'MODERATE USD WEAKNESS', confidence: 0.72 },
    { date: '2026-04-25', regime: 'MODERATE USD WEAKNESS', confidence: 0.68 },
    { date: '2026-04-24', regime: 'NEUTRAL', confidence: 0.51 },
    { date: '2026-04-23', regime: 'NEUTRAL', confidence: 0.48 },
    { date: '2026-04-22', regime: 'MODERATE USD STRENGTH', confidence: 0.59 },
    { date: '2026-04-17', regime: 'MODERATE USD STRENGTH', confidence: 0.61 },
    { date: '2026-04-16', regime: 'STRONG USD STRENGTH', confidence: 0.77 },
  ],
  USDJPY: [
    { date: '2026-04-26', regime: 'STRONG USD STRENGTH', confidence: 0.84 },
    { date: '2026-04-25', regime: 'STRONG USD STRENGTH', confidence: 0.82 },
    { date: '2026-04-24', regime: 'STRONG USD STRENGTH', confidence: 0.79 },
    { date: '2026-04-23', regime: 'STRONG USD STRENGTH', confidence: 0.75 },
    { date: '2026-04-22', regime: 'MODERATE USD STRENGTH', confidence: 0.66 },
    { date: '2026-04-17', regime: 'MODERATE USD STRENGTH', confidence: 0.63 },
    { date: '2026-04-16', regime: 'VOL_EXPANDING', confidence: 0.55 },
  ],
  USDINR: [
    { date: '2026-04-26', regime: 'MODERATE DEPRECIATION PRESSURE', confidence: 0.63 },
    { date: '2026-04-25', regime: 'MODERATE DEPRECIATION PRESSURE', confidence: 0.60 },
    { date: '2026-04-24', regime: 'MODERATE DEPRECIATION PRESSURE', confidence: 0.58 },
    { date: '2026-04-23', regime: 'NEUTRAL', confidence: 0.46 },
    { date: '2026-04-22', regime: 'NEUTRAL', confidence: 0.49 },
    { date: '2026-04-17', regime: 'MODERATE APPRECIATION PRESSURE', confidence: 0.55 },
    { date: '2026-04-16', regime: 'MODERATE APPRECIATION PRESSURE', confidence: 0.57 },
  ],
};

export const MOCK_VALIDATION: ValidationRow[] = [
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

export const MOCK_CALENDAR: MacroEvent[] = [
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

export const REGIME_HEATMAP_COLORS: Record<string, string> = {
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

export const MOCK_HEATMAP: HeatmapData = (() => {
  const regimes: Record<string, string[]> = {
    EURUSD: ['STRONG USD STRENGTH','STRONG USD STRENGTH','MODERATE USD STRENGTH','MODERATE USD STRENGTH','NEUTRAL','NEUTRAL','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','NEUTRAL','NEUTRAL','MODERATE USD STRENGTH','MODERATE USD STRENGTH','NEUTRAL','NEUTRAL','NEUTRAL','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','NEUTRAL','NEUTRAL','NEUTRAL','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS','NEUTRAL','MODERATE USD WEAKNESS','MODERATE USD WEAKNESS'],
    USDJPY: ['STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','VOL_EXPANDING','MODERATE USD STRENGTH','MODERATE USD STRENGTH','MODERATE USD STRENGTH','MODERATE USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','MODERATE USD STRENGTH','MODERATE USD STRENGTH','MODERATE USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH','STRONG USD STRENGTH'],
    USDINR: ['MODERATE APPRECIATION PRESSURE','MODERATE APPRECIATION PRESSURE','MODERATE APPRECIATION PRESSURE','MODERATE APPRECIATION PRESSURE','NEUTRAL','NEUTRAL','NEUTRAL','NEUTRAL','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','NEUTRAL','NEUTRAL','NEUTRAL','NEUTRAL','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','NEUTRAL','NEUTRAL','NEUTRAL','NEUTRAL','NEUTRAL','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE','NEUTRAL','MODERATE DEPRECIATION PRESSURE','MODERATE DEPRECIATION PRESSURE'],
  };
  const dates = Array.from({ length: 30 }, (_, i) => {
    const d = new Date('2026-04-26');
    d.setDate(d.getDate() - (29 - i));
    return d.toISOString().slice(0, 10);
  });
  return { dates, regimes };
})();

export const MOCK_EQUITY = {
  dates: ['Apr 7','Apr 8','Apr 9','Apr 10','Apr 11','Apr 14','Apr 15','Apr 16','Apr 17','Apr 22','Apr 23','Apr 24','Apr 25','Apr 26'],
  EURUSD: [0, 0.18, 0.04, -0.14, 0.04, 0.22, 0.48, 0.30, -0.18, -0.14, 0.04, 0.35, 0.66, 0.97],
  USDJPY: [0, 0.31, 0.55, 0.48, 0.62, 0.87, 0.61, 0.55, 0.72, 1.11, 1.50, 2.02, 2.54, 3.02],
  USDINR: [0, 0.04, 0.04, 0.04, 0.04, 0.12, 0.12, 0.02, 0.02, 0.14, 0.16, 0.28, 0.21, 0.21],
  ALL: [] as number[],
};
MOCK_EQUITY.ALL = MOCK_EQUITY.dates.map((_, i) =>
  (MOCK_EQUITY.EURUSD[i] + MOCK_EQUITY.USDJPY[i] + MOCK_EQUITY.USDINR[i]) / 3
);

export const BRIEF_SECTIONS: Record<string, BriefSection> = {
  EURUSD: { regime: 'MODERATE USD WEAKNESS', confidence: 0.72, composite: -0.81, analysis: `Rate differential continued to compress (-0.45 spread vs -0.38 last week). CFTC positioning shows net EUR longs at 34th percentile - room to extend. Realized vol 6.2 annualized, below the 30d implied of 7.1 suggesting vol-sellers favor the range.\n\nCall: Bias EUR/USD higher into 1.0820 resistance. Stop on daily close below 1.0690.`, primaryDriver: 'Rate differential compressing; COT short-cover underway' },
  USDJPY: { regime: 'STRONG USD STRENGTH', confidence: 0.84, composite: 1.43, analysis: `BoJ maintained YCC at 1.0% cap. 2Y rate spread widened to 3.82, cycle high. COT at 78th percentile - positioning extended but momentum intact. Vol at 8.1 realized vs 9.3 implied - tail risk premium building.\n\nCall: USD/JPY constructive above 153.80. Target 155.50. Risk: BoJ jawboning or surprise pivot.`, primaryDriver: 'BoJ YCC intact; rate spread at cycle high' },
  USDINR: { regime: 'MODERATE DEPRECIATION PRESSURE', confidence: 0.63, composite: 0.61, analysis: `RBI cap limiting moves. 4.1 rate differential supports dollar demand vs rupee. COT at 52nd percentile - neutral positioning. Realized vol contained at 3.1 - regime likely range-bound near term.\n\nCall: USD/INR mild upside bias. Range 83.75-84.20 likely to contain near-term move.`, primaryDriver: 'RBI intervention cap; DXY correlation elevated' },
};

export const MOCK_AI_BRIEF = `OVERVIEW
This is a placeholder AI brief. Real AI integration comes in Phase 5.

EXPECTATIONS
Consensus expects placeholder data. Prior: N/A.

WHY IT MATTERS
This event affects FX pairs through monetary policy transmission channels.

SCENARIOS
BEAT (35%): USD strengthens, pairs move in dollar bullish direction.
IN LINE (45%): Muted reaction, current regime confirmed.
MISS (20%): USD weakens, regime shift risk increases.

REGIME IMPLICATIONS
Outcome will be assessed against current regime calls on the following trading day.`;

export const MOCK_AI_ANALYSIS = `OUTLOOK
Current signals point to continued regime persistence with moderate conviction. Rate differential and positioning are aligned; volatility remains contained.

KEY RISKS
• Central bank communication shift — unexpected hawkish/dovish pivot
• COT positioning extreme could trigger short squeeze or profit-taking
• Macro surprise in NFP or CPI data could override composite signal

SCENARIOS
BULL (40%): Regime strengthens, composite extends, confidence above 80%
BASE (45%): Regime holds, composite stable, tactical range-trade
BEAR (15%): Regime breaks, composite crosses neutral band, confidence drops

WATCH LEVELS
• Composite crossing ±0.4 signals neutral zone — regime call degrades
• Confidence below 55% triggers reassessment of primary driver`;
