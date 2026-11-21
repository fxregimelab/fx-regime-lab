import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const cache = new Map();
function load(file) {
  if (cache.has(file)) return cache.get(file);
  const source =
    process.env.FX_REPAIR_QUERY_BASELINE === "1" &&
    file.endsWith("supabase/queries.ts")
      ? execFileSync(
          "git",
          ["show", "9fa1505:web/src/lib/supabase/queries.ts"],
          { encoding: "utf8" },
        )
      : readFileSync(file, "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText;
  const module = { exports: {} };
  const localRequire = (name) =>
    name.startsWith("@/")
      ? load(path.resolve("src", `${name.slice(2)}.ts`).replaceAll("\\", "/"))
      : name.startsWith(".")
        ? load(
            path
              .resolve(path.dirname(file), `${name}.ts`)
              .replaceAll("\\", "/"),
          )
        : require(name);
  new Function("module", "exports", "require", output)(
    module,
    module.exports,
    localRequire,
  );
  cache.set(file, module.exports);
  return module.exports;
}
const queries = load(
  path.resolve("src/lib/supabase/queries.ts").replaceAll("\\", "/"),
);

function client(tables, error = null) {
  const requests = [];
  return {
    requests,
    from(table) {
      const state = {
        table,
        filters: [],
        orders: [],
        start: 0,
        end: Number.POSITIVE_INFINITY,
      };
      const q = {
        select() {
          return q;
        },
        eq(key, value) {
          state.filters.push((r) => r[key] === value);
          return q;
        },
        gte(key, value) {
          state.filters.push((r) => r[key] >= value);
          return q;
        },
        lt(key, value) {
          state.filters.push((r) => r[key] < value);
          return q;
        },
        not(key, _op, value) {
          state.filters.push((r) => r[key] !== value);
          return q;
        },
        in(key, values) {
          state.filters.push((r) => values.includes(r[key]));
          return q;
        },
        order(key, { ascending = true } = {}) {
          state.orders.push([key, ascending]);
          return q;
        },
        range(start, end) {
          state.start = start;
          state.end = end;
          return q;
        },
        limit(limit) {
          state.end = limit === null ? Number.POSITIVE_INFINITY : limit - 1;
          return q;
        },
        // biome-ignore lint/suspicious/noThenProperty: Supabase query builders implement PromiseLike.
        then(resolve, reject) {
          requests.push(state);
          let rows = (tables[table] ?? []).filter((r) =>
            state.filters.every((f) => f(r)),
          );
          rows = [...rows]
            .sort((a, b) => {
              for (const [key, asc] of state.orders) {
                if (a[key] !== b[key])
                  return (a[key] > b[key] ? 1 : -1) * (asc ? 1 : -1);
              }
              return 0;
            })
            .slice(state.start, state.end + 1);
          return Promise.resolve({ data: error ? null : rows, error }).then(
            resolve,
            reject,
          );
        },
      };
      return q;
    },
  };
}

const row = {
  id: 1,
  call_id: 1,
  pair: "EURUSD",
  date: "2026-04-01",
  call_date: "2026-04-01",
  predicted_direction: "BEARISH",
  predicted_regime: "TRENDING",
  confidence: 0.7,
  data_source: "live",
  strategy_version: "v2",
  model_version: "2.0-live",
  evaluation_version: "publication-snapshot-v2",
  is_superseded: false,
  population_version: "published-calls-v1",
  evaluation_present: true,
  evaluation_id: 1,
  log_return_t5_bps: 0,
  correct_t5: false,
  actual_direction_t5: "NEUTRAL",
  brier_score_t5: 0.49,
  log_return_net_bps_t5: -0.2,
  correct_net_t5: false,
  cost_bps_t5: 0.2,
  log_return_t20_bps: null,
  correct_t20: null,
  brier_score_t20: null,
  log_return_net_bps_t20: null,
  correct_net_t20: null,
  cost_bps_t20: null,
};

test("live metrics retrieve every row beyond 200 and 1000 without a date heuristic", async () => {
  const rows = Array.from({ length: 2201 }, (_, i) => ({
    ...row,
    id: i + 1,
    call_id: i + 1,
  }));
  const db = client({ validation_observations: rows });
  const actual = await queries.getValidationLogT5T20(db, null, "live");
  assert.equal(actual.length, 2201);
  assert.equal(db.requests.length, 3);
  assert.equal(actual[0].modelVersion, "2.0-live");
});

test("source, strategy, model, evaluation and population filters are exact", async () => {
  const wrong = [
    { data_source: "backtest" },
    { data_source: null },
    { model_version: "2.1" },
    { strategy_version: "v1" },
    { evaluation_version: "legacy-unversioned" },
    { evaluation_version: "published-direction-v1" },
    { population_version: "evaluation-records-v1" },
  ];
  const db = client({
    validation_observations: [
      row,
      ...wrong.map((change, i) => ({ ...row, id: i + 2, ...change })),
    ],
  });
  const actual = await queries.getValidationLogT5T20(db, null, "live");
  assert.equal(actual.length, 1);
  assert.equal(actual[0].t5Outcome, "WRONG");
  assert.equal(actual[0].t20Outcome, "—");
});

test("neutral is an abstention and remains visible without a Brier score", async () => {
  const db = client({
    validation_observations: [
      {
        ...row,
        predicted_direction: "NEUTRAL",
        correct_t5: null,
        brier_score_t5: null,
      },
    ],
  });
  const actual = await queries.getValidationLogT5T20(db, null, "live");
  assert.equal(actual.length, 1);
  assert.equal(actual[0].t5Outcome, "NEUTRAL");
});

test("requested replay model does not mix models or use a publication date cutoff", async () => {
  const db = client({
    validation_observations: [
      {
        ...row,
        date: "2026-09-01",
        call_date: "2026-09-01",
        data_source: "backtest",
        model_version: "2.1-m3",
      },
      {
        ...row,
        id: 2,
        data_source: "backtest",
        model_version: "2.0-historical",
      },
    ],
  });
  const actual = await queries.getValidationLogT5T20(
    db,
    null,
    "backtest",
    "2.1-m3",
  );
  assert.equal(actual.length, 1);
  assert.equal(actual[0].modelVersion, "2.1-m3");
  assert.equal(actual[0].date, "2026-09-01");
});

test("query errors do not fall back to unfiltered evidence", async () => {
  const db = client({}, { message: "missing evaluation_version" });
  await assert.rejects(
    queries.getValidationByVersion(db, "2.1-m3"),
    /unavailable/,
  );
  assert.equal(db.requests.length, 1);
});

test("aggregate snapshot filters and denominators match selected group", async () => {
  const stats = {
    ...row,
    as_of_date: "2026-09-01",
    window_days: 0,
    t5_total_calls: 100,
    t5_directional_calls: 30,
    t5_net_directional_calls: 20,
    t5_probability_score_calls: 25,
    t5_abstention_calls: 10,
    t5_missing_outcome_calls: 60,
    t5_win_rate: 0.6,
    t5_mean_signed_gross_return_bps: 8,
    t5_mean_log_return_bps: -8,
    t5_sharpe_like: 99,
  };
  const db = client({
    validation_stats: [
      stats,
      { ...stats, id: 2, model_version: "other", t5_win_rate: 1 },
      { ...stats, id: 3, window_days: 90, t5_win_rate: 1 },
      {
        ...stats,
        id: 4,
        population_version: "evaluation-records-v1",
        t5_win_rate: 1,
      },
    ],
  });
  const actual = await queries.getValidationStats(db, "t5", "live");
  assert.equal(actual.length, 1);
  assert.equal(actual[0].sampleSize, 30);
  assert.equal(actual[0].netSampleSize, 20);
  assert.equal(actual[0].avgReturnBps, 8);
  assert.equal(actual[0].sharpeLike, null);
  assert.equal(actual[0].winRateCI, null);
});

test("missing evaluations stay visible by call identity and reduce scored share", async () => {
  const missing = {
    ...row,
    id: 2,
    call_id: 2,
    evaluation_id: null,
    evaluation_present: false,
    log_return_t5_bps: null,
    correct_t5: null,
    brier_score_t5: null,
    log_return_net_bps_t5: null,
    correct_net_t5: null,
    cost_bps_t5: null,
  };
  const db = client({
    validation_observations: [
      row,
      missing,
      {
        ...missing,
        id: 3,
        call_id: 3,
        date: "2026-08-31",
        call_date: "2026-08-31",
      },
    ],
  });
  const rows = await queries.getValidationLogT5T20(db, null);
  assert.equal(rows.length, 3);
  assert.equal(rows.find((r) => r.callId === 2).t5Outcome, "—");
  assert.equal(rows.find((r) => r.callId === 2).evaluationId, null);
  assert.ok(db.requests.every((q) => q.table === "validation_observations"));
  const { computeStatsFromLog } = load(
    path.resolve("src/lib/track-record.ts").replaceAll("\\", "/"),
  );
  const stats = computeStatsFromLog(rows, null, "t5", "2026-09-01");
  assert.equal(stats.totalCalls, 3);
  assert.equal(stats.evaluationCalls, 1);
  assert.equal(stats.missingEvaluationCalls, 2);
  assert.equal(stats.pendingCalls, 1);
  assert.equal(stats.missingOutcomeCalls, 1);
  assert.equal(stats.sampleSize, 1);
  assert.equal(stats.coverage, 1 / 3);
  assert.equal(stats.populationVersion, "published-calls-v1");
});

test("model chooser uses actual replay model metadata and no invented fallback", async () => {
  assert.deepEqual(await queries.getBacktestVersions(client({})), []);
  const db = client({
    regime_calls: [
      {
        id: 1,
        model_version: "2.0-historical",
        data_source: "backtest",
        strategy_version: "v2",
      },
      {
        id: 2,
        model_version: "2.0-live",
        data_source: "live",
        strategy_version: "v2",
      },
    ],
  });
  assert.deepEqual(await queries.getBacktestVersions(db), ["2.0-historical"]);
});

test("public calculator agrees with Python on eligibility and payoff denominators", async () => {
  const changes = [
    {},
    { predicted_direction: "BULLISH", log_return_t5_bps: 25, correct_t5: true },
    { predicted_direction: "NEUTRAL", correct_t5: null, brier_score_t5: null },
    { correct_t5: null, log_return_t5_bps: null },
    { brier_score_t5: null, cost_bps_t5: null },
    { cost_bps_t5: -1 },
    { log_return_net_bps_t5: null },
    { predicted_direction: "UNKNOWN" },
    { date: "2026-08-31", call_date: "2026-08-31", evaluation_present: false },
    { date: "2026-09-02", call_date: "2026-09-02" },
    { date: "2026-02-31", call_date: "2026-02-31" },
  ];
  const evidence = changes.map((change, i) => ({
    ...row,
    id: i + 1,
    ...change,
  }));
  const python = execFileSync(
    "python",
    [
      "-c",
      `
import json, sys
from dataclasses import asdict
from datetime import date
from src.validation.aggregate import _compute_horizon
rows = json.load(sys.stdin)
print(json.dumps({h: asdict(_compute_horizon(rows, label, "brier_score_"+h, "correct_"+h, "log_return_"+h+"_bps", date(2026,9,1))) for h,label in [("t5","T+5"),("t20","T+20")]}))
`,
    ],
    {
      cwd: path.resolve("../pipeline"),
      input: JSON.stringify(evidence),
      encoding: "utf8",
    },
  );
  const expected = JSON.parse(python);
  const mapped = await queries.getValidationLogT5T20(
    client({ validation_observations: evidence }),
    null,
  );
  const { computeStatsFromLog } = load(
    path.resolve("src/lib/track-record.ts").replaceAll("\\", "/"),
  );
  const fields = {
    totalCalls: "total_calls",
    evaluationCalls: "evaluation_calls",
    missingEvaluationCalls: "missing_evaluation_calls",
    matureCalls: "mature_calls",
    pendingCalls: "pending_calls",
    directionalCalls: "directional_calls",
    sampleSize: "directional_calls",
    wins: "wins",
    abstainedCalls: "abstention_calls",
    unknownDirectionCalls: "unknown_direction_calls",
    missingOutcomeCalls: "missing_outcome_calls",
    brierSampleSize: "probability_score_calls",
    netSampleSize: "net_directional_calls",
    winRate: "win_rate",
    netWinRate: "net_win_rate",
    costBps: "cost_bps",
    brierScore: "mean_brier",
    avgReturnBps: "mean_log_return_bps",
    rolling90dAccuracy: "rolling_90d_accuracy",
  };
  for (const horizon of ["t5", "t20"]) {
    const actual = computeStatsFromLog(
      mapped,
      "EUR/USD",
      horizon,
      "2026-09-01",
    );
    for (const [publicKey, pythonKey] of Object.entries(fields)) {
      const value = actual[publicKey];
      assert.equal(
        typeof value === "number" ? Number(value.toFixed(6)) : value,
        expected[horizon][pythonKey],
        `${horizon}.${publicKey}`,
      );
    }
  }
});

test("legacy table renders abstention and unavailable outcomes without inventing losses", () => {
  const { ValidationTable } = load(
    path
      .resolve("src/components/regime/ValidationTable.tsx")
      .replaceAll("\\", "/"),
  );
  const { createElement } = require("react");
  const { renderToStaticMarkup } = require("react-dom/server");
  const html = renderToStaticMarkup(
    createElement(ValidationTable, {
      rows: [
        {
          date: "2026-04-01",
          pair: "EURUSD",
          call: "NEUTRAL",
          outcome: "neutral",
          return_pct: null,
        },
        {
          date: "2026-04-02",
          pair: "EURUSD",
          call: "BEARISH",
          outcome: "pending",
          return_pct: null,
        },
      ],
    }),
  );
  assert.match(html, /ABSTAINED/);
  assert.match(html, /UNAVAILABLE/);
  assert.doesNotMatch(html, /INCORRECT|0\.00/);
  assert.match(html, /MARKET MOVE \(BPS\)/);
});
