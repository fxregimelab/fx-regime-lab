import { ValidationTable } from '@/components/ValidationTable';
import { mapValidationRow } from '@/lib/supabase/map-row';
import type { Database } from '@/lib/supabase/database.types';
import type { ValidationRow } from '@/lib/types';
import Link from 'next/link';

type ValidationDb = Database['public']['Tables']['validation_log']['Row'];

export function HomeValidationStrip({
  rows,
  rolling7dPct,
}: {
  rows: ValidationDb[];
  rolling7dPct: number | null;
}) {
  const mapped: ValidationRow[] = (rows ?? [])
    .map(mapValidationRow)
    .filter((r): r is ValidationRow => r != null)
    .slice(0, 6);
  const accStr =
    rolling7dPct != null ? `${rolling7dPct >= 10 ? rolling7dPct.toFixed(1) : rolling7dPct.toFixed(2)}%` : '—';

  return (
    <section className="border-y border-[#111] bg-[#0a0a0a]">
      <div className="mx-auto max-w-[1280px] px-6 py-14">
        <div className="mb-8 flex flex-wrap items-start justify-between gap-6">
          <div>
            <p className="mb-2 font-mono text-[10px] tracking-[0.12em] text-[#444]">VALIDATION LOG</p>
            <h2 className="font-sans text-[20px] font-bold tracking-tight text-[#f2f2f2]">
              Next-day outcome, on the record.
            </h2>
            <p className="mt-2 max-w-xl font-sans text-[13px] leading-relaxed text-[#525252]">
              Every call validated the following trading day. No revisions, no ex-post edits.
            </p>
          </div>
          <div className="text-right">
            <p className="font-mono text-[36px] font-bold leading-none tracking-[-0.04em] text-[#22c55e]">
              {accStr}
            </p>
            <p className="mt-1 font-mono text-[10px] tracking-[0.1em] text-[#444]">7-DAY ACCURACY</p>
          </div>
        </div>
        <ValidationTable rows={mapped} variant="dark" />
        <Link
          href="/performance"
          className="mt-4 inline-block border border-[#1f1f1f] px-4 py-2 font-mono text-[11px] text-[#555] hover:text-[#888]"
        >
          Full validation log →
        </Link>
      </div>
    </section>
  );
}
