'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, LineSeries, AreaSeries } from 'lightweight-charts';

// Regime → semi-transparent fill color
const REGIME_BAND_COLOR: Record<string, string> = {
  BULLISH: '#22c55e22',
  BEARISH: '#ef444422',
  NEUTRAL: '#73737322',
  VOL_EXPANDING: '#3b82f622',
  VOL_CONTRACTING: '#f59e0b22',
};

interface ClientChartProps {
  pairLabel: string;
  data?: { date: string; spot: number | null }[];
  regimeData?: { date: string; regime: string; confidence: number }[];
  color?: string;
}

export default function ClientChart({
  pairLabel: _pairLabel,
  data,
  regimeData,
  color = '#4BA3E3',
}: ClientChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);

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

    chartRef.current = chart;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [color]);

  useEffect(() => {
    if (!chartRef.current || !data) return;

    const validSpots = data.filter((d) => d.spot != null);
    if (!validSpots.length) return;

    const chart = chartRef.current;

    // --- Regime background bands ---
    if (regimeData?.length) {
      const regimeMap = new Map(regimeData.map((r) => [r.date, r.regime]));
      const spotValues = validSpots.map((d) => Number(d.spot));
      const minVal = Math.min(...spotValues);
      const maxVal = Math.max(...spotValues);
      const pad = (maxVal - minVal) * 0.15;
      const bandTop = maxVal + pad;

      // Group consecutive dates with same regime into bands
      const groups: { from: string; to: string; regime: string }[] = [];
      let curRegime = '';
      let curFrom = '';

      for (const s of validSpots) {
        const r = regimeMap.get(s.date) ?? 'NEUTRAL';
        if (r !== curRegime) {
          if (curRegime) groups.push({ from: curFrom, to: s.date, regime: curRegime });
          curRegime = r;
          curFrom = s.date;
        }
      }
      if (curRegime) {
        groups.push({ from: curFrom, to: validSpots[validSpots.length - 1].date, regime: curRegime });
      }

      for (const g of groups) {
        const bandColor = REGIME_BAND_COLOR[g.regime] ?? '#73737322';
        const areaSeries = chart.addSeries(AreaSeries, {
          lineColor: 'transparent',
          topColor: bandColor,
          bottomColor: bandColor,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        areaSeries.setData([
          { time: g.from as `${number}-${number}-${number}`, value: bandTop },
          { time: g.to as `${number}-${number}-${number}`, value: bandTop },
        ]);
      }
    }

    // --- Price line (always on top) ---
    const lineSeries = chart.addSeries(LineSeries, {
      color: color,
      lineWidth: 2,
      crosshairMarkerVisible: true,
      priceLineVisible: false,
    });

    const formattedData = validSpots.map((d) => ({
      time: d.date as `${number}-${number}-${number}`,
      value: Number(d.spot),
    }));
    lineSeries.setData(formattedData);
    chart.timeScale().fitContent();
  }, [data, regimeData, color]);

  return <div ref={chartContainerRef} className="w-full h-full" />;
}
