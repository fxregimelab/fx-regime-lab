export interface PairMeta {
  label: 'EURUSD' | 'USDJPY' | 'USDINR';
  display: string;
  urlSlug: string;
  pairColor: string;
}

export interface RegimeCall {
  pair: string;
  date: string;
  regime: string;
  confidence: number;
  signal_composite: number;
  rate_signal: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  primary_driver: string;
  created_at: string;
}

export interface SignalRow {
  pair: string;
  date: string;
  rate_diff_2y: number;
  cot_percentile: number;
  realized_vol_20d: number;
  realized_vol_5d: number;
  implied_vol_30d: number | null;
  spot: number;
  day_change: number;
  day_change_pct: number;
  created_at: string;
}

export interface ValidationRow {
  date: string;
  pair: string;
  call: string;
  outcome: 'correct' | 'incorrect';
  return_pct: number;
}

export interface MacroEvent {
  date: string;
  event: string;
  impact: 'HIGH' | 'MEDIUM' | 'LOW';
  pairs: string[];
  category: 'US' | 'EU' | 'JP' | 'IN' | 'UK';
  ai_brief?: string | null;
}

export interface HistoryRow {
  date: string;
  regime: string;
  confidence: number;
}

export interface HeatmapData {
  dates: string[];
  regimes: Record<string, string[]>;
}

export interface BriefSection {
  regime: string;
  confidence: number;
  composite: number;
  analysis: string;
  primaryDriver: string;
}
