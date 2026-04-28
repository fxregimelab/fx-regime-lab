export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      signals: {
        Row: {
          id: number
          date: string
          pair: string
          spot: number | null
          rate_diff_2y: number | null
          rate_diff_10y: number | null
          rate_diff_zscore: number | null
          cot_lev_money_net: number | null
          cot_asset_mgr_net: number | null
          cot_percentile: number | null
          realized_vol_5d: number | null
          realized_vol_20d: number | null
          implied_vol_30d: number | null
          vol_skew: number | null
          atm_vol: number | null
          risk_reversal_25d: number | null
          oi_delta: number | null
          oi_price_alignment: string | null
          cross_asset_vix: number | null
          cross_asset_dxy: number | null
          cross_asset_oil: number | null
          cross_asset_us10y: number | null
          created_at: string
          day_change: number | null
          day_change_pct: number | null
        }
        Insert: {
          id?: number
          date: string
          pair: string
          spot?: number | null
          rate_diff_2y?: number | null
          rate_diff_10y?: number | null
          rate_diff_zscore?: number | null
          cot_lev_money_net?: number | null
          cot_asset_mgr_net?: number | null
          cot_percentile?: number | null
          realized_vol_5d?: number | null
          realized_vol_20d?: number | null
          implied_vol_30d?: number | null
          vol_skew?: number | null
          atm_vol?: number | null
          risk_reversal_25d?: number | null
          oi_delta?: number | null
          oi_price_alignment?: string | null
          cross_asset_vix?: number | null
          cross_asset_dxy?: number | null
          cross_asset_oil?: number | null
          cross_asset_us10y?: number | null
          created_at?: string
          day_change?: number | null
          day_change_pct?: number | null
        }
        Update: Partial<Database['public']['Tables']['signals']['Insert']>
      }
      regime_calls: {
        Row: {
          id: number
          date: string
          pair: string
          regime: string
          confidence: number
          signal_composite: number
          rate_signal: string | null
          cot_signal: string | null
          vol_signal: string | null
          rr_signal: string | null
          oi_signal: string | null
          primary_driver: string | null
          created_at: string
        }
        Insert: {
          id?: number
          date: string
          pair: string
          regime: string
          confidence: number
          signal_composite: number
          rate_signal?: string | null
          cot_signal?: string | null
          vol_signal?: string | null
          rr_signal?: string | null
          oi_signal?: string | null
          primary_driver?: string | null
          created_at?: string
        }
        Update: Partial<Database['public']['Tables']['regime_calls']['Insert']>
      }
      validation_log: {
        Row: {
          id: number
          date: string
          pair: string
          predicted_direction: string | null
          predicted_regime: string | null
          confidence: number | null
          actual_direction: string | null
          actual_return_1d: number | null
          actual_return_5d: number | null
          correct_1d: boolean | null
          correct_5d: boolean | null
          notes: string | null
          created_at: string
        }
        Insert: {
          id?: number
          date: string
          pair: string
          predicted_direction?: string | null
          predicted_regime?: string | null
          confidence?: number | null
          actual_direction?: string | null
          actual_return_1d?: number | null
          actual_return_5d?: number | null
          correct_1d?: boolean | null
          correct_5d?: boolean | null
          notes?: string | null
          created_at?: string
        }
        Update: Partial<Database['public']['Tables']['validation_log']['Insert']>
      }
      brief_log: {
        Row: {
          id: number
          date: string
          brief_text: string | null
          eurusd_regime: string | null
          usdjpy_regime: string | null
          usdinr_regime: string | null
          macro_context: string | null
          created_at: string
        }
        Insert: {
          id?: number
          date: string
          brief_text?: string | null
          eurusd_regime?: string | null
          usdjpy_regime?: string | null
          usdinr_regime?: string | null
          macro_context?: string | null
          created_at?: string
        }
        Update: Partial<Database['public']['Tables']['brief_log']['Insert']>
      }
      macro_events: {
        Row: {
          id: number
          date: string
          event: string
          impact: string
          pairs: string[]
          category: string | null
          ai_brief: string | null
          created_at: string
        }
        Insert: {
          id?: number
          date: string
          event: string
          impact: string
          pairs: string[]
          category?: string | null
          ai_brief?: string | null
          created_at?: string
        }
        Update: Partial<Database['public']['Tables']['macro_events']['Insert']>
      }
      brief: {
        Row: {
          id: number
          date: string
          pair: string
          regime: string
          confidence: number
          composite: number
          analysis: string | null
          primary_driver: string | null
          created_at: string
        }
        Insert: {
          id?: number
          date: string
          pair: string
          regime: string
          confidence: number
          composite: number
          analysis?: string | null
          primary_driver?: string | null
          created_at?: string
        }
        Update: Partial<Database['public']['Tables']['brief']['Insert']>
      }
    }
  }
}
