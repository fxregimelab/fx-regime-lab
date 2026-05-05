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
