-- Add missing regime_calls columns required by RegimeCall dataclass

ALTER TABLE regime_calls
  ADD COLUMN IF NOT EXISTS data_quality_score DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS stress_level TEXT,
  ADD COLUMN IF NOT EXISTS predicted_direction TEXT,
  ADD COLUMN IF NOT EXISTS cot_signal TEXT,
  ADD COLUMN IF NOT EXISTS vol_signal TEXT,
  ADD COLUMN IF NOT EXISTS oi_signal TEXT,
  ADD COLUMN IF NOT EXISTS rr_signal TEXT,
  ADD COLUMN IF NOT EXISTS special_signal_value DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS special_signal_label TEXT,
  ADD COLUMN IF NOT EXISTS model_version TEXT;
