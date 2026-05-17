-- Migration: Add missing anon SELECT policy for desk_open_cards
-- The table was created with RLS enabled and deny policies for write ops,
-- but the SELECT policy for anonymous reads was never added.

DROP POLICY IF EXISTS "anon_read_desk_open_cards" ON desk_open_cards;
CREATE POLICY "anon_read_desk_open_cards"
ON desk_open_cards
FOR SELECT
TO anon
USING (true);
