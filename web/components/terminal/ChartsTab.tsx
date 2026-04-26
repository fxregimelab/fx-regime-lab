'use client';

import type { PairMeta } from '@/lib/types';
import { LineSeries, createChart, type Time } from 'lightweight-charts';
import { useEffect, useRef } from 'react';

export function ChartsTab({
  pair,
  pairColor,
  equityDates,
  equitySeries,
}: {
  pair: PairMeta;
  pairColor: string;
  equityDates: string[];
  equitySeries: Record<string, number[]>;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const y = equitySeries[pair.label];
    if (!Array.isArray(y) || y.length === 0) return;

    const chart = createChart(el, {
      width: el.clientWidth,
      height: 280,
      layout: {
        background: { color: '#080808' },
        textColor: '#555',
      },
      grid: {
        vertLines: { color: '#1e1e1e' },
        horzLines: { color: '#1e1e1e' },
      },
      rightPriceScale: { borderColor: '#1e1e1e' },
      timeScale: { borderColor: '#1e1e1e', timeVisible: true },
    });
    const line = chart.addSeries(LineSeries, {
      color: pairColor,
      lineWidth: 2,
    });

    const data = equityDates.map((d, i) => ({
      time: d as Time,
      value: y[i] ?? 0,
    }));
    line.setData(data);
    chart.timeScale().fitContent();

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        chart.applyOptions({ width: w });
      }
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [pair.label, pairColor, equityDates, equitySeries]);

  return (
    <div>
      <div ref={ref} className="h-[280px] w-full min-h-0" />
      <p className="mt-3 font-sans text-[12px] text-[#555]">
        {equityDates.length === 0
          ? 'No equity data yet — run the pipeline first.'
          : `${equityDates[0]} → ${equityDates[equityDates.length - 1]}`}
      </p>
    </div>
  );
}
