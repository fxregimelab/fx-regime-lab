"use client";

import { useQuery } from "@tanstack/react-query";
import type { G10CorrelationJson } from "./g10Correlation";
import { createClient } from "./supabase/client";
import type { Database } from "./supabase/database.types";

type UniverseRow = Database["public"]["Tables"]["universe"]["Row"];
type RegimeCallRow = Database["public"]["Tables"]["regime_calls"]["Row"];
type SignalRow = Database["public"]["Tables"]["signals"]["Row"];
type DeskOpenCardsRow = Database["public"]["Tables"]["desk_open_cards"]["Row"];
type ValidationLogRow = Database["public"]["Tables"]["validation_log"]["Row"];
type BriefLogRow = Database["public"]["Tables"]["brief_log"]["Row"];
export type StrategyLedgerRow =
  Database["public"]["Tables"]["strategy_ledger"]["Row"];
type MacroEventsRow = Database["public"]["Tables"]["macro_events"]["Row"];
type ResearchAnalogsRow =
  Database["public"]["Tables"]["research_analogs"]["Row"];
type ResearchMemoRow = Database["public"]["Tables"]["research_memos"]["Row"];
type HistoricalPricesRow =
  Database["public"]["Tables"]["historical_prices"]["Row"];

const CANONICAL_PAIRS = ["EURUSD", "USDJPY", "USDINR"] as const;
type CanonicalPair = (typeof CANONICAL_PAIRS)[number];

function isCanonicalPair(pair: string): pair is CanonicalPair {
  return CANONICAL_PAIRS.includes(pair as CanonicalPair);
}

/* ─── Legacy type exports (used by memo page, terminal nav, etc.) ─── */

export type LatestSignalRow = Pick<
  SignalRow,
  | "pair"
  | "date"
  | "spot"
  | "rate_diff_2y"
  | "rate_diff_10y"
  | "rate_diff_10y_real"
  | "breakeven_inflation_10y"
  | "rate_z_tactical"
  | "rate_z_structural"
  | "z_blended"
  | "skew_alignment"
  | "realized_vol_20d"
  | "realized_vol_5d"
  | "implied_vol_30d"
  | "cross_asset_us10y"
  | "day_change_pct"
  | "india_vix"
  | "inr_forward_premium"
  | "oi_delta"
  | "volume_rvol"
  | "structural_instability"
  | "ecb_balance_sheet"
  | "bund_btp_spread"
  | "boj_policy_rate"
  | "created_at"
>;

export type LatestRegimeCallRow = Pick<
  RegimeCallRow,
  | "pair"
  | "date"
  | "regime"
  | "confidence"
  | "signal_composite"
  | "rate_signal"
  | "cot_signal"
  | "vol_signal"
  | "rr_signal"
  | "oi_signal"
  | "primary_driver"
  | "created_at"
>;

export type DominanceItem = {
  rank: number;
  signal_family: string;
  signal_strength: number;
  beta: number;
  dominance_score: number;
};

export type MarkovPayload = {
  continuation_probability: number;
  transitions: Record<string, number>;
  weighted_sample_size?: number;
};

export type TelemetryAuditPayload = {
  cot_is_stale?: boolean;
  cot_age_days?: number | null;
  underwater_triggered?: boolean;
  parameter_instability?: boolean;
  weighted_sample_size?: number;
  overnight_day_change_pct?: number;
  Systemic_Cluster?: boolean;
  overnight_vol_threshold?: number;
  overnight_vix?: number | null;
  overnight_dxy?: number | null;
  overnight_vix_triggered?: boolean;
  rate_z_tactical_mad?: number | null;
  rate_z_structural_mad?: number | null;
  dynamic_beta?: number | null;
};

export type DeskOpenCardSnapshotRow = {
  date: string;
  pair: string;
  structural_regime: string;
  dominance_array: DominanceItem[];
  pain_index: number | null;
  markov_probabilities: MarkovPayload | null;
  ai_brief: string | null;
  telemetry_audit: TelemetryAuditPayload | null;
  parameter_instability: boolean;
  invalidation_triggered: boolean;
  telemetry_status: string;
  global_rank: number | null;
  apex_score: number | null;
  regime_age: number | null;
};

/* ──────────────────────────────────────────────
   Universe
   ────────────────────────────────────────────── */

export function useUniverse() {
  return useQuery<string[]>({
    queryKey: ["universe", "fx_pairs"],
    queryFn: async () => {
      const supabase = createClient();
      const { data, error } = await supabase
        .from("universe")
        .select("pair")
        .eq("class", "FX")
        .order("pair", { ascending: true });
      if (error) throw error;
      const canonical = new Set<string>(["EURUSD", "USDJPY", "USDINR"]);
      return ((data ?? []) as { pair: string }[])
        .map((r) => r.pair)
        .filter((p) => canonical.has(p));
    },
    staleTime: 60 * 60 * 1000,
  });
}

/* ──────────────────────────────────────────────
   Latest Regime Calls
   ────────────────────────────────────────────── */

export function useLatestRegimeCalls() {
  return useQuery<Record<string, LatestRegimeCallRow>>({
    queryKey: ["regime_calls", "latest"],
    queryFn: async () => {
      const supabase = createClient();
      const { data, error } = await supabase
        .from("regime_calls")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(50);
      if (error) throw error;
      const rows = (data ?? []) as RegimeCallRow[];
      const filtered = rows.filter((r) => isCanonicalPair(r.pair));
      const latest: Record<string, LatestRegimeCallRow> = {};
      for (const row of filtered) {
        if (!latest[row.pair]) {
          latest[row.pair] = row as LatestRegimeCallRow;
        }
      }
      return latest;
    },
  });
}

/* ──────────────────────────────────────────────
   Latest Signals
   ────────────────────────────────────────────── */

export function useLatestSignals() {
  return useQuery<Record<string, LatestSignalRow>>({
    queryKey: ["signals", "latest"],
    queryFn: async () => {
      const supabase = createClient();
      const { data, error } = await supabase
        .from("signals")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(50);
      if (error) throw error;
      const rows = (data ?? []) as SignalRow[];
      const filtered = rows.filter((r) => isCanonicalPair(r.pair));
      const latest: Record<string, LatestSignalRow> = {};
      for (const row of filtered) {
        if (!latest[row.pair]) {
          latest[row.pair] = row as LatestSignalRow;
        }
      }
      return latest;
    },
  });
}

/* ──────────────────────────────────────────────
   Latest Desk Open Cards Snapshot
   ────────────────────────────────────────────── */

export type DeskOpenCardsSnapshot = {
  asOfDate: string | null;
  cards: DeskOpenCardSnapshotRow[];
  rankJumpByPair: Record<string, number>;
};

function mapDeskRow(row: DeskOpenCardsRow): DeskOpenCardSnapshotRow {
  const audit = (row.telemetry_audit as TelemetryAuditPayload | null) ?? null;
  return {
    date: row.date,
    pair: row.pair,
    structural_regime: row.structural_regime,
    dominance_array: (row.dominance_array as DominanceItem[] | null) ?? [],
    pain_index: row.pain_index,
    markov_probabilities:
      (row.markov_probabilities as MarkovPayload | null) ?? null,
    ai_brief: row.ai_brief,
    telemetry_audit: audit,
    parameter_instability: Boolean(audit?.parameter_instability),
    invalidation_triggered: Boolean(row.invalidation_triggered),
    telemetry_status: row.telemetry_status ?? "ONLINE",
    global_rank: row.global_rank ?? null,
    apex_score: row.apex_score ?? null,
    regime_age: row.regime_age ?? null,
  };
}

function utcPrevCalendarDay(isoDate: string): string {
  const d = new Date(`${isoDate}T12:00:00.000Z`);
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
}

export function useLatestDeskOpenCardsSnapshot() {
  const universeQ = useUniverse();
  const pairs = universeQ.data ?? [];
  return useQuery<DeskOpenCardsSnapshot>({
    queryKey: ["desk_open_cards", "snapshot", pairs],
    queryFn: async (): Promise<DeskOpenCardsSnapshot> => {
      const supabase = createClient();
      const { data: head, error: headErr } = await supabase
        .from("desk_open_cards")
        .select("date")
        .in("pair", pairs)
        .order("date", { ascending: false })
        .limit(1);
      if (headErr) throw headErr;
      const headRow = (head ?? [])[0] as { date: string } | undefined;
      const latest = headRow?.date ?? null;
      if (!latest) {
        return { asOfDate: null, cards: [], rankJumpByPair: {} };
      }

      const { data: rows, error } = await supabase
        .from("desk_open_cards")
        .select("*")
        .eq("date", latest)
        .in("pair", pairs);
      if (error) throw error;
      const cards = ((rows as DeskOpenCardsRow[]) ?? []).map(mapDeskRow);

      const prevDay = utcPrevCalendarDay(latest);
      const { data: prevRows, error: prevErr } = await supabase
        .from("desk_open_cards")
        .select("pair, global_rank")
        .eq("date", prevDay)
        .in("pair", pairs);
      if (prevErr) throw prevErr;

      const prevRankByPair: Record<string, number> = {};
      for (const r of (prevRows as {
        pair: string;
        global_rank: number | null;
      }[]) ?? []) {
        if (r.global_rank != null) prevRankByPair[r.pair] = r.global_rank;
      }

      const rankJumpByPair: Record<string, number> = {};
      for (const c of cards) {
        const prev = prevRankByPair[c.pair];
        const curr = c.global_rank;
        if (prev != null && curr != null && prev > curr) {
          rankJumpByPair[c.pair] = prev - curr;
        }
      }

      return { asOfDate: latest, cards, rankJumpByPair };
    },
    enabled: universeQ.isSuccess && pairs.length > 0,
    staleTime: 60000,
  });
}

/* ──────────────────────────────────────────────
   Cross Asset Pulse
   ────────────────────────────────────────────── */

export function useCrossAssetPulse() {
  return useQuery<
    {
      pair: string;
      latestPrice: number;
      latestRegime: RegimeCallRow | null;
      latestSignal: SignalRow | null;
    }[]
  >({
    queryKey: ["cross_asset_pulse"],
    queryFn: async () => {
      const supabase = createClient();
      const [regimesRes, signalsRes, pricesRes] = await Promise.all([
        supabase
          .from("regime_calls")
          .select("*")
          .order("created_at", { ascending: false })
          .limit(10),
        supabase
          .from("signals")
          .select("*")
          .order("created_at", { ascending: false })
          .limit(10),
        supabase
          .from("historical_prices")
          .select("*")
          .in("pair", CANONICAL_PAIRS as unknown as string[])
          .order("date", { ascending: false })
          .limit(3),
      ]);

      if (regimesRes.error) throw regimesRes.error;
      if (signalsRes.error) throw signalsRes.error;
      if (pricesRes.error) throw pricesRes.error;

      const regimes = ((regimesRes.data ?? []) as RegimeCallRow[]).filter((r) =>
        isCanonicalPair(r.pair),
      );
      const signals = ((signalsRes.data ?? []) as SignalRow[]).filter((r) =>
        isCanonicalPair(r.pair),
      );
      const prices = (pricesRes.data ?? []) as HistoricalPricesRow[];

      const result: {
        pair: string;
        latestPrice: number;
        latestRegime: RegimeCallRow | null;
        latestSignal: SignalRow | null;
      }[] = [];

      for (const pair of CANONICAL_PAIRS) {
        const latestRegime = regimes.find((r) => r.pair === pair) ?? null;
        const latestSignal = signals.find((r) => r.pair === pair) ?? null;
        const latestPriceRow = prices.find((p) => p.pair === pair);
        result.push({
          pair,
          latestPrice: latestPriceRow?.close ?? 0,
          latestRegime,
          latestSignal,
        });
      }
      return result;
    },
  });
}

/* ──────────────────────────────────────────────
   Validation Log
   ────────────────────────────────────────────── */

export function useValidationLog(pair?: string) {
  return useQuery<ValidationLogRow[]>({
    queryKey: ["validation_log", pair ?? "all"],
    queryFn: async () => {
      const supabase = createClient();
      let query = supabase
        .from("validation_log")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(50);
      if (pair) {
        if (!isCanonicalPair(pair)) return [];
        query = query.eq("pair", pair);
      }
      const { data, error } = await query;
      if (error) throw error;
      return ((data ?? []) as ValidationLogRow[]).filter((r) =>
        isCanonicalPair(r.pair),
      );
    },
  });
}

/* ──────────────────────────────────────────────
   Strategy Ledger
   ────────────────────────────────────────────── */

export function useStrategyLedger(pair?: string) {
  return useQuery<StrategyLedgerRow[]>({
    queryKey: ["strategy_ledger", pair ?? "all"],
    queryFn: async () => {
      const supabase = createClient();
      let query = supabase
        .from("strategy_ledger")
        .select("*")
        .order("date", { ascending: false })
        .limit(100);
      if (pair) {
        if (!isCanonicalPair(pair)) return [];
        query = query.eq("pair", pair);
      }
      const { data, error } = await query;
      if (error) throw error;
      return ((data ?? []) as StrategyLedgerRow[]).filter((r) =>
        isCanonicalPair(r.pair),
      );
    },
  });
}

/* ──────────────────────────────────────────────
   Upcoming Macro Events
   ────────────────────────────────────────────── */

export function useUpcomingMacroEvents(days = 7) {
  return useQuery<MacroEventsRow[]>({
    queryKey: ["macro_events", days],
    queryFn: async () => {
      const supabase = createClient();
      const today = new Date().toISOString().split("T")[0];
      const future = new Date(Date.now() + days * 24 * 60 * 60 * 1000)
        .toISOString()
        .split("T")[0];
      const { data, error } = await supabase
        .from("macro_events")
        .select("*")
        .gte("date", today)
        .lte("date", future)
        .order("date", { ascending: true })
        .limit(50);
      if (error) throw error;
      return data ?? [];
    },
  });
}

/* ──────────────────────────────────────────────
   G10 Correlation Matrix
   ────────────────────────────────────────────── */

export function useG10CorrelationMatrix() {
  return useQuery<G10CorrelationJson>({
    queryKey: ["g10_correlation"],
    queryFn: async () => {
      const supabase = createClient();
      const { data, error } = await supabase
        .from("historical_prices")
        .select("*")
        .in("pair", CANONICAL_PAIRS as unknown as string[])
        .order("date", { ascending: false })
        .limit(90 * CANONICAL_PAIRS.length);

      if (error) throw error;
      const rows = (data ?? []) as HistoricalPricesRow[];

      const byPair = new Map<string, HistoricalPricesRow[]>();
      for (const row of rows) {
        const arr = byPair.get(row.pair) ?? [];
        arr.push(row);
        byPair.set(row.pair, arr);
      }

      const result: G10CorrelationJson = {};
      const pairs = Array.from(byPair.keys());
      for (const p of pairs) {
        const row: Record<string, number> = {};
        result[p] = row;
        for (const q of pairs) {
          if (p === q) {
            row[q] = 1;
            continue;
          }
          if (p > q) continue; // only populate p < q, symmetric access handled by correlationFromJson
          const pRows = byPair.get(p) ?? [];
          const qRows = byPair.get(q) ?? [];
          const pMap = new Map(pRows.map((r) => [r.date, r.close]));
          const qMap = new Map(qRows.map((r) => [r.date, r.close]));
          const commonDates = Array.from(pMap.keys()).filter((d) =>
            qMap.has(d),
          );
          const pVals: number[] = [];
          const qVals: number[] = [];
          for (const d of commonDates) {
            const pv = pMap.get(d);
            const qv = qMap.get(d);
            if (pv != null && qv != null) {
              pVals.push(pv);
              qVals.push(qv);
            }
          }
          if (pVals.length < 2) {
            row[q] = 0;
            continue;
          }
          const meanP = pVals.reduce((a, b) => a + b, 0) / pVals.length;
          const meanQ = qVals.reduce((a, b) => a + b, 0) / qVals.length;
          let num = 0;
          let denP = 0;
          let denQ = 0;
          for (let i = 0; i < pVals.length; i++) {
            const dp = pVals[i] - meanP;
            const dq = qVals[i] - meanQ;
            num += dp * dq;
            denP += dp * dp;
            denQ += dq * dq;
          }
          const denom = Math.sqrt(denP * denQ);
          row[q] = denom === 0 ? 0 : num / denom;
        }
      }
      return result;
    },
  });
}

/* ──────────────────────────────────────────────
   Research Memos List
   ────────────────────────────────────────────── */

export function useResearchMemosList() {
  return useQuery<Pick<ResearchMemoRow, "id" | "date" | "title">[]>({
    queryKey: ["research_memos", "list"],
    queryFn: async () => {
      const supabase = createClient();
      const { data, error } = await supabase
        .from("research_memos")
        .select("id, date, title")
        .order("date", { ascending: false })
        .limit(50);
      if (error) throw error;
      return (data as Pick<ResearchMemoRow, "id" | "date" | "title">[]) ?? [];
    },
  });
}

/* ──────────────────────────────────────────────
   Event Risk Matrices
   ────────────────────────────────────────────── */

export function useEventRiskMatrices(pair: string) {
  type EventRiskMatrixRow =
    Database["public"]["Tables"]["event_risk_matrices"]["Row"];
  return useQuery<EventRiskMatrixRow[]>({
    queryKey: ["event_risk_matrices", pair, "next_14d"],
    queryFn: async () => {
      if (!isCanonicalPair(pair)) return [];
      const supabase = createClient();
      const today = new Date().toISOString().split("T")[0];
      const future = new Date();
      future.setDate(future.getDate() + 14);
      const { data, error } = await supabase
        .from("event_risk_matrices")
        .select("*")
        .eq("pair", pair)
        .gte("date", today)
        .lte("date", future.toISOString().split("T")[0])
        .order("date", { ascending: true });
      if (error) throw error;
      return (data as EventRiskMatrixRow[]) ?? [];
    },
    enabled: !!pair,
    staleTime: Number.POSITIVE_INFINITY,
  });
}

/* ──────────────────────────────────────────────
   Telemetry Status (legacy — convexity radar page)
   ────────────────────────────────────────────── */

export function useTelemetryStatus(pair: string) {
  return useQuery<{
    invalidation_triggered: boolean;
    telemetry_status: string;
  } | null>({
    queryKey: ["desk_open_cards", "telemetry", pair],
    queryFn: async () => {
      const supabase = createClient();
      const { data, error } = await supabase
        .from("desk_open_cards")
        .select("invalidation_triggered, telemetry_status")
        .eq("pair", pair)
        .order("date", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      const row = data as Pick<
        DeskOpenCardsRow,
        "invalidation_triggered" | "telemetry_status"
      > | null;
      if (!row) return null;
      return {
        invalidation_triggered: Boolean(row.invalidation_triggered),
        telemetry_status: (row.telemetry_status as string) ?? "ONLINE",
      };
    },
    enabled: !!pair,
    staleTime: 60000,
    refetchInterval: 60000,
  });
}

/* ──────────────────────────────────────────────
   Brief Log
   ────────────────────────────────────────────── */

export function useLatestBrief() {
  return useQuery<BriefLogRow | null>({
    queryKey: ["brief_log", "latest"],
    queryFn: async () => {
      const supabase = createClient();
      const { data, error } = await supabase
        .from("brief_log")
        .select("*")
        .order("date", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      return data as BriefLogRow | null;
    },
  });
}

export function useBriefLogDominanceSeries(limit = 5) {
  return useQuery<Array<{ date: string; dollar_dominance: number | null }>>({
    queryKey: ["brief_log", "dollar_dominance_series", limit],
    queryFn: async () => {
      const supabase = createClient();
      const { data, error } = await supabase
        .from("brief_log")
        .select("date,dollar_dominance")
        .order("date", { ascending: false })
        .limit(limit);
      if (error) throw error;
      const rows = (
        (data ?? []) as Array<{ date: string; dollar_dominance: number | null }>
      ).slice();
      return rows.reverse();
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useResearchMemoReader(id: string | null) {
  return useQuery<Pick<
    ResearchMemoRow,
    "id" | "date" | "title" | "raw_content" | "link_url"
  > | null>({
    queryKey: ["research_memos", "reader", id],
    queryFn: async () => {
      if (!id) return null;
      const supabase = createClient();
      const { data, error } = await supabase
        .from("research_memos")
        .select("id, date, title, raw_content, link_url")
        .eq("id", id)
        .maybeSingle();
      if (error) throw error;
      return data as Pick<
        ResearchMemoRow,
        "id" | "date" | "title" | "raw_content" | "link_url"
      > | null;
    },
    enabled: id != null && id.length > 0,
  });
}
