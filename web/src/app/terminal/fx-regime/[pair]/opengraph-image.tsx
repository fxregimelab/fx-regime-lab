import { ImageResponse } from 'next/og';
import { createClient } from '@supabase/supabase-js';
import { PAIRS } from '@/lib/mockData';

export const runtime = 'edge';

export const alt = 'FX Regime Lab';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default async function Image({ params }: { params: Promise<{ pair: string }> }) {
  const { pair: pairSlug } = await params;
  const pair = PAIRS.find((p) => p.urlSlug === pairSlug.toLowerCase()) ?? PAIRS[0];

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  let regime = '—';
  let confPct: number | null = null;

  if (url && anon) {
    const supabase = createClient(url, anon);
    const { data } = await supabase
      .from('regime_calls')
      .select('regime, confidence')
      .eq('pair', pair.label)
      .order('date', { ascending: false })
      .limit(1)
      .maybeSingle();
    const row = data as { regime?: string; confidence?: number } | null;
    if (row?.regime) regime = String(row.regime);
    if (row?.confidence != null) confPct = Math.round(Number(row.confidence) * 100);
  }

  return new ImageResponse(
    (
      <div
        style={{
          width: size.width,
          height: size.height,
          background: '#000000',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: 48,
          color: '#ffffff',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div
            style={{
              fontSize: 88,
              fontWeight: 800,
              letterSpacing: -3,
              lineHeight: 1,
            }}
          >
            {pair.display}
          </div>
          <div
            style={{
              fontSize: 38,
              color: '#a3a3a3',
              maxWidth: 1000,
              lineHeight: 1.2,
            }}
          >
            {regime}
          </div>
          <div style={{ fontSize: 30, color: '#e8e8e8', fontVariantNumeric: 'tabular-nums' as const }}>
            CONFIDENCE {confPct != null ? `${confPct}%` : '—'}
          </div>
        </div>
        <div
          style={{
            fontSize: 24,
            color: '#666666',
            letterSpacing: '0.35em',
            textTransform: 'uppercase' as const,
          }}
        >
          FX Regime Lab
        </div>
      </div>
    ),
    { ...size },
  );
}
