import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's type-stripping runner requires the explicit .ts extension.
import handler from "../src/pages/api/linkedin-alpha-hook.ts";

type MockResponse = {
  headers: Record<string, string>;
  statusCode: number | null;
  body: unknown;
  setHeader(name: string, value: string): MockResponse;
  status(code: number): MockResponse;
  json(body: unknown): MockResponse;
};

function response(): MockResponse {
  return {
    headers: {},
    statusCode: null,
    body: null,
    setHeader(name, value) {
      this.headers[name] = value;
      return this;
    },
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(body) {
      this.body = body;
      return this;
    },
  };
}

test("POST is permanently retired and cannot spend through fetch", () => {
  const originalFetch = globalThis.fetch;
  const originalKey = process.env.OPENROUTER_API_KEY;
  let fetchCalls = 0;
  globalThis.fetch = (() => {
    fetchCalls += 1;
    throw new Error("fetch must not be called");
  }) as typeof fetch;
  process.env.OPENROUTER_API_KEY = "present-but-must-not-be-read";

  try {
    const res = response();
    handler(
      { method: "POST", body: { cardData: { pair: "EURUSD" } } } as never,
      res as never,
    );

    assert.equal(res.statusCode, 410);
    assert.deepEqual(res.body, {
      error: "This server-generated sharing route has been retired.",
    });
    assert.equal(res.headers["Cache-Control"], "no-store, max-age=0");
    assert.equal(fetchCalls, 0);
  } finally {
    globalThis.fetch = originalFetch;
    if (originalKey === undefined) {
      Reflect.deleteProperty(process.env, "OPENROUTER_API_KEY");
    } else process.env.OPENROUTER_API_KEY = originalKey;
  }
});

test("GET returns 405 with the retired route policy headers", () => {
  const res = response();
  handler({ method: "GET" } as never, res as never);

  assert.equal(res.statusCode, 405);
  assert.deepEqual(res.body, { error: "Method not allowed" });
  assert.equal(res.headers.Allow, "POST");
  assert.equal(res.headers["Cache-Control"], "no-store, max-age=0");
});
