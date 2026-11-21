import { PairAccuracyCards } from "@/components/performance/PairAccuracyCards";
import { PairBreakdownTable } from "@/components/performance/PairBreakdownTable";
import { RegimeBreakdown } from "@/components/performance/RegimeBreakdown";
import { StatsCard } from "@/components/performance/StatsCard";
import { ValidationTable } from "@/components/regime/ValidationTable";
import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import { fmtPropCI, wilsonCI } from "@/lib/stats";
import {
  getBacktestVersions,
  getRegimeBreakdown,
  getValidationLogT5T20,
} from "@/lib/supabase/queries";
import type {
  RegimeBreakdownRow,
  ValidationRowT5,
  ValidationStats,
} from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import {
  computeStatsFromLog,
  fmtBps,
  fmtBrier,
  fmtPctRaw,
} from "@/lib/track-record";
import type { Metadata } from "next";
import { BacktestTabClient } from "./components/BacktestTabClient";
import { TrackRecordTabs } from "./components/TrackRecordTabs";

export const metadata: Metadata = {
  title: "Track Record | FX Regime Lab",
  description:
    "Directional published calls by pair, horizon, and exact model cohort.",
};

export const revalidate = 3600;

const LIVE_MODEL_VERSION = "2.0-live";
const PAIR_LABELS = ["EUR/USD", "USD/JPY", "USD/INR"] as const;

function EmptyState({ message }: { message: string }) {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-8 py-12 text-center">
      <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
        {message}
      </p>
      <p className="font-sans text-[13px] text-[var(--color-text-secondary)]">
        The page stays unavailable until the matching published calls can be
        read.
      </p>
    </div>
  );
}

function LiveTabContent({
  statsT5,
  statsT20,
  validation,
  regimeBreakdown,
  allT5,
  allT20,
}: {
  statsT5: ValidationStats[];
  statsT20: ValidationStats[];
  validation: ValidationRowT5[];
  regimeBreakdown: RegimeBreakdownRow[];
  allT5: ValidationStats;
  allT20: ValidationStats;
}) {
  const lastDate =
    validation
      .map((row) => row.date)
      .sort()
      .at(-1) ?? null;
  const t5WinCI = wilsonCI(allT5.wins ?? 0, allT5.directionalCalls ?? 0);
  const t20WinCI = wilsonCI(allT20.wins ?? 0, allT20.directionalCalls ?? 0);

  return (
    <div>
      <div className="mb-8 pb-4 border-b border-[var(--color-border)] flex flex-wrap items-baseline gap-x-5 gap-y-2">
        <span className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase">
          Live published calls
        </span>
        <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
          v2 · {LIVE_MODEL_VERSION} · publication-snapshot-v2
        </span>
        <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
          AS OF {allT5.asOfDate}
        </span>
        {lastDate && (
          <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
            LAST CALL {lastDate}
          </span>
        )}
      </div>

      <div className="mb-8 px-5 py-4 border border-[var(--color-brand-amber)]/30 bg-[var(--color-brand-amber)]/5">
        <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
          Results use matching live published calls. Published neutral calls
          abstain. Directional calls in the realized-return deadband count as
          wrong. Each metric shows its own eligible sample; confidence scores
          remain a heuristic and have not been calibrated as probabilities on a
          held-out set. Calls without a current evaluation stay in the totals
          with unavailable outcomes. Price movement starts at each call’s saved
          spot and ends at the exact-date historical close. Calls without
          original price evidence remain unscored; these prices do not establish
          an executable trade after publication.
        </p>
      </div>

      <PairAccuracyCards statsT5={statsT5} statsT20={statsT20} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-8">
        <StatsCard
          label="T+5 DIRECTIONAL ACCURACY"
          value={fmtPctRaw(allT5.winRate)}
          sub={`${allT5.directionalCalls ?? 0} scored of ${allT5.totalCalls ?? 0} published calls`}
          sampleSize={allT5.directionalCalls}
          ci={fmtPropCI(allT5.winRate, t5WinCI)}
        />
        <StatsCard
          label="T+5 NET-PAYOFF WIN RATE"
          value={fmtPctRaw(allT5.netWinRate)}
          sub={
            allT5.costBps == null
              ? "cost fields unavailable"
              : `mean cost assumption ${allT5.costBps.toFixed(2)} bps`
          }
          sampleSize={allT5.netSampleSize}
        />
        <StatsCard
          label="T+20 DIRECTIONAL ACCURACY"
          value={fmtPctRaw(allT20.winRate)}
          sub={`${allT20.directionalCalls ?? 0} scored of ${allT20.totalCalls ?? 0} published calls`}
          sampleSize={allT20.directionalCalls}
          ci={fmtPropCI(allT20.winRate, t20WinCI)}
        />
        <StatsCard
          label="T+20 NET-PAYOFF WIN RATE"
          value={fmtPctRaw(allT20.netWinRate)}
          sub={
            allT20.costBps == null
              ? "cost fields unavailable"
              : `mean cost assumption ${allT20.costBps.toFixed(2)} bps`
          }
          sampleSize={allT20.netSampleSize}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-8">
        <StatsCard
          label="T+5 BRIER (HEURISTIC)"
          value={fmtBrier(allT5.brierScore)}
          sub={`${allT5.brierSampleSize ?? 0} valid directional scores`}
          sampleSize={allT5.brierSampleSize}
        />
        <StatsCard
          label="T+20 BRIER (HEURISTIC)"
          value={fmtBrier(allT20.brierScore)}
          sub={`${allT20.brierSampleSize ?? 0} valid directional scores`}
          sampleSize={allT20.brierSampleSize}
        />
        <StatsCard
          label="T+5 MEAN SIGNED PAYOFF"
          value={fmtBps(allT5.avgReturnBps)}
          sub="gross hypothetical payoff per eligible call"
          sampleSize={allT5.directionalCalls}
        />
        <StatsCard
          label="T+20 MEAN SIGNED PAYOFF"
          value={fmtBps(allT20.avgReturnBps)}
          sub="gross hypothetical payoff per eligible call"
          sampleSize={allT20.directionalCalls}
        />
      </div>

      <div className="mb-10 px-5 py-4 border border-[var(--color-border)] bg-[var(--color-surface)]">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
          Scored share of published calls
        </p>
        <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
          T+5 scored share {fmtPctRaw(allT5.coverage)}: {allT5.matureCalls ?? 0}{" "}
          mature, {allT5.pendingCalls ?? 0} pending maturity,{" "}
          {allT5.abstainedCalls ?? 0} mature abstentions,{" "}
          {allT5.missingOutcomeCalls ?? 0} mature directional calls with missing
          outcomes, and {allT5.unknownDirectionCalls ?? 0} mature calls with an
          unknown direction. T+20 scored share {fmtPctRaw(allT20.coverage)}:{" "}
          {allT20.matureCalls ?? 0} mature, {allT20.pendingCalls ?? 0} pending
          maturity, {allT20.abstainedCalls ?? 0} mature abstentions,{" "}
          {allT20.missingOutcomeCalls ?? 0} mature directional calls with
          missing outcomes, and {allT20.unknownDirectionCalls ?? 0} mature calls
          with an unknown direction. Of {allT5.totalCalls ?? 0} published calls,{" "}
          {allT5.evaluationCalls ?? 0} have a current evaluation and{" "}
          {allT5.missingEvaluationCalls ?? 0} have none. Scored share includes
          pending calls and abstentions in its denominator; it is not
          directional accuracy.
        </p>
      </div>

      <RegimeBreakdown rows={regimeBreakdown} horizon="t5" />
      <RegimeBreakdown rows={regimeBreakdown} horizon="t20" />
      <div className="mb-10">
        <PairBreakdownTable statsT5={statsT5} statsT20={statsT20} />
      </div>
      <div className="mb-10">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
          Validation history · T+5 / T+20
        </p>
        <ValidationTable rows={validation} tone="dark" mode="t5t20" />
      </div>

      <p className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider leading-relaxed pt-5 mt-5 border-t border-[var(--color-border)]">
        RAW MARKET RETURNS AND SIGNED HYPOTHETICAL PAYOFFS ARE DISTINCT.
        OVERLAPPING CALLS DO NOT DEFINE AN EQUITY CURVE, SHARPE RATIO, OR
        DRAWDOWN. RESEARCH ONLY — NOT INVESTMENT ADVICE.
      </p>
    </div>
  );
}

function RegimeValidationTabContent() {
  return (
    <div>
      <div className="mb-8 pb-4 border-b border-[var(--color-border)]">
        <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-2">
          Legacy exploratory simulation
        </p>
        <h2 className="font-sans font-semibold text-[22px] text-[var(--color-text)] tracking-tight mb-2">
          Pending reconciliation
        </h2>
        <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
          Earlier sizing simulations are quarantined from the public track
          record. Their Sharpe, Sortino, total P&amp;L, and drawdown fields are
          not validated performance because overlapping calls do not establish
          portfolio exposures. They will remain hidden until the simulation
          contract is reconciled with the published validation cohort.
        </p>
      </div>
    </div>
  );
}

export default async function TrackRecordPage() {
  const supabase = await createClient();
  const [validation, regimeBreakdown, versions] = await Promise.all([
    getValidationLogT5T20(supabase, null, "live", LIVE_MODEL_VERSION),
    getRegimeBreakdown(supabase, null, "live", LIVE_MODEL_VERSION),
    getBacktestVersions(supabase),
  ]);
  const asOfDate = new Date().toISOString().slice(0, 10);
  const allT5 = computeStatsFromLog(validation, null, "t5", asOfDate);
  const allT20 = computeStatsFromLog(validation, null, "t20", asOfDate);
  const statsT5 = [
    ...PAIR_LABELS.map((pair) =>
      computeStatsFromLog(validation, pair, "t5", asOfDate),
    ),
    allT5,
  ];
  const statsT20 = [
    ...PAIR_LABELS.map((pair) =>
      computeStatsFromLog(validation, pair, "t20", asOfDate),
    ),
    allT20,
  ];

  const selectedVersion = versions[0] ?? "";

  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <AuditTrailBannerServer variant="shell" />
      <main
        id="main-content"
        className="max-w-[1152px] mx-auto px-6 pt-28 pb-20 w-full"
      >
        <div className="mb-6 pb-6 border-b border-[var(--color-border)]">
          <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-2.5">
            Track Record
          </p>
          <h1 className="font-sans font-semibold text-[32px] text-[var(--color-text)] tracking-tight">
            Validation Archive
          </h1>
          <p className="font-sans text-[15px] text-[var(--color-text-secondary)] mt-2 leading-[1.6]">
            Published directional results, separated by source and model
            version.
          </p>
        </div>

        <TrackRecordTabs
          liveContent={
            validation.length === 0 ? (
              <EmptyState message="Live published calls unavailable" />
            ) : (
              <LiveTabContent
                statsT5={statsT5}
                statsT20={statsT20}
                validation={validation}
                regimeBreakdown={regimeBreakdown}
                allT5={allT5}
                allT20={allT20}
              />
            )
          }
          backtestedContent={
            <BacktestTabClient
              versions={versions}
              initialVersion={selectedVersion}
            />
          }
          validationContent={<RegimeValidationTabContent />}
        />
      </main>
      <Footer />
    </div>
  );
}
