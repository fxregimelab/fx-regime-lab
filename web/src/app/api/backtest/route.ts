import { NextRequest, NextResponse } from "next/server";
import { computeStatsFromLog } from "@/lib/track-record";
import {
  getRegimeCallsByVersion,
  getRegimeBreakdownByVersion,
  getSimulationResults,
  getValidationLogT5T20,
} from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";

export const revalidate = 3600;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const version = searchParams.get("version") ?? "v3";

  try {
    const supabase = await createClient();

    const [versionedCalls, versionedBreakdown, simulationResults, backtestValidation] =
      await Promise.all([
        getRegimeCallsByVersion(supabase, version, undefined, undefined, 100),
        getRegimeBreakdownByVersion(supabase, version, 100),
        getSimulationResults(supabase, version),
        getValidationLogT5T20(supabase, 100, "backtest"),
      ]);

    const PAIR_LABELS = ["EUR/USD", "USD/JPY", "USD/INR"] as const;

    const backtestT5 = computeStatsFromLog(backtestValidation, null, "t5");
    const backtestT20 = computeStatsFromLog(backtestValidation, null, "t20");
    const backtestT5ByPair = PAIR_LABELS.map((p) =>
      computeStatsFromLog(backtestValidation, p, "t5"),
    );

    return NextResponse.json({
      versionedCalls,
      versionedBreakdown,
      simulationResults,
      backtestT5,
      backtestT20,
      backtestT5ByPair,
    });
  } catch (error) {
    console.error("Backtest API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch backtest data" },
      { status: 500 },
    );
  }
}
