/** ISO date string or Date → locale short date */
export function formatDate(input: string | Date, locale = 'en-GB'): string {
  const d = typeof input === 'string' ? new Date(`${input}T12:00:00Z`) : input;
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  }).format(d);
}

/** 0.42 → 42% */
export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

/** Decimal as basis points string */
export function formatBps(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return '—';
  return `${(value * 10000).toFixed(digits)} bps`;
}
