import {
  cotLevel,
  impliedLevel,
  rateDiffLevel,
  statusClass,
  volLevel,
} from '@/lib/terminal/signal-status';
import type { PairMeta, RegimeCall, SignalRow } from '@/lib/types';
import { fmt2, fmtInt } from '@/lib/utils/format';

type Row = { name: string; value: string; level: 'ELEVATED' | 'NORMAL' | 'LOW' };

function tableRows(signal: SignalRow): Row[] {
  return [
    {
      name: 'Rate diff 2Y',
      value: fmt2(signal.rate_diff_2y),
      level: rateDiffLevel(signal.rate_diff_2y),
    },
    {
      name: 'COT percentile',
      value: fmtInt(signal.cot_percentile),
      level: cotLevel(signal.cot_percentile),
    },
    {
      name: 'Realized vol 20D',
      value: fmt2(signal.realized_vol_20d),
      level: volLevel(signal.realized_vol_20d),
    },
    {
      name: 'Realized vol 5D',
      value: fmt2(signal.realized_vol_5d),
      level: volLevel(signal.realized_vol_5d),
    },
    {
      name: 'Implied vol 30D',
      value: signal.implied_vol_30d == null ? '—' : fmt2(signal.implied_vol_30d),
      level: impliedLevel(signal.implied_vol_30d),
    },
  ];
}

const cards: {
  key: keyof SignalRow | 'cot';
  label: string;
  sub: string;
  fmt: (s: SignalRow) => string;
}[] = [
  {
    key: 'rate_diff_2y',
    label: 'RATE DIFF 2Y',
    sub: '2Y spread',
    fmt: (s) => fmt2(s.rate_diff_2y),
  },
  {
    key: 'cot_percentile',
    label: 'COT %',
    sub: 'positioning',
    fmt: (s) => fmtInt(s.cot_percentile),
  },
  {
    key: 'realized_vol_20d',
    label: 'REAL VOL 20D',
    sub: 'ann.',
    fmt: (s) => fmt2(s.realized_vol_20d),
  },
  {
    key: 'realized_vol_5d',
    label: 'REAL VOL 5D',
    sub: 'ann.',
    fmt: (s) => fmt2(s.realized_vol_5d),
  },
  {
    key: 'implied_vol_30d',
    label: 'IMPLIED VOL 30D',
    sub: '30d',
    fmt: (s) => (s.implied_vol_30d == null ? '—' : fmt2(s.implied_vol_30d)),
  },
];

export function SignalsTab({
  pair: _pair,
  regime: _regime,
  signal,
  signalHistory,
}: {
  pair: PairMeta;
  regime: RegimeCall;
  signal: SignalRow;
  signalHistory: SignalRow[];
}) {
  const rows = tableRows(signal);
  return (
    <div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {cards.map((c) => (
          <div key={c.label} className="border border-[#1e1e1e] bg-[#0c0c0c] p-3">
            <p className="font-mono text-[8px] font-normal tracking-widest text-[#555]">
              {c.label}
            </p>
            <p className="mt-1 font-mono text-[18px] font-bold text-[#e8e8e8]">{c.fmt(signal)}</p>
            <p className="mt-0.5 font-mono text-[8px] text-[#555]">{c.sub}</p>
          </div>
        ))}
      </div>
      <div className="mt-6 space-y-0 border border-[#1e1e1e]">
        {rows.map((r) => (
          <div
            key={r.name}
            className="flex items-center justify-between border-b border-[#1e1e1e] px-3 py-2.5 last:border-b-0"
          >
            <span className="font-mono text-[10px] text-[#555]">{r.name}</span>
            <div className="flex items-center gap-3">
              <span className="font-mono text-[13px] text-[#e8e8e8]">{r.value}</span>
              <span className={statusClass(r.level)}>{r.level}</span>
            </div>
          </div>
        ))}
      </div>

      {signalHistory.length > 1 ? (
        <div className="mt-6 border border-[#1e1e1e]">
          <div className="border-b border-[#1e1e1e] bg-[#0c0c0c] px-3 py-2">
            <span className="font-mono text-[8px] tracking-widest text-[#555]">RECENT ROWS</span>
          </div>
          <div className="grid grid-cols-[1fr_1fr_1fr_1fr] gap-2 border-b border-[#1e1e1e] px-3 py-2 font-mono text-[8px] text-[#555]">
            <span>DATE</span>
            <span>SPOT</span>
            <span>2Y</span>
            <span>COT%</span>
          </div>
          <ul>
            {signalHistory.map((s) => (
              <li
                key={`${s.pair}-${s.date}`}
                className="grid grid-cols-4 gap-2 border-b border-[#111] px-3 py-2 font-mono text-[10px] text-[#e8e8e8] last:border-b-0"
              >
                <span>{s.date}</span>
                <span>{fmt2(s.spot)}</span>
                <span>{fmt2(s.rate_diff_2y)}</span>
                <span>{fmtInt(s.cot_percentile)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
