import {
  getRegimeBreakdown,
  getValidationLogT5T20,
} from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import { computeStatsFromLog } from "@/lib/track-record";
import { type NextRequest, NextResponse } from "next/server";

export const revalidate = 3600;

const PAIR_LABELS = ["EUR/USD", "USD/JPY", "USD/INR"] as const;

export async function GET(request: NextRequest) {
  const version = new URL(request.url).searchParams.get("version")?.trim();
  if (!version) {
    return NextResponse.json(
      { error: "An explicit backtest model version is required" },
      { status: 400 },
    );
  }

  try {
    const supabase = await createClient();
    const [validation, regimeBreakdown] = await Promise.all([
      getValidationLogT5T20(supabase, null, "backtest", version),
      getRegimeBreakdown(supabase, null, "backtest", version),
    ]);
    const asOfDate = new Date().toISOString().slice(0, 10);

    return NextResponse.json({
      version,
      regimeBreakdown,
      backtestT5: computeStatsFromLog(validation, null, "t5", asOfDate),
      backtestT20: computeStatsFromLog(validation, null, "t20", asOfDate),
      backtestT5ByPair: PAIR_LABELS.map((pair) =>
        computeStatsFromLog(validation, pair, "t5", asOfDate),
      ),
      backtestT20ByPair: PAIR_LABELS.map((pair) =>
        computeStatsFromLog(validation, pair, "t20", asOfDate),
      ),
    });
  } catch (error) {
    console.error("Backtest API error:", error);
    return NextResponse.json(
      { error: "The complete backtest cohort is unavailable" },
      { status: 500 },
    );
  }
}
