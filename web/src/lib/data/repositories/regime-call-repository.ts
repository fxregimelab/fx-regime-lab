import type { Database } from "@/lib/supabase/database.types";
import type { TypedSupabaseClient } from "../adapters/supabase-client";
import { toRegimeCall } from "../adapters/supabase-validation-adapter";
import type { RegimeCall } from "../domain/regime";

type RegimeCallRow = Database["public"]["Tables"]["regime_calls"]["Row"];

export const RegimeCallRepository = {
  async getLatest(
    supabase: TypedSupabaseClient,
  ): Promise<Record<string, RegimeCall>> {
    const { data, error } = await supabase
      .from("regime_calls")
      .select("*")
      .order("date", { ascending: false })
      .limit(100);

    if (error || !data) return {};

    const latest: Record<string, RegimeCall> = {};
    for (const row of data as RegimeCallRow[]) {
      const pair = row.pair;
      if (!latest[pair]) {
        latest[pair] = toRegimeCall(row);
      }
    }
    return latest;
  },
};
