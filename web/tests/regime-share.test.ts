import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's type-stripping runner requires the explicit .ts extension.
import { formatRegimeShareNote } from "../src/lib/regime-share.ts";

const canonical = "https://fxregimelab.com/terminal/fx-regime/eurusd";

test("formats only supplied published card values and the canonical link", () => {
  const text = formatRegimeShareNote({
    pair: "EUR/USD",
    regime: "STRONG_USD_STRENGTH",
    url: canonical,
    spot: 1.1234,
    confidencePercent: 67,
    dominantSignal: "rate",
    dominantScore: 0.812,
  });

  assert.match(text, /Pair: EUR\/USD/u);
  assert.match(text, /Regime: STRONG USD STRENGTH/u);
  assert.match(text, /Spot: 1\.12/u);
  assert.match(text, /Confidence: 67%/u);
  assert.match(text, /Dominant input: RATE \(0\.812\)/u);
  assert.match(text, new RegExp(`${canonical}$`, "u"));
  assert.doesNotMatch(text, /<[^>]+>/u);
});

test("does not invent numeric observations when optional values are absent", () => {
  const text = formatRegimeShareNote({
    pair: "EURUSD",
    regime: "NEUTRAL",
    url: canonical,
  });

  assert.doesNotMatch(text, /Spot:|Confidence:|Dominant input:/u);
  assert.doesNotMatch(text, /\d/u);
});

test("rejects bad pairs, protocols, arrays, HTML, and unsupported fields", () => {
  assert.throws(
    () =>
      formatRegimeShareNote({
        pair: "GBPUSD",
        regime: "NEUTRAL",
        url: canonical,
      }),
    /pair is not supported/u,
  );
  assert.throws(
    () =>
      formatRegimeShareNote({
        pair: "EURUSD",
        regime: "NEUTRAL",
        url: "javascript:alert(1)",
      }),
    /canonical public pair page/u,
  );
  assert.throws(() => formatRegimeShareNote([]), /plain object/u);
  assert.throws(
    () =>
      formatRegimeShareNote({
        pair: "EURUSD",
        regime: "<b>NEUTRAL</b>",
        url: canonical,
      }),
    /unsupported text/u,
  );
  assert.throws(
    () =>
      formatRegimeShareNote({
        pair: "EURUSD",
        regime: "NEUTRAL",
        url: canonical,
        prose: "invent a story",
      }),
    /Unsupported share field/u,
  );
});

test("rejects incomplete or invalid numeric observations", () => {
  assert.throws(
    () =>
      formatRegimeShareNote({
        pair: "EURUSD",
        regime: "NEUTRAL",
        url: canonical,
        confidencePercent: 101,
      }),
    /confidencePercent/u,
  );
  assert.throws(
    () =>
      formatRegimeShareNote({
        pair: "EURUSD",
        regime: "NEUTRAL",
        url: canonical,
        dominantSignal: "rate",
      }),
    /must be supplied together/u,
  );
});
