import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { ValidationRepository } from "../repositories/validation-repository";

type QueryResult = { data: unknown; error: null | { message: string } };

function createMockSupabase(
  validationRows: Record<string, unknown>[],
  regimeRows: Record<string, unknown>[] = [],
  statsRows: Record<string, unknown>[] = [],
) {
  return {
    from: (table: string) => {
      const filters: Record<string, unknown> = {};
      let dateGte: string | null = null;
      let dateLt: string | null = null;

      const builder = {
        select: () => builder,
        eq: (col: string, val: unknown) => {
          filters[col] = val;
          return builder;
        },
        not: () => builder,
        order: () => builder,
        limit: () => builder,
        gte: (_col: string, val: string) => {
          dateGte = val;
          return builder;
        },
        lt: (_col: string, val: string) => {
          dateLt = val;
          return builder;
        },
        in: () => builder,
      };

      const resolveRows = () => {
        if (table === "validation_log") {
          return validationRows.filter((row) => {
            if (filters.is_superseded === false && row.is_superseded === true) {
              return false;
            }
            const date = String(row.date);
            if (dateGte && date < dateGte) return false;
            if (dateLt && date >= dateLt) return false;
            return true;
          });
        }
        if (table === "regime_calls") return regimeRows;
        if (table === "validation_stats") {
          return statsRows.filter((row) => {
            const asOf = String(row.as_of_date);
            if (dateGte && asOf < dateGte) return false;
            if (dateLt && asOf >= dateLt) return false;
            return true;
          });
        }
        return [];
      };

      // biome-ignore lint/suspicious/noThenProperty: mock query builder must be thenable for await
      Object.defineProperty(builder, "then", {
        value: (
          resolve: (value: QueryResult) => void,
          _reject?: (reason: unknown) => void,
        ) => {
          resolve({ data: resolveRows(), error: null });
        },
      });

      return builder;
    },
  };
}

describe("ValidationRepository.getLogT5T20", () => {
  it("maps validation rows to domain entries with display pairs", async () => {
    const supabase = createMockSupabase(
      [
        {
          date: "2026-06-01",
          pair: "EURUSD",
          call_id: 1,
          is_superseded: false,
          brier_score_t5: 0.1,
          log_return_t5_bps: 12,
          log_return_net_bps_t5: 10,
          correct_t5: true,
          actual_direction_t5: "UP",
          correct_net_t5: true,
          cost_bps_t5: 0.2,
          log_return_t20_bps: 20,
          log_return_net_bps_t20: 18,
          correct_t20: false,
          actual_direction_t20: "DOWN",
          correct_net_t20: false,
          cost_bps_t20: 0.2,
          brier_score_t20: 0.4,
        },
      ],
      [{ id: 1, predicted_direction: "UP" }],
    );

    const rows = await ValidationRepository.getLogT5T20(
      supabase as never,
      100,
      "live",
    );

    assert.equal(rows.length, 1);
    assert.equal(rows[0].pair, "EUR/USD");
    assert.equal(rows[0].predicted, "UP");
    assert.equal(rows[0].t5Outcome, "CORRECT");
    assert.equal(rows[0].t20Outcome, "WRONG");
  });

  it("filters live rows by cutoff date", async () => {
    const supabase = createMockSupabase([
      {
        date: "2026-04-01",
        pair: "USDJPY",
        is_superseded: false,
        brier_score_t5: 0.2,
        correct_t5: true,
        actual_direction_t5: "UP",
        correct_t20: true,
        actual_direction_t20: "UP",
      },
      {
        date: "2026-06-01",
        pair: "USDJPY",
        is_superseded: false,
        brier_score_t5: 0.2,
        correct_t5: true,
        actual_direction_t5: "UP",
        correct_t20: true,
        actual_direction_t20: "UP",
      },
    ]);

    const live = await ValidationRepository.getLogT5T20(
      supabase as never,
      100,
      "live",
    );
    const backtest = await ValidationRepository.getLogT5T20(
      supabase as never,
      100,
      "backtest",
    );

    assert.equal(live.length, 1);
    assert.equal(live[0].date, "2026-06-01");
    assert.equal(backtest.length, 1);
    assert.equal(backtest[0].date, "2026-04-01");
  });
});

describe("ValidationRepository.getStats", () => {
  it("returns latest as-of-date stats for the requested horizon", async () => {
    const supabase = createMockSupabase(
      [],
      [],
      [
        {
          pair: "EURUSD",
          as_of_date: "2026-06-01",
          t5_win_rate: 0.6,
          t5_win_rate_ci_lower: 0.5,
          t5_win_rate_ci_upper: 0.7,
          t5_net_win_rate: 0.55,
          t5_net_win_rate_ci_lower: 0.45,
          t5_net_win_rate_ci_upper: 0.65,
          t5_wins: 6,
          t5_mean_brier: 0.2,
          t5_total_calls: 10,
          t5_mean_log_return_bps: 5,
          t5_sharpe_like: 1.1,
          t5_rolling_90d_accuracy: 0.58,
        },
        {
          pair: "EURUSD",
          as_of_date: "2026-05-01",
          t5_win_rate: 0.4,
          t5_win_rate_ci_lower: 0.3,
          t5_win_rate_ci_upper: 0.5,
          t5_wins: 4,
          t5_total_calls: 10,
        },
        {
          pair: "EURUSD",
          as_of_date: "2026-04-01",
          t5_win_rate: 0.9,
          t5_wins: 9,
          t5_total_calls: 10,
        },
      ],
    );

    const stats = await ValidationRepository.getStats(
      supabase as never,
      "t5",
      "live",
    );

    assert.equal(stats.length, 1);
    assert.equal(stats[0].pair, "EUR/USD");
    assert.equal(stats[0].horizon, "t5");
    assert.equal(stats[0].winRate, 0.6);
    assert.equal(stats[0].asOfDate, "2026-06-01");
  });
});
