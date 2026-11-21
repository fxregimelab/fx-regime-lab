import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const cache = new Map();

function load(file) {
  if (cache.has(file)) return cache.get(file);
  const output = ts.transpileModule(readFileSync(file, "utf8"), {
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

function client(tables, errors = {}) {
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
          state.filters.push((row) => row[key] === value);
          return q;
        },
        in(key, values) {
          state.filters.push((row) => values.includes(row[key]));
          return q;
        },
        lte(key, value) {
          state.filters.push((row) => row[key] <= value);
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
          state.end = limit - 1;
          return q;
        },
        // biome-ignore lint/suspicious/noThenProperty: Supabase query builders implement PromiseLike.
        then(resolve, reject) {
          requests.push({ ...state });
          const error = errors[table] ?? null;
          let rows = (tables[table] ?? []).filter((row) =>
            state.filters.every((filter) => filter(row)),
          );
          rows = [...rows]
            .sort((a, b) => {
              for (const [key, ascending] of state.orders) {
                if (a[key] !== b[key])
                  return (a[key] > b[key] ? 1 : -1) * (ascending ? 1 : -1);
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

function call(overrides = {}) {
  return {
    id: 1,
    pair: "EURUSD",
    date: "2026-09-27",
    regime: "TRENDING",
    confidence: 0.7,
    signal_composite: 0.4,
    data_source: "live",
    strategy_version: "v2",
    model_version: "2.0-live",
    created_at: "2026-09-27T01:00:00Z",
    ...overrides,
  };
}

function signalPayload(overrides = {}) {
  return {
    pair: "EURUSD",
    date: "2026-09-27",
    rate_diff_2y: null,
    rate_diff_10y: null,
    cot_percentile: null,
    realized_vol_20d: null,
    realized_vol_5d: null,
    implied_vol_30d: null,
    spot: null,
    day_change: null,
    day_change_pct: null,
    cross_asset_vix: null,
    cross_asset_dxy: null,
    cross_asset_oil: null,
    cross_asset_us10y: null,
    cross_asset_gold: null,
    cross_asset_copper: null,
    cross_asset_stoxx: null,
    oi_delta: null,
    volume_rvol: null,
    structural_instability: false,
    breakeven_inflation_10y: null,
    rate_diff_10y_real: null,
    rate_z_tactical: null,
    rate_z_structural: null,
    z_blended: null,
    realized_vol_rank: null,
    skew_alignment: null,
    risk_reversal_25d: null,
    risk_reversal_source: "PENDING_REAL_DATA",
    days_since_cot: 0,
    fpi_flow: null,
    cot_net_pos: null,
    cot_asset_mgr_net: null,
    cot_lev_money_net: null,
    ecb_balance_sheet: null,
    bund_btp_spread: null,
    boj_policy_rate: null,
    india_vix: null,
    inr_forward_premium: null,
    data_quality_notes: null,
    ...overrides,
  };
}

test("current calls exclude future, backtest, unknown provenance, and other strategies", async () => {
  const db = client({
    regime_calls: [
      call({ id: 10, model_version: "model-a" }),
      call({ id: 11, model_version: "model-b" }),
      call({ id: 99, date: "2026-09-28" }),
      call({ id: 98, data_source: "backtest" }),
      call({ id: 97, data_source: null }),
      call({ id: 96, strategy_version: "v1" }),
      call({ id: 95, pair: "GBPUSD" }),
      call({ id: 20, pair: "USDJPY", model_version: "jpy-live" }),
      call({ id: 30, pair: "USDINR", model_version: "inr-live" }),
    ],
  });
  const actual = await queries.getLatestRegimeCalls(db, "2026-09-27");
  assert.deepEqual(Object.keys(actual).sort(), ["EURUSD", "USDINR", "USDJPY"]);
  assert.equal(actual.EURUSD.id, 11);
  assert.equal(actual.EURUSD.model_version, "model-b");
  assert.ok(db.requests[0].orders.some(([field]) => field === "id"));
});

test("independent pair queries prevent many revisions from starving another locked pair", async () => {
  const revisions = Array.from({ length: 1005 }, (_, index) =>
    call({ id: 2000 - index, model_version: `eur-${index}` }),
  );
  const db = client({
    regime_calls: [
      ...revisions,
      call({ id: 3, pair: "USDJPY", date: "2026-09-26" }),
      call({ id: 2, pair: "USDINR", date: "2026-09-26" }),
    ],
  });
  const actual = await queries.getLatestRegimeCalls(db, "2026-09-27");
  assert.equal(actual.EURUSD.id, 2000);
  assert.equal(actual.USDJPY.id, 3);
  assert.equal(actual.USDINR.id, 2);
  assert.equal(db.requests.length, 3);
  assert.deepEqual(
    db.requests.map((request) => request.table),
    ["regime_calls", "regime_calls", "regime_calls"],
  );
});

test("history paginates before session dedupe and retains durable ID and model label", async () => {
  const revisions = Array.from({ length: 1005 }, (_, index) =>
    call({ id: 3000 - index, model_version: `revision-${index}` }),
  );
  const prior = call({
    id: 8,
    date: "2026-09-26",
    model_version: "prior-session",
  });
  const db = client({ regime_calls: [...revisions, prior] });
  const actual = await queries.getHistoricalRegimeCalls(db, "EUR/USD", 2);
  assert.deepEqual(
    actual.map(({ id, date, model_version }) => ({ id, date, model_version })),
    [
      { id: 3000, date: "2026-09-27", model_version: "revision-0" },
      { id: 8, date: "2026-09-26", model_version: "prior-session" },
    ],
  );
  assert.equal(db.requests.length, 2);
});

test("signals use exact selected call IDs and ignore unrelated newer evidence", async () => {
  const calls = {
    EURUSD: { ...call({ id: 11, model_version: "selected" }) },
  };
  const db = client({
    live_publication_signals: [
      {
        call_id: 11,
        pair: "EURUSD",
        date: "2026-09-27",
        signal_payload: signalPayload({ spot: 1.17 }),
      },
      {
        call_id: 12,
        pair: "EURUSD",
        date: "2026-09-27",
        signal_payload: signalPayload({ spot: 9.99 }),
      },
    ],
    signals: [{ pair: "EURUSD", date: "2026-09-27", spot: 8.88 }],
  });
  const actual = await queries.getLatestSignals(db, calls);
  assert.equal(actual.EURUSD.spot, 1.17);
  assert.equal(actual.EURUSD.created_at, null);
  assert.deepEqual(
    db.requests.map((request) => request.table),
    ["live_publication_signals"],
  );
});

test("missing legacy evidence is explicit absence and never falls back to mutable signals", async () => {
  const selected = { EURUSD: call({ id: 42 }) };
  const db = client({
    live_publication_signals: [],
    signals: [{ pair: "EURUSD", date: "2026-09-27", spot: 1.23 }],
  });
  assert.deepEqual(await queries.getLatestSignals(db, selected), {});
  assert.deepEqual(
    db.requests.map((request) => request.table),
    ["live_publication_signals"],
  );
});

test("mismatched view or payload identity is rejected instead of rewritten", async () => {
  const selected = { EURUSD: call({ id: 42 }) };
  const wrongViewDate = client({
    live_publication_signals: [
      {
        call_id: 42,
        pair: "EURUSD",
        date: "2026-09-26",
        signal_payload: signalPayload({ date: "2026-09-26" }),
      },
    ],
  });
  await assert.rejects(
    queries.getLatestSignals(wrongViewDate, selected),
    /does not match its selected call/,
  );

  const wrongPayloadPair = client({
    live_publication_signals: [
      {
        call_id: 42,
        pair: "EURUSD",
        date: "2026-09-27",
        signal_payload: signalPayload({ pair: "USDJPY" }),
      },
    ],
  });
  await assert.rejects(
    queries.getLatestSignals(wrongPayloadPair, selected),
    /inconsistent identity/,
  );
});

test("publication readers propagate database failures", async () => {
  await assert.rejects(
    queries.getLatestRegimeCalls(
      client({}, { regime_calls: { message: "call failure" } }),
      "2026-09-27",
    ),
    /call failure/,
  );
  await assert.rejects(
    queries.getLatestSignals(
      client({}, { live_publication_signals: { message: "signal failure" } }),
      { EURUSD: call({ id: 1 }) },
    ),
    /signal failure/,
  );
  await assert.rejects(
    queries.getHistoricalRegimeCalls(
      client({}, { regime_calls: { message: "history failure" } }),
      "EURUSD",
      30,
    ),
    /history failure/,
  );
});

test("owned routes pass their selected call set into signal evidence reads", () => {
  for (const file of [
    "src/app/page.tsx",
    "src/app/desk/page.tsx",
    "src/app/desk/fx-regime/[pair]/page.tsx",
  ]) {
    const source = readFileSync(file, "utf8");
    assert.match(source, /getLatestSignals\(supabase, calls\)/, file);
    assert.doesNotMatch(source, /getLatestSignals\(supabase\)/, file);
  }
  const layout = readFileSync("src/app/desk/layout.tsx", "utf8");
  assert.doesNotMatch(layout, /getLatestSignals/, "desk layout");
  assert.match(
    [
      readFileSync("src/app/page.tsx", "utf8"),
      readFileSync("src/app/desk/page.tsx", "utf8"),
      readFileSync("src/app/desk/fx-regime/[pair]/page.tsx", "utf8"),
    ].join("\n"),
    /INPUTS UNAVAILABLE/,
  );

  const signalCard = readFileSync(
    "src/components/dashboard/SignalCard.tsx",
    "utf8",
  );
  assert.match(signalCard, /call_id: call\?\.id \?\? null/);
  assert.match(signalCard, /regime_calls, live_publication_signals/);
  assert.match(
    signalCard,
    /model_version: call\?\.model_version \?\? "unknown"/,
  );
  assert.match(signalCard, /REVISED PUBLICATION/);
  assert.match(signalCard, /OBSERVED SESSIONS/);
  assert.doesNotMatch(signalCard, /sourceTable: "regime_calls, signals"/);
  assert.doesNotMatch(
    signalCard,
    /dataVersion: call\?\.model_version \?\? "v3"/,
  );
});
