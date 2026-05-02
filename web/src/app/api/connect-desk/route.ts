import { createCipheriv, randomBytes, scryptSync } from 'node:crypto';
import { createClient } from '@supabase/supabase-js';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import type { Database } from '@/lib/supabase/database.types';

export const runtime = 'nodejs';

const SALT = 'fxrl-connect-desk-kdf-v1______';

function validateWebhookUrl(raw: string): URL {
  const trimmed = raw.trim();
  if (!trimmed) throw new Error('Webhook URL required');
  let u: URL;
  try {
    u = new URL(trimmed);
  } catch {
    throw new Error('Invalid URL');
  }
  if (u.protocol !== 'https:') throw new Error('HTTPS required');
  const h = u.hostname.toLowerCase();
  const ok =
    h === 'hooks.slack.com' ||
    h === 'discord.com' ||
    h === 'discordapp.com' ||
    h === 'symphony.com' ||
    h.endsWith('.symphony.com');
  if (!ok) throw new Error('URL must be a Slack, Discord, or Symphony webhook endpoint');
  if (h === 'hooks.slack.com' && !u.pathname.startsWith('/services/')) {
    throw new Error('Slack URL must be a /services/… incoming webhook');
  }
  if ((h === 'discord.com' || h === 'discordapp.com') && !u.pathname.startsWith('/api/webhooks/')) {
    throw new Error('Discord URL must be an /api/webhooks/… endpoint');
  }
  return u;
}

/** CRO: AES-256-GCM when CONNECT_DESK_ENCRYPTION_KEY set; else kms_pending envelope (dev only). */
function sealWebhookUrl(plain: string): string {
  const secret = process.env.CONNECT_DESK_ENCRYPTION_KEY;
  if (!secret || secret.length < 16) {
    return `kms_pending:v0:${Buffer.from(plain, 'utf8').toString('base64url')}`;
  }
  const key = scryptSync(secret, SALT, 32);
  const iv = randomBytes(12);
  const cipher = createCipheriv('aes-256-gcm', key, iv);
  const enc = Buffer.concat([cipher.update(plain, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  return ['enc', 'v1', iv.toString('base64url'), tag.toString('base64url'), enc.toString('base64url')].join(':');
}

export async function POST(req: NextRequest) {
  let body: { webhookUrl?: string; pairFilter?: string | null };
  try {
    body = (await req.json()) as { webhookUrl?: string; pairFilter?: string | null };
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const webhookUrl = body.webhookUrl;
  if (typeof webhookUrl !== 'string') {
    return NextResponse.json({ error: 'webhookUrl must be a string' }, { status: 400 });
  }

  try {
    validateWebhookUrl(webhookUrl);
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Validation failed';
    return NextResponse.json({ error: msg }, { status: 400 });
  }

  const pairFilter =
    body.pairFilter === null || body.pairFilter === undefined || body.pairFilter === ''
      ? null
      : String(body.pairFilter).slice(0, 16);

  const sealed = sealWebhookUrl(webhookUrl.trim());

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceKey) {
    return NextResponse.json({ error: 'Server missing Supabase configuration' }, { status: 503 });
  }

  const admin = createClient<Database>(url, serviceKey);
  const row: Database['public']['Tables']['webhook_subscriptions']['Insert'] = {
    webhook_url_encrypted: sealed,
    pair_filter: pairFilter,
  };
  // Supabase-js can infer `insert` as `never` for newer schema shapes; row matches DB Insert.
  const { error } = await admin.from('webhook_subscriptions').insert(row as never);

  if (error) {
    return NextResponse.json({ error: 'Persist failed' }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
