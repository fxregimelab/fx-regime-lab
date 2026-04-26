export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      ai_usage_log: {
        Row: {
          created_at: string | null
          date: string
          id: string
          model: string | null
          purpose: string | null
          request_count: number
        }
        Insert: {
          created_at?: string | null
          date: string
          id?: string
          model?: string | null
          purpose?: string | null
          request_count?: number
        }
        Update: {
          created_at?: string | null
          date?: string
          id?: string
          model?: string | null
          purpose?: string | null
          request_count?: number
        }
        Relationships: []
      }
      brief: {
        Row: {
          analysis: string
          composite: number
          confidence: number
          created_at: string | null
          date: string
          id: string
          pair: string
          primary_driver: string | null
          regime: string
        }
        Insert: {
          analysis: string
          composite: number
          confidence: number
          created_at?: string | null
          date: string
          id?: string
          pair: string
          primary_driver?: string | null
          regime: string
        }
        Update: {
          analysis?: string
          composite?: number
          confidence?: number
          created_at?: string | null
          date?: string
          id?: string
          pair?: string
          primary_driver?: string | null
          regime?: string
        }
        Relationships: []
      }
      brief_log: {
        Row: {
          brief_text: string | null
          created_at: string | null
          date: string
          eurusd_regime: string | null
          id: number
          macro_context: string | null
          usdinr_regime: string | null
          usdjpy_regime: string | null
        }
        Insert: {
          brief_text?: string | null
          created_at?: string | null
          date: string
          eurusd_regime?: string | null
          id?: number
          macro_context?: string | null
          usdinr_regime?: string | null
          usdjpy_regime?: string | null
        }
        Update: {
          brief_text?: string | null
          created_at?: string | null
          date?: string
          eurusd_regime?: string | null
          id?: number
          macro_context?: string | null
          usdinr_regime?: string | null
          usdjpy_regime?: string | null
        }
        Relationships: []
      }
      macro_events: {
        Row: {
          ai_brief: string | null
          category: string | null
          created_at: string | null
          date: string
          event: string
          id: string
          impact: string
          pairs: string[]
        }
        Insert: {
          ai_brief?: string | null
          category?: string | null
          created_at?: string | null
          date: string
          event: string
          id?: string
          impact: string
          pairs?: string[]
        }
        Update: {
          ai_brief?: string | null
          category?: string | null
          created_at?: string | null
          date?: string
          event?: string
          id?: string
          impact?: string
          pairs?: string[]
        }
        Relationships: []
      }
      paper_positions: {
        Row: {
          closed_date: string | null
          conviction_level: string | null
          created_at: string | null
          direction: string
          entry_price: number
          exit_price: number | null
          id: number
          invalidation_thesis: string | null
          notes: string | null
          opened_date: string
          pair: string
          pnl_pct: number | null
          pnl_pips: number | null
          r_multiple: number | null
          regime_at_entry: string | null
          status: string | null
          stop_loss: number
          target_1: number | null
          target_2: number | null
          target_3: number | null
        }
        Insert: {
          closed_date?: string | null
          conviction_level?: string | null
          created_at?: string | null
          direction: string
          entry_price: number
          exit_price?: number | null
          id?: number
          invalidation_thesis?: string | null
          notes?: string | null
          opened_date: string
          pair: string
          pnl_pct?: number | null
          pnl_pips?: number | null
          r_multiple?: number | null
          regime_at_entry?: string | null
          status?: string | null
          stop_loss: number
          target_1?: number | null
          target_2?: number | null
          target_3?: number | null
        }
        Update: {
          closed_date?: string | null
          conviction_level?: string | null
          created_at?: string | null
          direction?: string
          entry_price?: number
          exit_price?: number | null
          id?: number
          invalidation_thesis?: string | null
          notes?: string | null
          opened_date?: string
          pair?: string
          pnl_pct?: number | null
          pnl_pips?: number | null
          r_multiple?: number | null
          regime_at_entry?: string | null
          status?: string | null
          stop_loss?: number
          target_1?: number | null
          target_2?: number | null
          target_3?: number | null
        }
        Relationships: []
      }
      pipeline_errors: {
        Row: {
          date: string
          error_message: string
          id: number
          notes: string | null
          pair: string | null
          source: string
          timestamp: string | null
        }
        Insert: {
          date?: string
          error_message: string
          id?: number
          notes?: string | null
          pair?: string | null
          source: string
          timestamp?: string | null
        }
        Update: {
          date?: string
          error_message?: string
          id?: number
          notes?: string | null
          pair?: string | null
          source?: string
          timestamp?: string | null
        }
        Relationships: []
      }
      regime_calls: {
        Row: {
          confidence: number | null
          cot_signal: string | null
          created_at: string | null
          date: string
          id: number
          oi_signal: string | null
          pair: string
          predicted_direction: string | null
          primary_driver: string | null
          rate_signal: string | null
          regime: string
          rr_signal: string | null
          signal_composite: number | null
          vol_signal: string | null
        }
        Insert: {
          confidence?: number | null
          cot_signal?: string | null
          created_at?: string | null
          date: string
          id?: number
          oi_signal?: string | null
          pair: string
          predicted_direction?: string | null
          primary_driver?: string | null
          rate_signal?: string | null
          regime: string
          rr_signal?: string | null
          signal_composite?: number | null
          vol_signal?: string | null
        }
        Update: {
          confidence?: number | null
          cot_signal?: string | null
          created_at?: string | null
          date?: string
          id?: number
          oi_signal?: string | null
          pair?: string
          predicted_direction?: string | null
          primary_driver?: string | null
          rate_signal?: string | null
          regime?: string
          rr_signal?: string | null
          signal_composite?: number | null
          vol_signal?: string | null
        }
        Relationships: []
      }
      signals: {
        Row: {
          atm_vol: number | null
          cot_asset_mgr_net: number | null
          cot_lev_money_net: number | null
          cot_percentile: number | null
          created_at: string | null
          cross_asset_dxy: number | null
          cross_asset_oil: number | null
          cross_asset_vix: number | null
          date: string
          id: number
          implied_vol_30d: number | null
          oi_delta: number | null
          oi_price_alignment: string | null
          pair: string
          rate_diff_10y: number | null
          rate_diff_2y: number | null
          rate_diff_zscore: number | null
          realized_vol_20d: number | null
          realized_vol_5d: number | null
          risk_reversal_25d: number | null
          spot: number | null
          vol_skew: number | null
        }
        Insert: {
          atm_vol?: number | null
          cot_asset_mgr_net?: number | null
          cot_lev_money_net?: number | null
          cot_percentile?: number | null
          created_at?: string | null
          cross_asset_dxy?: number | null
          cross_asset_oil?: number | null
          cross_asset_vix?: number | null
          date: string
          id?: number
          implied_vol_30d?: number | null
          oi_delta?: number | null
          oi_price_alignment?: string | null
          pair: string
          rate_diff_10y?: number | null
          rate_diff_2y?: number | null
          rate_diff_zscore?: number | null
          realized_vol_20d?: number | null
          realized_vol_5d?: number | null
          risk_reversal_25d?: number | null
          spot?: number | null
          vol_skew?: number | null
        }
        Update: {
          atm_vol?: number | null
          cot_asset_mgr_net?: number | null
          cot_lev_money_net?: number | null
          cot_percentile?: number | null
          created_at?: string | null
          cross_asset_dxy?: number | null
          cross_asset_oil?: number | null
          cross_asset_vix?: number | null
          date?: string
          id?: number
          implied_vol_30d?: number | null
          oi_delta?: number | null
          oi_price_alignment?: string | null
          pair?: string
          rate_diff_10y?: number | null
          rate_diff_2y?: number | null
          rate_diff_zscore?: number | null
          realized_vol_20d?: number | null
          realized_vol_5d?: number | null
          risk_reversal_25d?: number | null
          spot?: number | null
          vol_skew?: number | null
        }
        Relationships: []
      }
      validation_log: {
        Row: {
          actual_direction: string | null
          actual_return_1d: number | null
          actual_return_5d: number | null
          confidence: number | null
          correct_1d: boolean | null
          correct_5d: boolean | null
          created_at: string | null
          date: string
          id: number
          notes: string | null
          pair: string
          predicted_direction: string | null
          predicted_regime: string | null
        }
        Insert: {
          actual_direction?: string | null
          actual_return_1d?: number | null
          actual_return_5d?: number | null
          confidence?: number | null
          correct_1d?: boolean | null
          correct_5d?: boolean | null
          created_at?: string | null
          date: string
          id?: number
          notes?: string | null
          pair: string
          predicted_direction?: string | null
          predicted_regime?: string | null
        }
        Update: {
          actual_direction?: string | null
          actual_return_1d?: number | null
          actual_return_5d?: number | null
          confidence?: number | null
          correct_1d?: boolean | null
          correct_5d?: boolean | null
          created_at?: string | null
          date?: string
          id?: number
          notes?: string | null
          pair?: string
          predicted_direction?: string | null
          predicted_regime?: string | null
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
