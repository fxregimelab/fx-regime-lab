-- FX Regime Lab V3 — Structured brief summaries for rich UI rendering

ALTER TABLE brief_log
ADD COLUMN IF NOT EXISTS structured_summary JSONB;

COMMENT ON COLUMN brief_log.structured_summary IS
  'AI-generated structured brief data: key_takeaways, pair_cards, risk_flags, macro_theme. Pre-baked for UI rendering without text parsing.';
