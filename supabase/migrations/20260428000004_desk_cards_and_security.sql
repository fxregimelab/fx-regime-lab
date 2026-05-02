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
