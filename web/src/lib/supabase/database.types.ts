export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5";
  };
  public: {
    Tables: {
      ai_usage_log: {
        Row: {
          created_at: string | null;
          date: string;
          id: string;
          model: string | null;
          purpose: string | null;
          request_count: number;
        };
        Insert: {
          created_at?: string | null;
          date: string;
          id?: string;
          model?: string | null;
          purpose?: string | null;
          request_count?: number;
        };
        Update: {
          created_at?: string | null;
          date?: string;
          id?: string;
          model?: string | null;
          purpose?: string | null;
          request_count?: number;
        };
        Relationships: [];
      };
      audit_log: {
        Row: {
          correlation_id: string | null;
          created_at: string | null;
          id: string;
          new_value: Json | null;
          old_value: Json | null;
          operation: string;
          row_id: string | null;
          table_name: string;
        };
        Insert: {
          correlation_id?: string | null;
          created_at?: string | null;
          id?: string;
          new_value?: Json | null;
          old_value?: Json | null;
          operation: string;
          row_id?: string | null;
          table_name: string;
        };
        Update: {
          correlation_id?: string | null;
          created_at?: string | null;
          id?: string;
          new_value?: Json | null;
          old_value?: Json | null;
          operation?: string;
          row_id?: string | null;
          table_name?: string;
        };
        Relationships: [];
      };
      brief: {
        Row: {
          analysis: string;
          composite: number;
          confidence: number;
          created_at: string | null;
          date: string;
          id: string;
          pair: string;
          primary_driver: string | null;
          regime: string;
        };
        Insert: {
          analysis: string;
          composite: number;
          confidence: number;
          created_at?: string | null;
          date: string;
          id?: string;
          pair: string;
          primary_driver?: string | null;
          regime: string;
        };
        Update: {
          analysis?: string;
          composite?: number;
          confidence?: number;
          created_at?: string | null;
          date?: string;
          id?: string;
          pair?: string;
          primary_driver?: string | null;
          regime?: string;
        };
        Relationships: [];
      };
      brief_log: {
        Row: {
          audusd_regime: string | null;
          brief_text: string | null;
          created_at: string | null;
          date: string;
          dollar_dominance: number | null;
          eurusd_regime: string | null;
          gbpusd_regime: string | null;
          id: number;
          idiosyncratic_outlier: string | null;
          macro_context: string | null;
          pair_regimes: Json | null;
          sentiment_json: Json | null;
          usdcad_regime: string | null;
          usdchf_regime: string | null;
          usdinr_regime: string | null;
          usdjpy_regime: string | null;
        };
        Insert: {
          audusd_regime?: string | null;
          brief_text?: string | null;
          created_at?: string | null;
          date: string;
          dollar_dominance?: number | null;
          eurusd_regime?: string | null;
          gbpusd_regime?: string | null;
          id?: number;
          idiosyncratic_outlier?: string | null;
          macro_context?: string | null;
          pair_regimes?: Json | null;
          sentiment_json?: Json | null;
          usdcad_regime?: string | null;
          usdchf_regime?: string | null;
          usdinr_regime?: string | null;
          usdjpy_regime?: string | null;
        };
        Update: {
          audusd_regime?: string | null;
          brief_text?: string | null;
          created_at?: string | null;
          date?: string;
          dollar_dominance?: number | null;
          eurusd_regime?: string | null;
          gbpusd_regime?: string | null;
          id?: number;
          idiosyncratic_outlier?: string | null;
          macro_context?: string | null;
          pair_regimes?: Json | null;
          sentiment_json?: Json | null;
          usdcad_regime?: string | null;
          usdchf_regime?: string | null;
          usdinr_regime?: string | null;
          usdjpy_regime?: string | null;
        };
        Relationships: [];
      };
      desk_open_cards: {
        Row: {
          ai_brief: string | null;
          apex_score: number | null;
          date: string;
          dominance_array: Json | null;
          global_rank: number | null;
          invalidation_triggered: boolean | null;
          markov_probabilities: Json | null;
          pain_index: number | null;
          pair: string;
          regime_age: number | null;
          structural_regime: string;
          telemetry_audit: Json | null;
          telemetry_status: string | null;
        };
        Insert: {
          ai_brief?: string | null;
          apex_score?: number | null;
          date: string;
          dominance_array?: Json | null;
          global_rank?: number | null;
          invalidation_triggered?: boolean | null;
          markov_probabilities?: Json | null;
          pain_index?: number | null;
          pair: string;
          regime_age?: number | null;
          structural_regime: string;
          telemetry_audit?: Json | null;
          telemetry_status?: string | null;
        };
        Update: {
          ai_brief?: string | null;
          apex_score?: number | null;
          date?: string;
          dominance_array?: Json | null;
          global_rank?: number | null;
          invalidation_triggered?: boolean | null;
          markov_probabilities?: Json | null;
          pain_index?: number | null;
          pair?: string;
          regime_age?: number | null;
          structural_regime?: string;
          telemetry_audit?: Json | null;
          telemetry_status?: string | null;
        };
        Relationships: [];
      };
      event_aliases: {
        Row: {
          alias_name: string;
          canonical_name: string;
          id: string;
        };
        Insert: {
          alias_name: string;
          canonical_name: string;
          id?: string;
        };
        Update: {
          alias_name?: string;
          canonical_name?: string;
          id?: string;
        };
        Relationships: [];
      };
      event_risk_matrices: {
        Row: {
          active_regime: string;
          ai_context: string | null;
          asymmetry_direction: string | null;
          asymmetry_ratio: number | null;
          beat_median_return: number | null;
          created_at: string | null;
          date: string;
          event_name: string;
          id: string;
          inline_median_return: number | null;
          mean_reversion_prob: number | null;
          median_mie_multiplier: number | null;
          miss_median_return: number | null;
          pair: string;
          sample_size: number;
          t1_exhaustion_p16: number | null;
          t1_exhaustion_p2_5: number | null;
          t1_exhaustion_p84: number | null;
          t1_exhaustion_p97_5: number | null;
          t1_tail_risk_p05: number | null;
          t1_tail_risk_p95: number | null;
        };
        Insert: {
          active_regime: string;
          ai_context?: string | null;
          asymmetry_direction?: string | null;
          asymmetry_ratio?: number | null;
          beat_median_return?: number | null;
          created_at?: string | null;
          date: string;
          event_name: string;
          id?: string;
          inline_median_return?: number | null;
          mean_reversion_prob?: number | null;
          median_mie_multiplier?: number | null;
          miss_median_return?: number | null;
          pair: string;
          sample_size: number;
          t1_exhaustion_p16?: number | null;
          t1_exhaustion_p2_5?: number | null;
          t1_exhaustion_p84?: number | null;
          t1_exhaustion_p97_5?: number | null;
          t1_tail_risk_p05?: number | null;
          t1_tail_risk_p95?: number | null;
        };
        Update: {
          active_regime?: string;
          ai_context?: string | null;
          asymmetry_direction?: string | null;
          asymmetry_ratio?: number | null;
          beat_median_return?: number | null;
          created_at?: string | null;
          date?: string;
          event_name?: string;
          id?: string;
          inline_median_return?: number | null;
          mean_reversion_prob?: number | null;
          median_mie_multiplier?: number | null;
          miss_median_return?: number | null;
          pair?: string;
          sample_size?: number;
          t1_exhaustion_p16?: number | null;
          t1_exhaustion_p2_5?: number | null;
          t1_exhaustion_p84?: number | null;
          t1_exhaustion_p97_5?: number | null;
          t1_tail_risk_p05?: number | null;
          t1_tail_risk_p95?: number | null;
        };
        Relationships: [];
      };
      health_checks: {
        Row: {
          completed_at: string | null;
          created_at: string | null;
          data_quality_score: number | null;
          error_log: string | null;
          id: number;
          pairs_published: number | null;
          pipeline_date: string;
          sources_failed: number | null;
          sources_used: number | null;
          stress_level: string | null;
        };
        Insert: {
          completed_at?: string | null;
          created_at?: string | null;
          data_quality_score?: number | null;
          error_log?: string | null;
          id?: number;
          pairs_published?: number | null;
          pipeline_date: string;
          sources_failed?: number | null;
          sources_used?: number | null;
          stress_level?: string | null;
        };
        Update: {
          completed_at?: string | null;
          created_at?: string | null;
          data_quality_score?: number | null;
          error_log?: string | null;
          id?: number;
          pairs_published?: number | null;
          pipeline_date?: string;
          sources_failed?: number | null;
          sources_used?: number | null;
          stress_level?: string | null;
        };
        Relationships: [];
      };
      historical_cot: {
        Row: {
          asset_mgr_net: number | null;
          created_at: string | null;
          date: string;
          id: number;
          lev_money_net: number | null;
          net_long: number | null;
          open_interest: number | null;
          pair: string;
        };
        Insert: {
          asset_mgr_net?: number | null;
          created_at?: string | null;
          date: string;
          id?: number;
          lev_money_net?: number | null;
          net_long?: number | null;
          open_interest?: number | null;
          pair: string;
        };
        Update: {
          asset_mgr_net?: number | null;
          created_at?: string | null;
          date?: string;
          id?: number;
          lev_money_net?: number | null;
          net_long?: number | null;
          open_interest?: number | null;
          pair?: string;
        };
        Relationships: [];
      };
      historical_cross_asset: {
        Row: {
          copper: number | null;
          created_at: string | null;
          date: string;
          dxy: number | null;
          gold: number | null;
          id: number;
          oil: number | null;
          stoxx: number | null;
          vix: number | null;
        };
        Insert: {
          copper?: number | null;
          created_at?: string | null;
          date: string;
          dxy?: number | null;
          gold?: number | null;
          id?: number;
          oil?: number | null;
          stoxx?: number | null;
          vix?: number | null;
        };
        Update: {
          copper?: number | null;
          created_at?: string | null;
          date?: string;
          dxy?: number | null;
          gold?: number | null;
          id?: number;
          oil?: number | null;
          stoxx?: number | null;
          vix?: number | null;
        };
        Relationships: [];
      };
      historical_implied_vol: {
        Row: {
          created_at: string | null;
          date: string;
          euv: number | null;
          id: number;
          jxv: number | null;
        };
        Insert: {
          created_at?: string | null;
          date: string;
          euv?: number | null;
          id?: number;
          jxv?: number | null;
        };
        Update: {
          created_at?: string | null;
          date?: string;
          euv?: number | null;
          id?: number;
          jxv?: number | null;
        };
        Relationships: [];
      };
      historical_macro_surprises: {
        Row: {
          actual: number | null;
          consensus: number | null;
          created_at: string | null;
          date: string;
          event_name: string;
          id: string;
          previous: number | null;
          surprise_bps: number | null;
          surprise_direction: string;
          time: string | null;
        };
        Insert: {
          actual?: number | null;
          consensus?: number | null;
          created_at?: string | null;
          date: string;
          event_name: string;
          id?: string;
          previous?: number | null;
          surprise_bps?: number | null;
          surprise_direction: string;
          time?: string | null;
        };
        Update: {
          actual?: number | null;
          consensus?: number | null;
          created_at?: string | null;
          date?: string;
          event_name?: string;
          id?: string;
          previous?: number | null;
          surprise_bps?: number | null;
          surprise_direction?: string;
          time?: string | null;
        };
        Relationships: [];
      };
      historical_prices: {
        Row: {
          close: number | null;
          created_at: string | null;
          date: string;
          fetch_timestamp: string | null;
          high: number | null;
          id: string;
          low: number | null;
          open: number | null;
          pair: string;
          source: string | null;
          volume: number | null;
        };
        Insert: {
          close?: number | null;
          created_at?: string | null;
          date: string;
          fetch_timestamp?: string | null;
          high?: number | null;
          id?: string;
          low?: number | null;
          open?: number | null;
          pair: string;
          source?: string | null;
          volume?: number | null;
        };
        Update: {
          close?: number | null;
          created_at?: string | null;
          date?: string;
          fetch_timestamp?: string | null;
          high?: number | null;
          id?: string;
          low?: number | null;
          open?: number | null;
          pair?: string;
          source?: string | null;
          volume?: number | null;
        };
        Relationships: [];
      };
      historical_yields: {
        Row: {
          created_at: string | null;
          date: string;
          id: number;
          series_id: string;
          value: number | null;
        };
        Insert: {
          created_at?: string | null;
          date: string;
          id?: number;
          series_id: string;
          value?: number | null;
        };
        Update: {
          created_at?: string | null;
          date?: string;
          id?: number;
          series_id?: string;
          value?: number | null;
        };
        Relationships: [];
      };
      macro_events: {
        Row: {
          ai_brief: string | null;
          category: string | null;
          created_at: string | null;
          date: string;
          event: string;
          id: string;
          impact: string;
          pairs: string[];
        };
        Insert: {
          ai_brief?: string | null;
          category?: string | null;
          created_at?: string | null;
          date: string;
          event: string;
          id?: string;
          impact: string;
          pairs?: string[];
        };
        Update: {
          ai_brief?: string | null;
          category?: string | null;
          created_at?: string | null;
          date?: string;
          event?: string;
          id?: string;
          impact?: string;
          pairs?: string[];
        };
        Relationships: [];
      };
      macro_releases: {
        Row: {
          actual_value: number | null;
          cleveland_fed_estimate: number | null;
          consensus_estimate: number | null;
          created_at: string | null;
          id: string;
          our_model_estimate: number | null;
          release_date: string;
          release_name: string;
          surprise_direction: string | null;
          surprise_magnitude: number | null;
        };
        Insert: {
          actual_value?: number | null;
          cleveland_fed_estimate?: number | null;
          consensus_estimate?: number | null;
          created_at?: string | null;
          id?: string;
          our_model_estimate?: number | null;
          release_date: string;
          release_name: string;
          surprise_direction?: string | null;
          surprise_magnitude?: number | null;
        };
        Update: {
          actual_value?: number | null;
          cleveland_fed_estimate?: number | null;
          consensus_estimate?: number | null;
          created_at?: string | null;
          id?: string;
          our_model_estimate?: number | null;
          release_date?: string;
          release_name?: string;
          surprise_direction?: string | null;
          surprise_magnitude?: number | null;
        };
        Relationships: [];
      };
      model_predictions: {
        Row: {
          cleveland_fed_estimate: number | null;
          consensus_estimate: number | null;
          created_at: string | null;
          features_snapshot: Json | null;
          id: string;
          model_type: string;
          predicted_value: number;
          prediction_std: number | null;
          probability_above_consensus: number | null;
          release_date: string;
          release_name: string;
        };
        Insert: {
          cleveland_fed_estimate?: number | null;
          consensus_estimate?: number | null;
          created_at?: string | null;
          features_snapshot?: Json | null;
          id?: string;
          model_type: string;
          predicted_value: number;
          prediction_std?: number | null;
          probability_above_consensus?: number | null;
          release_date: string;
          release_name: string;
        };
        Update: {
          cleveland_fed_estimate?: number | null;
          consensus_estimate?: number | null;
          created_at?: string | null;
          features_snapshot?: Json | null;
          id?: string;
          model_type?: string;
          predicted_value?: number;
          prediction_std?: number | null;
          probability_above_consensus?: number | null;
          release_date?: string;
          release_name?: string;
        };
        Relationships: [];
      };
      pair_profiles: {
        Row: {
          confidence_adjustment_rules: Json | null;
          cot_weight: number;
          created_at: string | null;
          display_name: string;
          driver_tag: string | null;
          id: number;
          oi_weight: number;
          pair: string;
          primary_anchor_market: string | null;
          rate_weight: number;
          regime_thresholds: Json;
          special_signal_label: string | null;
          special_signal_source: string | null;
          special_weight: number;
          updated_at: string | null;
          vol_weight: number;
        };
        Insert: {
          confidence_adjustment_rules?: Json | null;
          cot_weight?: number;
          created_at?: string | null;
          display_name: string;
          driver_tag?: string | null;
          id?: number;
          oi_weight?: number;
          pair: string;
          primary_anchor_market?: string | null;
          rate_weight?: number;
          regime_thresholds?: Json;
          special_signal_label?: string | null;
          special_signal_source?: string | null;
          special_weight?: number;
          updated_at?: string | null;
          vol_weight?: number;
        };
        Update: {
          confidence_adjustment_rules?: Json | null;
          cot_weight?: number;
          created_at?: string | null;
          display_name?: string;
          driver_tag?: string | null;
          id?: number;
          oi_weight?: number;
          pair?: string;
          primary_anchor_market?: string | null;
          rate_weight?: number;
          regime_thresholds?: Json;
          special_signal_label?: string | null;
          special_signal_source?: string | null;
          special_weight?: number;
          updated_at?: string | null;
          vol_weight?: number;
        };
        Relationships: [];
      };
      paper_bets: {
        Row: {
          bet_direction: string;
          created_at: string | null;
          edge_pct: number;
          entry_price: number;
          id: string;
          kelly_fraction: number;
          market_id: string;
          market_implied_probability: number;
          our_model_probability: number;
          pnl_usdc: number | null;
          release_name: string | null;
          resolution: number | null;
          resolved_at: string | null;
          status: string | null;
          virtual_size_usdc: number;
        };
        Insert: {
          bet_direction: string;
          created_at?: string | null;
          edge_pct: number;
          entry_price: number;
          id?: string;
          kelly_fraction: number;
          market_id: string;
          market_implied_probability: number;
          our_model_probability: number;
          pnl_usdc?: number | null;
          release_name?: string | null;
          resolution?: number | null;
          resolved_at?: string | null;
          status?: string | null;
          virtual_size_usdc: number;
        };
        Update: {
          bet_direction?: string;
          created_at?: string | null;
          edge_pct?: number;
          entry_price?: number;
          id?: string;
          kelly_fraction?: number;
          market_id?: string;
          market_implied_probability?: number;
          our_model_probability?: number;
          pnl_usdc?: number | null;
          release_name?: string | null;
          resolution?: number | null;
          resolved_at?: string | null;
          status?: string | null;
          virtual_size_usdc?: number;
        };
        Relationships: [
          {
            foreignKeyName: "paper_bets_market_id_fkey";
            columns: ["market_id"];
            isOneToOne: false;
            referencedRelation: "polymarket_markets";
            referencedColumns: ["market_id"];
          },
        ];
      };
      paper_positions: {
        Row: {
          closed_date: string | null;
          conviction_level: string | null;
          created_at: string | null;
          direction: string;
          entry_price: number;
          exit_price: number | null;
          id: number;
          invalidation_thesis: string | null;
          notes: string | null;
          opened_date: string;
          pair: string;
          pnl_pct: number | null;
          pnl_pips: number | null;
          r_multiple: number | null;
          regime_at_entry: string | null;
          status: string | null;
          stop_loss: number;
          target_1: number | null;
          target_2: number | null;
          target_3: number | null;
        };
        Insert: {
          closed_date?: string | null;
          conviction_level?: string | null;
          created_at?: string | null;
          direction: string;
          entry_price: number;
          exit_price?: number | null;
          id?: number;
          invalidation_thesis?: string | null;
          notes?: string | null;
          opened_date: string;
          pair: string;
          pnl_pct?: number | null;
          pnl_pips?: number | null;
          r_multiple?: number | null;
          regime_at_entry?: string | null;
          status?: string | null;
          stop_loss: number;
          target_1?: number | null;
          target_2?: number | null;
          target_3?: number | null;
        };
        Update: {
          closed_date?: string | null;
          conviction_level?: string | null;
          created_at?: string | null;
          direction?: string;
          entry_price?: number;
          exit_price?: number | null;
          id?: number;
          invalidation_thesis?: string | null;
          notes?: string | null;
          opened_date?: string;
          pair?: string;
          pnl_pct?: number | null;
          pnl_pips?: number | null;
          r_multiple?: number | null;
          regime_at_entry?: string | null;
          status?: string | null;
          stop_loss?: number;
          target_1?: number | null;
          target_2?: number | null;
          target_3?: number | null;
        };
        Relationships: [];
      };
      performance_summary: {
        Row: {
          avg_edge: number | null;
          calibration_error: number | null;
          computed_date: string;
          created_at: string | null;
          id: string;
          max_drawdown: number | null;
          open_bets: number | null;
          resolved_bets: number | null;
          sharpe_ratio: number | null;
          total_bets: number | null;
          total_pnl_usdc: number | null;
          win_rate: number | null;
        };
        Insert: {
          avg_edge?: number | null;
          calibration_error?: number | null;
          computed_date: string;
          created_at?: string | null;
          id?: string;
          max_drawdown?: number | null;
          open_bets?: number | null;
          resolved_bets?: number | null;
          sharpe_ratio?: number | null;
          total_bets?: number | null;
          total_pnl_usdc?: number | null;
          win_rate?: number | null;
        };
        Update: {
          avg_edge?: number | null;
          calibration_error?: number | null;
          computed_date?: string;
          created_at?: string | null;
          id?: string;
          max_drawdown?: number | null;
          open_bets?: number | null;
          resolved_bets?: number | null;
          sharpe_ratio?: number | null;
          total_bets?: number | null;
          total_pnl_usdc?: number | null;
          win_rate?: number | null;
        };
        Relationships: [];
      };
      pipeline_errors: {
        Row: {
          correlation_id: string | null;
          created_at: string;
          date: string;
          error_message: string;
          error_type: string | null;
          id: number;
          message: string | null;
          notes: string | null;
          pair: string | null;
          run_date: string | null;
          source: string;
          step: string;
          timestamp: string | null;
          traceback: string | null;
        };
        Insert: {
          correlation_id?: string | null;
          created_at?: string;
          date?: string;
          error_message: string;
          error_type?: string | null;
          id?: number;
          message?: string | null;
          notes?: string | null;
          pair?: string | null;
          run_date?: string | null;
          source: string;
          step?: string;
          timestamp?: string | null;
          traceback?: string | null;
        };
        Update: {
          correlation_id?: string | null;
          created_at?: string;
          date?: string;
          error_message?: string;
          error_type?: string | null;
          id?: number;
          message?: string | null;
          notes?: string | null;
          pair?: string | null;
          run_date?: string | null;
          source?: string;
          step?: string;
          timestamp?: string | null;
          traceback?: string | null;
        };
        Relationships: [];
      };
      pipeline_runs: {
        Row: {
          ai_calls_failed: number | null;
          ai_calls_made: number | null;
          correlation_id: string | null;
          created_at: string | null;
          date: string;
          dqs_score: number | null;
          duration_seconds: number | null;
          errors: Json | null;
          id: string;
          pairs_processed: number | null;
          pairs_skipped: Json | null;
          sources_used: Json | null;
          status: string | null;
        };
        Insert: {
          ai_calls_failed?: number | null;
          ai_calls_made?: number | null;
          correlation_id?: string | null;
          created_at?: string | null;
          date: string;
          dqs_score?: number | null;
          duration_seconds?: number | null;
          errors?: Json | null;
          id?: string;
          pairs_processed?: number | null;
          pairs_skipped?: Json | null;
          sources_used?: Json | null;
          status?: string | null;
        };
        Update: {
          ai_calls_failed?: number | null;
          ai_calls_made?: number | null;
          correlation_id?: string | null;
          created_at?: string | null;
          date?: string;
          dqs_score?: number | null;
          duration_seconds?: number | null;
          errors?: Json | null;
          id?: string;
          pairs_processed?: number | null;
          pairs_skipped?: Json | null;
          sources_used?: Json | null;
          status?: string | null;
        };
        Relationships: [];
      };
      polymarket_markets: {
        Row: {
          category: string | null;
          current_no_price: number | null;
          current_yes_price: number | null;
          end_date: string | null;
          id: string;
          last_updated: string | null;
          market_id: string;
          question: string;
          spread: number | null;
          volume_usdc: number | null;
        };
        Insert: {
          category?: string | null;
          current_no_price?: number | null;
          current_yes_price?: number | null;
          end_date?: string | null;
          id?: string;
          last_updated?: string | null;
          market_id: string;
          question: string;
          spread?: number | null;
          volume_usdc?: number | null;
        };
        Update: {
          category?: string | null;
          current_no_price?: number | null;
          current_yes_price?: number | null;
          end_date?: string | null;
          id?: string;
          last_updated?: string | null;
          market_id?: string;
          question?: string;
          spread?: number | null;
          volume_usdc?: number | null;
        };
        Relationships: [];
      };
      regime_calls: {
        Row: {
          confidence: number | null;
          conviction: number | null;
          correlation_id: string | null;
          cot_signal: string | null;
          created_at: string | null;
          data_quality_score: number | null;
          date: string;
          directional_bias: string | null;
          entry_timing: string | null;
          id: number;
          model_version: string | null;
          oi_signal: string | null;
          pair: string;
          position_size: string | null;
          predicted_direction: string | null;
          primary_driver: string | null;
          rate_signal: string | null;
          regime: string;
          rr_signal: string | null;
          signal_composite: number | null;
          special_signal_label: string | null;
          special_signal_value: number | null;
          stop_level: number | null;
          stress_level: string | null;
          vol_signal: string | null;
          write_hash: string | null;
        };
        Insert: {
          confidence?: number | null;
          conviction?: number | null;
          correlation_id?: string | null;
          cot_signal?: string | null;
          created_at?: string | null;
          data_quality_score?: number | null;
          date: string;
          directional_bias?: string | null;
          entry_timing?: string | null;
          id?: number;
          model_version?: string | null;
          oi_signal?: string | null;
          pair: string;
          position_size?: string | null;
          predicted_direction?: string | null;
          primary_driver?: string | null;
          rate_signal?: string | null;
          regime: string;
          rr_signal?: string | null;
          signal_composite?: number | null;
          special_signal_label?: string | null;
          special_signal_value?: number | null;
          stop_level?: number | null;
          stress_level?: string | null;
          vol_signal?: string | null;
          write_hash?: string | null;
        };
        Update: {
          confidence?: number | null;
          conviction?: number | null;
          correlation_id?: string | null;
          cot_signal?: string | null;
          created_at?: string | null;
          data_quality_score?: number | null;
          date?: string;
          directional_bias?: string | null;
          entry_timing?: string | null;
          id?: number;
          model_version?: string | null;
          oi_signal?: string | null;
          pair?: string;
          position_size?: string | null;
          predicted_direction?: string | null;
          primary_driver?: string | null;
          rate_signal?: string | null;
          regime?: string;
          rr_signal?: string | null;
          signal_composite?: number | null;
          special_signal_label?: string | null;
          special_signal_value?: number | null;
          stop_level?: number | null;
          stress_level?: string | null;
          vol_signal?: string | null;
          write_hash?: string | null;
        };
        Relationships: [];
      };
      research_analogs: {
        Row: {
          as_of_date: string;
          context_label: string | null;
          created_at: string | null;
          current_composite: number | null;
          current_trend_5d: number | null;
          forward_30d_return: number | null;
          id: string;
          match_date: string;
          match_score: number;
          matched_trend_5d: number | null;
          pair: string;
          rank: number;
          regime_stability: number | null;
        };
        Insert: {
          as_of_date: string;
          context_label?: string | null;
          created_at?: string | null;
          current_composite?: number | null;
          current_trend_5d?: number | null;
          forward_30d_return?: number | null;
          id?: string;
          match_date: string;
          match_score: number;
          matched_trend_5d?: number | null;
          pair: string;
          rank: number;
          regime_stability?: number | null;
        };
        Update: {
          as_of_date?: string;
          context_label?: string | null;
          created_at?: string | null;
          current_composite?: number | null;
          current_trend_5d?: number | null;
          forward_30d_return?: number | null;
          id?: string;
          match_date?: string;
          match_score?: number;
          matched_trend_5d?: number | null;
          pair?: string;
          rank?: number;
          regime_stability?: number | null;
        };
        Relationships: [];
      };
      research_memos: {
        Row: {
          ai_thesis_summary: Json;
          created_at: string;
          date: string;
          id: string;
          link_url: string;
          raw_content: string;
          title: string;
        };
        Insert: {
          ai_thesis_summary?: Json;
          created_at?: string;
          date: string;
          id?: string;
          link_url: string;
          raw_content: string;
          title: string;
        };
        Update: {
          ai_thesis_summary?: Json;
          created_at?: string;
          date?: string;
          id?: string;
          link_url?: string;
          raw_content?: string;
          title?: string;
        };
        Relationships: [];
      };
      signals: {
        Row: {
          boj_policy_rate: number | null;
          breakeven_inflation_10y: number | null;
          bund_btp_spread: number | null;
          cot_asset_mgr_net: number | null;
          cot_lev_money_net: number | null;
          cot_net_pos: number | null;
          cot_percentile: number | null;
          created_at: string | null;
          cross_asset_copper: number | null;
          cross_asset_dxy: number | null;
          cross_asset_gold: number | null;
          cross_asset_oil: number | null;
          cross_asset_stoxx: number | null;
          cross_asset_us10y: number | null;
          cross_asset_vix: number | null;
          ecb_balance_sheet: number | null;
          date: string;
          day_change: number | null;
          day_change_pct: number | null;
          fpi_flow: number | null;
          id: number;
          india_vix: number | null;
          inr_forward_premium: number | null;
          implied_vol_30d: number | null;
          oi_delta: number | null;
          pair: string;
          rate_diff_10y: number | null;
          rate_diff_10y_real: number | null;
          rate_diff_2y: number | null;
          rate_z_structural: number | null;
          rate_z_tactical: number | null;
          realized_vol_20d: number | null;
          realized_vol_5d: number | null;
          realized_vol_rank: number | null;
          risk_reversal_25d: number | null;
          skew_alignment: number | null;
          spot: number | null;
          structural_instability: boolean;
          volume_rvol: number | null;
        };
        Insert: {
          boj_policy_rate?: number | null;
          breakeven_inflation_10y?: number | null;
          bund_btp_spread?: number | null;
          cot_asset_mgr_net?: number | null;
          cot_lev_money_net?: number | null;
          cot_net_pos?: number | null;
          cot_percentile?: number | null;
          created_at?: string | null;
          cross_asset_copper?: number | null;
          cross_asset_dxy?: number | null;
          cross_asset_gold?: number | null;
          cross_asset_oil?: number | null;
          cross_asset_stoxx?: number | null;
          cross_asset_us10y?: number | null;
          cross_asset_vix?: number | null;
          ecb_balance_sheet?: number | null;
          date: string;
          day_change?: number | null;
          day_change_pct?: number | null;
          fpi_flow?: number | null;
          id?: number;
          india_vix?: number | null;
          inr_forward_premium?: number | null;
          implied_vol_30d?: number | null;
          oi_delta?: number | null;
          pair: string;
          rate_diff_10y?: number | null;
          rate_diff_10y_real?: number | null;
          rate_diff_2y?: number | null;
          rate_z_structural?: number | null;
          rate_z_tactical?: number | null;
          realized_vol_20d?: number | null;
          realized_vol_5d?: number | null;
          realized_vol_rank?: number | null;
          risk_reversal_25d?: number | null;
          skew_alignment?: number | null;
          spot?: number | null;
          structural_instability?: boolean;
          volume_rvol?: number | null;
        };
        Update: {
          boj_policy_rate?: number | null;
          breakeven_inflation_10y?: number | null;
          bund_btp_spread?: number | null;
          cot_asset_mgr_net?: number | null;
          cot_lev_money_net?: number | null;
          cot_net_pos?: number | null;
          cot_percentile?: number | null;
          created_at?: string | null;
          cross_asset_copper?: number | null;
          cross_asset_dxy?: number | null;
          cross_asset_gold?: number | null;
          cross_asset_oil?: number | null;
          cross_asset_stoxx?: number | null;
          cross_asset_us10y?: number | null;
          cross_asset_vix?: number | null;
          date?: string;
          day_change?: number | null;
          day_change_pct?: number | null;
          fpi_flow?: number | null;
          id?: number;
          implied_vol_30d?: number | null;
          oi_delta?: number | null;
          pair?: string;
          rate_diff_10y?: number | null;
          rate_diff_10y_real?: number | null;
          rate_diff_2y?: number | null;
          rate_z_structural?: number | null;
          rate_z_tactical?: number | null;
          realized_vol_20d?: number | null;
          realized_vol_5d?: number | null;
          realized_vol_rank?: number | null;
          risk_reversal_25d?: number | null;
          skew_alignment?: number | null;
          spot?: number | null;
          structural_instability?: boolean;
          volume_rvol?: number | null;
        };
        Relationships: [];
      };
      strategy_ledger: {
        Row: {
          brier_score_t5: number | null;
          confidence: number | null;
          date: string;
          direction: string;
          entry_close: number | null;
          id: string;
          max_pain_bps: number | null;
          pair: string;
          primary_driver: string;
          regime: string;
          t1_close: number | null;
          t1_hit: number | null;
          t3_close: number | null;
          t3_hit: number | null;
          t5_close: number | null;
          t5_hit: number | null;
        };
        Insert: {
          brier_score_t5?: number | null;
          confidence?: number | null;
          date: string;
          direction: string;
          entry_close?: number | null;
          id?: string;
          max_pain_bps?: number | null;
          pair: string;
          primary_driver: string;
          regime: string;
          t1_close?: number | null;
          t1_hit?: number | null;
          t3_close?: number | null;
          t3_hit?: number | null;
          t5_close?: number | null;
          t5_hit?: number | null;
        };
        Update: {
          brier_score_t5?: number | null;
          confidence?: number | null;
          date?: string;
          direction?: string;
          entry_close?: number | null;
          id?: string;
          max_pain_bps?: number | null;
          pair?: string;
          primary_driver?: string;
          regime?: string;
          t1_close?: number | null;
          t1_hit?: number | null;
          t3_close?: number | null;
          t3_hit?: number | null;
          t5_close?: number | null;
          t5_hit?: number | null;
        };
        Relationships: [];
      };
      universe: {
        Row: {
          class: string;
          cot_ticker: string | null;
          id: string;
          pair: string;
          spot_ticker: string | null;
          volume_ticker: string | null;
          yield_base: string | null;
          yield_quote: string | null;
        };
        Insert: {
          class: string;
          cot_ticker?: string | null;
          id?: string;
          pair: string;
          spot_ticker?: string | null;
          volume_ticker?: string | null;
          yield_base?: string | null;
          yield_quote?: string | null;
        };
        Update: {
          class?: string;
          cot_ticker?: string | null;
          id?: string;
          pair?: string;
          spot_ticker?: string | null;
          volume_ticker?: string | null;
          yield_base?: string | null;
          yield_quote?: string | null;
        };
        Relationships: [];
      };
      validation_log: {
        Row: {
          actual_direction: string | null;
          actual_direction_t20: string | null;
          actual_direction_t5: string | null;
          call: string | null;
          actual_return_20d: number | null;
          actual_return_5d: number | null;
          brier_20d: number | null;
          brier_5d: number | null;
          brier_score_t20: number | null;
          brier_score_t5: number | null;
          call_date: string | null;
          call_id: number | null;
          confidence: number | null;
          correct_20d: boolean | null;
          correct_5d: boolean | null;
          correct_t20: boolean | null;
          correct_t5: boolean | null;
          created_at: string | null;
          date: string;
          id: number;
          is_superseded: boolean | null;
          log_return_t20_bps: number | null;
          log_return_t5_bps: number | null;
          notes: string | null;
          pair: string;
        };
        Insert: {
          actual_direction?: string | null;
          actual_direction_t20?: string | null;
          actual_direction_t5?: string | null;
          call?: string | null;
          actual_return_20d?: number | null;
          actual_return_5d?: number | null;
          brier_20d?: number | null;
          brier_5d?: number | null;
          brier_score_t20?: number | null;
          brier_score_t5?: number | null;
          call_date?: string | null;
          call_id?: number | null;
          confidence?: number | null;
          correct_20d?: boolean | null;
          correct_5d?: boolean | null;
          correct_t20?: boolean | null;
          correct_t5?: boolean | null;
          created_at?: string | null;
          date: string;
          id?: number;
          is_superseded?: boolean | null;
          log_return_t20_bps?: number | null;
          log_return_t5_bps?: number | null;
          notes?: string | null;
          pair: string;
        };
        Update: {
          actual_direction?: string | null;
          actual_direction_t20?: string | null;
          actual_direction_t5?: string | null;
          call?: string | null;
          actual_return_20d?: number | null;
          actual_return_5d?: number | null;
          brier_20d?: number | null;
          brier_5d?: number | null;
          brier_score_t20?: number | null;
          brier_score_t5?: number | null;
          call_date?: string | null;
          call_id?: number | null;
          confidence?: number | null;
          correct_20d?: boolean | null;
          correct_5d?: boolean | null;
          correct_t20?: boolean | null;
          correct_t5?: boolean | null;
          created_at?: string | null;
          date?: string;
          id?: number;
          is_superseded?: boolean | null;
          log_return_t20_bps?: number | null;
          log_return_t5_bps?: number | null;
          notes?: string | null;
          pair?: string;
        };
        Relationships: [
          {
            foreignKeyName: "fk_validation_log_call_id";
            columns: ["call_id"];
            isOneToOne: false;
            referencedRelation: "regime_calls";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "validation_log_call_id_fkey";
            columns: ["call_id"];
            isOneToOne: false;
            referencedRelation: "regime_calls";
            referencedColumns: ["id"];
          },
        ];
      };
      validation_stats: {
        Row: {
          as_of_date: string;
          computed_at: string;
          created_at: string | null;
          id: number;
          pair: string;
          t20_brier_skill: number | null;
          t20_calibration_json: Json | null;
          t20_directional_calls: number | null;
          t20_max_drawdown_bps: number | null;
          t20_mean_brier: number | null;
          t20_mean_log_return_bps: number | null;
          t20_return_std_bps: number | null;
          t20_rolling_90d_accuracy: number | null;
          t20_sharpe_like: number | null;
          t20_total_calls: number | null;
          t20_win_rate: number | null;
          t20_wins: number | null;
          t5_brier_skill: number | null;
          t5_calibration_json: Json | null;
          t5_directional_calls: number | null;
          t5_max_drawdown_bps: number | null;
          t5_mean_brier: number | null;
          t5_mean_log_return_bps: number | null;
          t5_return_std_bps: number | null;
          t5_rolling_90d_accuracy: number | null;
          t5_sharpe_like: number | null;
          t5_total_calls: number | null;
          t5_win_rate: number | null;
          t5_wins: number | null;
        };
        Insert: {
          as_of_date: string;
          computed_at?: string;
          created_at?: string | null;
          id?: number;
          pair: string;
          t20_brier_skill?: number | null;
          t20_calibration_json?: Json | null;
          t20_directional_calls?: number | null;
          t20_max_drawdown_bps?: number | null;
          t20_mean_brier?: number | null;
          t20_mean_log_return_bps?: number | null;
          t20_return_std_bps?: number | null;
          t20_rolling_90d_accuracy?: number | null;
          t20_sharpe_like?: number | null;
          t20_total_calls?: number | null;
          t20_win_rate?: number | null;
          t20_wins?: number | null;
          t5_brier_skill?: number | null;
          t5_calibration_json?: Json | null;
          t5_directional_calls?: number | null;
          t5_max_drawdown_bps?: number | null;
          t5_mean_brier?: number | null;
          t5_mean_log_return_bps?: number | null;
          t5_return_std_bps?: number | null;
          t5_rolling_90d_accuracy?: number | null;
          t5_sharpe_like?: number | null;
          t5_total_calls?: number | null;
          t5_win_rate?: number | null;
          t5_wins?: number | null;
        };
        Update: {
          as_of_date?: string;
          computed_at?: string;
          created_at?: string | null;
          id?: number;
          pair?: string;
          t20_brier_skill?: number | null;
          t20_calibration_json?: Json | null;
          t20_directional_calls?: number | null;
          t20_max_drawdown_bps?: number | null;
          t20_mean_brier?: number | null;
          t20_mean_log_return_bps?: number | null;
          t20_return_std_bps?: number | null;
          t20_rolling_90d_accuracy?: number | null;
          t20_sharpe_like?: number | null;
          t20_total_calls?: number | null;
          t20_win_rate?: number | null;
          t20_wins?: number | null;
          t5_brier_skill?: number | null;
          t5_calibration_json?: Json | null;
          t5_directional_calls?: number | null;
          t5_max_drawdown_bps?: number | null;
          t5_mean_brier?: number | null;
          t5_mean_log_return_bps?: number | null;
          t5_return_std_bps?: number | null;
          t5_rolling_90d_accuracy?: number | null;
          t5_sharpe_like?: number | null;
          t5_total_calls?: number | null;
          t5_win_rate?: number | null;
          t5_wins?: number | null;
        };
        Relationships: [];
      };

    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      calculate_dual_correlation: {
        Args: { p_lookback: number; p_pair: string };
        Returns: number;
      };
      get_g10_correlation_matrix: { Args: never; Returns: Json };
      historical_prices_for_max_chart: {
        Args: { p_cutoff: string; p_pair: string };
        Returns: {
          close: number;
          created_at: string;
          date: string;
          high: number;
          low: number;
          open: number;
          pair: string;
          volume: number;
        }[];
      };
      increment_ai_usage: {
        Args: { p_date: string; p_model: string; p_purpose: string };
        Returns: boolean;
      };
      match_historical_analogs: {
        Args: {
          as_of_date: string;
          current_comp: number;
          current_trend: number;
          limit_rows?: number;
          target_pair: string;
        };
        Returns: {
          context_label: string;
          current_composite: number;
          current_trend_5d: number;
          forward_30d_return: number;
          match_date: string;
          match_score: number;
          matched_trend_5d: number;
          rank: number;
          regime_stability: number;
        }[];
      };
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">;

type DefaultSchema = DatabaseWithoutInternals[Extract<
  keyof Database,
  "public"
>];

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R;
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R;
      }
      ? R
      : never
    : never;

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I;
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I;
      }
      ? I
      : never
    : never;

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U;
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U;
      }
      ? U
      : never
    : never;

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never;

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never;

export const Constants = {
  public: {
    Enums: {},
  },
} as const;
