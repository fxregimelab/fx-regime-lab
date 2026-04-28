'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AreaSeries,
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries,
  LineStyle,
} from 'lightweight-charts';
import { useHistoricalData } from '@/lib/queries';

type SignalPoint = {
  date: string;
  spot?: number | null;
  rate_diff_2y?: number | null;
  rate_diff_10y?: number | null;
  cot_lev_money_net?: number | null;
};

type RegimePoint = {
  date: string;
  regime: string;
};

type RangeKey = '1M' | '3M' | '1Y' | '5Y' | 'MAX';

const REGIME_BAND_COLOR: Record<string, string> = {
  BULLISH: '#22c55e11',
  BEARISH: '#ef444411',
  NEUTRAL: '#73737311',
  VOL_EXPANDING: '#3b82f611',
  VOL_CONTRACTING: '#f59e0b11',
};

const RANGE_BTNS: RangeKey[] = ['1M', '3M', '1Y', '5Y', 'MAX'];

interface TradingViewChartProps {
  pairLabel: string;
  data?: SignalPoint[];
  regimeData?: RegimePoint[];
  color?: string;
}

function rangeSinceDate(range: Exclude<RangeKey, 'MAX'>) {
  const d = new Date();
  if (range === '1M') d.setMonth(d.getMonth() - 1);
  if (range === '3M') d.setMonth(d.getMonth() - 3);
  if (range === '1Y') d.setFullYear(d.getFullYear() - 1);
  if (range === '5Y') d.setFullYear(d.getFullYear() - 5);
  return d.toISOString().slice(0, 10);
}

export default function TradingViewChart({ pairLabel, data, regimeData, color = '#4BA3E3' }: TradingViewChartProps) {
  const [range, setRange] = useState<RangeKey>('1Y');
  const archiveQ = useHistoricalData(pairLabel, range === 'MAX');

  const pricePaneRef = useRef<HTMLDivElement>(null);
  const yieldPaneRef = useRef<HTMLDivElement>(null);
  const cotPaneRef = useRef<HTMLDivElement>(null);

  const archiveRows = useMemo(
    () =>
      (archiveQ.data ?? []).map((row) => ({
        date: row.date,
        spot: row.close,
        rate_diff_2y: null,
        rate_diff_10y: null,
        cot_lev_money_net: null,
      })),
    [archiveQ.data],
  );

  const filtered = useMemo(() => {
    const base = range === 'MAX' && archiveRows.length ? archiveRows : data ?? [];
    if (range === 'MAX') return base;
    const since = rangeSinceDate(range);
    return base.filter((row) => row.date >= since);
  }, [data, range, archiveRows]);

  useEffect(() => {
    if (!pricePaneRef.current || !yieldPaneRef.current || !cotPaneRef.current) return;
    if (!filtered.length || (range === 'MAX' && archiveQ.isPending)) return;

    const sharedOptions = {
      layout: {
        background: { type: ColorType.Solid as const, color: '#000000' },
        textColor: '#8a8a8a',
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: '#111111' },
        horzLines: { color: '#111111' },
      },
      autoSize: true,
      crosshair: {
        vertLine: {
          color: '#555',
          style: LineStyle.LargeDashed,
          width: 1,
          visible: true,
          labelVisible: true,
        },
        horzLine: {
          color: '#555',
          style: LineStyle.LargeDashed,
          width: 1,
          visible: true,
          labelVisible: true,
        },
      },
      localization: {
        priceFormatter: (value: number) => value.toLocaleString(undefined, { maximumFractionDigits: 4, minimumFractionDigits: 2 }),
      },
      rightPriceScale: {
        borderColor: '#111111',
      },
      timeScale: {
        borderColor: '#111111',
        timeVisible: true,
      },
    };

    const priceChart = createChart(pricePaneRef.current, {
      ...sharedOptions,
      height: 280,
    });
    const yieldChart = createChart(yieldPaneRef.current, {
      ...sharedOptions,
      height: 120,
    });
    const cotChart = createChart(cotPaneRef.current, {
      ...sharedOptions,
      height: 120,
    });

    // Ensure consistent Y-axis width for horizontal sync
    [priceChart, yieldChart, cotChart].forEach((c) => {
      c.applyOptions({
        rightPriceScale: {
          width: 80,
          autoScale: true,
          borderColor: '#111111',
        },
      });
    });

    const y2Series = yieldChart.addSeries(LineSeries, {
      color: '#22c55e',
      lineWidth: 1,
      priceLineVisible: false,
      title: 'SPREAD 2Y',
    });
    const y10Series = yieldChart.addSeries(LineSeries, {
      color: '#f59e0b',
      lineWidth: 1,
      priceLineVisible: false,
      title: 'SPREAD 10Y',
    });

    const cotSeries = cotChart.addSeries(HistogramSeries, {
      color: '#4b5563',
      base: 0,
      priceLineVisible: false,
      title: 'COT NET',
    });

    const priceData = filtered
      .filter((x) => x.spot != null)
      .map((x) => ({ time: x.date as `${number}-${number}-${number}`, value: Number(x.spot) }));
    const y2Data = filtered
      .filter((x) => x.rate_diff_2y != null)
      .map((x) => ({ time: x.date as `${number}-${number}-${number}`, value: Number(x.rate_diff_2y) }));
    const y10Data = filtered
      .filter((x) => x.rate_diff_10y != null)
      .map((x) => ({ time: x.date as `${number}-${number}-${number}`, value: Number(x.rate_diff_10y) }));
    const cotData = filtered
      .filter((x) => x.cot_lev_money_net != null)
      .map((x) => ({
        time: x.date as `${number}-${number}-${number}`,
        value: Number(x.cot_lev_money_net),
        color: Number(x.cot_lev_money_net) >= 0 ? '#22c55e88' : '#ef444488',
      }));

    y2Series.setData(y2Data);
    y10Series.setData(y10Data);
    cotSeries.setData(cotData);

    if (regimeData?.length && priceData.length) {
      const regimeMap = new Map(regimeData.map((r) => [r.date, r.regime]));
      let lastRegime = '';
      let segmentStart = '';
      const segments: Array<{ from: string; to: string; regime: string }> = [];

      for (const row of priceData) {
        const regime = regimeMap.get(row.time) ?? 'NEUTRAL';
        if (!lastRegime) {
          lastRegime = regime;
          segmentStart = row.time;
          continue;
        }
        if (regime !== lastRegime) {
          segments.push({ from: segmentStart, to: row.time, regime: lastRegime });
          segmentStart = row.time;
          lastRegime = regime;
        }
      }
      segments.push({
        from: segmentStart || priceData[0].time,
        to: priceData[priceData.length - 1].time,
        regime: lastRegime || 'NEUTRAL',
      });

      for (const seg of segments) {
        const fill = REGIME_BAND_COLOR[seg.regime] ?? '#73737311';
        const segmentData = priceData.filter((row) => row.time >= seg.from && row.time <= seg.to);
        if (!segmentData.length) continue;
        const area = priceChart.addSeries(AreaSeries, {
          topColor: fill,
          bottomColor: fill,
          lineColor: 'transparent',
          lastValueVisible: false,
          crosshairMarkerVisible: false,
          priceLineVisible: false,
        });
        area.setData(segmentData);
      }
    }

    const priceSeries = priceChart.addSeries(LineSeries, {
      color,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
    });
    priceSeries.setData(priceData);

    const charts = [priceChart, yieldChart, cotChart];
    const mainSeries = [priceSeries, y2Series, cotSeries];

    let syncing = false;

    charts.forEach((chart, sourceIdx) => {
      chart.timeScale().subscribeVisibleLogicalRangeChange((rangeVal) => {
        if (!rangeVal || syncing) return;
        syncing = true;
        charts.forEach((target, targetIdx) => {
          if (targetIdx !== sourceIdx) {
            target.timeScale().setVisibleLogicalRange(rangeVal);
          }
        });
        syncing = false;
      });

      chart.subscribeCrosshairMove((param) => {
        if (syncing) return;
        syncing = true;
        charts.forEach((target, targetIdx) => {
          if (targetIdx === sourceIdx) return;
          if (!param.time) {
            target.clearCrosshairPosition();
            return;
          }
          let value: number | undefined;
          for (const seriesValue of param.seriesData.values()) {
            const candidate = seriesValue as { value?: number; close?: number };
            if (candidate?.value != null || candidate?.close != null) {
              value = candidate.value ?? candidate.close;
              break;
            }
          }
          if (value == null) return;
          target.setCrosshairPosition(value, param.time, mainSeries[targetIdx]);
        });
        syncing = false;
      });
    });

    priceChart.timeScale().fitContent();
    yieldChart.timeScale().fitContent();
    cotChart.timeScale().fitContent();

    return () => {
      priceChart.remove();
      yieldChart.remove();
      cotChart.remove();
    };
  }, [filtered, regimeData, color, range, archiveQ.isPending]);

  return (
    <div className="w-full h-full flex flex-col tabular-nums">
      <div className="flex-1 border border-[#111] bg-[#000000] overflow-hidden">
        {range === 'MAX' && archiveQ.isPending ? (
          <div className="w-full h-full flex items-center justify-center">
            <p className="font-mono text-[11px] text-[#666] tracking-widest">Loading Historical Archive...</p>
          </div>
        ) : range === 'MAX' && !archiveRows.length ? (
          <div className="w-full h-full flex items-center justify-center">
            <p className="font-mono text-[11px] text-[#666] tracking-widest">Historical archive unavailable.</p>
          </div>
        ) : (
          <div className="w-full h-full grid grid-rows-[280px_120px_120px]">
            <div ref={pricePaneRef} className="border-b border-[#111]" />
            <div ref={yieldPaneRef} className="border-b border-[#111]" />
            <div ref={cotPaneRef} />
          </div>
        )}
      </div>

      <div className="mt-2 flex items-center gap-1">
        {RANGE_BTNS.map((btn) => {
          const active = btn === range;
          return (
            <button
              key={btn}
              type="button"
              onClick={() => setRange(btn)}
              className={`h-6 px-3 border border-[#333] bg-[#000000] font-mono text-[10px] tracking-widest ${
                active ? 'text-white' : 'text-[#888] hover:text-[#b3b3b3]'
              }`}
            >
              [ {btn} ]
            </button>
          );
        })}
      </div>
    </div>
  );
}
