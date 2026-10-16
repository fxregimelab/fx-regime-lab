-- ============================================================
-- DB Cleanup: Remove stale columns never written by the
-- current 3-pair pipeline (post M.1-M.3).
--
-- AUDIT REF: docs/DB_AUDIT_STRATEGY.md Section 2.2, 2.4
-- ============================================================

-- 1. signals: drop 6 columns never populated by writer.py
--    (rate_diff_mom, realized_vol_21 were added by Round 1
--     audit migration but never written; atm_vol, vol_skew,
--     rate_diff_zscore, oi_price_alignment are legacy artifacts)
ALTER TABLE public.signals
    DROP COLUMN IF EXISTS rate_diff_mom,
    DROP COLUMN IF EXISTS realized_vol_21,
    DROP COLUMN IF EXISTS atm_vol,
    DROP COLUMN IF EXISTS oi_price_alignment,
    DROP COLUMN IF EXISTS rate_diff_zscore,
    DROP COLUMN IF EXISTS vol_skew;

-- 2. validation_log: drop 10 columns from early iterations
--    that are never populated by the current validation engine.
--    NOTE: predicted_direction and predicted_regime are still written and
--    read by pipeline/src/validation/engine.py and must be retained.
ALTER TABLE public.validation_log
    DROP COLUMN IF EXISTS validation_date,
    DROP COLUMN IF EXISTS is_correct,
    DROP COLUMN IF EXISTS pnl_bps,
    DROP COLUMN IF EXISTS actual_return_1d,
    DROP COLUMN IF EXISTS alpha_return_1d,
    DROP COLUMN IF EXISTS correct_1d,
    DROP COLUMN IF EXISTS dxy_return_1d,
    DROP COLUMN IF EXISTS max_intraday_adverse_bps,
    DROP COLUMN IF EXISTS regime_at_call,
    DROP COLUMN IF EXISTS vol_regime_at_call;
