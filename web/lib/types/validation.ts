/** Row shape for public.validation_log (Supabase) */
export interface ValidationRow {
  id: number;
  date: string;
  pair: string;
  predicted_direction: string | null;
  predicted_regime: string | null;
  confidence: number | null;
  actual_direction: string | null;
  actual_return_1d: number | null;
  actual_return_5d: number | null;
  correct_1d: boolean | null;
  correct_5d: boolean | null;
  notes: string | null;
  created_at: string;
}

/** Derived rolling accuracy — computed client- or server-side from validation_log */
export interface AccuracyMetrics {
  windowDays: number;
  pair?: string;
  count_1d: number;
  correct_1d: number;
  rate_1d: number | null;
  count_5d: number;
  correct_5d: number;
  rate_5d: number | null;
}
