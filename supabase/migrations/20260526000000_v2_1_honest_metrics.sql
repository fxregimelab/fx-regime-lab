-- ============================================
-- FX Regime Lab v2.1 Migration
-- Cleanup for honest public release
-- ============================================

-- 1. Cost-adjusted metrics in validation_log
ALTER TABLE validation_log
ADD COLUMN IF NOT EXISTS log_return_net_bps NUMERIC,
ADD COLUMN IF NOT EXISTS correct_net BOOLEAN,
ADD COLUMN IF NOT EXISTS cost_bps NUMERIC DEFAULT 0.0;

COMMENT ON COLUMN validation_log.log_return_net_bps IS 'Return after estimated transaction costs';
COMMENT ON COLUMN validation_log.correct_net IS 'Correct after costs (directional)';

-- 2. Confidence intervals in validation_stats
ALTER TABLE validation_stats
ADD COLUMN IF NOT EXISTS t5_win_rate_ci_lower NUMERIC,
ADD COLUMN IF NOT EXISTS t5_win_rate_ci_upper NUMERIC,
ADD COLUMN IF NOT EXISTS t5_net_win_rate NUMERIC,
ADD COLUMN IF NOT EXISTS t5_net_win_rate_ci_lower NUMERIC,
ADD COLUMN IF NOT EXISTS t5_net_win_rate_ci_upper NUMERIC,
ADD COLUMN IF NOT EXISTS t20_win_rate_ci_lower NUMERIC,
ADD COLUMN IF NOT EXISTS t20_win_rate_ci_upper NUMERIC,
ADD COLUMN IF NOT EXISTS t20_net_win_rate NUMERIC,
ADD COLUMN IF NOT EXISTS t20_net_win_rate_ci_lower NUMERIC,
ADD COLUMN IF NOT EXISTS t20_net_win_rate_ci_upper NUMERIC;

-- 3. COT staleness tracking
ALTER TABLE signals
ADD COLUMN IF NOT EXISTS days_since_cot INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS risk_reversal_source TEXT DEFAULT 'PENDING_REAL_DATA';

COMMENT ON COLUMN signals.days_since_cot IS 'Days since last COT report publication';
COMMENT ON COLUMN signals.risk_reversal_source IS 'Source of RR data';

-- 4. Add metadata about data quality
ALTER TABLE signals
ADD COLUMN IF NOT EXISTS data_quality_notes TEXT[] DEFAULT '{}';

-- 5. Index for common queries
CREATE INDEX IF NOT EXISTS idx_validation_net ON validation_log(pair, date DESC)
INCLUDE (correct_net, cost_bps, log_return_net_bps);
