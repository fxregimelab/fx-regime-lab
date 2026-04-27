/** Site constants only — no mock market data. Live data comes from `queries.ts` + Supabase. */

export const BRAND = {
  eurusd: '#4BA3E3',
  usdjpy: '#F5923A',
  usdinr: '#C84A31',
  accent: '#F5923A',
};

export const PAIRS = [
  { label: 'EURUSD', display: 'EUR/USD', urlSlug: 'eurusd', pairColor: BRAND.eurusd },
  { label: 'USDJPY', display: 'USD/JPY', urlSlug: 'usdjpy', pairColor: BRAND.usdjpy },
  { label: 'USDINR', display: 'USD/INR', urlSlug: 'usdinr', pairColor: BRAND.usdinr },
];

export const REGIME_HEATMAP_COLORS: Record<string, string> = {
  'STRONG USD STRENGTH': '#1e3a5f',
  'MODERATE USD STRENGTH': '#2d5a8e',
  NEUTRAL: '#3a3a3a',
  'MODERATE USD WEAKNESS': '#7a3f1f',
  'STRONG USD WEAKNESS': '#a0522d',
  VOL_EXPANDING: '#7a5c00',
  'STRONG DEPRECIATION PRESSURE': '#6b1a1a',
  'MODERATE DEPRECIATION PRESSURE': '#8b2a2a',
  'MODERATE APPRECIATION PRESSURE': '#1a5a2a',
  'STRONG APPRECIATION PRESSURE': '#0d3a1a',
  DIRECTIONAL_ONLY: '#333',
  UNKNOWN: '#1a1a1a',
};
