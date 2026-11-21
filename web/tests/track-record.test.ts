import assert from "node:assert/strict";
import test from "node:test";
import type { ValidationRowT5 } from "../src/lib/supabase/queries.ts";
// @ts-expect-error Node's strip-types runner requires the source extension.
import { computeStatsFromLog } from "../src/lib/track-record.ts";

function row(overrides: Partial<ValidationRowT5> = {}): ValidationRowT5 {
  return {
    date: "2026-08-03",
    pair: "EUR/USD",
    predicted: "BULLISH",
    t5ReturnBps: 10,
    t5ReturnNetBps: 9.8,
    t5Outcome: "CORRECT",
    t5CorrectNet: true,
    t5CostBps: 0.2,
    t5Brier: 0.04,
    t20ReturnBps: 20,
    t20ReturnNetBps: 19.8,
    t20Outcome: "CORRECT",
    t20CorrectNet: true,
    t20CostBps: 0.2,
    t20Brier: 0.04,
    dataSource: "live",
    strategyVersion: "v2",
    modelVersion: "2.0-live",
    evaluationVersion: "publication-snapshot-v2",
    ...overrides,
  };
}

test("mirrors bearish raw returns into signed gross payoff", () => {
  const stats = computeStatsFromLog(
    [row(), row({ predicted: "BEARISH", t5ReturnBps: -30 })],
    null,
    "t5",
    "2026-08-31",
  );
  assert.equal(stats.avgReturnBps, 20);
  assert.equal(stats.sharpeLike, null);
});

test("keeps gross payoff separate when net fields are missing", () => {
  const stats = computeStatsFromLog(
    [
      row({
        t5ReturnBps: 12,
        t5ReturnNetBps: null,
        t5CorrectNet: null,
        t5CostBps: null,
      }),
    ],
    null,
    "t5",
    "2026-08-31",
  );
  assert.equal(stats.avgReturnBps, 12);
  assert.equal(stats.netWinRate, null);
  assert.equal(stats.netSampleSize, 0);
});

test("counts published neutral as an abstention", () => {
  const stats = computeStatsFromLog(
    [row({ predicted: "NEUTRAL", t5Outcome: "NEUTRAL", t5Brier: 0 })],
    null,
    "t5",
    "2026-08-31",
  );
  assert.equal(stats.totalCalls, 1);
  assert.equal(stats.abstainedCalls, 1);
  assert.equal(stats.sampleSize, 0);
  assert.equal(stats.brierSampleSize, 0);
});

test("excludes pending and immature outcomes", () => {
  const stats = computeStatsFromLog(
    [
      row({ date: "2026-08-03", t5Outcome: "—" }),
      row({ date: "2026-08-28", t5Outcome: "CORRECT" }),
    ],
    null,
    "t5",
    "2026-08-31",
  );
  assert.equal(stats.totalCalls, 2);
  assert.equal(stats.sampleSize, 0);
  assert.equal(stats.matureCalls, 1);
  assert.equal(stats.pendingCalls, 1);
  assert.equal(stats.missingOutcomeCalls, 1);
});

test("uses the requested as-of date rather than the last row date", () => {
  const stats = computeStatsFromLog(
    [
      row({ date: "2026-01-02" }),
      row({ date: "2026-08-03", t5Outcome: "WRONG" }),
      row({ date: "2027-01-04" }),
    ],
    null,
    "t5",
    "2026-08-31",
  );
  assert.equal(stats.asOfDate, "2026-08-31");
  assert.equal(stats.totalCalls, 2);
  assert.equal(stats.rolling90dAccuracy, 0);
});

test("rejects invalid values and incomplete net payoffs", () => {
  const stats = computeStatsFromLog(
    [
      row({ t5ReturnBps: Number.NaN }),
      row({ date: "2026-08-04", t5Brier: Number.POSITIVE_INFINITY }),
      row({ date: "2026-08-05", t5ReturnNetBps: Number.NaN }),
    ],
    null,
    "t5",
    "2026-08-31",
  );
  assert.equal(stats.sampleSize, 2);
  assert.equal(stats.brierSampleSize, 1);
  assert.equal(stats.netSampleSize, 1);
});

test("scores a mature directional deadband outcome as wrong", () => {
  const stats = computeStatsFromLog(
    [row({ t5ReturnBps: 2, t5Outcome: "WRONG", t5Brier: 0.64 })],
    null,
    "t5",
    "2026-08-31",
  );
  assert.equal(stats.sampleSize, 1);
  assert.equal(stats.winRate, 0);
});

test("rejects impossible dates and invalid as-of dates", () => {
  const stats = computeStatsFromLog(
    [row({ date: "2026-02-31" })],
    null,
    "t5",
    "2026-08-31",
  );
  assert.equal(stats.totalCalls, 1);
  assert.equal(stats.matureCalls, 0);
  assert.equal(stats.pendingCalls, 1);
  assert.throws(
    () => computeStatsFromLog([row()], null, "t5", "2026-02-31"),
    /Invalid as-of date/,
  );
});

test("fails closed when cohort metadata is mixed", () => {
  assert.throws(
    () =>
      computeStatsFromLog(
        [row(), row({ date: "2026-08-04", modelVersion: "2.1-live" })],
        null,
        "t5",
        "2026-08-31",
      ),
    /mixed cohort metadata/,
  );
});
