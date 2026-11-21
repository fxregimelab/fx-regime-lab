"use client";

import { PairBreakdownTable } from "@/components/performance/PairBreakdownTable";
import { RegimeBreakdown } from "@/components/performance/RegimeBreakdown";
import type {
  RegimeBreakdownRow,
  ValidationStats,
} from "@/lib/supabase/queries";
import { fmtBrier, fmtPctRaw } from "@/lib/track-record";
import { useEffect, useState } from "react";
import { VersionSelector } from "./VersionSelector";

interface BacktestData {
  version: string;
  regimeBreakdown: RegimeBreakdownRow[];
  backtestT5: ValidationStats;
  backtestT20: ValidationStats;
  backtestT5ByPair: ValidationStats[];
  backtestT20ByPair: ValidationStats[];
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-8 py-12 text-center">
      <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
        {message}
      </p>
      <p className="font-sans text-[13px] text-[var(--color-text-secondary)]">
        No substitute version or partial published-call set is shown.
      </p>
    </div>
  );
}

export function BacktestTabClient({
  versions,
  initialVersion,
}: {
  versions: string[];
  initialVersion: string;
}) {
  const [selectedVersion, setSelectedVersion] = useState(initialVersion);
  const [data, setData] = useState<BacktestData | null>(null);
  const [loading, setLoading] = useState(versions.length > 0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedVersion) {
      setLoading(false);
      setData(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/api/backtest?version=${encodeURIComponent(selectedVersion)}`)
      .then((response) => {
        if (!response.ok)
          throw new Error("The backtest published calls could not be loaded");
        return response.json();
      })
      .then((payload: BacktestData) => {
        if (!cancelled) {
          setData(payload);
          setLoading(false);
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setError(
            cause instanceof Error ? cause.message : "Backtest unavailable",
          );
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedVersion]);

  if (versions.length === 0) {
    return (
      <EmptyState message="No reconciled backtest model versions are available" />
    );
  }

  const selector = (
    <div className="mb-8 pb-4 border-b border-[var(--color-border)] flex flex-wrap items-center gap-4">
      <span className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase">
        Historical replay published calls
      </span>
      <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
        MODEL VERSION
      </span>
      <VersionSelector
        versions={versions}
        selectedVersion={selectedVersion}
        onChange={setSelectedVersion}
      />
    </div>
  );

  if (loading) {
    return (
      <div>
        {selector}
        <p className="font-mono text-[10px] text-[var(--color-text-muted)]">
          LOADING PUBLISHED CALLS…
        </p>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div>
        {selector}
        <EmptyState message={error ?? "Backtest published calls unavailable"} />
      </div>
    );
  }

  const { backtestT5, backtestT20, backtestT5ByPair, backtestT20ByPair } = data;
  if (
    (backtestT5.totalCalls ?? 0) === 0 &&
    (backtestT20.totalCalls ?? 0) === 0
  ) {
    return (
      <div>
        {selector}
        <EmptyState message="No published calls match this exact backtest cohort" />
      </div>
    );
  }

  return (
    <div>
      {selector}
      <div className="mb-8 px-5 py-4 border border-[var(--color-brand-amber)]/30 bg-[var(--color-brand-amber)]/5">
        <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
          Historical replay · v2 · {data.version} · publication-snapshot-v2.
          These results include every persisted call in one exact backtest
          cohort, including calls with no current evaluation. These results are
          not a live track record or a portfolio backtest, and they do not imply
          an equity curve, Sharpe ratio, or drawdown. Each evaluation uses that
          call’s saved entry spot and an exact-date historical close. Missing
          original price evidence remains unavailable.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-10">
        {[
          [
            "T+5 ACCURACY",
            fmtPctRaw(backtestT5.winRate),
            `${backtestT5.directionalCalls ?? 0} / ${backtestT5.totalCalls ?? 0} published calls scored`,
          ],
          [
            "T+5 BRIER",
            fmtBrier(backtestT5.brierScore),
            `n=${backtestT5.brierSampleSize ?? 0} heuristic scores`,
          ],
          [
            "T+20 ACCURACY",
            fmtPctRaw(backtestT20.winRate),
            `${backtestT20.directionalCalls ?? 0} / ${backtestT20.totalCalls ?? 0} published calls scored`,
          ],
          [
            "T+20 BRIER",
            fmtBrier(backtestT20.brierScore),
            `n=${backtestT20.brierSampleSize ?? 0} heuristic scores`,
          ],
        ].map(([label, value, detail]) => (
          <div key={label} className="bg-[var(--color-surface)] p-4">
            <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
              {label}
            </p>
            <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tabular-nums">
              {value}
            </p>
            <p className="font-mono text-[9px] text-[var(--color-text-muted)] mt-1">
              {detail}
            </p>
          </div>
        ))}
      </div>

      <div className="mb-8 px-5 py-4 border border-[var(--color-border)] bg-[var(--color-surface)]">
        <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
          T+5 scored share of published calls {fmtPctRaw(backtestT5.coverage)}{" "}
          with {backtestT5.pendingCalls ?? 0} pending maturity,{" "}
          {backtestT5.abstainedCalls ?? 0} mature abstentions,{" "}
          {backtestT5.missingOutcomeCalls ?? 0} mature directional calls with
          missing outcomes, and {backtestT5.unknownDirectionCalls ?? 0} mature
          calls with an unknown direction. T+20 scored share of evaluation
          records {fmtPctRaw(backtestT20.coverage)}
          with {backtestT20.pendingCalls ?? 0} pending maturity,{" "}
          {backtestT20.abstainedCalls ?? 0} mature abstentions,{" "}
          {backtestT20.missingOutcomeCalls ?? 0} mature directional calls with
          missing outcomes, and {backtestT20.unknownDirectionCalls ?? 0} mature
          calls with an unknown direction.{" "}
          {backtestT5.missingEvaluationCalls ?? 0} calls have no current
          evaluation and remain in both denominators. Scored share is not
          directional accuracy.
        </p>
      </div>

      <PairBreakdownTable
        statsT5={[...backtestT5ByPair, backtestT5]}
        statsT20={[...backtestT20ByPair, backtestT20]}
      />
      <div className="mt-10">
        <RegimeBreakdown rows={data.regimeBreakdown} horizon="t5" />
        <RegimeBreakdown rows={data.regimeBreakdown} horizon="t20" />
      </div>
    </div>
  );
}
