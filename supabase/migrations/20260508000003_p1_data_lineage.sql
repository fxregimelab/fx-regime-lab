-- P1-T4: Data lineage for historical_prices
-- Tracks which source provided each price point and when it was fetched.

ALTER TABLE public.historical_prices
    ADD COLUMN IF NOT EXISTS source VARCHAR(20),
    ADD COLUMN IF NOT EXISTS fetch_timestamp TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_historical_prices_source
    ON public.historical_prices (source)
    WHERE source IS NOT NULL;

COMMENT ON COLUMN public.historical_prices.source IS
    'Data provider: polygon, alphavantage, yfinance, or manual.';
