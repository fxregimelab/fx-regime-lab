import { BriefTabs } from '@/app/(site)/brief/BriefTabs';
import type { BriefTabPayload } from '@/app/(site)/brief/brief-types';
import { ErrorBoundaryCard } from '@/components/states';
import { PAIRS } from '@/lib/mock/data';
import type { Database } from '@/lib/supabase/database.types';
import { defaultSignalRow, mapSignalRowWithChange, mapValidationRow } from '@/lib/supabase/map-row';
import { getLatestBrief, getLatestSignals, getValidationLog } from '@/lib/supabase/queries';
import type { PairMeta, SignalRow, ValidationRow } from '@/lib/types';
import Link from 'next/link';

type BriefRow = Database['public']['Tables']['brief']['Row'];

const DEFAULT_MACRO =
  'Dollar index, Fed guidance, and risk tone drive G10 regimes. Cross-check the pair sections below against your risk calendar. Macro copy updates when the morning brief pipeline publishes per-pair analysis.';

function utcToday(): string {
  return new Date().toISOString().slice(0, 10);
}

function macroFromBriefs(briefByLabel: Record<PairMeta['label'], BriefTabPayload | null>): string {
  for (const p of PAIRS) {
    const b = briefByLabel[p.label];
    if (b?.analysis) {
      const first = b.analysis.split('\n\n')[0]?.trim();
      if (first) return first;
    }
  }
  return DEFAULT_MACRO;
}

function maxIsoDate(dates: (string | undefined)[]): string {
  const ok = dates.filter((d): d is string => !!d);
  if (!ok.length) return utcToday();
  return ok.reduce((a, b) => (a > b ? a : b));
}

export default async function BriefPage() {
  const [valRes, bEur, sEur, bJpy, sJpy, bInr, sInr] = await Promise.all([
    getValidationLog(),
    getLatestBrief('EURUSD'),
    getLatestSignals('EURUSD'),
    getLatestBrief('USDJPY'),
    getLatestSignals('USDJPY'),
    getLatestBrief('USDINR'),
    getLatestSignals('USDINR'),
  ]);

  if (valRes.error) {
    return (
      <div className="mx-auto max-w-[1280px] px-6 py-10">
        <ErrorBoundaryCard message={valRes.error.message} tone="shell" />
      </div>
    );
  }

  const briefErrors: string[] = [];
  const briefByLabel: Record<PairMeta['label'], BriefTabPayload | null> = {
    EURUSD: null,
    USDJPY: null,
    USDINR: null,
  };
  const signalByLabel: Record<PairMeta['label'], SignalRow | null> = {
    EURUSD: null,
    USDJPY: null,
    USDINR: null,
  };

  const briefPairs: { label: PairMeta['label']; res: typeof bEur; sig: typeof sEur }[] = [
    { label: 'EURUSD', res: bEur, sig: sEur },
    { label: 'USDJPY', res: bJpy, sig: sJpy },
    { label: 'USDINR', res: bInr, sig: sInr },
  ];

  for (const { label, res, sig } of briefPairs) {
    if (res.error) briefErrors.push(res.error.message);
    else {
      const r = res.data?.[0] as BriefRow | undefined;
      if (r) {
        briefByLabel[label] = {
          regime: r.regime,
          confidence: r.confidence,
          composite: r.composite,
          analysis: r.analysis,
          primaryDriver: r.primary_driver,
        };
      }
    }
    const briefDate = (res.data?.[0] as BriefRow | undefined)?.date ?? utcToday();
    if (!sig.error && sig.data?.[0]) {
      signalByLabel[label] = mapSignalRowWithChange(sig.data);
    } else {
      signalByLabel[label] = defaultSignalRow(label, briefDate);
    }
  }

  const validationRows: ValidationRow[] = (valRes.data ?? [])
    .map(mapValidationRow)
    .filter((r): r is ValidationRow => r != null);

  const topError = briefErrors[0];
  const titleDate = maxIsoDate(
    briefPairs.map((x) => (x.res.data?.[0] as BriefRow | undefined)?.date),
  );
  const macroBody = macroFromBriefs(briefByLabel);

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      {topError ? (
        <div className="mb-6">
          <ErrorBoundaryCard message={topError} tone="shell" />
        </div>
      ) : null}

      <div className="mb-10 grid grid-cols-1 gap-6 border-b border-[#e5e5e5] pb-8 sm:grid-cols-[1fr_auto] sm:items-start">
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2.5">
            <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-[#22c55e]" />
            <span className="font-mono text-[11px] tracking-[0.1em] text-[#888]">MORNING BRIEF</span>
            <span className="font-mono text-[11px] text-[#ccc]">{titleDate}</span>
          </div>
          <h1 className="font-sans text-[28px] font-extrabold tracking-tight text-[#0a0a0a] sm:text-[32px]">
            Daily Brief — {titleDate}
          </h1>
        </div>
        <Link
          href="/terminal"
          className="inline-flex h-fit shrink-0 items-center justify-center border border-[#e5e5e5] bg-white px-4 py-2.5 font-mono text-[11px] text-[#555] transition hover:bg-[#fafafa]"
        >
          Open terminal →
        </Link>
      </div>

      <div className="mb-10 border border-[#e5e5e5] border-l-[3px] border-l-[#0a0a0a] bg-[#fafafa] px-5 py-4">
        <p className="mb-2 font-mono text-[10px] tracking-[0.1em] text-[#888]">MACRO CONTEXT</p>
        <p className="font-sans text-[14px] leading-[1.7] text-[#333]">{macroBody}</p>
      </div>

      <BriefTabs briefByLabel={briefByLabel} signalByLabel={signalByLabel} validationRows={validationRows} />

      <div className="mt-12 border-t border-[#e5e5e5] pt-8">
        <p className="font-mono text-[10px] leading-[1.8] tracking-[0.06em] text-[#c0c0c0]">
          RESEARCH AND LEARNING ONLY. NOT INVESTMENT ADVICE. ALL CALLS LOGGED PRIOR TO MARKET OPEN.
          OUTCOMES VALIDATED NEXT TRADING DAY.
        </p>
      </div>
    </div>
  );
}
