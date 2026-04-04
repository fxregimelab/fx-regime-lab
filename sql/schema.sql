-- FX Regime Lab — apply in Supabase SQL editor (see contaxt files/PLAN.md)

CREATE TABLE IF NOT EXISTS signals (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  pair VARCHAR(10) NOT NULL,
  rate_diff_2y FLOAT,
  rate_diff_10y FLOAT,
  rate_diff_zscore FLOAT,
  cot_lev_money_net BIGINT,
  cot_asset_mgr_net BIGINT,
  cot_percentile FLOAT,
  realized_vol_5d FLOAT,
  realized_vol_20d FLOAT,
  implied_vol_30d FLOAT,
  vol_skew FLOAT,
  atm_vol FLOAT,
  risk_reversal_25d FLOAT,
  oi_delta INT,
  oi_price_alignment VARCHAR(10),
  cross_asset_vix FLOAT,
  cross_asset_dxy FLOAT,
  cross_asset_oil FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS regime_calls (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  pair VARCHAR(10) NOT NULL,
  regime VARCHAR(30) NOT NULL,
  confidence FLOAT,
  signal_composite FLOAT,
  rate_signal VARCHAR(10),
  cot_signal VARCHAR(10),
  vol_signal VARCHAR(10),
  rr_signal VARCHAR(10),
  oi_signal VARCHAR(10),
  primary_driver TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS validation_log (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  pair VARCHAR(10) NOT NULL,
  predicted_direction VARCHAR(10),
  predicted_regime VARCHAR(30),
  confidence FLOAT,
  actual_direction VARCHAR(10),
  actual_return_1d FLOAT,
  actual_return_5d FLOAT,
  correct_1d BOOLEAN,
  correct_5d BOOLEAN,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS paper_positions (
  id SERIAL PRIMARY KEY,
  opened_date DATE NOT NULL,
  closed_date DATE,
  pair VARCHAR(10) NOT NULL,
  direction VARCHAR(10) NOT NULL,
  entry_price FLOAT NOT NULL,
  stop_loss FLOAT NOT NULL,
  target_1 FLOAT,
  target_2 FLOAT,
  target_3 FLOAT,
  invalidation_thesis TEXT,
  conviction_level VARCHAR(10),
  regime_at_entry VARCHAR(30),
  status VARCHAR(20),
  exit_price FLOAT,
  pnl_pips FLOAT,
  pnl_pct FLOAT,
  r_multiple FLOAT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brief_log (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  brief_text TEXT,
  eurusd_regime VARCHAR(30),
  usdjpy_regime VARCHAR(30),
  usdinr_regime VARCHAR(30),
  macro_context TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_errors (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL DEFAULT CURRENT_DATE,
  source VARCHAR(50) NOT NULL,
  pair VARCHAR(10),
  error_message TEXT NOT NULL,
  notes TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_date_pair ON signals(date, pair);
CREATE INDEX IF NOT EXISTS idx_regime_calls_date_pair ON regime_calls(date, pair);
CREATE INDEX IF NOT EXISTS idx_validation_date_pair ON validation_log(date, pair);
CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_unique ON signals(date, pair);
CREATE UNIQUE INDEX IF NOT EXISTS idx_regime_unique ON regime_calls(date, pair);
CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_unique ON validation_log(date, pair);
CREATE INDEX IF NOT EXISTS idx_pipeline_errors_date_source ON pipeline_errors(date, source);
CREATE UNIQUE INDEX IF NOT EXISTS idx_brief_log_date ON brief_log(date);

ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE regime_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE brief_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_errors ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public_read_signals" ON signals;
CREATE POLICY "public_read_signals" ON signals FOR SELECT USING (true);
DROP POLICY IF EXISTS "public_read_regime" ON regime_calls;
CREATE POLICY "public_read_regime" ON regime_calls FOR SELECT USING (true);
DROP POLICY IF EXISTS "public_read_validation" ON validation_log;
CREATE POLICY "public_read_validation" ON validation_log FOR SELECT USING (true);
DROP POLICY IF EXISTS "public_read_positions" ON paper_positions;
CREATE POLICY "public_read_positions" ON paper_positions FOR SELECT USING (true);
DROP POLICY IF EXISTS "public_read_brief_log" ON brief_log;
CREATE POLICY "public_read_brief_log" ON brief_log FOR SELECT USING (true);
-- pipeline_errors: no SELECT policy for anon — internal only
