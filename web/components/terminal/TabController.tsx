'use client';

import type { HistoryRow, MacroEvent, PairMeta, RegimeCall, SignalRow } from '@/lib/types';
import { useState } from 'react';

import { AiTab } from './AiTab';
import { AttributionTab } from './AttributionTab';
import { CalendarTab } from './CalendarTab';
import { ChartsTab } from './ChartsTab';
import { HistoryTab } from './HistoryTab';
import { SignalsTab } from './SignalsTab';

export type DeskTabId = 'signals' | 'history' | 'charts' | 'attribution' | 'calendar' | 'ai';

const TABS: { id: DeskTabId; label: string }[] = [
  { id: 'signals', label: 'SIGNALS' },
  { id: 'history', label: 'HISTORY' },
  { id: 'charts', label: 'CHARTS' },
  { id: 'attribution', label: 'ATTRIBUTION' },
  { id: 'calendar', label: 'CALENDAR' },
  { id: 'ai', label: 'AI' },
];

export function TabController({
  pair,
  pairColor,
  regime,
  signal,
  signalHistory,
  history,
  events,
  aiAnalysis,
  aiPrimaryDriver,
  aiFetchError,
  equityDates,
  equitySeries,
}: {
  pair: PairMeta;
  pairColor: string;
  regime: RegimeCall;
  signal: SignalRow;
  signalHistory: SignalRow[];
  history: HistoryRow[];
  events: MacroEvent[];
  aiAnalysis: string | null;
  aiPrimaryDriver: string | null;
  aiFetchError: string | null;
  equityDates: string[];
  equitySeries: Record<string, number[]>;
}) {
  const [active, setActive] = useState<DeskTabId>('signals');

  return (
    <div>
      <div className="flex overflow-x-auto border-b border-[#1e1e1e] bg-[#080808]">
        {TABS.map((t) => {
          const isOn = active === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setActive(t.id)}
              className={
                isOn
                  ? `shrink-0 border-b-2 px-3 py-3 font-mono text-[10px] font-bold tracking-widest text-[#e8e8e8] ${borderActive(pairColor)}`
                  : 'shrink-0 border-b-2 border-transparent px-3 py-3 font-mono text-[10px] font-normal tracking-widest text-[#555] hover:text-[#999]'
              }
            >
              {t.label}
            </button>
          );
        })}
      </div>
      <div className="pt-4">
        {active === 'signals' && (
          <SignalsTab pair={pair} regime={regime} signal={signal} signalHistory={signalHistory} />
        )}
        {active === 'history' && <HistoryTab history={history} pairColor={pairColor} />}
        {active === 'charts' && (
          <ChartsTab
            pair={pair}
            pairColor={pairColor}
            equityDates={equityDates}
            equitySeries={equitySeries}
          />
        )}
        {active === 'attribution' && (
          <AttributionTab
            signal={signal}
            pairColor={pairColor}
            signalComposite={regime.signal_composite}
          />
        )}
        {active === 'calendar' && <CalendarTab pair={pair} events={events} />}
        {active === 'ai' && (
          <AiTab
            pair={pair}
            analysis={aiAnalysis}
            primaryDriver={aiPrimaryDriver}
            fetchError={aiFetchError}
          />
        )}
      </div>
    </div>
  );
}

function borderActive(color: string): string {
  if (color === '#4BA3E3') return 'border-[#4BA3E3]';
  if (color === '#F5923A') return 'border-[#F5923A]';
  return 'border-[#D94030]';
}
