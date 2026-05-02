import { NextResponse } from 'next/server';
import { truncateLinkedInPost } from '@/lib/linkedin-truncate';

const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';
const PRIMARY_MODEL = 'google/gemma-3-27b-it:free';

/** Mirrors ``pipeline/src/ai/client.py`` ``generate_linkedin_alpha_hook_async`` prompt contract. */
function buildPrompt(cardData: Record<string, unknown>): string {
  const payload = JSON.stringify(cardData);
  const baseUrl = (process.env.SITE_PUBLIC_URL || 'https://fxregimelab.com').replace(/\/$/, '');
  return (
    'You are an Institutional FX Strategist. Write a 1,200 character LinkedIn post ' +
    'based on the provided Apex Target data.\n' +
    'STRICT CONSTRAINTS:\n' +
    '- STRICTLY NO MARKETING FLUFF.\n' +
    '- No emojis.\n' +
    '- No hashtags.\n' +
    '- Style: institutional shorthand only (e.g., "1.5x MAD breach," "COT extremes," ' +
    '"Asymmetric Downside").\n' +
    '- Structure exactly four blocks separated by line breaks:\n' +
    '  [REGIME ALERT] then [THE NUMBERS] then [THE SQUEEZE RISK] then [LINK]\n' +
    '- In [LINK], give one plain URL: use pair slug from data (lowercase, e.g. eurusd) as ' +
    `${baseUrl}/terminal/fx-regime/<slug>\n` +
    `APEX_TARGET_JSON:\n${payload}\n` +
    'Output: plain text only. Max ~1200 characters. No markdown.'
  );
}

export async function POST(req: Request) {
  const key = process.env.OPENROUTER_API_KEY;
  if (!key) {
    return NextResponse.json({ error: 'OPENROUTER_API_KEY not configured' }, { status: 503 });
  }
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }
  const cardData =
    body && typeof body === 'object' && 'cardData' in body && (body as { cardData: unknown }).cardData
      ? (body as { cardData: Record<string, unknown> }).cardData
      : null;
  if (!cardData || typeof cardData !== 'object') {
    return NextResponse.json({ error: 'Missing cardData object' }, { status: 400 });
  }

  const res = await fetch(OPENROUTER_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': 'https://fxregimelab.com',
      'X-Title': 'FX Regime Lab',
    },
    body: JSON.stringify({
      model: PRIMARY_MODEL,
      messages: [{ role: 'user', content: buildPrompt(cardData) }],
      max_tokens: 520,
      temperature: 0.3,
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    return NextResponse.json(
      { error: 'OpenRouter request failed', detail: errText.slice(0, 200) },
      { status: 502 },
    );
  }

  const data = (await res.json()) as {
    choices?: Array<{ message?: { content?: string | null } }>;
  };
  const raw = data.choices?.[0]?.message?.content?.trim() ?? '';
  if (!raw) {
    return NextResponse.json({ error: 'Empty model response' }, { status: 502 });
  }
  const text = truncateLinkedInPost(raw);
  return NextResponse.json({ text });
}
