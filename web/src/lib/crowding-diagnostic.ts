export const CROWDING_DIAGNOSTIC_VERSION = "crowding-description-v1";

const PAIRS = ["EURUSD", "USDJPY", "USDINR"] as const;
const DIRECTIONS = ["BULLISH", "BEARISH", "NEUTRAL"] as const;
const ALIGNMENTS = [
  "ALIGNED",
  "OPPOSED",
  "ABSTAINED",
  "FLAT_REPORTED_NET",
  "UNAVAILABLE",
] as const;
const STATUSES = ["PROVISIONAL", "UNAVAILABLE"] as const;

type CrowdingStatus = (typeof STATUSES)[number];
type Alignment = (typeof ALIGNMENTS)[number];

export type CrowdingDiagnostic = {
  version: typeof CROWDING_DIAGNOSTIC_VERSION;
  pair: (typeof PAIRS)[number];
  call_id: number | null;
  as_of_date: string;
  predicted_direction: (typeof DIRECTIONS)[number] | null;
  cot: {
    status: CrowdingStatus;
    report_date: string | null;
    report_age_days: number | null;
    net_long: number | null;
    asset_mgr_net: number | null;
    lev_money_net: number | null;
    pair_direction: -1 | 0 | 1 | null;
    alignment: Alignment;
    series_definition: "UNKNOWN";
    release_status: "UNVERIFIED";
    rank_percentile: null;
    reasons: string[];
  };
  price: {
    status: CrowdingStatus;
    latest_date: string | null;
    spot: number | null;
    mean_close_40: number | null;
    observation_count: number;
    relative_to_mean_pct: number | null;
    reasons: string[];
  };
  participant_loss_estimate: null;
  squeeze_probability: null;
  point_in_time_qualified: false;
};

export type CrowdingDiagnosticRead =
  | { kind: "valid"; diagnostic: CrowdingDiagnostic }
  | { kind: "missing" | "legacy" | "malformed" };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(
  value: Record<string, unknown>,
  keys: readonly string[],
): boolean {
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  return (
    actual.length === expected.length &&
    actual.every((key, index) => key === expected[index])
  );
}

function isIsoDate(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/u.test(value)) {
    return false;
  }
  const parsed = new Date(`${value}T00:00:00.000Z`);
  return (
    !Number.isNaN(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === value
  );
}

function isFiniteNumberOrNull(value: unknown): value is number | null {
  return (
    value === null || (typeof value === "number" && Number.isFinite(value))
  );
}

function isSafeIntegerOrNull(value: unknown): value is number | null {
  return (
    value === null || (typeof value === "number" && Number.isSafeInteger(value))
  );
}

function isReasons(value: unknown): value is string[] {
  return (
    Array.isArray(value) &&
    value.every((reason) => typeof reason === "string" && reason.length > 0)
  );
}

function daysBetween(earlier: string, later: string): number {
  return (
    (Date.parse(`${later}T00:00:00.000Z`) -
      Date.parse(`${earlier}T00:00:00.000Z`)) /
    86_400_000
  );
}

function expectedAlignment(
  predictedDirection: CrowdingDiagnostic["predicted_direction"],
  pairDirection: -1 | 0 | 1,
): Alignment {
  if (predictedDirection === null) return "UNAVAILABLE";
  if (predictedDirection === "NEUTRAL") return "ABSTAINED";
  if (pairDirection === 0) return "FLAT_REPORTED_NET";
  const callDirection = predictedDirection === "BULLISH" ? 1 : -1;
  return callDirection === pairDirection ? "ALIGNED" : "OPPOSED";
}

function isCot(
  value: unknown,
  pair: CrowdingDiagnostic["pair"],
  asOfDate: string,
  predictedDirection: CrowdingDiagnostic["predicted_direction"],
): value is CrowdingDiagnostic["cot"] {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, [
      "status",
      "report_date",
      "report_age_days",
      "net_long",
      "asset_mgr_net",
      "lev_money_net",
      "pair_direction",
      "alignment",
      "series_definition",
      "release_status",
      "rank_percentile",
      "reasons",
    ])
  ) {
    return false;
  }
  if (
    !STATUSES.includes(value.status as CrowdingStatus) ||
    !(value.report_date === null || isIsoDate(value.report_date)) ||
    !isSafeIntegerOrNull(value.report_age_days) ||
    (typeof value.report_age_days === "number" && value.report_age_days < 0) ||
    !isSafeIntegerOrNull(value.net_long) ||
    !isSafeIntegerOrNull(value.asset_mgr_net) ||
    !isSafeIntegerOrNull(value.lev_money_net) ||
    !([null, -1, 0, 1] as unknown[]).includes(value.pair_direction) ||
    !ALIGNMENTS.includes(value.alignment as Alignment) ||
    value.series_definition !== "UNKNOWN" ||
    value.release_status !== "UNVERIFIED" ||
    value.rank_percentile !== null ||
    !isReasons(value.reasons)
  ) {
    return false;
  }
  if (value.status === "PROVISIONAL") {
    if (
      pair === "USDINR" ||
      value.report_date === null ||
      value.report_date > asOfDate ||
      value.report_age_days === null ||
      value.report_age_days !== daysBetween(value.report_date, asOfDate) ||
      value.net_long === null ||
      value.pair_direction === null
    ) {
      return false;
    }
    const sourceDirection: -1 | 0 | 1 =
      value.net_long === 0 ? 0 : value.net_long > 0 ? 1 : -1;
    const pairDirection = (
      pair === "EURUSD" ? sourceDirection : -sourceDirection
    ) as -1 | 0 | 1;
    return (
      value.pair_direction === pairDirection &&
      value.alignment === expectedAlignment(predictedDirection, pairDirection)
    );
  }
  if (
    value.net_long !== null ||
    value.asset_mgr_net !== null ||
    value.lev_money_net !== null ||
    value.pair_direction !== null ||
    value.alignment !== "UNAVAILABLE"
  ) {
    return false;
  }
  if (value.report_date === null) return value.report_age_days === null;
  return (
    value.report_date <= asOfDate &&
    value.report_age_days === daysBetween(value.report_date, asOfDate)
  );
}

function isPrice(
  value: unknown,
  asOfDate: string,
): value is CrowdingDiagnostic["price"] {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, [
      "status",
      "latest_date",
      "spot",
      "mean_close_40",
      "observation_count",
      "relative_to_mean_pct",
      "reasons",
    ])
  ) {
    return false;
  }
  if (
    !STATUSES.includes(value.status as CrowdingStatus) ||
    !(value.latest_date === null || isIsoDate(value.latest_date)) ||
    !isFiniteNumberOrNull(value.spot) ||
    !isFiniteNumberOrNull(value.mean_close_40) ||
    !isFiniteNumberOrNull(value.relative_to_mean_pct) ||
    typeof value.observation_count !== "number" ||
    !Number.isSafeInteger(value.observation_count) ||
    value.observation_count < 0 ||
    value.observation_count > 40 ||
    !isReasons(value.reasons)
  ) {
    return false;
  }
  if (value.status === "PROVISIONAL") {
    if (
      value.latest_date === null ||
      value.latest_date > asOfDate ||
      value.spot === null ||
      value.spot <= 0 ||
      value.observation_count < 1
    ) {
      return false;
    }
    if (value.observation_count < 40) {
      return (
        value.mean_close_40 === null &&
        value.relative_to_mean_pct === null &&
        value.reasons.includes("INSUFFICIENT_PRICE_OBSERVATIONS")
      );
    }
    if (
      value.mean_close_40 === null &&
      value.relative_to_mean_pct === null &&
      value.reasons.includes("INVALID_PRICE_ARITHMETIC")
    ) {
      return true;
    }
    if (
      value.mean_close_40 === null ||
      value.mean_close_40 <= 0 ||
      value.relative_to_mean_pct === null
    ) {
      return false;
    }
    const expected = 100 * (value.spot / value.mean_close_40 - 1);
    if (!Number.isFinite(expected)) return false;
    const tolerance = Math.max(1e-9, Math.abs(expected) * 1e-9);
    return Math.abs(value.relative_to_mean_pct - expected) <= tolerance;
  }
  if (value.reasons.includes("INVALID_PRICE_ARITHMETIC")) {
    return (
      value.latest_date !== null &&
      value.latest_date <= asOfDate &&
      value.spot !== null &&
      value.spot > 0 &&
      value.observation_count === 40 &&
      value.mean_close_40 === null &&
      value.relative_to_mean_pct === null
    );
  }
  return (
    value.latest_date === null &&
    value.spot === null &&
    value.mean_close_40 === null &&
    value.observation_count === 0 &&
    value.relative_to_mean_pct === null
  );
}

export function readCrowdingDiagnostic(
  value: unknown,
  expectedPair?: string | null,
): CrowdingDiagnosticRead {
  if (value === null || value === undefined) return { kind: "missing" };
  if (!isRecord(value)) return { kind: "malformed" };
  if (value.version !== CROWDING_DIAGNOSTIC_VERSION) {
    return { kind: "legacy" };
  }
  const pair = value.pair as CrowdingDiagnostic["pair"];
  const asOfDate = value.as_of_date;
  const predictedDirection =
    value.predicted_direction as CrowdingDiagnostic["predicted_direction"];
  const normalizedExpectedPair = expectedPair
    ? expectedPair.toUpperCase().replace(/[\s/]/gu, "")
    : null;
  if (
    !hasExactKeys(value, [
      "version",
      "pair",
      "call_id",
      "as_of_date",
      "predicted_direction",
      "cot",
      "price",
      "participant_loss_estimate",
      "squeeze_probability",
      "point_in_time_qualified",
    ]) ||
    !PAIRS.includes(value.pair as CrowdingDiagnostic["pair"]) ||
    !(
      value.call_id === null ||
      (Number.isSafeInteger(value.call_id) && Number(value.call_id) > 0)
    ) ||
    !isIsoDate(asOfDate) ||
    !(
      value.predicted_direction === null ||
      DIRECTIONS.includes(
        value.predicted_direction as NonNullable<
          CrowdingDiagnostic["predicted_direction"]
        >,
      )
    ) ||
    (normalizedExpectedPair !== null && normalizedExpectedPair !== pair) ||
    !isCot(value.cot, pair, asOfDate, predictedDirection) ||
    !isPrice(value.price, asOfDate) ||
    value.participant_loss_estimate !== null ||
    value.squeeze_probability !== null ||
    value.point_in_time_qualified !== false
  ) {
    return { kind: "malformed" };
  }
  return { kind: "valid", diagnostic: value as CrowdingDiagnostic };
}

export function formatSignedInteger(value: number): string {
  if (!Number.isSafeInteger(value)) return "unavailable";
  if (value === 0) return "0";
  return `${value > 0 ? "+" : ""}${value.toLocaleString("en-US")}`;
}

export function formatSignedPercent(value: number): string {
  if (!Number.isFinite(value)) return "unavailable";
  if (Object.is(value, -0) || value === 0) return "0.00%";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function formatAlignment(alignment: Alignment): string {
  return {
    ALIGNED: "aligned with call",
    OPPOSED: "opposed to call",
    ABSTAINED: "call abstained",
    FLAT_REPORTED_NET: "reported net is flat",
    UNAVAILABLE: "alignment unavailable",
  }[alignment];
}

export function crowdingUnavailableMessage(
  kind: Exclude<CrowdingDiagnosticRead["kind"], "valid">,
): string {
  return {
    missing: "Crowding descriptions unavailable: no versioned diagnostic.",
    legacy:
      "Crowding descriptions unavailable: legacy estimates are not validated.",
    malformed:
      "Crowding descriptions unavailable: malformed diagnostic payload.",
  }[kind];
}
