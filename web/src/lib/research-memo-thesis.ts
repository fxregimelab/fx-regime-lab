import type { Json } from '@/lib/supabase/database.types';

/** Normalize `research_memos.ai_thesis_summary` JSONB to display bullets (max 5). */
export function parseThesisBulletsFromJson(raw: Json | null | undefined): string[] {
  if (raw == null) return [];
  if (!Array.isArray(raw)) return [];
  const out: string[] = [];
  for (const x of raw) {
    if (typeof x !== 'string') continue;
    const t = x.trim();
    if (t) out.push(t);
  }
  return out.slice(0, 5);
}

/** Monday-start week identity in UTC (YYYY-MM-DD of that Monday). */
function mondayKeyUtc(isoDate: string): string {
  const [y, m, d] = isoDate.slice(0, 10).split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d, 12, 0, 0));
  const dow = dt.getUTCDay();
  const offset = dow === 0 ? -6 : 1 - dow;
  dt.setUTCDate(dt.getUTCDate() + offset);
  return dt.toISOString().slice(0, 10);
}

/** True when memo `date` falls in the same calendar week as `anchorDate` (Mon–Sun, UTC). */
export function isSameWeekUtc(isoDate: string, anchorDate: string): boolean {
  return mondayKeyUtc(isoDate) === mondayKeyUtc(anchorDate);
}
