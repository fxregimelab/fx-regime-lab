import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const require = createRequire(import.meta.url);

function resolveLocal(fromFile, request) {
  const base = request.startsWith("@/")
    ? path.resolve("src", request.slice(2))
    : path.resolve(path.dirname(fromFile), request);
  for (const candidate of [
    base,
    `${base}.ts`,
    `${base}.tsx`,
    path.join(base, "index.ts"),
    path.join(base, "index.tsx"),
  ]) {
    if (existsSync(candidate)) return candidate.replaceAll("\\", "/");
  }
  throw new Error(`Cannot resolve ${request} from ${fromFile}`);
}

function makeLoader(stubs = {}) {
  const cache = new Map();
  function load(file) {
    if (cache.has(file)) return cache.get(file);
    const output = ts.transpileModule(readFileSync(file, "utf8"), {
      compilerOptions: {
        esModuleInterop: true,
        jsx: ts.JsxEmit.ReactJSX,
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
      },
    }).outputText;
    const module = { exports: {} };
    cache.set(file, module.exports);
    const localRequire = (name) => {
      if (Object.hasOwn(stubs, name)) return stubs[name];
      if (name.startsWith("@/") || name.startsWith(".")) {
        return load(resolveLocal(file, name));
      }
      return require(name);
    };
    new Function("module", "exports", "require", output)(
      module,
      module.exports,
      localRequire,
    );
    cache.set(file, module.exports);
    return module.exports;
  }
  return load;
}

const passthrough = ({ children }) =>
  React.createElement("div", null, children);
const deskLoader = makeLoader({
  "@/components/ui/BinaryResolve": {
    BinaryResolve: ({ value }) => React.createElement("span", null, value),
  },
  "@/components/ui/GhostResolve": { GhostResolve: passthrough },
  "@/components/ui/data-lineage": { DataLineage: passthrough },
  "@/components/ui/reproducibility-export": {
    ReproducibilityExport: () => null,
  },
  "@/lib/regime-share": { formatRegimeShareNote: () => "share" },
  "framer-motion": {
    AnimatePresence: passthrough,
    motion: new Proxy(
      {},
      {
        get:
          (_target, tag) =>
          ({ children, ...props }) =>
            React.createElement(tag, props, children),
      },
    ),
  },
});

const desk = deskLoader(
  path.resolve("src/components/ui/desk-card.tsx").replaceAll("\\", "/"),
);
const diagnostic = deskLoader(
  path.resolve("src/lib/crowding-diagnostic.ts").replaceAll("\\", "/"),
);

function validDiagnostic(overrides = {}) {
  const base = {
    version: "crowding-description-v1",
    pair: "EURUSD",
    call_id: 71,
    as_of_date: "2026-09-27",
    predicted_direction: "BULLISH",
    cot: {
      status: "PROVISIONAL",
      report_date: "2026-09-22",
      report_age_days: 5,
      net_long: -1200,
      asset_mgr_net: 300,
      lev_money_net: -1500,
      pair_direction: -1,
      alignment: "OPPOSED",
      series_definition: "UNKNOWN",
      release_status: "UNVERIFIED",
      rank_percentile: null,
      reasons: ["CATEGORY_PROVENANCE_UNAVAILABLE"],
    },
    price: {
      status: "PROVISIONAL",
      latest_date: "2026-09-27",
      spot: 1.17,
      mean_close_40: 1.2,
      observation_count: 40,
      relative_to_mean_pct: -2.5,
      reasons: [],
    },
    participant_loss_estimate: null,
    squeeze_probability: null,
    point_in_time_qualified: false,
  };
  return {
    ...base,
    ...overrides,
    cot: { ...base.cot, ...(overrides.cot ?? {}) },
    price: { ...base.price, ...(overrides.price ?? {}) },
  };
}

function unavailableCot(...reasons) {
  return {
    status: "UNAVAILABLE",
    report_date: null,
    report_age_days: null,
    net_long: null,
    asset_mgr_net: null,
    lev_money_net: null,
    pair_direction: null,
    alignment: "UNAVAILABLE",
    series_definition: "UNKNOWN",
    release_status: "UNVERIFIED",
    rank_percentile: null,
    reasons,
  };
}

function unavailablePrice(...reasons) {
  return {
    status: "UNAVAILABLE",
    latest_date: null,
    spot: null,
    mean_close_40: null,
    observation_count: 0,
    relative_to_mean_pct: null,
    reasons,
  };
}

function deskProps(overrides = {}) {
  return {
    variant: "hero",
    pairDisplay: "EUR/USD",
    spot: 1.17,
    confidence: 0.64,
    rankJump: 7,
    regimeAge: 3,
    apexScoreDisplay: 98,
    structuralRegime: "TRANSITIONAL",
    invalidationTriggered: false,
    telemetryStatus: "ONLINE",
    dominanceArray: [],
    painIndex: 99,
    markovProbabilities: null,
    aiBrief: JSON.stringify({
      bias_summary: "Rate spread still supports the call.",
      catalyst_driver: "Next inflation release.",
      squeeze_risk: "EXTREME squeeze danger from underwater participants.",
    }),
    telemetryAudit: { crowding_diagnostic: validDiagnostic() },
    ...overrides,
  };
}

function renderDesk(overrides = {}) {
  return renderToStaticMarkup(
    React.createElement(desk.DeskCard, deskProps(overrides)),
  );
}

test("DeskCard renders signed provisional descriptions and suppresses legacy risk claims", () => {
  const html = renderDesk();
  assert.match(
    html,
    /Reported net \(provisional\): -1,200 contracts · opposed to call/,
  );
  assert.match(html, /Report date: 2026-09-22 · category definition unknown/);
  assert.match(html, /Source availability: unverified/);
  assert.match(
    html,
    /Close vs 40-observation mean: -2\.50% · latest close date: 2026-09-27/,
  );
  assert.match(html, /Participant losses and squeeze probability unavailable/);
  assert.match(html, /Rate spread still supports the call/);
  assert.match(html, /Next inflation release/);
  assert.doesNotMatch(html, /EXTREME squeeze danger|underwater participants/i);
  assert.doesNotMatch(
    html,
    /APEX|PAIN INDX|RANK JUMP|ASYMMETRIC SETUP|No extreme divergence/i,
  );
  assert.doesNotMatch(html, />98</);
  assert.doesNotMatch(html, />99(?:\.00)?</);
});

test("missing, legacy, and malformed diagnostics are explicit unavailable states", () => {
  const missing = renderDesk({ telemetryAudit: {} });
  const legacy = renderDesk({
    telemetryAudit: {
      crowding_diagnostic: { version: "pain-index-v1", pain: 99 },
    },
  });
  const malformed = renderDesk({
    telemetryAudit: {
      crowding_diagnostic: {
        version: "crowding-description-v1",
        pair: "EURUSD",
      },
    },
  });
  assert.match(missing, /no versioned diagnostic/);
  assert.match(legacy, /legacy estimates are not validated/);
  assert.match(malformed, /malformed diagnostic payload/);
  for (const html of [missing, legacy, malformed]) {
    assert.match(
      html,
      /Participant losses and squeeze probability unavailable/,
    );
    assert.doesNotMatch(html, /No extreme divergence|CONTROLLED|ELEVATED/i);
  }
});

test("zero is preserved while NaN and false qualification are rejected", () => {
  const zero = validDiagnostic({
    cot: { net_long: 0, pair_direction: 0, alignment: "FLAT_REPORTED_NET" },
    price: { spot: 1.2, relative_to_mean_pct: 0 },
  });
  const zeroHtml = renderDesk({
    telemetryAudit: { crowding_diagnostic: zero },
  });
  assert.match(
    zeroHtml,
    /Reported net \(provisional\): 0 contracts · reported net is flat/,
  );
  assert.match(zeroHtml, /Close vs 40-observation mean: 0\.00%/);

  assert.equal(
    diagnostic.readCrowdingDiagnostic(
      validDiagnostic({ price: { relative_to_mean_pct: Number.NaN } }),
    ).kind,
    "malformed",
  );
  assert.equal(
    diagnostic.readCrowdingDiagnostic(
      validDiagnostic({ point_in_time_qualified: true }),
    ).kind,
    "malformed",
  );
  assert.equal(
    diagnostic.readCrowdingDiagnostic(
      validDiagnostic({ cot: { release_status: "VERIFIED" } }),
    ).kind,
    "malformed",
  );
});

test("actual core short-history payload preserves valid COT and latest price", () => {
  const shortHistory = validDiagnostic({
    price: {
      status: "PROVISIONAL",
      latest_date: "2026-09-26",
      spot: 1.18,
      mean_close_40: null,
      observation_count: 39,
      relative_to_mean_pct: null,
      reasons: ["REPORT_DATE_ONLY", "INSUFFICIENT_PRICE_OBSERVATIONS"],
    },
  });
  assert.equal(diagnostic.readCrowdingDiagnostic(shortHistory).kind, "valid");
  const html = renderDesk({
    spot: 1.18,
    telemetryAudit: { crowding_diagnostic: shortHistory },
  });
  assert.match(html, /Reported net \(provisional\): -1,200 contracts/);
  assert.match(
    html,
    /Latest supplied close: 1\.18 · date: 2026-09-26 · observations: 39/,
  );
  assert.match(html, /Close vs 40-observation mean: unavailable/);
  assert.doesNotMatch(html, /malformed diagnostic payload/);
});

test("COT and price availability remain independent", () => {
  const validCotMissingPrice = validDiagnostic({
    price: unavailablePrice("SPOT_HISTORY_UNAVAILABLE"),
  });
  const noCotValidPrice = validDiagnostic({
    cot: unavailableCot(
      "COT_REPORT_UNAVAILABLE",
      "CATEGORY_PROVENANCE_UNAVAILABLE",
    ),
  });
  const cotHtml = renderDesk({
    telemetryAudit: { crowding_diagnostic: validCotMissingPrice },
  });
  assert.match(cotHtml, /Reported net \(provisional\): -1,200 contracts/);
  assert.match(cotHtml, /Close vs 40-observation mean: unavailable/);

  const priceHtml = renderDesk({
    telemetryAudit: { crowding_diagnostic: noCotValidPrice },
  });
  assert.match(priceHtml, /Reported net: unavailable/);
  assert.match(priceHtml, /Close vs 40-observation mean: -2\.50%/);

  const underflow = validDiagnostic({
    price: {
      status: "UNAVAILABLE",
      latest_date: "2026-09-27",
      spot: 5e-324,
      mean_close_40: null,
      observation_count: 40,
      relative_to_mean_pct: null,
      reasons: ["REPORT_DATE_ONLY", "INVALID_PRICE_ARITHMETIC"],
    },
  });
  const underflowHtml = renderDesk({
    telemetryAudit: { crowding_diagnostic: underflow },
  });
  assert.match(underflowHtml, /Reported net \(provisional\): -1,200 contracts/);
  assert.match(underflowHtml, /Close vs 40-observation mean: unavailable/);
  assert.doesNotMatch(underflowHtml, /malformed diagnostic payload/);
});

test("valid diagnostics render only on their matching locked pair", () => {
  const fixtures = [
    {
      display: "EUR/USD",
      payload: validDiagnostic(),
      expected: /-1,200 contracts · opposed to call/,
    },
    {
      display: "USD/JPY",
      payload: validDiagnostic({
        pair: "USDJPY",
        cot: { net_long: 100, pair_direction: -1, alignment: "OPPOSED" },
      }),
      expected: /\+100 contracts · opposed to call/,
    },
    {
      display: "USD/INR",
      payload: validDiagnostic({
        pair: "USDINR",
        cot: unavailableCot(
          "UNSUPPORTED_COT_PAIR",
          "CATEGORY_PROVENANCE_UNAVAILABLE",
        ),
      }),
      expected: /Reported net: unavailable/,
    },
  ];
  for (const { display, payload, expected } of fixtures) {
    const html = renderDesk({
      pairDisplay: display,
      telemetryAudit: { crowding_diagnostic: payload },
    });
    assert.match(html, expected, display);
    assert.doesNotMatch(html, /malformed diagnostic payload/, display);
  }

  const mismatch = renderDesk({
    pairDisplay: "EUR/USD",
    telemetryAudit: {
      crowding_diagnostic: validDiagnostic({
        pair: "USDJPY",
        cot: { net_long: 100, pair_direction: -1, alignment: "OPPOSED" },
      }),
    },
  });
  assert.match(mismatch, /malformed diagnostic payload/);
  assert.doesNotMatch(mismatch, /\+100 contracts/);
});

test("semantic contradictions and future observations are malformed", () => {
  const unavailableWithDeviation = validDiagnostic({
    price: {
      ...unavailablePrice("INVALID_SPOT_HISTORY"),
      relative_to_mean_pct: 2,
    },
  });
  const malformed = [
    validDiagnostic({
      cot: { report_date: "2026-09-28", report_age_days: 0 },
    }),
    validDiagnostic({ cot: { report_age_days: 4 } }),
    validDiagnostic({ price: { latest_date: "2026-09-28" } }),
    validDiagnostic({ price: { spot: 0, relative_to_mean_pct: -100 } }),
    validDiagnostic({ price: { mean_close_40: -1 } }),
    validDiagnostic({ price: { spot: 1e308, mean_close_40: 1e-308 } }),
    unavailableWithDeviation,
    validDiagnostic({ cot: { pair_direction: 1, alignment: "ALIGNED" } }),
    validDiagnostic({ cot: { alignment: "ALIGNED" } }),
    validDiagnostic({ price: { relative_to_mean_pct: 2.5 } }),
  ];
  for (const payload of malformed) {
    assert.equal(diagnostic.readCrowdingDiagnostic(payload).kind, "malformed");
  }
  const html = renderDesk({
    telemetryAudit: { crowding_diagnostic: unavailableWithDeviation },
  });
  assert.match(html, /malformed diagnostic payload/);
  assert.doesNotMatch(html, /2\.00%/);
});

test("legacy raw brief text cannot pass unsupported claims through", () => {
  const html = renderDesk({
    aiBrief: "PAIN 99: underwater positioning means squeeze danger is ELEVATED",
  });
  assert.match(html, /\[ DIAGNOSTICS \]/);
  assert.match(html, /Participant losses and squeeze probability unavailable/);
  assert.doesNotMatch(html, /PAIN 99|underwater positioning|ELEVATED/);
});

test("DeskCardTelemetryRow does not render an old Apex badge", () => {
  const html = renderToStaticMarkup(
    React.createElement(desk.DeskCardTelemetryRow, {
      pairLabel: "EUR/USD",
      spot: 1.17,
      structuralRegime: "TRANSITIONAL",
      confidence: 0.64,
      apexScoreDisplay: 87,
      telemetryAudit: { crowding_diagnostic: validDiagnostic() },
    }),
  );
  assert.match(html, /EUR\/USD/);
  assert.doesNotMatch(html, />87</);
  assert.doesNotMatch(html, /APEX|PAIN/i);
});

test("desk query mapper suppresses stored pain, Apex, and rank-jump promotion", async () => {
  const requests = [];
  const tables = {
    desk_open_cards: [
      {
        date: "2026-09-27",
        pair: "EURUSD",
        structural_regime: "TRANSITIONAL",
        dominance_array: [],
        pain_index: 99,
        markov_probabilities: null,
        ai_brief: null,
        telemetry_audit: { crowding_diagnostic: validDiagnostic() },
        invalidation_triggered: false,
        telemetry_status: "ONLINE",
        global_rank: 1,
        apex_score: 0.98,
        regime_age: 2,
      },
    ],
  };
  const client = {
    from(table) {
      const state = { table, filters: [] };
      const query = {
        select() {
          return query;
        },
        in(key, values) {
          state.filters.push((row) => values.includes(row[key]));
          return query;
        },
        eq(key, value) {
          state.filters.push((row) => row[key] === value);
          return query;
        },
        order() {
          return query;
        },
        limit() {
          return query;
        },
        // biome-ignore lint/suspicious/noThenProperty: Supabase query builders implement PromiseLike.
        then(resolve, reject) {
          requests.push({ table });
          const data = (tables[table] ?? []).filter((row) =>
            state.filters.every((filter) => filter(row)),
          );
          return Promise.resolve({ data, error: null }).then(resolve, reject);
        },
      };
      return query;
    },
  };
  const queryLoader = makeLoader({
    "@tanstack/react-query": {
      useQuery: (options) =>
        options.queryKey[0] === "universe"
          ? { data: ["EURUSD"], isSuccess: true }
          : options,
    },
    "./supabase/client": { createClient: () => client },
  });
  const queries = queryLoader(
    path.resolve("src/lib/queries.ts").replaceAll("\\", "/"),
  );
  const snapshotQuery = queries.useLatestDeskOpenCardsSnapshot();
  const snapshot = await snapshotQuery.queryFn();
  assert.equal(snapshot.cards[0].pain_index, null);
  assert.equal(snapshot.cards[0].global_rank, null);
  assert.equal(snapshot.cards[0].apex_score, null);
  assert.deepEqual(snapshot.rankJumpByPair, {});
  assert.deepEqual(
    requests.map(({ table }) => table),
    ["desk_open_cards", "desk_open_cards"],
  );
});
