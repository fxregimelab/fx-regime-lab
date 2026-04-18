// Validation log table
'use client';

import type { ValidationRow } from '@/lib/types/validation';

type Props = {
  rows: ValidationRow[];
  loading?: boolean;
  /** `shell`: light public page. `terminal`: dark desk (default). */
  variant?: 'terminal' | 'shell';
};

export function ValidationTable({ rows, loading, variant = 'terminal' }: Props) {
  const shell = variant === 'shell';
  const wrap = shell
    ? 'overflow-x-auto rounded-md border border-neutral-200 bg-white'
    : 'overflow-x-auto rounded-md border border-neutral-800';
  const table = shell
    ? 'shell-validation-table min-w-full border-collapse font-mono text-[11px] text-neutral-800'
    : 'min-w-full border-collapse font-mono text-[11px] text-neutral-300';
  const thead = shell ? 'bg-neutral-100 text-neutral-600' : 'bg-black/40 text-neutral-500';
  const rowBorder = shell ? 'border-t border-neutral-200' : 'border-t border-neutral-800';
  const emptyMsg = shell ? 'text-neutral-600' : 'text-neutral-500';

  if (loading) {
    return <p className={`font-mono text-xs ${emptyMsg}`}>Loading validation…</p>;
  }
  if (!rows.length) {
    return <p className={`font-mono text-xs ${emptyMsg}`}>No validation rows.</p>;
  }

  const fmtConfidence = (conf: number | null) => {
    if (conf == null || Number.isNaN(conf)) return '—';
    const pct = conf <= 1 ? Math.round(conf * 100) : Math.round(conf);
    return `${pct}%`;
  };

  const outcome1d = (correct: boolean | null) => {
    if (correct == null) {
      return <span className={shell ? 'text-neutral-400' : 'text-neutral-500'}>—</span>;
    }
    if (correct) {
      return (
        <span className={shell ? 'text-emerald-600' : 'text-emerald-400'} aria-label="Correct">
          ✓
        </span>
      );
    }
    return (
      <span className={shell ? 'text-red-600' : 'text-red-400'} aria-label="Incorrect">
        ✗
      </span>
    );
  };

  return (
    <div className={wrap}>
      <table className={table}>
        <thead className={thead}>
          <tr>
            <th className="px-2 py-2 text-left">Date</th>
            <th className="px-2 py-2 text-left">Pair</th>
            <th className="px-2 py-2 text-left">Pred</th>
            <th className="px-2 py-2 text-left">Actual</th>
            <th className="px-2 py-2 text-right">Conf.</th>
            <th
              className="px-2 py-2 text-right"
              title="NEUTRAL predictions are not scored for directional accuracy."
            >
              1d
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className={rowBorder}>
              <td className="px-2 py-1">
                {shell ? (
                  <time dateTime={r.date} title={r.date} className="tabular-nums">
                    <span className="hidden sm:inline">{r.date}</span>
                    <span className="sm:hidden">
                      {r.date.length >= 10 ? r.date.slice(5, 10) : r.date}
                    </span>
                  </time>
                ) : (
                  r.date
                )}
              </td>
              <td className="px-2 py-1">{r.pair}</td>
              <td className="px-2 py-1">{r.predicted_direction ?? '—'}</td>
              <td className="px-2 py-1">{r.actual_direction ?? '—'}</td>
              <td className="px-2 py-1 text-right tabular-nums">{fmtConfidence(r.confidence)}</td>
              <td className="px-2 py-1 text-right">{outcome1d(r.correct_1d)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p
        className={`border-t px-2 py-2 font-sans text-[10px] leading-snug ${shell ? 'border-neutral-200 text-neutral-500' : 'border-neutral-800 text-neutral-500'}`}
      >
        NEUTRAL predictions are not scored for directional accuracy.
      </p>
    </div>
  );
}
