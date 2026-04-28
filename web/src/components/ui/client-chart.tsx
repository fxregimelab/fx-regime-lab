'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, LineSeries } from 'lightweight-charts';

type SpotPoint = { time: string; value: number };

interface ClientChartProps {
  pairLabel: string;
  data?: { date: string; spot: number | null }[];
  color?: string;
}

export default function ClientChart({ pairLabel, data, color = '#4BA3E3' }: ClientChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const lineSeriesRef = useRef<any>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#666',
        fontSize: 10,
        fontFamily: 'JetBrains Mono, monospace',
      },
      grid: {
        vertLines: { color: '#141414' },
        horzLines: { color: '#141414' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 360,
      timeScale: {
        borderColor: '#1e1e1e',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#1e1e1e',
      },
    });

    // v5 API uses addSeries
    const lineSeries = chart.addSeries(LineSeries, {
      color: color,
      lineWidth: 2,
      crosshairMarkerVisible: true,
      priceLineVisible: false,
    });

    chartRef.current = chart;
    lineSeriesRef.current = lineSeries;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [color]);

  useEffect(() => {
    if (lineSeriesRef.current && data) {
      const formattedData = data
        .filter((d) => d.spot != null)
        .map((d) => ({
          time: d.date,
          value: Number(d.spot),
        }));
      
      if (formattedData.length > 0) {
        lineSeriesRef.current.setData(formattedData);
        chartRef.current?.timeScale().fitContent();
      }
    }
  }, [data]);

  return <div ref={chartContainerRef} className="w-full h-full" />;
}
