-- FX Regime Lab — Canonical Schema (auto-generated from migrations)
-- DO NOT EDIT DIRECTLY. Add changes via timestamped migrations in supabase/migrations/


-- === supabase/migrations/20260401000001_initial_schema.sql ===
-- Migration: initial_schema (Phase 3)

CREATE TABLE IF NOT EXISTS regime_calls (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  pair             TEXT        NOT NULL,
  date             DATE        NOT NULL,
  regime           TEXT        NOT NULL,
  confidence       FLOAT       NOT NULL,
  signal_composite FLOAT       NOT NULL,
  rate_signal      TEXT        NOT NULL,
  primary_driver   TEXT,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, date)
);

CREATE TABLE IF NOT EXISTS signals (
  id               UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
  pair             TEXT  NOT NULL,
  date             DATE  NOT NULL,
  rate_diff_2y     FLOAT,
  cot_percentile   FLOAT,
  realized_vol_20d FLOAT,
  realized_vol_5d  FLOAT,
  implied_vol_30d  FLOAT,
  spot             FLOAT,
  day_change       FLOAT,
  day_change_pct   FLOAT,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, date)
);

CREATE TABLE IF NOT EXISTS validation_log (
  id         UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
  date       DATE  NOT NULL,
  pair       TEXT  NOT NULL,
  call       TEXT  NOT NULL,
  outcome    TEXT  NOT NULL CHECK (outcome IN ('correct', 'incorrect')),
  return_pct FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, date)
);

CREATE TABLE IF NOT EXISTS brief (
  id             UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
  date           DATE  NOT NULL,
  pair           TEXT  NOT NULL,
  regime         TEXT  NOT NULL,
  confidence     FLOAT NOT NULL,
  composite      FLOAT NOT NULL,
  analysis       TEXT  NOT NULL,
  primary_driver TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, date)
);

CREATE TABLE IF NOT EXISTS macro_events (
  id         UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  date       DATE    NOT NULL,
  event      TEXT    NOT NULL,
  impact     TEXT    NOT NULL CHECK (impact IN ('HIGH', 'MEDIUM', 'LOW')),
  pairs      TEXT[]  NOT NULL DEFAULT '{}',
  category   TEXT,
  ai_brief   TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (date, event)
);

CREATE TABLE IF NOT EXISTS ai_usage_log (
  id            UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  date          DATE    NOT NULL,
  request_count INTEGER NOT NULL DEFAULT 1,
  purpose       TEXT,
  model         TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- === supabase/migrations/20260401000002_rls_policies.sql ===
-- Migration: RLS policies (Phase 3)

ALTER TABLE regime_calls   ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals         ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_log  ENABLE ROW LEVEL SECURITY;
ALTER TABLE brief           ENABLE ROW LEVEL SECURITY;
ALTER TABLE macro_events    ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_usage_log    ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_regime_calls" ON regime_calls  FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_signals"      ON signals        FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_validation"   ON validation_log FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_brief"        ON brief          FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_macro_events" ON macro_events   FOR SELECT TO anon USING (true);

-- === supabase/migrations/20260401000003_indexes.sql ===
-- Migration: indexes (Phase 3)

CREATE INDEX IF NOT EXISTS idx_regime_calls_pair_date ON regime_calls  (pair, date DESC);
CREATE INDEX IF NOT EXISTS idx_signals_pair_date      ON signals        (pair, date DESC);
CREATE INDEX IF NOT EXISTS idx_validation_pair_date   ON validation_log (pair, date DESC);
CREATE INDEX IF NOT EXISTS idx_macro_events_date      ON macro_events   (date, impact);
CREATE INDEX IF NOT EXISTS idx_brief_pair_date        ON brief          (pair, date DESC);

-- === supabase/migrations/20260404154618_remote_schema.sql ===

-- === supabase/migrations/20260426000001_phase3_new_tables.sql ===
-- Phase 3: new tables (brief, macro_events, ai_usage_log)
-- regime_calls / signals / validation_log already exist from prior schema

CREATE TABLE IF NOT EXISTS brief (
  id             UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
  date           DATE  NOT NULL,
  pair           TEXT  NOT NULL,
  regime         TEXT  NOT NULL,
  confidence     FLOAT NOT NULL,
  composite      FLOAT NOT NULL,
  analysis       TEXT  NOT NULL,
  primary_driver TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, date)
);

CREATE TABLE IF NOT EXISTS macro_events (
  id         UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  date       DATE    NOT NULL,
  event      TEXT    NOT NULL,
  impact     TEXT    NOT NULL CHECK (impact IN ('HIGH', 'MEDIUM', 'LOW')),
  pairs      TEXT[]  NOT NULL DEFAULT '{}',
  category   TEXT,
  ai_brief   TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (date, event)
);

CREATE TABLE IF NOT EXISTS ai_usage_log (
  id            UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  date          DATE    NOT NULL,
  request_count INTEGER NOT NULL DEFAULT 1,
  purpose       TEXT,
  model         TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE brief          ENABLE ROW LEVEL SECURITY;
ALTER TABLE macro_events   ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_usage_log   ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_brief"        ON brief        FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_macro_events" ON macro_events FOR SELECT TO anon USING (true);
-- ai_usage_log: no anon access (service role only)

-- Indexes
CREATE INDEX IF NOT EXISTS idx_brief_pair_date       ON brief        (pair, date DESC);
CREATE INDEX IF NOT EXISTS idx_macro_events_date     ON macro_events (date, impact);

-- === supabase/migrations/20260427205525_remote_alignment.sql ===
-- Alignment: version recorded on linked remote before this repository contained a matching file.
-- No-op to keep migration history consistent with supabase migration repair / db push workflows.
SELECT 1;

-- === supabase/migrations/20260428000001_hardening.sql ===
-- Hardening: Revoke public/authenticated access to sensitive log tables
-- These should only be accessible via service_role (pipeline)

-- 1. ai_usage_log
ALTER TABLE ai_usage_log DISABLE ROW LEVEL SECURITY; -- Or keep enabled but with no policies
REVOKE ALL ON ai_usage_log FROM anon, authenticated;
GRANT ALL ON ai_usage_log TO service_role;

-- 2. pipeline_errors (if it exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'pipeline_errors') THEN
        REVOKE ALL ON pipeline_errors FROM anon, authenticated;
        GRANT ALL ON pipeline_errors TO service_role;
    END IF;
END $$;

-- 3. Ensure RLS is active and clean on public tables
ALTER TABLE brief_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_brief_log" ON brief_log;
CREATE POLICY "anon_read_brief_log" ON brief_log FOR SELECT TO anon USING (true);

-- Validation log is public for transparency
ALTER TABLE validation_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_validation" ON validation_log;
CREATE POLICY "anon_read_validation" ON validation_log FOR SELECT TO anon USING (true);

-- === supabase/migrations/20260428000002_add_cross_asset_us10y.sql ===
-- Add raw US 10Y yield to signals for frontend pulse bar.
ALTER TABLE signals
ADD COLUMN IF NOT EXISTS cross_asset_us10y DOUBLE PRECISION;

-- === supabase/migrations/20260428000003_historical_data.sql ===
-- Deep history and analog research infrastructure.

CREATE TABLE IF NOT EXISTS historical_prices (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date       DATE NOT NULL,
  pair       TEXT NOT NULL,
  open       DOUBLE PRECISION,
  high       DOUBLE PRECISION,
  low        DOUBLE PRECISION,
  close      DOUBLE PRECISION,
  volume     DOUBLE PRECISION,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, date)
);

CREATE TABLE IF NOT EXISTS research_analogs (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  as_of_date            DATE NOT NULL,
  pair                  TEXT NOT NULL,
  rank                  INTEGER NOT NULL CHECK (rank BETWEEN 1 AND 3),
  match_date            DATE NOT NULL,
  match_score           DOUBLE PRECISION NOT NULL,
  forward_30d_return    DOUBLE PRECISION,
  regime_stability      DOUBLE PRECISION,
  context_label         TEXT,
  current_trend_5d      DOUBLE PRECISION,
  matched_trend_5d      DOUBLE PRECISION,
  current_composite     DOUBLE PRECISION,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, as_of_date, rank)
);

CREATE INDEX IF NOT EXISTS idx_historical_prices_pair_date
  ON historical_prices (pair, date DESC);

CREATE INDEX IF NOT EXISTS idx_research_analogs_pair_asof
  ON research_analogs (pair, as_of_date DESC);

ALTER TABLE historical_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_analogs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_historical_prices" ON historical_prices;
CREATE POLICY "anon_read_historical_prices"
  ON historical_prices
  FOR SELECT
  TO anon
  USING (true);

DROP POLICY IF EXISTS "anon_read_research_analogs" ON research_analogs;
CREATE POLICY "anon_read_research_analogs"
  ON research_analogs
  FOR SELECT
  TO anon
  USING (true);

-- === supabase/migrations/20260428000004_desk_cards_and_security.sql ===
CREATE TABLE IF NOT EXISTS desk_open_cards (
    date DATE NOT NULL,
    pair TEXT NOT NULL,
    structural_regime TEXT NOT NULL,
    dominance_array JSONB,
    pain_index FLOAT,
    markov_probabilities JSONB,
    ai_brief TEXT,
    telemetry_audit JSONB,
    invalidation_triggered BOOLEAN DEFAULT false,
    telemetry_status TEXT DEFAULT 'ONLINE',
    UNIQUE (pair, date)
);

ALTER TABLE desk_open_cards ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_deny_insert_signals" ON signals;
CREATE POLICY "anon_deny_insert_signals"
ON signals
FOR INSERT
TO anon
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_signals" ON signals;
CREATE POLICY "anon_deny_update_signals"
ON signals
FOR UPDATE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_delete_signals" ON signals;
CREATE POLICY "anon_deny_delete_signals"
ON signals
FOR DELETE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_insert_regime_calls" ON regime_calls;
CREATE POLICY "anon_deny_insert_regime_calls"
ON regime_calls
FOR INSERT
TO anon
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_regime_calls" ON regime_calls;
CREATE POLICY "anon_deny_update_regime_calls"
ON regime_calls
FOR UPDATE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_delete_regime_calls" ON regime_calls;
CREATE POLICY "anon_deny_delete_regime_calls"
ON regime_calls
FOR DELETE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_insert_brief" ON brief;
CREATE POLICY "anon_deny_insert_brief"
ON brief
FOR INSERT
TO anon
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_brief" ON brief;
CREATE POLICY "anon_deny_update_brief"
ON brief
FOR UPDATE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_delete_brief" ON brief;
CREATE POLICY "anon_deny_delete_brief"
ON brief
FOR DELETE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_insert_macro_events" ON macro_events;
CREATE POLICY "anon_deny_insert_macro_events"
ON macro_events
FOR INSERT
TO anon
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_macro_events" ON macro_events;
CREATE POLICY "anon_deny_update_macro_events"
ON macro_events
FOR UPDATE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_delete_macro_events" ON macro_events;
CREATE POLICY "anon_deny_delete_macro_events"
ON macro_events
FOR DELETE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_insert_historical_prices" ON historical_prices;
CREATE POLICY "anon_deny_insert_historical_prices"
ON historical_prices
FOR INSERT
TO anon
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_historical_prices" ON historical_prices;
CREATE POLICY "anon_deny_update_historical_prices"
ON historical_prices
FOR UPDATE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_delete_historical_prices" ON historical_prices;
CREATE POLICY "anon_deny_delete_historical_prices"
ON historical_prices
FOR DELETE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_insert_research_analogs" ON research_analogs;
CREATE POLICY "anon_deny_insert_research_analogs"
ON research_analogs
FOR INSERT
TO anon
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_research_analogs" ON research_analogs;
CREATE POLICY "anon_deny_update_research_analogs"
ON research_analogs
FOR UPDATE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_delete_research_analogs" ON research_analogs;
CREATE POLICY "anon_deny_delete_research_analogs"
ON research_analogs
FOR DELETE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_insert_desk_open_cards" ON desk_open_cards;
CREATE POLICY "anon_deny_insert_desk_open_cards"
ON desk_open_cards
FOR INSERT
TO anon
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_desk_open_cards" ON desk_open_cards;
CREATE POLICY "anon_deny_update_desk_open_cards"
ON desk_open_cards
FOR UPDATE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_delete_desk_open_cards" ON desk_open_cards;
CREATE POLICY "anon_deny_delete_desk_open_cards"
ON desk_open_cards
FOR DELETE
TO anon
USING (false);

-- === supabase/migrations/20260428000005_event_risk_schema.sql ===
-- Phase 2.1: historical macro consensus vs actual (event risk foundation)

CREATE TABLE IF NOT EXISTS historical_macro_surprises (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name          TEXT NOT NULL,
    date                DATE NOT NULL,
    time                TEXT,
    actual              DOUBLE PRECISION,
    consensus           DOUBLE PRECISION,
    previous            DOUBLE PRECISION,
    surprise_bps        DOUBLE PRECISION,
    surprise_direction  TEXT NOT NULL CHECK (surprise_direction IN ('BEAT', 'MISS', 'IN-LINE')),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (event_name, date)
);

ALTER TABLE historical_macro_surprises ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_historical_macro_surprises" ON historical_macro_surprises;
CREATE POLICY "anon_read_historical_macro_surprises"
ON historical_macro_surprises
FOR SELECT
TO anon
USING (true);

DROP POLICY IF EXISTS "anon_deny_insert_historical_macro_surprises" ON historical_macro_surprises;
CREATE POLICY "anon_deny_insert_historical_macro_surprises"
ON historical_macro_surprises
FOR INSERT
TO anon
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_historical_macro_surprises" ON historical_macro_surprises;
CREATE POLICY "anon_deny_update_historical_macro_surprises"
ON historical_macro_surprises
FOR UPDATE
TO anon
USING (false);

DROP POLICY IF EXISTS "anon_deny_delete_historical_macro_surprises" ON historical_macro_surprises;
CREATE POLICY "anon_deny_delete_historical_macro_surprises"
ON historical_macro_surprises
FOR DELETE
TO anon
USING (false);

CREATE INDEX IF NOT EXISTS idx_historical_macro_surprises_date
ON historical_macro_surprises (date);

CREATE INDEX IF NOT EXISTS idx_historical_macro_surprises_event_name
ON historical_macro_surprises (event_name);

-- === supabase/migrations/20260428000006_event_risk_matrices.sql ===
-- Phase 2.2: pre-computed regime-conditioned event risk matrices

CREATE TABLE IF NOT EXISTS event_risk_matrices (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date                   DATE NOT NULL,
    pair                   TEXT NOT NULL,
    event_name             TEXT NOT NULL,
    active_regime          TEXT NOT NULL,
    sample_size            INT NOT NULL,
    median_mie_multiplier  DOUBLE PRECISION,
    beat_median_return     DOUBLE PRECISION,
    miss_median_return     DOUBLE PRECISION,
    asymmetry_ratio        DOUBLE PRECISION,
    asymmetry_direction    TEXT,
    ai_context             TEXT,
    created_at             TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date, pair, event_name)
);

ALTER TABLE event_risk_matrices ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_event_risk_matrices" ON event_risk_matrices;
CREATE POLICY "anon_read_event_risk_matrices"
ON event_risk_matrices
FOR SELECT
TO anon
USING (true);

DROP POLICY IF EXISTS "anon_deny_insert_event_risk_matrices" ON event_risk_matrices;
CREATE POLICY "anon_deny_insert_event_risk_matrices"
ON event_risk_matrices
FOR INSERT
TO anon
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_update_event_risk_matrices" ON event_risk_matrices;
CREATE POLICY "anon_deny_update_event_risk_matrices"
ON event_risk_matrices
FOR UPDATE
TO anon
USING (false)
WITH CHECK (false);

DROP POLICY IF EXISTS "anon_deny_delete_event_risk_matrices" ON event_risk_matrices;
CREATE POLICY "anon_deny_delete_event_risk_matrices"
ON event_risk_matrices
FOR DELETE
TO anon
USING (false);

CREATE INDEX IF NOT EXISTS idx_event_risk_matrices_date
ON event_risk_matrices (date);

CREATE INDEX IF NOT EXISTS idx_event_risk_matrices_pair_event
ON event_risk_matrices (pair, event_name);

-- === supabase/migrations/20260428000007_strategy_ledger.sql ===
CREATE TABLE IF NOT EXISTS strategy_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    pair TEXT NOT NULL,
    regime TEXT NOT NULL,
    primary_driver TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_close DOUBLE PRECISION,
    confidence DOUBLE PRECISION,
    t1_close DOUBLE PRECISION,
    t3_close DOUBLE PRECISION,
    t5_close DOUBLE PRECISION,
    t1_hit INT,
    t3_hit INT,
    t5_hit INT,
    brier_score_t5 DOUBLE PRECISION,
    UNIQUE (date, pair, regime, primary_driver)
);

ALTER TABLE strategy_ledger ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anonymous read access on strategy_ledger" ON strategy_ledger;
CREATE POLICY "Allow anonymous read access on strategy_ledger"
    ON strategy_ledger FOR SELECT
    TO anon
    USING (true);

DROP POLICY IF EXISTS "Deny anonymous insert access on strategy_ledger" ON strategy_ledger;
CREATE POLICY "Deny anonymous insert access on strategy_ledger"
    ON strategy_ledger FOR INSERT
    TO anon
    WITH CHECK (false);

DROP POLICY IF EXISTS "Deny anonymous update access on strategy_ledger" ON strategy_ledger;
CREATE POLICY "Deny anonymous update access on strategy_ledger"
    ON strategy_ledger FOR UPDATE
    TO anon
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS "Deny anonymous delete access on strategy_ledger" ON strategy_ledger;
CREATE POLICY "Deny anonymous delete access on strategy_ledger"
    ON strategy_ledger FOR DELETE
    TO anon
    USING (false);

CREATE INDEX IF NOT EXISTS strategy_ledger_date_idx ON strategy_ledger (date);
CREATE INDEX IF NOT EXISTS strategy_ledger_pair_idx ON strategy_ledger (pair);

-- === supabase/migrations/20260428000008_analog_rpc.sql ===
-- Server-side historical analog matching (avoids loading deep history into Python).

CREATE OR REPLACE FUNCTION public.match_historical_analogs(
  target_pair text,
  as_of_date date,
  current_trend double precision,
  current_comp double precision,
  limit_rows integer DEFAULT 3
)
RETURNS TABLE (
  rank integer,
  match_date date,
  match_score double precision,
  forward_30d_return double precision,
  regime_stability double precision,
  context_label text,
  current_trend_5d double precision,
  matched_trend_5d double precision,
  current_composite double precision
)
LANGUAGE sql
STABLE
AS $function$
WITH ordered AS (
  SELECT
    hp.date AS d,
    hp.close AS c,
    LAG(hp.close, 5) OVER (ORDER BY hp.date) AS c_lag5,
    LEAD(hp.close, 30) OVER (ORDER BY hp.date) AS c_lead30
  FROM historical_prices hp
  WHERE hp.pair = target_pair
    AND hp.date < as_of_date
    AND hp.close IS NOT NULL
    AND hp.close > 0
),
candidates AS (
  SELECT
    o.d AS match_date,
    o.c,
    o.c_lag5,
    o.c_lead30,
    CASE
      WHEN o.c_lag5 IS NOT NULL AND o.c_lag5 > 0 THEN ((o.c / o.c_lag5) - 1.0) * 100.0
    END AS matched_trend_5d
  FROM ordered o
),
scored AS (
  SELECT
    cnd.match_date,
    cnd.matched_trend_5d,
    cnd.c,
    cnd.c_lead30,
    LEAST(2.0::double precision, GREATEST(-2.0::double precision, cnd.matched_trend_5d / 2.0))
      AS hist_comp_proxy,
    ABS(cnd.matched_trend_5d - current_trend) AS trend_dist,
    ABS(
      LEAST(2.0::double precision, GREATEST(-2.0::double precision, cnd.matched_trend_5d / 2.0))
      - current_comp
    ) AS comp_dist
  FROM candidates cnd
  WHERE cnd.matched_trend_5d IS NOT NULL
    AND cnd.c_lead30 IS NOT NULL
),
ranked AS (
  SELECT
    sc.match_date,
    sc.matched_trend_5d,
    current_trend,
    current_comp,
    (1.0 / (1.0 + (sc.trend_dist / 2.0))) AS trend_sim,
    (1.0 / (1.0 + (sc.comp_dist / 1.5))) AS comp_sim,
    (sc.trend_dist + sc.comp_dist) AS total_dist,
    ((sc.c_lead30 / sc.c) - 1.0) * 100.0 AS forward_30d_return,
    CASE
      WHEN EXTRACT(YEAR FROM sc.match_date)::integer <= 2009 THEN 'Post-GFC'
      WHEN EXTRACT(YEAR FROM sc.match_date)::integer <= 2016 THEN 'QE Divergence'
      WHEN EXTRACT(YEAR FROM sc.match_date)::integer <= 2020 THEN 'Late-Cycle / Election'
      WHEN EXTRACT(YEAR FROM sc.match_date)::integer <= 2022 THEN 'Pandemic / Shock'
      ELSE 'Tightening Cycle'
    END AS ctx_lbl
  FROM scored sc
),
topn AS (
  SELECT
    ROW_NUMBER() OVER (ORDER BY rnk.total_dist ASC, rnk.match_date DESC) AS rk,
    rnk.match_date,
    (100.0 * (0.75 * rnk.trend_sim + 0.25 * rnk.comp_sim)) AS ms,
    rnk.forward_30d_return,
    NULL::double precision AS stab,
    rnk.ctx_lbl,
    rnk.current_trend,
    rnk.matched_trend_5d,
    rnk.current_comp
  FROM ranked rnk
)
SELECT
  t.rk::integer,
  t.match_date,
  t.ms,
  t.forward_30d_return,
  t.stab,
  t.ctx_lbl,
  t.current_trend,
  t.matched_trend_5d,
  t.current_comp
FROM topn t
WHERE t.rk <= limit_rows
ORDER BY t.rk;
$function$;

GRANT EXECUTE ON FUNCTION public.match_historical_analogs(text, date, double precision, double precision, integer)
  TO service_role;
GRANT EXECUTE ON FUNCTION public.match_historical_analogs(text, date, double precision, double precision, integer)
  TO authenticated;

-- === supabase/migrations/20260428000009_add_commodity_signals.sql ===
-- Cross-asset expansion: commodities + EU equity index proxies on signals.

ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS cross_asset_gold DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS cross_asset_copper DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS cross_asset_stoxx DOUBLE PRECISION;

-- === supabase/migrations/20260428000010_structural_instability.sql ===
-- Structural instability flag (rate carry scale: 1y MAD vs 5y MAD)
ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS structural_instability BOOLEAN NOT NULL DEFAULT false;

-- === supabase/migrations/20260428000011_add_ranking_to_desk.sql ===
-- Cross-sectional apex ranking on desk_open_cards
ALTER TABLE desk_open_cards
  ADD COLUMN IF NOT EXISTS global_rank INT,
  ADD COLUMN IF NOT EXISTS apex_score DOUBLE PRECISION;

-- Pairwise return correlations for G10 cluster detection (JSON: { "EURUSD": { "USDJPY": 0.85, ... }, ... })
CREATE OR REPLACE FUNCTION public.get_g10_correlation_matrix()
RETURNS jsonb
LANGUAGE sql
STABLE
AS $sql$
WITH bounds AS (
  SELECT COALESCE(MAX(date), CURRENT_DATE) AS dmax
  FROM historical_prices
),
r AS (
  SELECT
    p.pair,
    p.date,
    CASE
      WHEN lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date) IS NOT NULL
        AND lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date) > 0
      THEN LN(p.close / lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date))
      ELSE NULL
    END AS lr
  FROM historical_prices p
  CROSS JOIN bounds b
  WHERE p.pair IN (
    'EURUSD', 'USDJPY', 'USDINR', 'GBPUSD', 'AUDUSD', 'USDCAD', 'USDCHF'
  )
    AND p.date >= (b.dmax - INTERVAL '120 days')::date
),
cp AS (
  SELECT
    a.pair AS pa,
    b.pair AS pb,
    corr(a.lr, b.lr) AS c
  FROM r a
  INNER JOIN r b ON a.date = b.date AND a.pair < b.pair
  WHERE a.lr IS NOT NULL AND b.lr IS NOT NULL
  GROUP BY a.pair, b.pair
),
agg AS (
  SELECT pa, jsonb_object_agg(pb, c) AS obj
  FROM cp
  WHERE c IS NOT NULL
  GROUP BY pa
)
SELECT COALESCE(jsonb_object_agg(pa, obj), '{}'::jsonb) FROM agg;
$sql$;

GRANT EXECUTE ON FUNCTION public.get_g10_correlation_matrix() TO anon, authenticated, service_role;

-- === supabase/migrations/20260428000012_universe_table.sql ===
-- Single source of truth for pipeline + web pair registry (replaces static JSON in production).

CREATE TABLE IF NOT EXISTS public.universe (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pair         TEXT NOT NULL UNIQUE,
  class        TEXT NOT NULL,
  spot_ticker  TEXT,
  yield_base   TEXT,
  yield_quote  TEXT,
  cot_ticker   TEXT
);

ALTER TABLE public.universe ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "universe_select_anon" ON public.universe;
CREATE POLICY "universe_select_anon"
  ON public.universe
  FOR SELECT
  TO anon, authenticated
  USING (true);

INSERT INTO public.universe (pair, class, spot_ticker, yield_base, yield_quote, cot_ticker)
VALUES
  ('EURUSD', 'FX', 'EURUSD=X', 'DGS2', 'ECB_RATE', '099741'),
  ('USDJPY', 'FX', 'JPY=X', 'DGS2', 'IRLTLT01JPM156N', '097741'),
  ('USDINR', 'FX', 'INR=X', 'DGS2', 'IN2YT=RR', NULL),
  ('GBPUSD', 'FX', 'GBPUSD=X', 'DGS2', 'GB2YT=RR', '096742'),
  ('AUDUSD', 'FX', 'AUDUSD=X', 'DGS2', 'AU2YT=RR', '232741'),
  ('USDCAD', 'FX', 'CAD=X', 'DGS2', 'CA2YT=RR', '090741'),
  ('USDCHF', 'FX', 'CHF=X', 'DGS2', 'CH2YT=RR', '092741')
ON CONFLICT (pair) DO UPDATE SET
  class = EXCLUDED.class,
  spot_ticker = EXCLUDED.spot_ticker,
  yield_base = EXCLUDED.yield_base,
  yield_quote = EXCLUDED.yield_quote,
  cot_ticker = EXCLUDED.cot_ticker;

-- === supabase/migrations/20260428000013_desk_regime_age_chart_thin.sql ===
-- Regime streak on desk cards + server-side MAX chart thinning (weekly outside 2Y window).

ALTER TABLE public.desk_open_cards
  ADD COLUMN IF NOT EXISTS regime_age INTEGER;

COMMENT ON COLUMN public.desk_open_cards.regime_age IS
  'Consecutive trading days (incl. as-of) the structural regime label has matched, vol-expanding suffix ignored.';

CREATE OR REPLACE FUNCTION public.historical_prices_for_max_chart(
  p_pair text,
  p_cutoff date
)
RETURNS TABLE (
  date date,
  pair text,
  open double precision,
  high double precision,
  low double precision,
  close double precision,
  volume double precision,
  created_at timestamptz
)
LANGUAGE sql
STABLE
AS $function$
  SELECT
    hp.date,
    hp.pair,
    hp.open,
    hp.high,
    hp.low,
    hp.close,
    hp.volume,
    hp.created_at
  FROM public.historical_prices hp
  WHERE hp.pair = p_pair
    AND (
      hp.date >= p_cutoff
      OR (
        hp.date < p_cutoff
        AND EXTRACT(ISODOW FROM hp.date) = 5
      )
    )
  ORDER BY hp.date ASC;
$function$;

GRANT EXECUTE ON FUNCTION public.historical_prices_for_max_chart(text, date)
  TO anon, authenticated, service_role;

-- === supabase/migrations/20260428000014_macro_aliases.sql ===
-- Semantic alias map: normalize varying release labels to canonical calendar keys.

CREATE TABLE IF NOT EXISTS public.event_aliases (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name  TEXT NOT NULL,
  alias_name      TEXT NOT NULL UNIQUE
);

ALTER TABLE public.event_aliases ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "event_aliases_select_anon" ON public.event_aliases;
CREATE POLICY "event_aliases_select_anon"
  ON public.event_aliases
  FOR SELECT
  TO anon, authenticated
  USING (true);

INSERT INTO public.event_aliases (canonical_name, alias_name) VALUES
  ('US Non-Farm Payrolls', 'US Non-Farm Payrolls'),
  ('US Non-Farm Payrolls', 'NFP'),
  ('US Non-Farm Payrolls', 'Non-Farm Payrolls'),
  ('US Non-Farm Payrolls', 'Nonfarm Payrolls'),
  ('US CPI YoY', 'US CPI YoY'),
  ('US CPI YoY', 'Consumer Price Index'),
  ('US CPI YoY', 'CPI'),
  ('US CPI YoY', 'CPI y/y'),
  ('FOMC Rate Decision', 'FOMC Rate Decision'),
  ('FOMC Rate Decision', 'Federal Reserve Interest Rate Decision'),
  ('US GDP Advance', 'US GDP Advance'),
  ('US GDP Advance', 'GDP'),
  ('US GDP Advance', 'Gross Domestic Product'),
  ('US PCE Deflator', 'US PCE Deflator'),
  ('US PCE Deflator', 'PCE Price Index'),
  ('US Unemployment Rate', 'US Unemployment Rate'),
  ('US Unemployment Rate', 'Unemployment Rate'),
  ('US PPI MoM', 'US PPI MoM'),
  ('US PPI MoM', 'Producer Price Index'),
  ('US Industrial Production', 'US Industrial Production'),
  ('US Industrial Production', 'Industrial Production')
ON CONFLICT (alias_name) DO NOTHING;

-- === supabase/migrations/20260428000015_event_risk_exhaustion_bands.sql ===
-- T+1 return distribution bands for Convexity Radar (percent units).

ALTER TABLE public.event_risk_matrices
  ADD COLUMN IF NOT EXISTS inline_median_return DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS t1_exhaustion_p2_5 DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS t1_exhaustion_p16 DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS t1_exhaustion_p84 DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS t1_exhaustion_p97_5 DOUBLE PRECISION;

COMMENT ON COLUMN public.event_risk_matrices.inline_median_return IS
  'Median T+1 close/close return (%) for IN-LINE surprise bucket.';
COMMENT ON COLUMN public.event_risk_matrices.t1_exhaustion_p16 IS
  '16th percentile of T+1 returns (%) — inner exhaustion band.';
COMMENT ON COLUMN public.event_risk_matrices.t1_exhaustion_p84 IS
  '84th percentile of T+1 returns (%) — inner exhaustion band.';

-- === supabase/migrations/20260428000016_systemic_synthesis.sql ===
-- Dual correlation: target pair log-returns vs cross-sectional mean of other G10 FX log-returns.

CREATE OR REPLACE FUNCTION public.calculate_dual_correlation(p_pair text, p_lookback int)
RETURNS double precision
LANGUAGE sql
STABLE
AS $sql$
WITH g10 AS (
  SELECT unnest(ARRAY[
    'EURUSD', 'USDJPY', 'USDINR', 'GBPUSD', 'AUDUSD', 'USDCAD', 'USDCHF'
  ]::text[]) AS pair
),
bounds AS (
  SELECT COALESCE(MAX(hp.date), CURRENT_DATE) AS dmax
  FROM historical_prices hp
  INNER JOIN g10 g ON g.pair = hp.pair
),
r AS (
  SELECT
    p.pair,
    p.date,
    CASE
      WHEN lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date) IS NOT NULL
        AND lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date) > 0
        AND p.close > 0
      THEN LN(p.close / lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date))
      ELSE NULL
    END AS lr
  FROM historical_prices p
  INNER JOIN g10 g ON g.pair = p.pair
  CROSS JOIN bounds b
  WHERE p.date >= (b.dmax - INTERVAL '400 days')::date
),
target AS (
  SELECT date, lr AS lr_target
  FROM r
  WHERE pair = p_pair
),
basket AS (
  SELECT
    date,
    AVG(lr) AS lr_basket
  FROM r
  WHERE pair <> p_pair
    AND lr IS NOT NULL
  GROUP BY date
),
joined AS (
  SELECT
    t.date,
    t.lr_target,
    b.lr_basket
  FROM target t
  INNER JOIN basket b ON b.date = t.date
  WHERE t.lr_target IS NOT NULL
    AND b.lr_basket IS NOT NULL
),
trimmed AS (
  SELECT
    lr_target,
    lr_basket,
    ROW_NUMBER() OVER (ORDER BY date DESC) AS rn
  FROM joined
)
SELECT corr(lr_target, lr_basket)
FROM trimmed
WHERE rn <= GREATEST(p_lookback, 5);
$sql$;

GRANT EXECUTE ON FUNCTION public.calculate_dual_correlation(text, int) TO anon, authenticated, service_role;

ALTER TABLE brief_log
  ADD COLUMN IF NOT EXISTS dollar_dominance double precision,
  ADD COLUMN IF NOT EXISTS idiosyncratic_outlier text,
  ADD COLUMN IF NOT EXISTS sentiment_json jsonb;

COMMENT ON COLUMN brief_log.dollar_dominance IS 'Book-wide USD thematic alignment 0–100 (percent).';
COMMENT ON COLUMN brief_log.idiosyncratic_outlier IS 'FX pair most idiosyncratic vs G10 basket (low dual correlation).';
COMMENT ON COLUMN brief_log.sentiment_json IS 'Pre-baked Polymarket + synthesis metadata for UI (single-query home).';

-- === supabase/migrations/20260428000017_terminal_launch_blockers.sql ===
-- G10 terminal: dual rate Z, breakeven, tail risk columns (service-role writes only; RLS unchanged).

ALTER TABLE public.signals
  ADD COLUMN IF NOT EXISTS breakeven_inflation_10y double precision,
  ADD COLUMN IF NOT EXISTS rate_diff_10y_real double precision,
  ADD COLUMN IF NOT EXISTS rate_z_tactical double precision,
  ADD COLUMN IF NOT EXISTS rate_z_structural double precision;

COMMENT ON COLUMN public.signals.breakeven_inflation_10y IS 'FRED T10YIE (10Y breakeven inflation, %).';
COMMENT ON COLUMN public.signals.rate_diff_10y_real IS 'Nominal 10Y spread minus breakeven (real tilt, heuristic).';
COMMENT ON COLUMN public.signals.rate_z_tactical IS 'MAD Z on carry: 252-day window.';
COMMENT ON COLUMN public.signals.rate_z_structural IS 'MAD Z on carry: 2520-day window.';

ALTER TABLE public.event_risk_matrices
  ADD COLUMN IF NOT EXISTS t1_tail_risk_p95 double precision,
  ADD COLUMN IF NOT EXISTS t1_tail_risk_p05 double precision;

COMMENT ON COLUMN public.event_risk_matrices.t1_tail_risk_p95 IS 'Historical T+1 return 95th percentile (%).';
COMMENT ON COLUMN public.event_risk_matrices.t1_tail_risk_p05 IS 'Historical T+1 return 5th percentile (%).';

-- === supabase/migrations/20260428000018_research_memos.sql ===
-- Weekly Substack macro memos: full body for reader UI; JSON thesis bullets for daily LLM grounding only.

CREATE TABLE IF NOT EXISTS public.research_memos (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    date date NOT NULL,
    title text NOT NULL,
    raw_content text NOT NULL,
    ai_thesis_summary jsonb NOT NULL DEFAULT '[]'::jsonb,
    link_url text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT research_memos_link_url_key UNIQUE (link_url)
);

CREATE INDEX IF NOT EXISTS research_memos_date_desc ON public.research_memos (date DESC);

ALTER TABLE public.research_memos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_research_memos"
ON public.research_memos
FOR SELECT
TO anon
USING (true);

CREATE POLICY "anon_deny_insert_research_memos"
ON public.research_memos
FOR INSERT
TO anon
WITH CHECK (false);

CREATE POLICY "anon_deny_update_research_memos"
ON public.research_memos
FOR UPDATE
TO anon
USING (false);

CREATE POLICY "anon_deny_delete_research_memos"
ON public.research_memos
FOR DELETE
TO anon
USING (false);

COMMENT ON TABLE public.research_memos IS 'Ingested Substack weekly memos; ai_thesis_summary feeds desk-card briefs (not raw_content).';

-- === supabase/migrations/20260428000019_webhook_subscriptions.sql ===
-- Desk webhook ingress (07:05 snapshot). Application-layer AES-GCM in API; column name reflects CRO encryption expectation.

CREATE TABLE IF NOT EXISTS public.webhook_subscriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_url_encrypted text NOT NULL
        CONSTRAINT webhook_url_encrypted_not_empty CHECK (length(trim(webhook_url_encrypted)) > 0),
    pair_filter text,
    created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.webhook_subscriptions IS
  'Write-only anon ingress; pipeline reads via service role. webhook_url_encrypted stores enc:v1:... (AES-256-GCM) or kms_pending envelope in dev — never plaintext in production.';

COMMENT ON COLUMN public.webhook_subscriptions.webhook_url_encrypted IS
  'AES-256-GCM ciphertext (prefix enc:v1:) when CONNECT_DESK_ENCRYPTION_KEY is set; kms_pending:v0: base64url only for local dev — rotate to encrypted before prod.';

ALTER TABLE public.webhook_subscriptions ENABLE ROW LEVEL SECURITY;

-- Write-only ingress for anon (no read/update)
CREATE POLICY "anon_insert_webhook_subscriptions"
ON public.webhook_subscriptions
FOR INSERT
TO anon
WITH CHECK (true);

CREATE POLICY "anon_deny_select_webhook_subscriptions"
ON public.webhook_subscriptions
FOR SELECT
TO anon
USING (false);

CREATE POLICY "anon_deny_update_webhook_subscriptions"
ON public.webhook_subscriptions
FOR UPDATE
TO anon
USING (false);

CREATE POLICY "anon_deny_delete_webhook_subscriptions"
ON public.webhook_subscriptions
FOR DELETE
TO anon
USING (false);

-- === supabase/migrations/20260428000020_ledger_mae.sql ===
-- Maximum adverse excursion (BPS) over T+1..T+5 forward window for strategy_ledger rows.
ALTER TABLE strategy_ledger
    ADD COLUMN IF NOT EXISTS max_pain_bps DOUBLE PRECISION;

-- === supabase/migrations/20260428114056_remote_history_alignment.sql ===
-- Aligns local migration history with remote: version was applied on production before this file existed in-repo.
-- Intentionally empty DDL; remote schema already reflects prior operations.
SELECT 1;

-- === supabase/migrations/20260504000000_pillar2_volume_rvol.sql ===
-- Pillar 2: RVOL Gate infrastructure (G10 Futures Proxies)

-- 1. Add volume_ticker to universe for institutional liquidity proxies
ALTER TABLE public.universe ADD COLUMN IF NOT EXISTS volume_ticker TEXT;

-- Seed G10 volume tickers (CME Futures)
UPDATE public.universe SET volume_ticker = '6E=F' WHERE pair = 'EURUSD';
UPDATE public.universe SET volume_ticker = '6J=F' WHERE pair = 'USDJPY';
UPDATE public.universe SET volume_ticker = '6B=F' WHERE pair = 'GBPUSD';
UPDATE public.universe SET volume_ticker = '6A=F' WHERE pair = 'AUDUSD';
UPDATE public.universe SET volume_ticker = '6C=F' WHERE pair = 'USDCAD';
UPDATE public.universe SET volume_ticker = '6S=F' WHERE pair = 'USDCHF';

-- 2. Add volume_rvol to signals table for Pillar 2 gating
ALTER TABLE public.signals ADD COLUMN IF NOT EXISTS volume_rvol DOUBLE PRECISION;

-- === supabase/migrations/20260504000001_pillar3_mean_reversion.sql ===
-- Pillar 3: Mean Reversion Tracking for Event Risk Radar

ALTER TABLE public.event_risk_matrices 
ADD COLUMN IF NOT EXISTS mean_reversion_prob DOUBLE PRECISION;

COMMENT ON COLUMN public.event_risk_matrices.mean_reversion_prob 
IS 'Probability (0-100) that price returns to within 20% of the daily range from the Open by end of T+0.';

-- === supabase/migrations/20260504000003_phase3_audit_fixes.sql ===
-- Fix 3.1: Explicit block for RLS mutations
DO $$ 
DECLARE 
    t text;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
          AND table_type = 'BASE TABLE'
    LOOP
        EXECUTE format('
            DROP POLICY IF EXISTS "Block insert for anon/auth" ON public.%I;
            DROP POLICY IF EXISTS "Block update for anon/auth" ON public.%I;
            DROP POLICY IF EXISTS "Block delete for anon/auth" ON public.%I;
            CREATE POLICY "Block insert for anon/auth" ON public.%I FOR INSERT TO anon, authenticated WITH CHECK (false);
            CREATE POLICY "Block update for anon/auth" ON public.%I FOR UPDATE TO anon, authenticated USING (false);
            CREATE POLICY "Block delete for anon/auth" ON public.%I FOR DELETE TO anon, authenticated USING (false);
        ', t, t, t, t, t, t);
    END LOOP;
END $$;

-- Fix 3.3: Indexing Inefficiency
CREATE INDEX IF NOT EXISTS idx_signals_pair_date_asc ON public.signals (pair, date);
CREATE INDEX IF NOT EXISTS idx_regime_calls_pair_date_asc ON public.regime_calls (pair, date);
CREATE INDEX IF NOT EXISTS idx_historical_prices_pair_date_asc ON public.historical_prices (pair, date);
CREATE INDEX IF NOT EXISTS idx_validation_log_pair_date_asc ON public.validation_log (pair, date);
CREATE INDEX IF NOT EXISTS idx_strategy_ledger_pair_date_asc ON public.strategy_ledger (pair, date);

-- === supabase/migrations/20260504000004_ai_rpc.sql ===
-- Fix 3.2: Atomic AI request increment
CREATE OR REPLACE FUNCTION increment_ai_usage(p_date text, p_purpose text, p_model text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO public.ai_usage_log (date, request_count, purpose, model)
    VALUES (p_date, 1, p_purpose, p_model);
    RETURN true;
END;
$$;

-- === supabase/migrations/20260505000000_round1_foundation_audit.sql ===
-- Migration: 20260505000000_round1_foundation_audit.sql
-- Goal: Align database with 3-Layer Signal Framework (CONTEXT.md)
-- Chambers: Strategy (Alpha) & Engineering (Engine)

-- 1. Update SIGNALS Table (Layer 2 + Layer 3 inputs per DATA_DICTIONARY.md)
ALTER TABLE public.signals
  ADD COLUMN IF NOT EXISTS rate_diff_mom      double precision,
  ADD COLUMN IF NOT EXISTS cot_net_pos        integer,
  ADD COLUMN IF NOT EXISTS realized_vol_21    double precision,
  ADD COLUMN IF NOT EXISTS risk_reversal_25d  double precision;

COMMENT ON COLUMN public.signals.rate_diff_mom IS '4-week momentum of rate_diff_2y (Layer 2)';
COMMENT ON COLUMN public.signals.cot_net_pos IS 'NonCommercial net positioning, contracts (Layer 2)';
COMMENT ON COLUMN public.signals.realized_vol_21 IS '21-day annualized price volatility (Layer 3)';
COMMENT ON COLUMN public.signals.risk_reversal_25d IS '25-delta risk reversal (Put vs Call premium) (Layer 3)';

-- cot_percentile already exists (initial_schema); document Layer for framework alignment
COMMENT ON COLUMN public.signals.cot_percentile IS 'Net positioning vs 3-year rolling window (Layer 2)';

-- 2. Update REGIME_CALLS Table
ALTER TABLE public.regime_calls
  ADD COLUMN IF NOT EXISTS directional_bias      text,
  ADD COLUMN IF NOT EXISTS conviction            integer;

COMMENT ON COLUMN public.regime_calls.directional_bias IS 'Long, Short, or Neutral (Layer 2)';
COMMENT ON COLUMN public.regime_calls.conviction IS 'Conviction score from 1 (Low) to 5 (High) (Layer 2)';

-- regime is Layer 1 gate output (DATA_DICTIONARY); explicit comment for ledger clarity
COMMENT ON COLUMN public.regime_calls.regime IS 'Layer 1 regime classification (e.g. Carry Collapse)';

-- Named constraints: survive ADD COLUMN IF NOT EXISTS (column already present) and match DATA_DICTIONARY.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'regime_calls_conviction_range'
  ) THEN
    ALTER TABLE public.regime_calls
      ADD CONSTRAINT regime_calls_conviction_range
      CHECK (conviction IS NULL OR (conviction >= 1 AND conviction <= 5));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'regime_calls_directional_bias_values'
  ) THEN
    ALTER TABLE public.regime_calls
      ADD CONSTRAINT regime_calls_directional_bias_values
      CHECK (
        directional_bias IS NULL
        OR directional_bias IN ('Long', 'Short', 'Neutral')
      );
  END IF;
END $$;

-- 3. Update VALIDATION_LOG Table
ALTER TABLE public.validation_log
  ADD COLUMN IF NOT EXISTS call_id         integer REFERENCES public.regime_calls (id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS validation_date date,
  ADD COLUMN IF NOT EXISTS is_correct      boolean,
  ADD COLUMN IF NOT EXISTS pnl_bps         double precision;

COMMENT ON COLUMN public.validation_log.call_id IS 'Immutable reference to regime_calls.id';
COMMENT ON COLUMN public.validation_log.validation_date IS 'T+5 or T+20 observation date';
COMMENT ON COLUMN public.validation_log.is_correct IS 'True if directional bias matched price movement';
COMMENT ON COLUMN public.validation_log.pnl_bps IS 'Price movement in basis points since call';

-- FK joins and T+5 / T+20 lookups per call (PostgreSQL does not auto-index referencing columns)
CREATE INDEX IF NOT EXISTS idx_validation_log_call_id_valdate
  ON public.validation_log (call_id, validation_date)
  WHERE call_id IS NOT NULL;

-- 4. Enforcement of immutability (Phase 2)
-- Safe if mis-attached: only blocks UPDATE; INSERT/DELETE still work unless separate triggers exist.
CREATE OR REPLACE FUNCTION public.protect_immutable_calls()
RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    RAISE EXCEPTION 'Regime calls are immutable once written to the ledger.';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: Trigger not applied yet so the pipeline can settle (Chamber 2 audit).

-- === supabase/migrations/20260505000001_round3_validation_engine.sql ===
-- Round 3: Validation Engine schema evolution
-- Adds T+20 log-return metrics, Brier scores, and call_date anchor.

-- 1. Add call_date to validation_log (nullable for legacy rows)
ALTER TABLE validation_log
    ADD COLUMN IF NOT EXISTS call_date DATE,
    ADD COLUMN IF NOT EXISTS actual_direction_t5 VARCHAR(10),
    ADD COLUMN IF NOT EXISTS actual_direction_t20 VARCHAR(10),
    ADD COLUMN IF NOT EXISTS log_return_t5_bps FLOAT,
    ADD COLUMN IF NOT EXISTS log_return_t20_bps FLOAT,
    ADD COLUMN IF NOT EXISTS correct_t5 BOOLEAN,
    ADD COLUMN IF NOT EXISTS correct_t20 BOOLEAN,
    ADD COLUMN IF NOT EXISTS brier_score_t5 FLOAT,
    ADD COLUMN IF NOT EXISTS brier_score_t20 FLOAT,
    ADD COLUMN IF NOT EXISTS is_superseded BOOLEAN DEFAULT false;

-- 2. Drop old unique index (it conflicts with new semantics where date = call_date)
DROP INDEX IF EXISTS idx_validation_unique;

-- 3. Create new unique index on (call_date, pair) for new rows
-- Legacy rows have call_date = NULL; Postgres NULLs do not conflict in unique indexes.
CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_call_pair ON validation_log (call_date, pair);

-- 4. Keep non-unique index on (date, pair) for legacy queries
CREATE INDEX IF NOT EXISTS idx_validation_date_pair ON validation_log (date, pair);

-- === supabase/migrations/20260505000002_validation_stats.sql ===
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

-- === supabase/migrations/20260505000003_layer3_execution_schema.sql ===
-- Migration: 20260505000001_layer3_execution_schema.sql
-- Goal: Add columns for Layer 3 (Execution HUD) tracking.
-- Chambers: Strategy (Alpha) & Engineering (Engine)

-- 1. Update SIGNALS Table
ALTER TABLE public.signals
  ADD COLUMN IF NOT EXISTS realized_vol_rank  double precision,
  ADD COLUMN IF NOT EXISTS skew_alignment      integer;

COMMENT ON COLUMN public.signals.realized_vol_rank IS 'Empirical CDF rank of 21d realized vol vs 3-year history (Layer 3)';
COMMENT ON COLUMN public.signals.skew_alignment IS 'Alignment between bias and 25d risk reversal (-1, 0, 1) (Layer 3)';

-- 2. Update REGIME_CALLS Table
ALTER TABLE public.regime_calls
  ADD COLUMN IF NOT EXISTS entry_timing   text,
  ADD COLUMN IF NOT EXISTS position_size  text,
  ADD COLUMN IF NOT EXISTS stop_level     double precision;

COMMENT ON COLUMN public.regime_calls.entry_timing IS 'ENTER or WAIT (Layer 3)';
COMMENT ON COLUMN public.regime_calls.position_size IS 'FULL or HALF (Layer 3)';
COMMENT ON COLUMN public.regime_calls.stop_level IS 'Calculated stop-loss level based on MIE/ADR (Layer 3)';

-- Constraints for Layer 3
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'regime_calls_entry_timing_values'
  ) THEN
    ALTER TABLE public.regime_calls
      ADD CONSTRAINT regime_calls_entry_timing_values
      CHECK (entry_timing IS NULL OR entry_timing IN ('ENTER', 'WAIT'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'regime_calls_position_size_values'
  ) THEN
    ALTER TABLE public.regime_calls
      ADD CONSTRAINT regime_calls_position_size_values
      CHECK (position_size IS NULL OR position_size IN ('FULL', 'HALF'));
  END IF;
END $$;
