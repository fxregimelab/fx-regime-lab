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
