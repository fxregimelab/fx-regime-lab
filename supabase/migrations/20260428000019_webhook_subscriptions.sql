-- Desk webhook ingress (07:05 snapshot). Application-layer AES-GCM in API; column name reflects CRO encryption expectation.

CREATE TABLE IF NOT EXISTS public.webhook_subscriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_url_encrypted text NOT NULL
        CONSTRAINT webhook_url_encrypted_not_empty CHECK (length(trim(webhook_url_encrypted)) > 0),
    pair_filter text,
    created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.webhook_subscriptions IS
  'Write-only anon ingress; pipeline reads via service role. webhook_url_encrypted stores enc:v1:... (AES-256-GCM) or kms_pending envelope in dev — never plaintext in production.';

COMMENT ON COLUMN public.webhook_subscriptions.webhook_url_encrypted IS
  'AES-256-GCM ciphertext (prefix enc:v1:) when CONNECT_DESK_ENCRYPTION_KEY is set; kms_pending:v0: base64url only for local dev — rotate to encrypted before prod.';

ALTER TABLE public.webhook_subscriptions ENABLE ROW LEVEL SECURITY;

-- Write-only ingress for anon (no read/update)
CREATE POLICY "anon_insert_webhook_subscriptions"
ON public.webhook_subscriptions
FOR INSERT
TO anon
WITH CHECK (true);

CREATE POLICY "anon_deny_select_webhook_subscriptions"
ON public.webhook_subscriptions
FOR SELECT
TO anon
USING (false);

CREATE POLICY "anon_deny_update_webhook_subscriptions"
ON public.webhook_subscriptions
FOR UPDATE
TO anon
USING (false);

CREATE POLICY "anon_deny_delete_webhook_subscriptions"
ON public.webhook_subscriptions
FOR DELETE
TO anon
USING (false);
