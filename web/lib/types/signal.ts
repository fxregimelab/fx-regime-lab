/**
 * Row shape for public.signals (Supabase).
 * UI name `SignalValue` — same table the pipeline writes today.
 */
export interface SignalValue {
  id: number;
  date: string;
  pair: string;
  spot: number | null;
  rate_diff_2y: number | null;
  rate_diff_10y: number | null;
  rate_diff_zscore: number | null;
  cot_lev_money_net: number | null;
  cot_asset_mgr_net: number | null;
  cot_percentile: number | null;
  realized_vol_5d: number | null;
  realized_vol_20d: number | null;
  implied_vol_30d: number | null;
  vol_skew: number | null;
  atm_vol: number | null;
  risk_reversal_25d: number | null;
  oi_delta: number | null;
  oi_price_alignment: string | null;
  cross_asset_vix: number | null;
  cross_asset_dxy: number | null;
  cross_asset_oil: number | null;
  created_at: string;
}

/** Metadata for presenting a column from signals in the UI */
export interface SignalDefinition {
  id: string;
  key: keyof Omit<SignalValue, 'id' | 'date' | 'pair' | 'created_at'>;
  label: string;
  unit?: string;
  description?: string;
}
