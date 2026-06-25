-- Pillar 2: RVOL Gate infrastructure (FX Futures Proxies)

-- 1. Add volume_ticker to universe for institutional liquidity proxies
ALTER TABLE public.universe ADD COLUMN IF NOT EXISTS volume_ticker TEXT;

-- Seed FX volume tickers (CME Futures)
UPDATE public.universe SET volume_ticker = '6E=F' WHERE pair = 'EURUSD';
UPDATE public.universe SET volume_ticker = '6J=F' WHERE pair = 'USDJPY';

-- 2. Add volume_rvol to signals table for Pillar 2 gating
ALTER TABLE public.signals ADD COLUMN IF NOT EXISTS volume_rvol DOUBLE PRECISION;
