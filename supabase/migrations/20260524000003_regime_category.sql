-- FX Regime Lab V3 — Regime categorization for UI filtering and visualization

ALTER TABLE regime_calls 
ADD COLUMN IF NOT EXISTS regime_category TEXT 
CHECK (regime_category IN ('RATE_DRIVEN', 'CARRY_DRIVEN', 'VOLATILITY_DRIVEN', 'POLICY_SHOCK', 'LIQUIDITY_SHOCK', 'NEUTRAL'));

-- Backfill: Update existing rows based on regime name patterns
-- Temporarily disable immutability trigger for backfill
ALTER TABLE regime_calls DISABLE TRIGGER trg_protect_immutable_calls;

UPDATE regime_calls 
SET regime_category = CASE
  WHEN regime LIKE '%CARRY%' OR regime LIKE '%UNWIND%' OR regime LIKE '%COLLAPSE%' THEN 'CARRY_DRIVEN'
  WHEN regime LIKE '%VOL%' OR regime LIKE '%VOLATILITY%' THEN 'VOLATILITY_DRIVEN'
  WHEN regime LIKE '%POLICY%' OR regime LIKE '%BREAKOUT%' THEN 'POLICY_SHOCK'
  WHEN regime LIKE '%LIQUIDITY%' OR regime LIKE '%SHOCK%' THEN 'LIQUIDITY_SHOCK'
  WHEN regime LIKE '%NEUTRAL%' THEN 'NEUTRAL'
  ELSE 'RATE_DRIVEN'
END
WHERE regime_category IS NULL;

-- Re-enable immutability trigger
ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls;

-- Create index for fast UI filtering
CREATE INDEX IF NOT EXISTS idx_regime_calls_category
  ON regime_calls (regime_category, pair, date DESC);
