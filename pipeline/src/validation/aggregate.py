"""Round 3 Phase 2 — Aggregate validation statistics.

Computes per-pair and overall metrics from the published-call population view:
- Brier score (mean, skill vs random)
- Win rate (directional accuracy)
- Descriptive signed payoff per call from underlying log-return bps
- Calibration buckets

Derived snapshots are upserted within an explicit source/model/scoring/population
version and window. Original calls and evaluations remain immutable.

The legacy ``sharpe_like`` and ``max_drawdown_bps`` dataclass fields are retained
for in-process compatibility but are always unavailable and are not persisted.
Overlapping forecast calls do not define portfolio exposures or an equity curve,
so those statistics would overstate what the validation ledger can support.

Rows without a parseable call date are legacy observations. Their stored
outcome fields cannot independently prove publication timing, horizon maturity,
or as-of eligibility, so they remain visible in the raw call count but are
excluded from scored cohorts.
"""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from scipy.stats import beta as beta_dist

from src.db import writer
from src.validation.calendar import add_trading_days

logger = logging.getLogger(__name__)

_RANDOM_BRIER_BASELINE = 0.25


@dataclass(frozen=True, slots=True)
class HorizonStats:
    """Statistics for a single horizon (T+5 or T+20)."""

    horizon: str
    total_calls: int
    directional_calls: int
    wins: int
    win_rate: float | None
    mean_brier: float | None
    brier_skill: float | None
    mean_log_return_bps: float | None
    return_std_bps: float | None
    sharpe_like: float | None
    max_drawdown_bps: float | None
    calibration_json: str
    rolling_90d_accuracy: float | None
    win_rate_ci_lower: float | None
    win_rate_ci_upper: float | None
    net_win_rate: float | None
    net_directional_calls: int
    net_win_rate_ci_lower: float | None
    net_win_rate_ci_upper: float | None
    cost_bps: float | None
    mature_calls: int = 0
    pending_calls: int = 0
    abstention_calls: int = 0
    unknown_direction_calls: int = 0
    missing_outcome_calls: int = 0
    probability_score_calls: int = 0
    calibration_calls: int = 0
    evaluation_calls: int = 0
    missing_evaluation_calls: int = 0


@dataclass(frozen=True, slots=True)
class AggregateStats:
    """Full aggregate payload for one pair (or ``ALL`` for overall)."""

    pair: str
    as_of_date: date
    t5: HorizonStats
    t20: HorizonStats
    data_source: str = "unknown"
    strategy_version: str = "unknown"
    model_version: str = "unknown"
    evaluation_version: str = "legacy-unversioned"
    window_days: int = 0
    population_version: str = "published-calls-v1"


def _mean(xs: list[float]) -> float | None:
    if not xs:
        return None
    return math.fsum(xs) / len(xs)


def _std(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    m = math.fsum(xs) / len(xs)
    var = math.fsum((x - m) ** 2 for x in xs) / len(xs)
    return float(math.sqrt(var))


def _finite_float(
    raw: Any,
    *,
    lower: float | None = None,
    upper: float | None = None,
) -> float | None:
    """Return a bounded finite float, rejecting booleans and invalid values."""
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    if lower is not None and value < lower:
        return None
    if upper is not None and value > upper:
        return None
    return value


def _parse_call_date(row: dict[str, Any]) -> date | None:
    raw = row.get("date") or row.get("call_date")
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if raw:
        try:
            return date.fromisoformat(str(raw)[:10])
        except (TypeError, ValueError):
            return None
    return None


def _horizon_trading_days(horizon: str) -> int:
    try:
        days = int(horizon.strip().upper().removeprefix("T+"))
    except ValueError as exc:
        raise ValueError(f"Unsupported validation horizon: {horizon!r}") from exc
    if days not in {5, 20}:
        raise ValueError(f"Unsupported validation horizon: {horizon!r}")
    return days


def _is_mature_as_of(row: dict[str, Any], horizon_days: int, as_of_date: date) -> bool:
    """Fence known call dates to the requested horizon and as-of date."""
    call_date = _parse_call_date(row)
    if call_date is None:
        return False
    return call_date <= as_of_date and add_trading_days(call_date, horizon_days) <= as_of_date


def _metadata_value(row: dict[str, Any], key: str, missing: str = "unknown") -> str:
    """Normalize missing cohort metadata without assigning a known provenance."""
    value = row.get(key)
    if value is None:
        return missing
    normalized = str(value).strip()
    return normalized or missing


def _cohort_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        _metadata_value(row, "data_source"),
        _metadata_value(row, "strategy_version"),
        _metadata_value(row, "model_version"),
        _metadata_value(row, "evaluation_version", "legacy-unversioned"),
    )


def _inclusive_cutoff(as_of_date: date, window_days: int) -> date:
    return as_of_date - timedelta(days=window_days - 1)


def _rows_in_window(
    rows: list[dict[str, Any]], as_of_date: date, window_days: int
) -> list[dict[str, Any]]:
    """Apply a calendar-day window anchored to the inclusive as-of date."""
    if window_days == 0:
        return rows
    cutoff = _inclusive_cutoff(as_of_date, window_days)
    return [
        row
        for row in rows
        if (call_date := _parse_call_date(row)) is not None
        and cutoff <= call_date <= as_of_date
    ]


def _calibration_buckets(
    confidences: list[float],
    corrects: list[bool],
    n_buckets: int = 5,
) -> dict[str, Any]:
    """Bucket predictions by confidence decile and report observed accuracy."""
    if not confidences or len(confidences) != len(corrects):
        return {}

    paired: list[tuple[float, bool]] = []
    for confidence, correct in zip(confidences, corrects):
        probability = _finite_float(confidence, lower=0.0, upper=1.0)
        if probability is None or not isinstance(correct, bool):
            continue
        paired.append((probability, correct))
    if not paired:
        return {}

    pairs = sorted(paired, key=lambda x: x[0])
    bucket_size = max(1, len(pairs) // n_buckets)
    buckets: list[dict[str, Any]] = []
    for i in range(0, len(pairs), bucket_size):
        chunk = pairs[i : i + bucket_size]
        avg_conf = _mean([c for c, _ in chunk])
        obs_acc = sum(1 for _, y in chunk if y) / len(chunk) if chunk else None
        buckets.append(
            {
                "bucket_index": i // bucket_size,
                "avg_confidence": round(avg_conf, 4) if avg_conf is not None else None,
                "observed_accuracy": round(obs_acc, 4) if obs_acc is not None else None,
                "n": len(chunk),
            }
        )
    return {"buckets": buckets}


def _clopper_pearson_ci(
    wins: int, n: int, alpha: float = 0.05
) -> tuple[float | None, float | None]:
    """Exact confidence interval for binomial proportion."""
    if n == 0:
        return None, None
    lower = float(beta_dist.ppf(alpha / 2, wins, n - wins + 1)) if wins > 0 else 0.0
    upper = float(beta_dist.ppf(1 - alpha / 2, wins + 1, n - wins)) if wins < n else 1.0
    return (lower, upper)


def _compute_horizon(
    rows: list[dict[str, Any]],
    horizon: str,
    brier_key: str,
    correct_key: str,
    return_key: str,
    as_of_date: date,
) -> HorizonStats:
    horizon_days = _horizon_trading_days(horizon)
    as_of_rows = [
        row
        for row in rows
        if (call_date := _parse_call_date(row)) is None or call_date <= as_of_date
    ]
    total = len(as_of_rows)
    evaluation_calls = sum(row.get("evaluation_present") is True for row in as_of_rows)

    mature_rows = [
        row
        for row in as_of_rows
        if _is_mature_as_of(row, horizon_days, as_of_date)
    ]
    mature_calls = len(mature_rows)
    pending_calls = total - mature_calls
    abstention_calls = sum(
        1
        for row in mature_rows
        if str(row.get("predicted_direction") or "").strip().upper() == "NEUTRAL"
    )
    unknown_direction_calls = sum(
        1
        for row in mature_rows
        if str(row.get("predicted_direction") or "").strip().upper()
        not in {"BULLISH", "BEARISH", "NEUTRAL"}
    )

    directional: list[dict[str, Any]] = []
    mature_directional_calls = 0
    for row in mature_rows:
        direction = str(row.get("predicted_direction") or "").strip().upper()
        correct = row.get(correct_key)
        observed_return = _finite_float(row.get(return_key))
        if direction in {"BULLISH", "BEARISH"}:
            mature_directional_calls += 1
        if (
            direction in {"BULLISH", "BEARISH"}
            and isinstance(correct, bool)
            and observed_return is not None
        ):
            directional.append(row)

    directional_calls = len(directional)
    missing_outcome_calls = mature_directional_calls - directional_calls
    wins = sum(1 for r in directional if r.get(correct_key) is True)
    win_rate = wins / directional_calls if directional_calls > 0 else None

    # Gross CI
    win_rate_ci_lower, win_rate_ci_upper = _clopper_pearson_ci(wins, directional_calls)

    # Net wins
    net_correct_key = correct_key.replace("correct", "correct_net")
    net_return_key = correct_key.replace("correct", "log_return_net_bps")
    cost_key = correct_key.replace("correct", "cost_bps")
    net_directional: list[tuple[dict[str, Any], float]] = []
    for row in directional:
        net_return = _finite_float(row.get(net_return_key))
        cost = _finite_float(row.get(cost_key), lower=0.0)
        if (
            isinstance(row.get(net_correct_key), bool)
            and net_return is not None
            and cost is not None
        ):
            net_directional.append((row, cost))
    net_wins = sum(1 for row, _ in net_directional if row[net_correct_key] is True)
    net_n = len(net_directional)
    net_win_rate = net_wins / net_n if net_n > 0 else None
    net_ci_lower, net_ci_upper = _clopper_pearson_ci(net_wins, net_n)

    # Cost is defined on the same complete net-payoff cohort as net accuracy.
    costs = [cost for _, cost in net_directional]
    avg_cost = _mean(costs) if costs else None

    briers = [
        score
        for r in directional
        if (score := _finite_float(r.get(brier_key), lower=0.0, upper=1.0))
        is not None
    ]
    mean_brier = _mean(briers) if briers else None
    probability_score_calls = len(briers)
    brier_skill = (
        (_RANDOM_BRIER_BASELINE - mean_brier) / _RANDOM_BRIER_BASELINE
        if mean_brier is not None
        else None
    )

    signed_payoffs = [
        float(r[return_key])
        * (1.0 if str(r["predicted_direction"]).strip().upper() == "BULLISH" else -1.0)
        for r in directional
    ]
    mean_ret = _mean(signed_payoffs)
    std_ret = _std(signed_payoffs)

    calibration_pairs = [
        (probability, r[correct_key])
        for r in directional
        if (
            probability := _finite_float(r.get("confidence"), lower=0.0, upper=1.0)
        )
        is not None
    ]
    confidences = [probability for probability, _ in calibration_pairs]
    corrects = [correct for _, correct in calibration_pairs]
    calib = _calibration_buckets(confidences, corrects)
    calibration_calls = len(calibration_pairs)

    # v1.0: rolling 90-day accuracy (last 90 calendar days of directional calls)
    cutoff_90d = _inclusive_cutoff(as_of_date, 90)

    recent_directional = [
        r
        for r in directional
        if (call_date := _parse_call_date(r)) is not None
        and cutoff_90d <= call_date <= as_of_date
    ]
    recent_wins = sum(1 for r in recent_directional if r.get(correct_key) is True)
    rolling_90d_acc = (
        recent_wins / len(recent_directional)
        if recent_directional
        else None
    )

    return HorizonStats(
        horizon=horizon,
        total_calls=total,
        directional_calls=directional_calls,
        wins=wins,
        win_rate=round(win_rate, 6) if win_rate is not None else None,
        win_rate_ci_lower=round(win_rate_ci_lower, 6) if win_rate_ci_lower is not None else None,
        win_rate_ci_upper=round(win_rate_ci_upper, 6) if win_rate_ci_upper is not None else None,
        mean_brier=round(mean_brier, 6) if mean_brier is not None else None,
        brier_skill=round(brier_skill, 6) if brier_skill is not None else None,
        mean_log_return_bps=round(mean_ret, 6) if mean_ret is not None else None,
        return_std_bps=round(std_ret, 6) if std_ret is not None else None,
        sharpe_like=None,
        max_drawdown_bps=None,
        calibration_json=json.dumps(calib),
        rolling_90d_accuracy=round(rolling_90d_acc, 6) if rolling_90d_acc is not None else None,
        net_win_rate=round(net_win_rate, 6) if net_win_rate is not None else None,
        net_directional_calls=net_n,
        net_win_rate_ci_lower=round(net_ci_lower, 6) if net_ci_lower is not None else None,
        net_win_rate_ci_upper=round(net_ci_upper, 6) if net_ci_upper is not None else None,
        cost_bps=round(avg_cost, 6) if avg_cost is not None else None,
        mature_calls=mature_calls,
        pending_calls=pending_calls,
        abstention_calls=abstention_calls,
        unknown_direction_calls=unknown_direction_calls,
        missing_outcome_calls=missing_outcome_calls,
        probability_score_calls=probability_score_calls,
        calibration_calls=calibration_calls,
        evaluation_calls=evaluation_calls,
        missing_evaluation_calls=total - evaluation_calls,
    )


def compute_aggregate_stats(
    pair_filter: str | None = None,
    as_of_date: date | None = None,
    lookback_days: int | None = None,
) -> list[AggregateStats]:
    """Compute stats for ``pair_filter`` (or all pairs) at the requested as-of.

    If ``lookback_days`` is set, only consider calls within that window;
    otherwise use the full history.
    """
    if as_of_date is None:
        as_of_date = date.today()

    window_days = lookback_days if lookback_days is not None and lookback_days > 0 else 0
    rows = writer.get_validation_log_for_stats(pair_filter, lookback_days, as_of_date)
    rows = _rows_in_window(rows, as_of_date, window_days)
    if not rows:
        logger.warning("No validation rows found for stats computation")
        return []

    results: list[AggregateStats] = []
    by_cohort: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_cohort[_cohort_key(row)].append(row)

    for cohort, cohort_rows in sorted(by_cohort.items()):
        data_source, strategy_version, model_version, evaluation_version = cohort
        by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in cohort_rows:
            pair = str(row.get("pair") or "UNKNOWN")
            by_pair[pair].append(row)

        pairs_to_process = [pair_filter] if pair_filter else sorted(by_pair)

        def build_stats(pair: str, pair_rows: list[dict[str, Any]]) -> AggregateStats:
            t5 = _compute_horizon(
                pair_rows,
                "T+5",
                "brier_score_t5",
                "correct_t5",
                "log_return_t5_bps",
                as_of_date,
            )
            t20 = _compute_horizon(
                pair_rows,
                "T+20",
                "brier_score_t20",
                "correct_t20",
                "log_return_t20_bps",
                as_of_date,
            )
            return AggregateStats(
                pair=pair,
                as_of_date=as_of_date,
                t5=t5,
                t20=t20,
                data_source=data_source,
                strategy_version=strategy_version,
                model_version=model_version,
                evaluation_version=evaluation_version,
                window_days=window_days,
            )

        for pair in pairs_to_process:
            if pair is None:
                continue
            pair_rows = by_pair.get(pair, [])
            if pair_rows:
                results.append(build_stats(pair, pair_rows))

        if not pair_filter and len(by_pair) > 1:
            results.append(build_stats("ALL", cohort_rows))

    return results


def _stats_to_payload(stats: AggregateStats) -> dict[str, Any]:
    """Serialize ``AggregateStats`` to a Supabase row dict."""
    base: dict[str, Any] = {
        "as_of_date": stats.as_of_date.isoformat(),
        "pair": stats.pair,
        "data_source": stats.data_source,
        "strategy_version": stats.strategy_version,
        "model_version": stats.model_version,
        "evaluation_version": stats.evaluation_version,
        "window_days": stats.window_days,
        "population_version": stats.population_version,
        "computed_at": date.today().isoformat(),
    }
    for horizon in ("t5", "t20"):
        h: HorizonStats = getattr(stats, horizon)
        prefix = f"{horizon}_"
        base[f"{prefix}total_calls"] = h.total_calls
        base[f"{prefix}directional_calls"] = h.directional_calls
        base[f"{prefix}wins"] = h.wins
        base[f"{prefix}win_rate"] = h.win_rate
        base[f"{prefix}mean_brier"] = h.mean_brier
        base[f"{prefix}brier_skill"] = h.brier_skill
        base[f"{prefix}mean_log_return_bps"] = h.mean_log_return_bps
        base[f"{prefix}mean_signed_gross_return_bps"] = h.mean_log_return_bps
        base[f"{prefix}return_std_bps"] = h.return_std_bps
        base[f"{prefix}calibration_json"] = h.calibration_json
        base[f"{prefix}rolling_90d_accuracy"] = h.rolling_90d_accuracy
        base[f"{prefix}win_rate_ci_lower"] = h.win_rate_ci_lower
        base[f"{prefix}win_rate_ci_upper"] = h.win_rate_ci_upper
        base[f"{prefix}net_win_rate"] = h.net_win_rate
        base[f"{prefix}net_directional_calls"] = h.net_directional_calls
        base[f"{prefix}net_win_rate_ci_lower"] = h.net_win_rate_ci_lower
        base[f"{prefix}net_win_rate_ci_upper"] = h.net_win_rate_ci_upper
        base[f"{prefix}cost_bps"] = h.cost_bps
        base[f"{prefix}mature_calls"] = h.mature_calls
        base[f"{prefix}pending_calls"] = h.pending_calls
        base[f"{prefix}abstention_calls"] = h.abstention_calls
        base[f"{prefix}unknown_direction_calls"] = h.unknown_direction_calls
        base[f"{prefix}missing_outcome_calls"] = h.missing_outcome_calls
        base[f"{prefix}probability_score_calls"] = h.probability_score_calls
        base[f"{prefix}calibration_calls"] = h.calibration_calls
        base[f"{prefix}evaluation_calls"] = h.evaluation_calls
        base[f"{prefix}missing_evaluation_calls"] = h.missing_evaluation_calls
    return base


def run_aggregate_stats(
    pair_filter: str | None = None,
    as_of_date: date | None = None,
    lookback_days: int | None = None,
) -> list[AggregateStats]:
    """Compute and persist aggregate stats to ``validation_stats``."""
    stats_list = compute_aggregate_stats(pair_filter, as_of_date, lookback_days)
    for stats in stats_list:
        payload = _stats_to_payload(stats)
        writer.write_validation_stats(payload)
        logger.info(
            "Validation stats persisted: %s T+5 win_rate=%s brier=%s",
            stats.pair,
            stats.t5.win_rate,
            stats.t5.mean_brier,
        )
    return stats_list


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_aggregate_stats()
