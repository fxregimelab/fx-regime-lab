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
