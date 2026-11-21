-- Deliberately bounded fixture: documented integer IDs and post-cleanup columns.
-- This does not claim to reproduce the full historical migration chain.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN CREATE ROLE anon; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN CREATE ROLE authenticated; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='service_role') THEN CREATE ROLE service_role; END IF;
END $$;
CREATE TABLE public.regime_calls (
  id serial PRIMARY KEY, date date NOT NULL, pair text NOT NULL,
  predicted_direction text, regime text, confidence float8,
  strategy_version text, data_source text, model_version text DEFAULT '2.0-live'
);
CREATE TABLE public.validation_log (
  id serial PRIMARY KEY, date date NOT NULL, pair text NOT NULL,
  call text NOT NULL, outcome text NOT NULL CHECK(outcome IN ('correct','incorrect')),
  return_pct float8, created_at timestamptz DEFAULT now(),
  call_id integer REFERENCES public.regime_calls(id), call_date date,
  is_superseded boolean DEFAULT false, confidence float8,
  log_return_t5_bps float8, correct_t5 boolean, brier_score_t5 float8, actual_direction_t5 text,
  log_return_t20_bps float8, correct_t20 boolean, brier_score_t20 float8, actual_direction_t20 text,
  actual_return_5d float8, correct_5d boolean, brier_5d float8,
  actual_return_20d float8, correct_20d boolean, brier_20d float8,
  UNIQUE(pair,date)
);
CREATE UNIQUE INDEX idx_validation_call_id ON public.validation_log(call_id) WHERE is_superseded=false;
CREATE UNIQUE INDEX idx_validation_call_pair ON public.validation_log(call_date,pair) WHERE is_superseded=false;
INSERT INTO public.regime_calls(date,pair,predicted_direction,regime,confidence,strategy_version,data_source)
VALUES ('2026-05-01','EURUSD','BEARISH','TRENDING',0.7,'v2','backtest'),
       ('2026-05-04','USDJPY','BULLISH','TRENDING',0.6,'v2','live'),
       ('2026-05-05','USDINR','NEUTRAL','RANGING',NULL,'v2','live'),
       ('2026-05-06','EURUSD','BEARISH','TRENDING',0.7,'v2','backtest');
INSERT INTO public.validation_log(date,pair,call,outcome,call_id,call_date,log_return_t5_bps,correct_t5)
VALUES ('2026-05-01','EURUSD','BEARISH','incorrect',1,'2026-05-01',-20,false);
