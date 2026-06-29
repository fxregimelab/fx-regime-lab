-- FX Regime Lab V2 Schema Migration
-- Run this in Supabase Dashboard SQL Editor
-- Date: 2026-05-20

-- ============================================================
-- Step 1: Add strategy_version and data_source to regime_calls
-- ============================================================
ALTER TABLE regime_calls 
    ADD COLUMN IF NOT EXISTS strategy_version VARCHAR(10) DEFAULT 'v2',
    ADD COLUMN IF NOT EXISTS data_source VARCHAR(20) DEFAULT 'live';

CREATE INDEX IF NOT EXISTS idx_regime_calls_version 
    ON regime_calls(pair, strategy_version, date DESC);

-- Backfill existing data (temporarily disable immutability trigger)
ALTER TABLE regime_calls DISABLE TRIGGER trg_protect_immutable_calls;

UPDATE regime_calls SET strategy_version = 'v2' WHERE strategy_version IS NULL;
UPDATE regime_calls SET data_source = 'backtest' WHERE date < '2026-05-01' AND data_source = 'live';
UPDATE regime_calls SET data_source = 'live' WHERE date >= '2026-05-01' AND data_source = 'live';

ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls;

-- ============================================================
-- Step 2: Create call_rationale table
-- ============================================================
CREATE TABLE IF NOT EXISTS call_rationale (
    id SERIAL PRIMARY KEY,
    call_id INTEGER NOT NULL REFERENCES regime_calls(id),
    date DATE NOT NULL,
    pair VARCHAR(10) NOT NULL,
    layer1_reasoning TEXT,
    layer2_reasoning TEXT,
    layer3_reasoning TEXT,
    primary_driver_detail TEXT,
    confidence_explanation TEXT,
    contrarian_flags TEXT[],
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_call_rationale_call_id UNIQUE (call_id)
);

CREATE INDEX IF NOT EXISTS idx_call_rationale_call_id ON call_rationale(call_id);
CREATE INDEX IF NOT EXISTS idx_call_rationale_date_pair ON call_rationale(date, pair);

-- ============================================================
-- Step 3: Create simulation_results table
-- ============================================================
CREATE TABLE IF NOT EXISTS simulation_results (
    id SERIAL PRIMARY KEY,
    strategy_version VARCHAR(10) NOT NULL,
    simulation_params JSONB NOT NULL,
    pair VARCHAR(10),
    date DATE NOT NULL,
    starting_capital DECIMAL(12,2),
    position_size DECIMAL(12,4),
    predicted_direction VARCHAR(10),
    actual_return_bps DECIMAL(10,4),
    pnl DECIMAL(12,4),
    cumulative_pnl DECIMAL(12,4),
    cumulative_return_pct DECIMAL(10,4),
    max_drawdown_pct DECIMAL(10,4),
    sharpe_30d DECIMAL(10,4),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sim_version_pair_date ON simulation_results(strategy_version, pair, date);

-- ============================================================
-- Step 4: Create backtest_versions metadata table
-- ============================================================
CREATE TABLE IF NOT EXISTS backtest_versions (
    version VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100),
    description TEXT,
    date_range_start DATE,
    date_range_end DATE,
    total_calls INTEGER,
    is_public BOOLEAN DEFAULT false,
    methodology_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO backtest_versions (version, name, description, date_range_start, date_range_end, total_calls, is_public, methodology_summary)
VALUES 
    ('v0', 'Prototype', 'Static-weight heuristic with rate differentials only. No COT, no vol gate. EUR/USD only. Reconstructed simulation.', '1997-01-30', '2003-11-30', 1800, true, 'Static weights: 100% rate differential z-score. Threshold-based labeling.'),
    ('v1', 'Multi-Signal Alpha', 'Added COT positioning and realized volatility. Expanded to USD/JPY. No cross-asset confirmation. Reconstructed simulation.', '2003-12-01', '2019-12-31', 4200, true, 'Weights: rates 50%, COT 30%, vol 20%. Pair-specific thresholds.'),
    ('v2', 'M.3 Regime Engine', 'Full three-layer architecture with dynamic betas, IV gate, RR modifier, OI alignment, cross-asset confirmation. All three pairs. Walk-forward simulation.', '1997-01-30', '2026-04-30', 19114, true, 'Eight signal families, pair-specific weights, causal windows only, walk-forward simulation.')
ON CONFLICT (version) DO UPDATE SET 
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    date_range_start = EXCLUDED.date_range_start,
    date_range_end = EXCLUDED.date_range_end,
    total_calls = EXCLUDED.total_calls,
    is_public = EXCLUDED.is_public,
    methodology_summary = EXCLUDED.methodology_summary;

-- ============================================================
-- Step 5: Update RLS policies
-- ============================================================
ALTER TABLE call_rationale ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulation_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_versions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS public_read_call_rationale ON call_rationale;
CREATE POLICY public_read_call_rationale ON call_rationale
    FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS public_read_simulation ON simulation_results;
CREATE POLICY public_read_simulation ON simulation_results
    FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS public_read_versions ON backtest_versions;
CREATE POLICY public_read_versions ON backtest_versions
    FOR SELECT TO anon USING (true);

-- ============================================================
-- Step 6: Update validation_log to add predicted_regime and validation_date
-- ============================================================
ALTER TABLE validation_log 
    ADD COLUMN IF NOT EXISTS predicted_regime VARCHAR(30),
    ADD COLUMN IF NOT EXISTS validation_date DATE;

-- ============================================================
-- Verification Queries (run these after applying)
-- ============================================================
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'regime_calls' AND column_name IN ('strategy_version', 'data_source');
-- SELECT strategy_version, data_source, COUNT(*) FROM regime_calls GROUP BY strategy_version, data_source;
-- SELECT * FROM backtest_versions ORDER BY version;
-- SELECT COUNT(*) FROM call_rationale;
-- SELECT COUNT(*) FROM simulation_results;
