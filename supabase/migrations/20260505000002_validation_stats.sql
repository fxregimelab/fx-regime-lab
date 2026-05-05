-- Round 3 Phase 2 — Aggregate validation statistics table

CREATE TABLE IF NOT EXISTS validation_stats (
  id SERIAL PRIMARY KEY,
  as_of_date DATE NOT NULL,
  pair VARCHAR(10) NOT NULL,
  computed_at DATE NOT NULL DEFAULT CURRENT_DATE,

  -- T+5 metrics
  t5_total_calls INT DEFAULT 0,
  t5_directional_calls INT DEFAULT 0,
  t5_wins INT DEFAULT 0,
  t5_win_rate FLOAT,
  t5_mean_brier FLOAT,
  t5_brier_skill FLOAT,
  t5_mean_log_return_bps FLOAT,
  t5_return_std_bps FLOAT,
  t5_sharpe_like FLOAT,
  t5_max_drawdown_bps FLOAT,
  t5_calibration_json JSONB,

  -- T+20 metrics
  t20_total_calls INT DEFAULT 0,
  t20_directional_calls INT DEFAULT 0,
  t20_wins INT DEFAULT 0,
  t20_win_rate FLOAT,
  t20_mean_brier FLOAT,
  t20_brier_skill FLOAT,
  t20_mean_log_return_bps FLOAT,
  t20_return_std_bps FLOAT,
  t20_sharpe_like FLOAT,
  t20_max_drawdown_bps FLOAT,
  t20_calibration_json JSONB,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_stats_as_of_pair
  ON validation_stats (as_of_date, pair);

CREATE INDEX IF NOT EXISTS idx_validation_stats_pair
  ON validation_stats (pair, as_of_date DESC);

ALTER TABLE validation_stats ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public_read_validation_stats" ON validation_stats;
CREATE POLICY "public_read_validation_stats" ON validation_stats FOR SELECT USING (true);
