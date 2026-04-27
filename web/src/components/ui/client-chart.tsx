'use client';

import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

type SpotPoint = { time: string; value: number };

interface ChartWithLineSeries {
  addLineSeries: (opts: { color?: string; lineWidth?: number }) => { setData: (d: SpotPoint[]) => void };
}

export default function ClientChart({ pairLabel }: { pairLabel: string }) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: { background: { color: 'transparent' }, textColor: '#444' },
      grid: { vertLines: { color: '#1a1a1a' }, horzLines: { color: '#1a1a1a' } },
      width: chartContainerRef.current.clientWidth,
      height: 360,
    });

    const lineSeries = (chart as unknown as ChartWithLineSeries).addLineSeries({ color: '#4BA3E3', lineWidth: 2 });
    lineSeries.setData([
      { time: '2026-04-10', value: 1.07 },
      { time: '2026-04-11', value: 1.072 },
      { time: '2026-04-12', value: 1.071 },
      { time: '2026-04-13', value: 1.074 },
      { time: '2026-04-14', value: 1.073 },
    ]);

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [pairLabel]);

  return <div ref={chartContainerRef} className="w-full h-full" />;
}
