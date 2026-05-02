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
