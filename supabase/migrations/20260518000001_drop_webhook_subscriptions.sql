-- Drop webhook_subscriptions table and policies
-- Reason: Violates IDENTITY.md — alert subscription infrastructure is not allowed

-- Drop table first (cascades policies). If table doesn't exist, skip.
DROP TABLE IF EXISTS public.webhook_subscriptions;
