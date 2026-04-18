// TradingView Lightweight Charts wrapper
'use client';

import { useEffect, useRef } from 'react';
import {
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type Time,
} from 'lightweight-charts';

export type TimePoint = LineData<Time>;

type Props = {
  data: TimePoint[];
  className?: string;
};

export function TimeSeriesChart({ data, className }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line', Time> | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const chart = createChart(el, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#a3a3a3',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.06)' },
        horzLines: { color: 'rgba(255,255,255,0.06)' },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      height: 280,
    });
    const series = chart.addSeries(LineSeries, { color: '#e8a045', lineWidth: 2 });
    chartRef.current = chart;
    seriesRef.current = series;
    series.setData(data);

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: el.clientWidth });
    });
    ro.observe(el);
    chart.applyOptions({ width: el.clientWidth });

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [data]);

  useEffect(() => {
    seriesRef.current?.setData(data);
  }, [data]);

  return <div ref={containerRef} className={className ?? 'lw-chart-container'} />;
}
