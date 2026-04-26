import { type BriefTabPayload, BriefTabs } from '@/app/(site)/brief/BriefTabs';
import { ErrorBoundaryCard } from '@/components/states';
import { PAIRS } from '@/lib/mock/data';
import type { Database } from '@/lib/supabase/database.types';
import { defaultSignalRow, mapSignalRow, mapValidationRow } from '@/lib/supabase/map-row';
import { getLatestBrief, getLatestSignals, getValidationLog } from '@/lib/supabase/queries';
import type { PairMeta, SignalRow, ValidationRow } from '@/lib/types';

type BriefRow = Database['public']['Tables']['brief']['Row'];

function utcToday(): string {
  return new Date().toISOString().slice(0, 10);
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
      signalByLabel[label] = mapSignalRow(sig.data[0]);
    } else {
      signalByLabel[label] = defaultSignalRow(label, briefDate);
    }
  }

  const validationRows: ValidationRow[] = (valRes.data ?? [])
    .map(mapValidationRow)
    .filter((r): r is ValidationRow => r != null);

  const topError = briefErrors[0];

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      {topError ? (
        <div className="mb-6">
          <ErrorBoundaryCard message={topError} tone="shell" />
        </div>
      ) : null}
      <div className="mb-8 border-b border-[#e5e5e5] pb-6">
        <p className="font-mono text-[10px] tracking-widest text-[#a0a0a0]">TODAY&apos;S BRIEF</p>
        <p className="mt-1 font-mono text-[12px] text-[#737373]">{utcToday()}</p>
        <h1 className="mt-3 font-sans text-[28px] font-extrabold tracking-tight text-[#0a0a0a] sm:text-[32px]">
          FX Regime Morning Brief
        </h1>
      </div>

      <div className="mb-10 bg-[#0a0a0a] px-5 py-5 text-[#e8e8e8]">
        <p className="font-sans text-[14px] italic leading-relaxed">
          Dollar index, Fed guidance, and risk tone drive G10 regimes. Cross-check the pair tabs
          below against your risk calendar.
        </p>
      </div>

      <BriefTabs
        briefByLabel={briefByLabel}
        signalByLabel={signalByLabel}
        validationRows={validationRows}
      />
    </div>
  );
}
