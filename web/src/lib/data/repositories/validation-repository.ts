import type { Database } from "@/lib/supabase/database.types";
import { DataSource, applyDataSourceDateFilter } from "../adapters/data-source";
import type { TypedSupabaseClient } from "../adapters/supabase-client";
import {
  toRegimeBreakdownEntry,
  toValidationEntry,
  toValidationStats,
} from "../adapters/supabase-validation-adapter";
import type {
  Horizon,
  RegimeBreakdownEntry,
  ValidationEntry,
  ValidationStats,
} from "../domain/validation";

type DbValidationLogRow = Database["public"]["Tables"]["validation_log"]["Row"];
type ValidationStatsRow =
  Database["public"]["Tables"]["validation_stats"]["Row"];

async function fetchPredictedDirections(
  supabase: TypedSupabaseClient,
  callIds: number[],
): Promise<Map<number, string>> {
  const predictedMap = new Map<number, string>();
  if (callIds.length === 0) return predictedMap;

  const { data: regimeData } = await supabase
    .from("regime_calls")
    .select("id, predicted_direction")
    .in("id", callIds);

  for (const rc of (regimeData ?? []) as Array<{
    id: number | null;
    predicted_direction: string | null;
  }>) {
    if (rc.id != null && rc.predicted_direction) {
      predictedMap.set(rc.id, rc.predicted_direction);
    }
  }
  return predictedMap;
}

export const ValidationRepository = {
  async getLogT5T20(
    supabase: TypedSupabaseClient,
    limit = 100,
    dataSource: DataSource = DataSource.Live,
  ): Promise<ValidationEntry[]> {
    let q = supabase
      .from("validation_log")
      .select("*")
      .eq("is_superseded", false)
      .not("brier_score_t5", "is", null)
      .order("date", { ascending: false })
      .limit(limit);

    q = applyDataSourceDateFilter(q, dataSource);

    const { data, error } = await q;
    if (error || !data) return [];

    const rows = data as DbValidationLogRow[];
    const callIds = rows
      .map((r) => r.call_id)
      .filter((id): id is number => id != null);
    const predictedMap = await fetchPredictedDirections(supabase, callIds);

    return rows.map((row) => toValidationEntry(row, predictedMap));
  },

  async getStats(
    supabase: TypedSupabaseClient,
    horizon: Horizon,
    dataSource: DataSource = DataSource.Live,
  ): Promise<ValidationStats[]> {
    let q = supabase
      .from("validation_stats")
      .select("*")
      .order("as_of_date", { ascending: false })
      .limit(100);

    q = applyDataSourceDateFilter(q, dataSource, "as_of_date");

    const { data, error } = await q;

    if (error || !data) return [];

    const rows = Array.isArray(data) ? (data as ValidationStatsRow[]) : [];
    const latestDate = rows[0]?.as_of_date;
    if (!latestDate) return [];

    const latest = rows.filter((r) => r.as_of_date === latestDate);
    return latest.map((row) => toValidationStats(row, horizon));
  },

  async getBreakdown(
    supabase: TypedSupabaseClient,
    limit = 100,
    dataSource: DataSource = DataSource.Live,
  ): Promise<RegimeBreakdownEntry[]> {
    let q = supabase
      .from("validation_log")
      .select(
        "date, pair, correct_t5, actual_direction_t5, correct_t20, actual_direction_t20",
      )
      .eq("is_superseded", false)
      .not("brier_score_t5", "is", null)
      .order("date", { ascending: false })
      .limit(limit);

    q = applyDataSourceDateFilter(q, dataSource);

    const { data: valData, error: valError } = await q;
    if (valError || !valData) return [];

    interface ValRow {
      date: string;
      pair: string;
    }

    const pairs = [...new Set((valData as ValRow[]).map((r) => r.pair))];
    const dates = [...new Set((valData as ValRow[]).map((r) => r.date))];
    const { data: regimeData, error: regimeError } = await supabase
      .from("regime_calls")
      .select("date, pair, regime")
      .in("pair", pairs)
      .in("date", dates);

    if (regimeError || !regimeData) return [];

    const regimeMap = new Map<string, string>();
    for (const r of regimeData as Array<{
      date: string;
      pair: string;
      regime: string;
    }>) {
      regimeMap.set(`${r.date}|${r.pair}`, r.regime);
    }

    return (valData as DbValidationLogRow[]).map((r) =>
      toRegimeBreakdownEntry(
        r,
        regimeMap.get(`${r.date}|${r.pair}`) ?? "UNKNOWN",
      ),
    );
  },
};
