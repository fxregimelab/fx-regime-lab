const PAIR_DETAILS = {
  EURUSD: { display: "EUR/USD", slug: "eurusd" },
  USDJPY: { display: "USD/JPY", slug: "usdjpy" },
  USDINR: { display: "USD/INR", slug: "usdinr" },
} as const;

type SupportedPair = keyof typeof PAIR_DETAILS;

export type RegimeShareInput = {
  pair: string;
  regime: string;
  url: string;
  spot?: number | null;
  confidencePercent?: number | null;
  dominantSignal?: string | null;
  dominantScore?: number | null;
};

const ALLOWED_KEYS = new Set<keyof RegimeShareInput>([
  "pair",
  "regime",
  "url",
  "spot",
  "confidencePercent",
  "dominantSignal",
  "dominantScore",
]);

function requirePlainObject(value: unknown): Record<string, unknown> {
  if (
    value === null ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw new TypeError("Share data must be a plain object.");
  }
  return value as Record<string, unknown>;
}

function requireBoundedText(
  value: unknown,
  field: string,
  maxLength: number,
): string {
  if (typeof value !== "string") {
    throw new TypeError(`${field} must be text.`);
  }
  const text = value.trim();
  const hasUnsupportedCharacter = [...text].some((character) => {
    const codePoint = character.codePointAt(0) ?? 0;
    return (
      character === "<" ||
      character === ">" ||
      codePoint < 32 ||
      codePoint === 127
    );
  });
  if (text.length === 0 || text.length > maxLength || hasUnsupportedCharacter) {
    throw new TypeError(`${field} contains unsupported text.`);
  }
  return text;
}

function optionalFiniteNumber(
  value: unknown,
  field: string,
  min: number,
  max: number,
): number | null {
  if (value == null) return null;
  if (
    typeof value !== "number" ||
    !Number.isFinite(value) ||
    value < min ||
    value > max
  ) {
    throw new TypeError(
      `${field} must be a finite number from ${min} to ${max}.`,
    );
  }
  return value;
}

function normalizePair(value: unknown): SupportedPair {
  const normalized = requireBoundedText(value, "pair", 12)
    .toUpperCase()
    .replace(/[\s/]/gu, "");
  if (!(normalized in PAIR_DETAILS)) {
    throw new TypeError("pair is not supported.");
  }
  return normalized as SupportedPair;
}

function requireCanonicalUrl(value: unknown, pair: SupportedPair): string {
  const raw = requireBoundedText(value, "url", 200);
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new TypeError("url must be an absolute URL.");
  }

  const expected = `https://fxregimelab.com/terminal/fx-regime/${PAIR_DETAILS[pair].slug}`;
  if (
    parsed.protocol !== "https:" ||
    parsed.href.replace(/\/$/u, "") !== expected
  ) {
    throw new TypeError("url must be the canonical public pair page.");
  }
  return expected;
}

export function formatRegimeShareNote(input: unknown): string {
  const data = requirePlainObject(input);
  for (const key of Object.keys(data)) {
    if (!ALLOWED_KEYS.has(key as keyof RegimeShareInput)) {
      throw new TypeError(`Unsupported share field: ${key}.`);
    }
  }

  const pair = normalizePair(data.pair);
  const regime = requireBoundedText(data.regime, "regime", 80).replace(
    /_/gu,
    " ",
  );
  const url = requireCanonicalUrl(data.url, pair);
  const spot = optionalFiniteNumber(data.spot, "spot", 0.000001, 1_000_000);
  const confidencePercent = optionalFiniteNumber(
    data.confidencePercent,
    "confidencePercent",
    0,
    100,
  );
  const dominantSignal =
    data.dominantSignal == null
      ? null
      : requireBoundedText(data.dominantSignal, "dominantSignal", 40);
  const dominantScore = optionalFiniteNumber(
    data.dominantScore,
    "dominantScore",
    0,
    1_000_000,
  );

  if ((dominantSignal === null) !== (dominantScore === null)) {
    throw new TypeError(
      "dominantSignal and dominantScore must be supplied together.",
    );
  }

  const observed = [`Pair: ${PAIR_DETAILS[pair].display}`, `Regime: ${regime}`];
  if (spot !== null) observed.push(`Spot: ${spot.toFixed(2)}`);
  if (confidencePercent !== null) {
    if (!Number.isInteger(confidencePercent)) {
      throw new TypeError(
        "confidencePercent must match the displayed integer.",
      );
    }
    observed.push(`Confidence: ${confidencePercent}%`);
  }
  if (dominantSignal !== null && dominantScore !== null) {
    observed.push(
      `Dominant input: ${dominantSignal.toUpperCase()} (${dominantScore.toFixed(3)})`,
    );
  }

  return [
    "[REGIME NOTE]",
    "FX Regime Lab published the following rules-based classification.",
    "",
    "[OBSERVED CARD DATA]",
    ...observed,
    "",
    "[RESEARCH CONTEXT]",
    "Public macro research for methodology and track-record review. Not investment advice.",
    "",
    "[LINK]",
    url,
  ].join("\n");
}
