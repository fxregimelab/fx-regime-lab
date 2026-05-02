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
          cross_asset_gold: number | null
          cross_asset_copper: number | null
          cross_asset_stoxx: number | null
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
          cross_asset_gold?: number | null
          cross_asset_copper?: number | null
          cross_asset_stoxx?: number | null
          created_at?: string
          day_change?: number | null
          day_change_pct?: number | null
        }
        Update: Partial<Database['public']['Tables']['signals']['Insert']>
      }
      strategy_ledger: {
        Row: {
          id: string
          date: string
          pair: string
          regime: string
          primary_driver: string
          direction: string
          entry_close: number | null
          confidence: number | null
          t1_close: number | null
          t3_close: number | null
          t5_close: number | null
          t1_hit: number | null
          t3_hit: number | null
          t5_hit: number | null
          brier_score_t5: number | null
        }
        Insert: {
          id?: string
          date: string
          pair: string
          regime: string
          primary_driver: string
          direction: string
          entry_close?: number | null
          confidence?: number | null
          t1_close?: number | null
          t3_close?: number | null
          t5_close?: number | null
          t1_hit?: number | null
          t3_hit?: number | null
          t5_hit?: number | null
          brier_score_t5?: number | null
        }
        Update: Partial<Database['public']['Tables']['strategy_ledger']['Insert']>
      }
      universe: {
        Row: {
          id: string
          pair: string
          class: string
          spot_ticker: string | null
          yield_base: string | null
          yield_quote: string | null
          cot_ticker: string | null
        }
        Insert: {
          id?: string
          pair: string
          class: string
          spot_ticker?: string | null
          yield_base?: string | null
          yield_quote?: string | null
          cot_ticker?: string | null
        }
        Update: Partial<Database['public']['Tables']['universe']['Insert']>
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
          dollar_dominance: number | null
          idiosyncratic_outlier: string | null
          sentiment_json: Json | null
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
          dollar_dominance?: number | null
          idiosyncratic_outlier?: string | null
          sentiment_json?: Json | null
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
      historical_prices: {
        Row: {
          id: number
          date: string
          pair: string
          open: number | null
          high: number | null
          low: number | null
          close: number | null
          volume: number | null
          created_at: string
        }
        Insert: {
          id?: number
          date: string
          pair: string
          open?: number | null
          high?: number | null
          low?: number | null
          close?: number | null
          volume?: number | null
          created_at?: string
        }
        Update: Partial<Database['public']['Tables']['historical_prices']['Insert']>
      }
      research_analogs: {
        Row: {
          id: number
          as_of_date: string
          pair: string
          rank: number
          match_date: string
          match_score: number
          forward_30d_return: number | null
          regime_stability: number | null
          context_label: string | null
          current_trend_5d: number | null
          matched_trend_5d: number | null
          current_composite: number | null
          created_at: string
        }
        Insert: {
          id?: number
          as_of_date: string
          pair: string
          rank: number
          match_date: string
          match_score: number
          forward_30d_return?: number | null
          regime_stability?: number | null
          context_label?: string | null
          current_trend_5d?: number | null
          matched_trend_5d?: number | null
          current_composite?: number | null
          created_at?: string
        }
        Update: Partial<Database['public']['Tables']['research_analogs']['Insert']>
      }
      research_memos: {
        Row: {
          id: string
          date: string
          title: string
          raw_content: string
          ai_thesis_summary: Json
          link_url: string
          created_at: string
        }
        Insert: {
          id?: string
          date: string
          title: string
          raw_content: string
          ai_thesis_summary?: Json
          link_url: string
          created_at?: string
        }
        Update: Partial<Database['public']['Tables']['research_memos']['Insert']>
      }
      webhook_subscriptions: {
        Row: {
          id: string
          webhook_url_encrypted: string
          pair_filter: string | null
          created_at: string
        }
        Insert: {
          id?: string
          webhook_url_encrypted: string
          pair_filter?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          webhook_url_encrypted?: string
          pair_filter?: string | null
          created_at?: string
        }
      }
      desk_open_cards: {
        Row: {
          date: string
          pair: string
          structural_regime: string
          dominance_array: Json | null
          pain_index: number | null
          markov_probabilities: Json | null
          ai_brief: string | null
          telemetry_audit: Json | null
          invalidation_triggered: boolean | null
          telemetry_status: string | null
          global_rank: number | null
          apex_score: number | null
          regime_age: number | null
        }
        Insert: {
          date: string
          pair: string
          structural_regime: string
          dominance_array?: Json | null
          pain_index?: number | null
          markov_probabilities?: Json | null
          ai_brief?: string | null
          telemetry_audit?: Json | null
          invalidation_triggered?: boolean | null
          telemetry_status?: string | null
          global_rank?: number | null
          apex_score?: number | null
          regime_age?: number | null
        }
        Update: Partial<Database['public']['Tables']['desk_open_cards']['Insert']>
      }
      event_aliases: {
        Row: {
          id: string
          canonical_name: string
          alias_name: string
        }
        Insert: {
          id?: string
          canonical_name: string
          alias_name: string
        }
        Update: Partial<Database['public']['Tables']['event_aliases']['Insert']>
      }
      event_risk_matrices: {
        Row: {
          id: string
          date: string
          pair: string
          event_name: string
          active_regime: string
          sample_size: number
          median_mie_multiplier: number | null
          beat_median_return: number | null
          miss_median_return: number | null
          inline_median_return: number | null
          asymmetry_ratio: number | null
          asymmetry_direction: string | null
          t1_exhaustion_p2_5: number | null
          t1_exhaustion_p16: number | null
          t1_exhaustion_p84: number | null
          t1_exhaustion_p97_5: number | null
          t1_tail_risk_p95: number | null
          t1_tail_risk_p05: number | null
          ai_context: string | null
          created_at: string | null
        }
        Insert: {
          id?: string
          date: string
          pair: string
          event_name: string
          active_regime: string
          sample_size: number
          median_mie_multiplier?: number | null
          beat_median_return?: number | null
          miss_median_return?: number | null
          inline_median_return?: number | null
          asymmetry_ratio?: number | null
          asymmetry_direction?: string | null
          t1_exhaustion_p2_5?: number | null
          t1_exhaustion_p16?: number | null
          t1_exhaustion_p84?: number | null
          t1_exhaustion_p97_5?: number | null
          t1_tail_risk_p95?: number | null
          t1_tail_risk_p05?: number | null
          ai_context?: string | null
          created_at?: string | null
        }
        Update: Partial<Database['public']['Tables']['event_risk_matrices']['Insert']>
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      historical_prices_for_max_chart: {
        Args: {
          p_pair: string
          p_cutoff: string
        }
        Returns: Array<{
          date: string
          pair: string
          open: number | null
          high: number | null
          low: number | null
          close: number | null
          volume: number | null
          created_at: string
        }>
      }
    }
    Enums: {
      [_ in never]: never
    }
  }
}
