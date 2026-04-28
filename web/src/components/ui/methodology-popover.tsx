'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

type MetricKey = 'cot' | 'rateDiff' | 'realizedVol' | 'composite';

const METHODOLOGY_DATA: Record<MetricKey, { def: string; bg: string; action: string }> = {
  cot: {
    def: 'CFTC weekly non-commercial net positions, normalized to a 3-year percentile rank.',
    bg: 'Tracks speculative crowd positioning. Extreme crowding historically precedes trend exhaustion.',
    action: 'A COT reading above 85% suggests a crowded trade prone to reversal.',
  },
  rateDiff: {
    def: 'The spread between 2-year or 10-year sovereign yields of the pair\'s underlying economies.',
    bg: 'Capital flows toward higher real yields. This is the primary driver of medium-term FX regime direction.',
    action: 'Widening spreads support the higher-yielding currency. A changing spread regime often flags a macro shift.',
  },
  realizedVol: {
    def: '5-day and 20-day historical volatility compared to 30-day implied volatility expectations.',
    bg: 'Regimes transition when volatility expands. We gate new regimes unless realized volatility confirms the breakout.',
    action: 'Expanding realized vol > 90th percentile confirms a regime break. Contracting vol favors mean-reversion.',
  },
  composite: {
    def: 'The weighted sum of normalized Rate Diff, COT, Volatility, and OI signals.',
    bg: 'Single signals are noisy. A composite score filters false positives and determines the final Regime label.',
    action: 'A score > +1.5 strongly indicates a BULLISH regime; < -1.5 indicates BEARISH.',
  }
};

export function MethodologyPopover({ metricKey }: { metricKey: MetricKey }) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const data = METHODOLOGY_DATA[metricKey];

  return (
    <div className="relative inline-block ml-1.5" ref={containerRef}>
      <button 
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(!open); }}
        className="text-[#666] hover:text-white transition-colors cursor-help font-mono text-[9px]"
        title="Methodology details"
      >
        [?]
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 5 }}
            transition={{ duration: 0.15 }}
            className="absolute z-[9999] bottom-full mb-2 right-0 md:left-1/2 md:-translate-x-1/2 w-[280px] bg-[#050505] border border-[#1a1a1a] shadow-none p-4 text-left pointer-events-auto rounded-none"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 border-b border-[#222] pb-2">
              <span className="font-mono text-[10px] text-[#737373] tracking-widest uppercase">Methodology</span>
            </div>
            
            <div className="space-y-3">
              <div>
                <span className="block font-mono text-[9px] text-[#555] tracking-widest mb-0.5">[ DEFINITION ]</span>
                <span className="font-sans text-[12px] text-[#dcdcdc] leading-snug tabular-nums">{data.def}</span>
              </div>
              <div>
                <span className="block font-mono text-[9px] text-[#555] tracking-widest mb-0.5">[ BACKGROUND ]</span>
                <span className="font-sans text-[12px] text-[#aaa] leading-snug tabular-nums">{data.bg}</span>
              </div>
              <div>
                <span className="block font-mono text-[9px] text-[#555] tracking-widest mb-0.5">[ INTERPRETATION ]</span>
                <span className="font-sans text-[12px] text-[#22c55e] leading-snug tabular-nums">{data.action}</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
