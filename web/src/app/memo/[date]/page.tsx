import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { createClient } from '@supabase/supabase-js';
import type { Database } from '@/lib/supabase/database.types';
import { DeskCard } from '@/components/ui/desk-card';
import { PAIRS } from '@/lib/mockData';
import type { DominanceItem, MarkovPayload, TelemetryAuditPayload } from '@/lib/queries';

type DeskRow = Database['public']['Tables']['desk_open_cards']['Row'];

function pairDisplay(label: string): string {
  return PAIRS.find((p) => p.label === label)?.display ?? label;
}

function assertMemoDateOpen(date: string): void {
  const today = new Date().toISOString().slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) notFound();
  if (date >= today) notFound();
  const memoStart = new Date(`${date}T00:00:00.000Z`);
  const openAt = memoStart.getTime() + 24 * 60 * 60 * 1000;
  if (Date.now() < openAt) notFound();
}

function mapDesk(row: DeskRow) {
  const audit = (row.telemetry_audit as TelemetryAuditPayload | null) ?? null;
  return {
    date: row.date,
    pair: row.pair,
    structural_regime: row.structural_regime,
    dominance_array: (row.dominance_array as DominanceItem[] | null) ?? [],
    pain_index: row.pain_index,
    markov_probabilities: (row.markov_probabilities as MarkovPayload | null) ?? null,
    ai_brief: row.ai_brief,
    telemetry_audit: audit,
    parameter_instability: Boolean(audit?.parameter_instability),
    invalidation_triggered: Boolean(row.invalidation_triggered),
    telemetry_status: row.telemetry_status ?? 'ONLINE',
    global_rank: row.global_rank ?? null,
    apex_score: row.apex_score ?? null,
    regime_age: row.regime_age ?? null,
  };
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ date: string }>;
}): Promise<Metadata> {
  const { date } = await params;
  return {
    title: `T+24h SEO Memo · ${date} | FX Regime Lab`,
    description: 'Lagged G10 systemic matrix and Apex Target archive. Forward-walking audit only.',
    robots: { index: true, follow: true },
  };
}

export default async function MemoArchivePage({ params }: { params: Promise<{ date: string }> }) {
  const { date } = await params;
  assertMemoDateOpen(date);

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) notFound();

  const supabase = createClient(url, anon);

  const [{ data: briefRow }, { data: deskRows }] = await Promise.all([
    supabase.from('brief_log').select('dollar_dominance,idiosyncratic_outlier').eq('date', date).maybeSingle(),
    supabase.from('desk_open_cards').select('*').eq('date', date),
  ]);

  const cards = ((deskRows ?? []) as DeskRow[]).map(mapDesk).sort((a, b) => {
    const ar = a.global_rank ?? 999;
    const br = b.global_rank ?? 999;
    return ar - br;
  });
  const rank1 = cards[0];
  if (!rank1) notFound();

  const [{ data: regimeRow }, { data: sigRow }, { data: ledgerRows }] = await Promise.all([
    supabase
      .from('regime_calls')
      .select('confidence')
      .eq('date', date)
      .eq('pair', rank1.pair)
      .maybeSingle(),
    supabase.from('signals').select('spot').eq('date', date).eq('pair', rank1.pair).maybeSingle(),
    supabase
      .from('strategy_ledger')
      .select('t1_hit,entry_close,t1_close,direction')
      .eq('date', date)
      .eq('pair', rank1.pair)
      .neq('direction', 'NEUTRAL')
      .limit(1),
  ]);

  const ledger = (ledgerRows ?? [])[0] ?? null;
  const conf = regimeRow?.confidence != null ? Number(regimeRow.confidence) : null;
  const spot = sigRow?.spot != null ? Number(sigRow.spot) : null;

  let t1ReturnPct: number | null = null;
  if (
    ledger?.entry_close != null &&
    ledger?.t1_close != null &&
    Number(ledger.entry_close) !== 0
  ) {
    t1ReturnPct = (Number(ledger.t1_close) / Number(ledger.entry_close) - 1) * 100;
  }

  let auditLabel: 'WIN' | 'LOSS' | 'PENDING' = 'PENDING';
  if (ledger?.t1_hit === 1) auditLabel = 'WIN';
  else if (ledger?.t1_hit === 0) auditLabel = 'LOSS';

  const dd = briefRow?.dollar_dominance ?? null;
  const outlier = briefRow?.idiosyncratic_outlier ?? null;

  return (
    <div className="min-h-screen bg-[#000000] text-[#e8e8e8]">
      <header className="border-b border-[#111] px-6 py-8">
        <p className="font-mono text-[10px] tracking-widest text-[#666] m-0">T+24H SEO MEMO ARCHIVE</p>
        <h1 className="font-sans text-2xl font-bold text-[#f5f5f5] tracking-tight mt-2 mb-0 tabular-nums">
          {date}
        </h1>
        <p className="font-mono text-[11px] text-[#737373] mt-2 m-0">
          Lagged publication — systemic read and Apex Target as of close. Not real-time execution.
        </p>
        <div className="mt-6">
          <Link
            href="/terminal"
            className="inline-block border border-[#10b981] bg-transparent px-4 py-2.5 font-mono text-[10px] tracking-widest text-[#a7f3d0] no-underline hover:text-[#6ee7b7] hover:border-[#34d399] tabular-nums"
          >
            [ ENTER LIVE TERMINAL → ]
          </Link>
        </div>
      </header>

      <main className="w-full px-6 md:px-8 py-10 space-y-10">
        <section>
          <p className="font-mono text-[10px] text-[#666] tracking-widest mb-4 m-0">[ G10 SYSTEMIC MATRIX ]</p>
          <div className="border border-[#111] bg-[#000000] grid grid-cols-1 md:grid-cols-2 gap-8 px-6 py-10">
            <div>
              <p className="font-mono text-[9px] text-[#555] tracking-widest m-0 mb-2">DOLLAR DOMINANCE</p>
              <p className="font-mono text-[32px] font-bold text-[#f5f5f5] tabular-nums leading-none m-0">
                {dd == null ? '—' : `${Number(dd).toFixed(1)}%`}
              </p>
            </div>
            <div>
              <p className="font-mono text-[9px] text-[#555] tracking-widest m-0 mb-2">OUTLIER</p>
              <p className="font-mono text-[16px] font-bold text-[#f5f5f5] leading-snug m-0 break-words">
                {outlier ?? '—'}
              </p>
            </div>
          </div>
        </section>

        <section>
          <p className="font-mono text-[10px] text-[#666] tracking-widest mb-4 m-0">
            [ APEX TARGET · RANK #1 · {pairDisplay(rank1.pair)} ]
          </p>
          <DeskCard
            variant="hero"
            pairDisplay={pairDisplay(rank1.pair)}
            spot={spot}
            confidence={conf}
            rankJump={undefined}
            regimeAge={rank1.regime_age}
            apexScoreDisplay={
              rank1.apex_score != null ? Math.round(rank1.apex_score * 100) : null
            }
            structuralRegime={rank1.structural_regime}
            invalidationTriggered={rank1.invalidation_triggered}
            telemetryStatus={rank1.telemetry_status}
            dominanceArray={rank1.dominance_array}
            painIndex={rank1.pain_index}
            markovProbabilities={rank1.markov_probabilities}
            aiBrief={rank1.ai_brief}
            telemetryAudit={rank1.telemetry_audit}
            parameterInstability={rank1.parameter_instability}
          />
        </section>
      </main>

      <footer className="border-t border-[#111] px-6 py-8 mt-8">
        <p className="font-mono text-[10px] text-[#555] tracking-widest mb-2 m-0">STRATEGY LEDGER · TRUST ANCHOR</p>
        <p className="font-mono text-[13px] text-[#e0e0e0] tabular-nums m-0">
          [ AUDIT RESULT: {auditLabel} | T+1 RETURN:{' '}
          {t1ReturnPct != null ? `${t1ReturnPct >= 0 ? '+' : ''}${t1ReturnPct.toFixed(2)}%` : '—'} ]
        </p>
        <p className="font-mono text-[10px] text-[#444] mt-3 m-0">
          Pair {rank1.pair} · strategy_ledger row for {date}. NEUTRAL directions excluded.
        </p>
      </footer>
    </div>
  );
}
