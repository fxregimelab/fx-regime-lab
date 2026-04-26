export function fmt2(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '—';
  return v.toFixed(2);
}

export function fmt4(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '—';
  return v.toFixed(4);
}

export function fmtPct(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '—';
  return `${Math.round(v * 100)}%`;
}

export function fmtInt(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '—';
  return v.toFixed(0);
}

export function fmtChg(v: number | null | undefined): { str: string; positive: boolean } {
  if (v == null || isNaN(v)) return { str: '—', positive: true };
  const sign = v >= 0 ? '+' : '';
  return { str: `${sign}${v.toFixed(2)}%`, positive: v >= 0 };
}

export function fmtSpot(v: number | null | undefined, pair: string): string {
  if (v == null) return '—';
  return v.toFixed(pair === 'USDJPY' ? 2 : 4);
}
