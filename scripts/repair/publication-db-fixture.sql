-- Independent publication fixture, not a rehearsal of historical migrations.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN CREATE ROLE anon; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN CREATE ROLE authenticated; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='service_role') THEN CREATE ROLE service_role; END IF;
END $$;
CREATE TABLE public.regime_calls (
  id serial PRIMARY KEY, pair text NOT NULL, date date NOT NULL, regime text NOT NULL,
  confidence double precision NOT NULL CHECK(confidence BETWEEN 0 AND 1),
  signal_composite double precision NOT NULL, rate_signal text NOT NULL,
  primary_driver text, entry_timing text CHECK(entry_timing IN ('ENTER','WAIT')),
  position_size text CHECK(position_size IN ('FULL','HALF')), stop_level double precision,
  data_quality_score double precision, stress_level text, predicted_direction text,
  directional_bias text, conviction integer CHECK(conviction BETWEEN 1 AND 5), cot_signal text, vol_signal text, oi_signal text,
  rr_signal text, special_signal_value double precision, special_signal_label text,
  regime_category text CHECK(regime_category IN ('RATE_DRIVEN','CARRY_DRIVEN','VOLATILITY_DRIVEN','POLICY_SHOCK','LIQUIDITY_SHOCK','NEUTRAL')),
  model_version text, strategy_version varchar(10), data_source varchar(20),
  correlation_id text, write_hash text, created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT regime_calls_directional_bias_values CHECK(directional_bias IS NULL OR directional_bias IN ('Long','Short','Neutral')),
  CONSTRAINT regime_calls_pair_date_unique UNIQUE(pair,date)
);
CREATE UNIQUE INDEX old_regime_date_pair ON public.regime_calls(date,pair);
CREATE INDEX retain_regime_pair ON public.regime_calls(pair);
CREATE TABLE public.signals (
  id serial PRIMARY KEY, pair text NOT NULL, date date NOT NULL,
  rate_diff_2y double precision, rate_diff_10y double precision, cot_percentile double precision,
  realized_vol_20d double precision, realized_vol_5d double precision, implied_vol_30d double precision,
  spot double precision, day_change double precision, day_change_pct double precision,
  cross_asset_vix double precision, cross_asset_dxy double precision, cross_asset_oil double precision,
  cross_asset_us10y double precision, cross_asset_gold double precision, cross_asset_copper double precision,
  cross_asset_stoxx double precision, oi_delta integer, volume_rvol double precision,
  structural_instability boolean DEFAULT false, breakeven_inflation_10y double precision,
  rate_diff_10y_real double precision, rate_z_tactical double precision, rate_z_structural double precision,
  z_blended real, realized_vol_rank double precision, skew_alignment integer,
  risk_reversal_25d double precision, risk_reversal_source text DEFAULT 'PENDING_REAL_DATA',
  days_since_cot integer DEFAULT 0, fpi_flow double precision, cot_net_pos integer,
  cot_asset_mgr_net bigint, cot_lev_money_net bigint, ecb_balance_sheet double precision,
  bund_btp_spread double precision, boj_policy_rate double precision, india_vix double precision,
  inr_forward_premium double precision, data_quality_notes text[],
  created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(pair,date)
);
-- Includes the v2.1 staleness/source/notes additions from 20260526000000.
CREATE TABLE public.call_rationale (
  id serial PRIMARY KEY, call_id integer NOT NULL REFERENCES public.regime_calls(id),
  date date NOT NULL, pair varchar(10) NOT NULL, layer1_reasoning text, layer2_reasoning text,
  layer3_reasoning text, primary_driver_detail text, confidence_explanation text,
  contrarian_flags text[], created_at timestamptz DEFAULT now(), UNIQUE(call_id)
);
GRANT USAGE ON SCHEMA public TO anon,authenticated,service_role;
-- Model existing broad Supabase grants, so the migration must remove write privileges.
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon,authenticated,service_role;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO anon,authenticated,service_role;
INSERT INTO public.regime_calls(pair,date,regime,confidence,signal_composite,rate_signal,
  predicted_direction,model_version,strategy_version,data_source,directional_bias)
VALUES('EURUSD','2026-09-01','TRENDING',0.6,0.7,'BULLISH','BULLISH','legacy','v2','live','Long');
INSERT INTO public.signals(pair,date,spot,data_quality_notes)
VALUES('EURUSD','2026-09-01',1.1,ARRAY['legacy snapshot, no asserted call provenance']);
INSERT INTO public.call_rationale(call_id,date,pair,layer1_reasoning)
VALUES(1,'2026-09-01','EURUSD','Untouched legacy rationale');
