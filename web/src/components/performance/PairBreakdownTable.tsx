import { normalizeProp } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import type { ValidationStats } from "@/lib/supabase/queries";

interface PairBreakdownTableProps {
  statsT5: ValidationStats[];
  statsT20: ValidationStats[];
}

function fmtPct(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${((normalizeProp(value) ?? 0) * 100).toFixed(1)}%`;
}

function fmtBrier(value: number | null | undefined) {
  return value == null || !Number.isFinite(value) ? "—" : value.toFixed(3);
}

export function PairBreakdownTable({
  statsT5,
  statsT20,
}: PairBreakdownTableProps) {
  const t5Map = new Map(statsT5.map((stats) => [stats.pair, stats]));
  const t20Map = new Map(statsT20.map((stats) => [stats.pair, stats]));
  const labels = [...PAIRS.map((pair) => pair.display), "ALL"];

  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
      <div className="px-5 py-3 border-b border-[var(--color-border)]">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
          Per-pair validation
        </p>
      </div>
      <div className="overflow-x-auto">
        <table
          className="w-full border-collapse font-mono text-[11px]"
          aria-label="Per-pair directional performance by published call"
        >
          <thead>
            <tr className="border-b border-[var(--color-border)] bg-[var(--color-elevated)]">
              {[
                "PAIR",
                "T+5 ACC",
                "T+5 SCORED / ALL CALLS",
                "T+5 BRIER N",
                "T+20 ACC",
                "T+20 SCORED / ALL CALLS",
                "T+20 BRIER N",
              ].map((heading) => (
                <th
                  key={heading}
                  scope="col"
                  className="px-4 py-2.5 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] font-semibold uppercase whitespace-nowrap"
                >
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {labels.map((label, index) => {
              const t5 = t5Map.get(label);
              const t20 = t20Map.get(label);
              return (
                <tr
                  key={label}
                  className={`border-b border-[var(--color-border-subtle)] last:border-b-0 ${label === "ALL" ? "border-t-2 font-bold" : index % 2 === 1 ? "bg-[var(--color-elevated)]" : "bg-[var(--color-surface)]"}`}
                >
                  <th
                    scope="row"
                    className="px-4 py-2.5 text-[var(--color-text-secondary)] whitespace-nowrap font-medium text-left"
                  >
                    {label}
                  </th>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtPct(t5?.winRate)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text-muted)]">
                    {t5?.directionalCalls ?? 0} / {t5?.totalCalls ?? 0}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtBrier(t5?.brierScore)} · n={t5?.brierSampleSize ?? 0}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtPct(t20?.winRate)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text-muted)]">
                    {t20?.directionalCalls ?? 0} / {t20?.totalCalls ?? 0}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtBrier(t20?.brierScore)} · n={t20?.brierSampleSize ?? 0}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
