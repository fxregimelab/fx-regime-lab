/**
 * Values persisted to `regime_calls.regime` by the Python pipeline.
 * Sources: `pipeline.py` (`_g10_label`, `VOL_EXPANDING` iv_gate override),
 * `inr_pipeline.py` (`_inr_score_label_fn`), `core/regime_persist.py` fallbacks.
 */
export type RegimeLabel =
  | 'UNKNOWN'
  | 'STRONG USD STRENGTH'
  | 'MODERATE USD STRENGTH'
  | 'NEUTRAL'
  | 'MODERATE USD WEAKNESS'
  | 'STRONG USD WEAKNESS'
  | 'VOL_EXPANDING'
  | 'STRONG DEPRECIATION PRESSURE'
  | 'MODERATE DEPRECIATION PRESSURE'
  | 'MODERATE APPRECIATION PRESSURE'
  | 'STRONG APPRECIATION PRESSURE'
  | 'DIRECTIONAL_ONLY';

export type PredictedDirection = 'LONG' | 'SHORT' | 'NEUTRAL';

/** Row shape for public.regime_calls (Supabase) */
export interface RegimeCall {
  id: number;
  date: string;
  pair: string;
  regime: RegimeLabel;
  confidence: number | null;
  signal_composite: number | null;
  rate_signal: string | null;
  cot_signal: string | null;
  vol_signal: string | null;
  rr_signal: string | null;
  oi_signal: string | null;
  primary_driver: string | null;
  created_at: string;
}
