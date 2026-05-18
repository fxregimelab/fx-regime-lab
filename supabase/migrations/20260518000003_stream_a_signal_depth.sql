-- Stream A: Signal Depth — Add pair-specific macro signal columns

ALTER TABLE public.signals
    ADD COLUMN ecb_balance_sheet float,
    ADD COLUMN bund_btp_spread float,
    ADD COLUMN boj_policy_rate float,
    ADD COLUMN india_vix float,
    ADD COLUMN inr_forward_premium float;

COMMENT ON COLUMN public.signals.ecb_balance_sheet IS 'ECB total assets (ECBASSETSW) in billions EUR. EURUSD macro input.';
COMMENT ON COLUMN public.signals.bund_btp_spread IS '10Y Bund - 10Y BTP in percentage points. EURUSD fragmentation proxy.';
COMMENT ON COLUMN public.signals.boj_policy_rate IS 'BoJ policy rate proxy (IRSTCI01JPM156N) in percent. USDJPY rate differential input.';
COMMENT ON COLUMN public.signals.india_vix IS 'India VIX level. USDINR stress indicator.';
COMMENT ON COLUMN public.signals.inr_forward_premium IS 'USD/INR 1M forward premium annualized in percent. USDINR flow indicator.';
