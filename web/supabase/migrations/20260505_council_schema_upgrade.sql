-- FX Regime Lab — Council of Markets Schema Upgrade
-- Date: 2026-05-05
-- Scope: pair_profiles table, regime_calls expansion, validation_log expansion,
--         brief_log expansion, health_checks table

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. PAIR PROFILES — Pair-specific methodology configuration
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS pair_profiles (
    id SERIAL PRIMARY KEY,
    pair VARCHAR(10) NOT NULL UNIQUE,
    display_name VARCHAR(20) NOT NULL,
    rate_weight DECIMAL(3,2) NOT NULL DEFAULT 0.40,
    cot_weight DECIMAL(3,2) NOT NULL DEFAULT 0.25,
    vol_weight DECIMAL(3,2) NOT NULL DEFAULT 0.20,
    oi_weight DECIMAL(3,2) NOT NULL DEFAULT 0.10,
    special_weight DECIMAL(3,2) NOT NULL DEFAULT 0.05,
    special_signal_label VARCHAR(50),
    special_signal_source VARCHAR(100),
    driver_tag VARCHAR(50),
    primary_anchor_market VARCHAR(20),
    regime_thresholds JSONB NOT NULL DEFAULT '{
        "strong_usd_strength": 1.20,
        "moderate_usd_strength": 0.60,
        "neutral_upper": 0.40,
        "neutral_lower": -0.40,
        "moderate_usd_weakness": -0.60,
        "strong_usd_weakness": -1.20
    }'::jsonb,
    confidence_adjustment_rules JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed data for the 3-pair FX basket
INSERT INTO pair_profiles (
    pair, display_name, rate_weight, cot_weight, vol_weight, oi_weight, 
    special_weight, special_signal_label, special_signal_source, driver_tag, 
    primary_anchor_market, confidence_adjustment_rules
) VALUES
('EURUSD', 'EUR/USD', 0.40, 0.25, 0.20, 0.10, 0.05, 
 'ECB_sentiment', 'NLP on ECB speeches', 'Rates-driven', 'London',
 '{"type": "none", "rationale": "Baseline — well-behaved rates cross"}'::jsonb),

('USDJPY', 'USD/JPY', 0.30, 0.20, 0.25, 0.15, 0.10, 
 'JPY_funding_stress', 'USD/JPY 3M cross-currency basis', 'Funding-driven', 'Tokyo',
 '{"type": "additive", "condition": "S_JPY > 0.5", "value": 0.05, 
   "rationale": "Funding stress adds conviction"}'::jsonb),

('USDINR', 'USD/INR', 0.30, 0.10, 0.20, 0.10, 0.30, 
 'EM_carry_RBI', 'Brent + RBI forward book + EM carry index', 'Carry-sensitive', 'Mumbai',
 '{"type": "subtractive", "condition": "Brent > P80", "value": -0.05, 
   "rationale": "Oil shock = model breakdown risk"}'::jsonb)

ON CONFLICT (pair) DO UPDATE SET
    rate_weight = EXCLUDED.rate_weight,
    cot_weight = EXCLUDED.cot_weight,
    vol_weight = EXCLUDED.vol_weight,
    oi_weight = EXCLUDED.oi_weight,
    special_weight = EXCLUDED.special_weight,
    special_signal_label = EXCLUDED.special_signal_label,
    driver_tag = EXCLUDED.driver_tag,
    updated_at = NOW();

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. REGIME CALLS — Expand with pair-specific fields
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE regime_calls 
ADD COLUMN IF NOT EXISTS special_signal_value DECIMAL(8,4),
ADD COLUMN IF NOT EXISTS special_signal_label VARCHAR(50),
ADD COLUMN IF NOT EXISTS model_version VARCHAR(20) DEFAULT '1.0-universal',
ADD COLUMN IF NOT EXISTS data_quality_score DECIMAL(3,2),
ADD COLUMN IF NOT EXISTS stress_level VARCHAR(10);

-- Backfill existing rows
UPDATE regime_calls SET model_version = '1.0-universal' WHERE model_version IS NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. VALIDATION LOG — Expand with alpha accuracy fields
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE validation_log
ADD COLUMN IF NOT EXISTS dxy_return_1d DECIMAL(8,4),
ADD COLUMN IF NOT EXISTS alpha_return_1d DECIMAL(8,4),
ADD COLUMN IF NOT EXISTS max_intraday_adverse_bps DECIMAL(8,2),
ADD COLUMN IF NOT EXISTS vol_regime_at_call VARCHAR(20),
ADD COLUMN IF NOT EXISTS regime_at_call VARCHAR(100);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. BRIEF LOG — Expand for 3 pairs + JSON migration
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE brief_log 
ADD COLUMN IF NOT EXISTS pair_regimes JSONB;

-- Migrate existing hardcoded columns to JSON
UPDATE brief_log 
SET pair_regimes = jsonb_build_object(
    'eurusd', eurusd_regime,
    'usdjpy', usdjpy_regime,
    'usdinr', usdinr_regime
)
WHERE pair_regimes IS NULL 
  AND (eurusd_regime IS NOT NULL OR usdjpy_regime IS NOT NULL OR usdinr_regime IS NOT NULL);

-- Drop expanded-pair columns that are outside the 3-pair lock
ALTER TABLE brief_log
DROP COLUMN IF EXISTS gbpusd_regime,
DROP COLUMN IF EXISTS audusd_regime,
DROP COLUMN IF EXISTS usdcad_regime,
DROP COLUMN IF EXISTS usdchf_regime;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. HEALTH CHECKS — Pipeline monitoring
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS health_checks (
    id SERIAL PRIMARY KEY,
    pipeline_date DATE NOT NULL UNIQUE,
    completed_at TIMESTAMPTZ,
    data_quality_score DECIMAL(3,2),
    stress_level VARCHAR(10),
    pairs_published INTEGER,
    sources_used INTEGER,
    sources_failed INTEGER,
    error_log TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. ROW LEVEL SECURITY — Enable RLS on new tables
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE pair_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE health_checks ENABLE ROW LEVEL SECURITY;

-- Allow public read access (same pattern as existing tables)
CREATE POLICY "Allow public read access" ON pair_profiles
    FOR SELECT USING (true);

CREATE POLICY "Allow public read access" ON health_checks
    FOR SELECT USING (true);

-- Service role can insert/update
CREATE POLICY "Allow service role insert" ON pair_profiles
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Allow service role insert" ON health_checks
    FOR ALL USING (auth.role() = 'service_role');

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. INDEXES — For query performance
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_regime_calls_model_version 
    ON regime_calls(model_version);

CREATE INDEX IF NOT EXISTS idx_regime_calls_stress_level 
    ON regime_calls(stress_level);

CREATE INDEX IF NOT EXISTS idx_validation_log_alpha_return 
    ON validation_log(alpha_return_1d) WHERE alpha_return_1d IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_health_checks_pipeline_date 
    ON health_checks(pipeline_date);
