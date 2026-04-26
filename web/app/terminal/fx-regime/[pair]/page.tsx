import { ErrorBoundaryCard } from '@/components/states';
import { MobileDrawer } from '@/components/terminal/MobileDrawer';
import { PairTopStrip } from '@/components/terminal/PairTopStrip';
import { TabController } from '@/components/terminal/TabController';
import { TerminalSidebar } from '@/components/terminal/TerminalSidebar';
import { PAIRS } from '@/lib/mock/data';
import type { Database } from '@/lib/supabase/database.types';
import {
  defaultSignalRow,
  mapHistoryRow,
  mapMacroEventRow,
  mapRegimeCallRow,
  mapSignalRow,
} from '@/lib/supabase/map-row';
import {
  getLatestBrief,
  getLatestRegimeCalls,
  getLatestSignals,
  getRegimeHistory,
  getUpcomingMacroEvents,
} from '@/lib/supabase/queries';
import { notFound } from 'next/navigation';

type BriefRow = Database['public']['Tables']['brief']['Row'];

export function generateStaticParams() {
  return PAIRS.map((p) => ({ pair: p.urlSlug }));
}

export default async function TerminalPairDeskPage({
  params,
}: {
  params: Promise<{ pair: string }>;
}) {
  const { pair: slug } = await params;
  const pair = PAIRS.find((p) => p.urlSlug === slug);
  if (!pair) notFound();

  const [regimeRes, sigRes, histRes, briefRes, eventsRes] = await Promise.all([
    getLatestRegimeCalls(),
    getLatestSignals(pair.label),
    getRegimeHistory(pair.label),
    getLatestBrief(pair.label),
    getUpcomingMacroEvents(),
  ]);

  if (regimeRes.error) {
    return (
      <div className="px-4 py-8 sm:px-6">
        <ErrorBoundaryCard tone="terminal" message={regimeRes.error.message} />
      </div>
    );
  }

  const regimeRows = (regimeRes.data ?? []).map(mapRegimeCallRow);
  const regime = regimeRows.find((r) => r.pair === pair.label);
  if (!regime) {
    return (
      <div className="px-4 py-8 font-mono text-[12px] text-[#ef4444]">
        No regime call found for {pair.label}. Run the pipeline or check Supabase.
      </div>
    );
  }

  const signalRows = sigRes.error ? [] : (sigRes.data ?? []).map(mapSignalRow);
  const signal = signalRows[0] ?? defaultSignalRow(pair.label, regime.date);

  const history = histRes.error ? [] : (histRes.data ?? []).map(mapHistoryRow);
  const events = eventsRes.error ? [] : (eventsRes.data ?? []).map(mapMacroEventRow);

  let aiAnalysis: string | null = null;
  let aiPrimaryDriver: string | null = null;
  const aiFetchError: string | null = briefRes.error?.message ?? null;
  if (!briefRes.error && briefRes.data?.[0]) {
    const br = briefRes.data[0] as BriefRow;
    aiAnalysis = br.analysis;
    aiPrimaryDriver = br.primary_driver;
  }

  return (
    <div className="pb-20 lg:pb-0">
      <PairTopStrip pair={pair} regime={regime} signal={signal} />
      <div className="grid lg:grid-cols-[1fr_320px] lg:gap-0">
        <div className="px-4 py-4 sm:px-6 sm:py-5">
          <TabController
            pair={pair}
            pairColor={pair.pairColor}
            regime={regime}
            signal={signal}
            signalHistory={signalRows}
            history={history}
            events={events}
            aiAnalysis={aiAnalysis}
            aiPrimaryDriver={aiPrimaryDriver}
            aiFetchError={aiFetchError}
          />
        </div>
        <TerminalSidebar
          pair={pair}
          events={events}
          aiAnalysis={aiAnalysis}
          aiPrimaryDriver={aiPrimaryDriver}
          aiFetchError={aiFetchError}
        />
      </div>
      <MobileDrawer
        pair={pair}
        events={events}
        aiAnalysis={aiAnalysis}
        aiPrimaryDriver={aiPrimaryDriver}
        aiFetchError={aiFetchError}
      />
    </div>
  );
}
