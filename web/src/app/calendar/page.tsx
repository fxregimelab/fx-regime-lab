'use client';

import { useState } from 'react';
import { Nav } from '@/components/layout/nav';
import { Footer } from '@/components/layout/footer';
import { MacroPulseBar, PULSE_BAR_H } from '@/components/ui/macro-pulse-bar';
import { useUpcomingMacroEvents } from '@/lib/queries';
import type { Database } from '@/lib/supabase/database.types';
import { motion, AnimatePresence } from 'framer-motion';

const SHELL_NAV_H = 54;
const SHELL_TOP_OFFSET = PULSE_BAR_H + SHELL_NAV_H;

type MacroEventRow = Database['public']['Tables']['macro_events']['Row'];

const HARDCODED_CONTEXT: Record<string, { bg: string; impact: string; history: string }> = {
  'Nonfarm Payrolls': {
    bg: 'Measures the change in the number of employed people during the previous month, excluding the farming industry.',
    impact: 'A higher than expected print usually strengthens the USD as it implies a hotter economy and higher rates.',
    history: 'Last 3 prints have surprised to the upside, averaging 250k+.'
  },
  'CPI': {
    bg: 'Consumer Price Index measures the average change over time in the prices paid by urban consumers for a market basket of consumer goods and services.',
    impact: 'Higher inflation prints pressure central banks to hike rates, typically boosting the domestic currency.',
    history: 'Core CPI has remained sticky above 3.0% for the past 4 months.'
  },
  'Fed': {
    bg: 'The Federal Reserve\'s decision on short-term interest rates and monetary policy.',
    impact: 'A rate hike or hawkish forward guidance usually strengthens the USD. A cut or dovish tone weakens it.',
    history: 'Markets are currently pricing in fewer cuts than previously anticipated.'
  },
  'ECB': {
    bg: 'The European Central Bank\'s decision on short-term interest rates.',
    impact: 'Hawkishness strengthens the EUR, narrowing the rate differential with the US.',
    history: 'ECB has signaled a willingness to diverge from the Fed if inflation allows.'
  },
  'BOJ': {
    bg: 'The Bank of Japan\'s monetary policy decision.',
    impact: 'Any step away from ultra-loose monetary policy (YCC) typically causes sharp JPY appreciation.',
    history: 'Gradual normalization continues after ending negative interest rates.'
  }
};

function getContext(eventName: string) {
  for (const [key, val] of Object.entries(HARDCODED_CONTEXT)) {
    if (eventName.includes(key)) {
      return val;
    }
  }
  return {
    bg: 'High-impact macroeconomic data release or central bank event.',
    impact: 'Deviation from consensus estimates will drive short-term volatility in the listed pairs.',
    history: 'Historical tracking not available for this specific event type.'
  };
}

export default function CalendarPage() {
  const eventsQ = useUpcomingMacroEvents();
  const events = (eventsQ.data ?? []) as MacroEventRow[];
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const selectedEvent = events.find(e => e.id === selectedId) || events[0];

  return (
    <>
      <MacroPulseBar />
      <Nav />
      <main className="min-h-screen bg-white text-[#0a0a0a]" style={{ marginTop: `${SHELL_TOP_OFFSET}px` }}>
        <section className="max-w-[1152px] mx-auto px-6 py-10">
          <h1 className="font-sans text-3xl font-bold mb-2 text-white">Macro Event Dossier</h1>
          <p className="font-mono text-[11px] text-[#8a8a8a] tracking-widest mb-6">
            G10 FX CALENDAR · IMPACT MATRIX · AI CONTEXT
          </p>
          
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6 items-start">
            {/* Left Pane: Calendar List */}
            <div className="border border-[#1e1e1e] bg-[#0a0a0a]">
              <div className="px-5 py-3 border-b border-[#1a1a1a] bg-[#0c0c0c]">
                <span className="font-mono text-[10px] text-[#888] tracking-widest">UPCOMING RELEASES</span>
              </div>
              {eventsQ.isPending ? (
                <div className="h-64 flex items-center justify-center animate-pulse">
                  <span className="font-mono text-[11px] text-[#666]">LOADING EVENTS...</span>
                </div>
              ) : (
                <div className="divide-y divide-[#1a1a1a]">
                  {events.map((e) => {
                    const isSelected = selectedEvent?.id === e.id;
                    return (
                      <div 
                        key={e.id}
                        onClick={() => setSelectedId(e.id)}
                        className={`p-4 cursor-pointer transition-colors ${isSelected ? 'bg-[#141414] border-l-2 border-l-white' : 'hover:bg-[#111] border-l-2 border-l-transparent'}`}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <span className="font-mono text-[11px] text-[#888] tabular-nums">{e.date}</span>
                          <span className={`font-mono text-[9px] px-1.5 py-0.5 ${e.impact === 'HIGH' ? 'bg-[#451a1a] text-[#ef4444]' : 'bg-[#1a1a1a] text-[#aaa]'}`}>{e.impact}</span>
                        </div>
                        <p className={`font-sans text-[14px] font-semibold ${isSelected ? 'text-white' : 'text-[#dcdcdc]'}`}>{e.event}</p>
                        <div className="flex gap-2 mt-2">
                          {e.pairs.map(p => (
                            <span key={p} className="font-mono text-[9px] text-[#666] tracking-widest border border-[#333] px-1">{p}</span>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right Pane: Event Dossier */}
            <div className="sticky top-[90px]">
              <AnimatePresence mode="wait">
                {selectedEvent && (
                  <motion.div 
                    key={selectedEvent.id}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    transition={{ duration: 0.15 }}
                    className="border border-[#1e1e1e] bg-[#0a0a0a] flex flex-col"
                  >
                    <div className="px-5 py-3 border-b border-[#1a1a1a] bg-[#0c0c0c] flex justify-between items-center">
                      <span className="font-mono text-[10px] text-[#888] tracking-widest">EVENT DOSSIER</span>
                      <span className="font-mono text-[10px] text-[#888] tabular-nums">{selectedEvent.date}</span>
                    </div>
                    <div className="p-5">
                      <h2 className="font-sans text-[18px] font-bold text-white mb-6 leading-snug">{selectedEvent.event}</h2>
                      
                      <div className="space-y-6">
                        <div>
                          <span className="block font-mono text-[9px] text-[#555] tracking-widest mb-1.5 border-b border-[#222] pb-1">[ EXPECTED FX IMPACT ]</span>
                          <p className="font-sans text-[13px] text-[#dcdcdc] leading-relaxed tabular-nums">
                            {getContext(selectedEvent.event).impact}
                          </p>
                        </div>
                        <div>
                          <span className="block font-mono text-[9px] text-[#555] tracking-widest mb-1.5 border-b border-[#222] pb-1">[ HISTORICAL CONTEXT ]</span>
                          <p className="font-sans text-[13px] text-[#dcdcdc] leading-relaxed tabular-nums">
                            {getContext(selectedEvent.event).history}
                          </p>
                        </div>
                        <div>
                          <span className="block font-mono text-[9px] text-[#555] tracking-widest mb-1.5 border-b border-[#222] pb-1 flex justify-between">
                            [ AI ANALYSIS ]
                            {selectedEvent.ai_brief && <span className="text-[#22c55e]">AVAILABLE</span>}
                          </span>
                          <div className="bg-[#050505] p-3 border border-[#1a1a1a]">
                            <p className="font-mono text-[11px] text-[#737373] leading-relaxed tabular-nums">
                              {selectedEvent.ai_brief ? selectedEvent.ai_brief : 'System analysis pending for this cycle. Pipeline has not yet generated an AI brief for this event.'}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
