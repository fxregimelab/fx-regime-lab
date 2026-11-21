"""Private, price-only daily research. All outcomes are after assumed costs.

This module never places an order and never backfills news or revised macro data
into history. A trade's feature date precedes its entry. Policy selection uses
training only; probabilities use a later calibration cohort and are checked on
an untouched chronological test cohort.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from src.private_desk.universe import PAIRS

UNIVERSE = PAIRS

EMBARGO = 5
MIN_TRAIN = 400
CALIBRATION_BARS = 400
TEST_BARS = 250
METHOD_VERSION = "private-price-v2-direction"


@dataclass(frozen=True)
class Policy:
    name: str
    lookback: int
    contrarian: bool
    minimum_strength: float
    stop_atr: float


POLICIES = (
    Policy("trend5_125", 5, False, 0.65, 1.25),
    Policy("trend5_175", 5, False, 0.65, 1.75),
    Policy("trend20_125", 20, False, 0.80, 1.25),
    Policy("trend20_175", 20, False, 0.80, 1.75),
    Policy("reversion5_125", 5, True, 1.25, 1.25),
    Policy("reversion5_175", 5, True, 1.25, 1.75),
)


@dataclass(frozen=True)
class Costs:
    spread_pips: float = 1.2
    slippage_pips_per_side: float = 0.2
    holding_pips_per_calendar_day: float = 0.15


def _day(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _missing_weekday_between(previous: datetime, following: datetime) -> bool:
    days = (following.date() - previous.date()).days
    if days > 3:
        return True
    return any((previous + timedelta(days=offset)).weekday() < 5 for offset in range(1, days))


def _window_has_gap(
    bars: list[dict[str, Any]], start: int, end: int, *, check_calendar: bool = False
) -> bool:
    """The first bar's marker belongs to the preceding, unused interval."""
    if start < 0 or end >= len(bars) or end < start:
        return True
    for index in range(start + 1, end + 1):
        if bars[index].get("gap_before"):
            return True
        if check_calendar and _missing_weekday_between(
            _day(str(bars[index - 1]["time"])), _day(str(bars[index]["time"]))
        ):
            return True
    return False


def validate_bars(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reject an entire malformed capture rather than silently correcting it."""
    result: list[dict[str, Any]] = []
    previous: datetime | None = None
    for raw in bars:
        stamp = str(raw["time"])
        day = _day(stamp)
        if previous is not None and day <= previous:
            raise ValueError("Bars must have unique, increasing timestamps.")
        prices = {name: float(raw[name]) for name in ("open", "high", "low", "close")}
        if not all(math.isfinite(value) and value > 0 for value in prices.values()):
            raise ValueError("OHLC prices must be finite and positive.")
        if prices["low"] > min(prices["open"], prices["close"]) or prices["high"] < max(
            prices["open"], prices["close"]
        ):
            raise ValueError("OHLC bounds are inconsistent.")
        normalized: dict[str, Any] = {"time": stamp, **prices}
        if "gap_before" in raw:
            if not isinstance(raw["gap_before"], bool):
                raise ValueError("Source gap marker must be boolean.")
            normalized["gap_before"] = raw["gap_before"]
        if previous is not None and _missing_weekday_between(previous, day):
            normalized["gap_before"] = True
        result.append(normalized)
        previous = day
    return result


def _atr(bars: list[dict[str, Any]], index: int, period: int = 14) -> float:
    ranges = [
        max(
            bars[i]["high"] - bars[i]["low"],
            abs(bars[i]["high"] - bars[i - 1]["close"]),
            abs(bars[i]["low"] - bars[i - 1]["close"]),
        )
        for i in range(index - period + 1, index + 1)
    ]
    return float(sum(ranges) / period)


def _signal(bars: list[dict[str, Any]], index: int, policy: Policy) -> tuple[int, float, float]:
    if index < 60:
        return 0, 0.0, 0.0
    if _window_has_gap(bars, index - max(14, policy.lookback), index):
        return 0, 0.0, 0.0
    atr = _atr(bars, index)
    if atr <= 0:
        return 0, 0.0, 0.0
    momentum = (bars[index]["close"] - bars[index - policy.lookback]["close"]) / atr
    strength = abs(momentum) / math.sqrt(policy.lookback)
    if strength < policy.minimum_strength:
        return 0, strength, atr
    direction = 1 if momentum > 0 else -1
    if policy.contrarian:
        direction *= -1
    # Extreme volatility and tiny candle ranges provide unreliable executable levels.
    if atr / bars[index]["close"] > 0.05 or atr / bars[index]["close"] < 0.0001:
        return 0, strength, atr
    return direction, strength, atr


def simulate_trade(
    pair: str,
    bars: list[dict[str, Any]],
    signal_index: int,
    direction: int,
    risk_distance: float,
    horizon: int,
    *,
    costs: Costs = Costs(),
    bar_interval: str = "1d",
    exit_at_open_index: int | None = None,
    extra_exit_slippage_pips: float = 0.0,
) -> dict[str, Any]:
    """Next-open execution with adverse ordering when a daily candle is ambiguous.

    A +1R touch closes half, then moves the remaining stop to entry. The remaining
    half targets +3R. A full winner therefore earns +2R before costs. Opening gaps
    through stops are filled at the opening price, including gaps after breakeven.
    """
    if direction not in (-1, 1) or risk_distance <= 0 or not math.isfinite(risk_distance):
        raise ValueError("Direction and risk distance are invalid.")
    if horizon < 1 or signal_index < 0 or signal_index + horizon >= len(bars):
        raise ValueError("A complete future holding horizon is required.")
    if not all(math.isfinite(value) and value >= 0 for value in asdict(costs).values()):
        raise ValueError("Cost assumptions must be nonnegative.")
    if bar_interval not in ("1d", "1h"):
        raise ValueError("Simulator supports daily or hourly bars.")
    if exit_at_open_index is not None and (
        type(exit_at_open_index) is not int
        or not signal_index + 1 < exit_at_open_index <= signal_index + horizon
    ):
        raise ValueError("A risk exit must follow entry and remain inside its horizon.")
    if (
        isinstance(extra_exit_slippage_pips, bool)
        or not math.isfinite(extra_exit_slippage_pips)
        or extra_exit_slippage_pips < 0
        or (exit_at_open_index is None and extra_exit_slippage_pips != 0)
    ):
        raise ValueError("Extra risk-exit slippage requires a valid requested exit.")
    if _window_has_gap(
        bars, signal_index, signal_index + horizon, check_calendar=bar_interval == "1d"
    ):
        raise ValueError("Holding label crosses a missing or quarantined observation.")
    entry_index = signal_index + 1
    entry = float(bars[entry_index]["open"])
    stop = entry - direction * risk_distance
    tp1 = entry + direction * risk_distance
    tp2 = entry + direction * 3 * risk_distance
    partial = False
    gross_r = 0.0
    ambiguity = 0
    outcome = "TIME_EXIT"
    exit_index = signal_index + horizon
    held_fraction_days = 0.0
    extra_slippage = 0.0
    prior_day = _day(str(bars[signal_index]["time"]))

    for index in range(entry_index, signal_index + horizon + 1):
        bar = bars[index]
        this_day = _day(str(bar["time"]))
        # The first bar incurs one day; later gaps include weekend financing.
        if bar_interval == "1d":
            calendar_days = (
                1.0 if index == entry_index else float(max(1, (this_day - prior_day).days))
            )
        else:
            calendar_days = (
                1 / 24
                if index == entry_index
                else max(1 / 24, (this_day - prior_day).total_seconds() / 86400)
            )
        held_fraction_days += calendar_days * (0.5 if partial else 1.0)
        prior_day = this_day
        open_r = direction * (bar["open"] - entry) / risk_distance
        if index == exit_at_open_index:
            # This counterfactual observes only the open, never today's candle extremes.
            extra_slippage = extra_exit_slippage_pips * (0.5 if partial else 1.0)
            if partial:
                gross_r = 0.5 + 0.5 * open_r
                outcome = "BREAKEVEN_GAP" if open_r <= 0 else "RISK_EXIT_AT_OPEN"
                if open_r >= 3:
                    gross_r, outcome = 2.0, "TARGET3"
            elif open_r <= -1:
                gross_r, outcome = open_r, "STOP_GAP"
            elif open_r >= 3:
                gross_r, outcome = 2.0, "TARGET3"
            elif open_r >= 1:
                partial = True
                gross_r, outcome = 0.5 + 0.5 * open_r, "RISK_EXIT_AT_OPEN"
            else:
                gross_r, outcome = open_r, "RISK_EXIT_AT_OPEN"
            exit_index = index
            break
        favorable = direction * ((bar["high"] if direction > 0 else bar["low"]) - entry)
        adverse = direction * ((bar["low"] if direction > 0 else bar["high"]) - entry)
        high_r, low_r = favorable / risk_distance, adverse / risk_distance
        exit_index = index

        if partial:
            if open_r <= 0:
                gross_r, outcome = 0.5 + 0.5 * open_r, "BREAKEVEN_GAP"
                break
            if open_r >= 3:
                gross_r, outcome = 2.0, "TARGET3"
                break
            if low_r <= 0:
                ambiguity += int(high_r >= 3)
                gross_r, outcome = 0.5, "BREAKEVEN"
                break
            if high_r >= 3:
                gross_r, outcome = 2.0, "TARGET3"
                break
        else:
            if open_r <= -1:
                gross_r, outcome = open_r, "STOP_GAP"
                break
            if open_r >= 1:
                partial = True  # The open is witnessed to precede the candle extremes.
                if open_r >= 3:
                    gross_r, outcome = 2.0, "TARGET3"
                    break
                if low_r <= 0:
                    ambiguity += int(high_r >= 3)
                    gross_r, outcome = 0.5, "BREAKEVEN"
                    break
                if high_r >= 3:
                    gross_r, outcome = 2.0, "TARGET3"
                    break
            elif low_r <= -1:
                ambiguity += int(high_r >= 1)
                gross_r, outcome = -1.0, "STOP"
                break
            elif high_r >= 1:
                partial = True
                if low_r <= 0:
                    ambiguity += 1
                    gross_r, outcome = 0.5, "BREAKEVEN"
                    break
                if high_r >= 3:
                    gross_r, outcome = 2.0, "TARGET3"
                    break
        close_r = direction * (bar["close"] - entry) / risk_distance
        gross_r = 0.5 + 0.5 * close_r if partial else close_r

    pip = 0.01 if pair.endswith("JPY") else 0.0001
    cost_r = (
        pip
        * (
            costs.spread_pips
            + 2 * costs.slippage_pips_per_side
            + costs.holding_pips_per_calendar_day * held_fraction_days
            + extra_slippage
        )
        / risk_distance
    )
    net_r = gross_r - cost_r
    return {
        "pair": pair,
        "signal_time": bars[signal_index]["time"],
        "entry_time": bars[entry_index]["time"],
        "exit_time": bars[exit_index]["time"],
        "signal_index": signal_index,
        "end_index": signal_index + horizon,
        "direction": "BUY" if direction > 0 else "SELL",
        "entry": entry,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "holding_days": horizon,
        "actual_bars_held": exit_index - signal_index,
        "gross_r": float(gross_r),
        "cost_r": float(cost_r),
        "net_r": float(net_r),
        "profitable": net_r > 0,
        "tp1_hit": partial or outcome == "TARGET3",
        "outcome": outcome,
        "ambiguous_bars": ambiguity,
    }


def wilson_interval(successes: int, count: int) -> list[float] | None:
    if count == 0:
        return None
    z = 1.959963984540054
    rate = successes / count
    denom = 1 + z * z / count
    center = (rate + z * z / (2 * count)) / denom
    half = z * math.sqrt(rate * (1 - rate) / count + z * z / (4 * count * count)) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _summary(trades: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(trades)
    if not count:
        return {"trade_count": 0, "net_ev_r": None, "net_win_rate": None, "win_rate_ci95": None}
    returns = [float(t["net_r"]) for t in trades]
    ev = _mean(returns)
    variance = sum((value - ev) ** 2 for value in returns) / max(1, count - 1)
    error = 1.96 * math.sqrt(variance / count)
    wins = sum(value > 0 for value in returns)
    equity, peak, drawdown = 0.0, 0.0, 0.0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    losses = -sum(value for value in returns if value < 0)
    return {
        "trade_count": count,
        "net_ev_r": ev,
        "net_ev_ci95_approx": [ev - error, ev + error],
        "net_win_rate": wins / count,
        "win_rate_ci95": wilson_interval(wins, count),
        "tp1_hit_rate": sum(bool(t["tp1_hit"]) for t in trades) / count,
        "gross_ev_r": _mean([float(t["gross_r"]) for t in trades]),
        "mean_cost_r": _mean([float(t["cost_r"]) for t in trades]),
        "total_net_r": equity,
        "max_drawdown_r": drawdown,
        "profit_factor": sum(value for value in returns if value > 0) / losses if losses else None,
        "ambiguous_trades": sum(t["ambiguous_bars"] > 0 for t in trades),
        "mean_bars_held": _mean([float(t["actual_bars_held"]) for t in trades]),
    }


def _cohort(rows: list[dict[str, Any]], start: int, end: int) -> list[dict[str, Any]]:
    # Fixed horizon cooldown avoids counting overlapping bets as independent trades.
    result: list[dict[str, Any]] = []
    next_entry = start
    for row in rows:
        index = int(row["signal_index"])
        if index >= next_entry and index >= start and int(row["end_index"]) < end:
            result.append(row)
            next_entry = int(row["end_index"]) + 1
    return result


def _selection(
    trial_rows: dict[str, list[dict[str, Any]]],
    start: int,
    end: int,
    minimum_trades: int = 30,
) -> tuple[str | None, list[dict[str, Any]]]:
    scored: list[dict[str, Any]] = []
    for name, rows in trial_rows.items():
        summary = _summary(_cohort(rows, start, end))
        score = (
            summary["net_ev_ci95_approx"][0] if summary["trade_count"] >= minimum_trades else None
        )
        scored.append({"trial": name, "selection_lower_ev_r": score, **summary})
    eligible = [item for item in scored if item["selection_lower_ev_r"] is not None]
    best = max(eligible, key=lambda item: item["selection_lower_ev_r"]) if eligible else None
    return str(best["trial"]) if best else None, scored


def _bucket(strength: float) -> int:
    return 0 if strength < 1.0 else 1 if strength < 1.75 else 2


def _calibrate(
    rows: list[dict[str, Any]], strength: float, direction: str
) -> tuple[float | None, list[dict[str, Any]]]:
    if direction not in ("BUY", "SELL"):
        return None, []
    bucket = _bucket(strength)
    same_direction = [row for row in rows if row["direction"] == direction]
    matching = [row for row in same_direction if _bucket(float(row["strength"])) == bucket]
    if len(matching) < 20 or len(same_direction) < 40:
        return None, matching
    return sum(bool(row["profitable"]) for row in matching) / len(matching), matching


def _direction_base_rate(rows: list[dict[str, Any]], direction: str) -> float | None:
    matching = [row for row in rows if row["direction"] == direction]
    return sum(bool(row["profitable"]) for row in matching) / len(matching) if matching else None


def _calibration_check(rows: list[dict[str, Any]]) -> dict[str, Any]:
    predicted = [row for row in rows if row.get("predicted_probability") is not None]
    if not predicted:
        return {"sample_count": 0, "passes": False, "brier_score": None, "ece": None}
    brier = _mean(
        [(float(row["predicted_probability"]) - float(row["profitable"])) ** 2 for row in predicted]
    )
    reference = _mean(
        [(float(row["training_base_rate"]) - float(row["profitable"])) ** 2 for row in predicted]
    )
    bins: list[dict[str, Any]] = []
    ece = 0.0
    for bucket in range(5):
        subset = [
            row
            for row in predicted
            if min(4, int(float(row["predicted_probability"]) * 5)) == bucket
        ]
        if subset:
            probability = _mean([float(row["predicted_probability"]) for row in subset])
            actual = sum(bool(row["profitable"]) for row in subset) / len(subset)
            ece += len(subset) / len(predicted) * abs(probability - actual)
            bins.append(
                {
                    "predicted": probability,
                    "observed": actual,
                    "sample_count": len(subset),
                    "observed_ci95": wilson_interval(
                        sum(bool(row["profitable"]) for row in subset), len(subset)
                    ),
                }
            )
    return {
        "sample_count": len(predicted),
        "brier_score": brier,
        "baseline_brier_score": reference,
        "ece": ece,
        "bins": bins,
        "passes": len(predicted) >= 100 and brier <= reference and ece <= 0.10,
        "definition": "Net-profitable partial-exit trade after the stated costs.",
    }


def _positive_ev_for_policy(
    comparable_calibration: dict[str, Any],
    selected_policy_heldout: dict[str, Any],
    matured_prediction_count: int,
) -> bool:
    """Other policies' profits cannot qualify the current policy's expected return."""
    return bool(
        comparable_calibration["trade_count"] >= 20
        and comparable_calibration["net_ev_ci95_approx"][0] > 0
        and selected_policy_heldout["trade_count"] >= 100
        and matured_prediction_count >= 100
        and selected_policy_heldout["net_ev_ci95_approx"][0] > 0
    )


def _empty(pair: str, reason: str, count: int = 0) -> dict[str, Any]:
    return {
        "pair": pair,
        "data_coverage": {"bar_count": count, "status": "UNAVAILABLE"},
        "backtest": {
            "method_version": METHOD_VERSION,
            "status": "UNAVAILABLE",
            "trade_count": 0,
            "trials": [],
            "folds": [],
            "trades": [],
            "summary": _summary([]),
            "calibration": {"passes": False},
        },
        "candidate": {
            "status": "ABSTAIN",
            "direction": None,
            "entry": None,
            "stop": None,
            "tp1": None,
            "tp2": None,
            "holding_days": None,
            "probability": None,
            "expected_r": None,
            "reasons": [reason],
            "as_of": None,
        },
        "chart": {"recent_ohlc": [], "equity": []},
        "session": {"status": "UNAVAILABLE", "reason": "Intraday session evidence is absent."},
    }


def analyze_pair(
    pair: str, bars: list[dict[str, Any]], *, horizons: tuple[int, ...] = (3, 5)
) -> dict[str, Any]:
    """Run reproducible expanding chronological research and return a private report."""
    if pair not in UNIVERSE:
        return _empty(pair, "Pair is outside the private research universe.", len(bars))
    if not horizons or any(horizon not in (3, 5) for horizon in horizons):
        return _empty(pair, "Only declared 3- and 5-day horizons are supported.", len(bars))
    try:
        clean = validate_bars(bars)
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        return _empty(pair, f"Invalid price capture: {exc}", len(bars))
    if len(clean) < 400:
        return _empty(pair, "At least 400 completed daily bars are required.", len(clean))
    short_history = len(clean) < MIN_TRAIN + CALIBRATION_BARS + 2 * EMBARGO + 50
    training_bars = 150 if short_history else MIN_TRAIN
    calibration_bars = 150 if short_history else CALIBRATION_BARS
    test_bars = 80 if short_history else TEST_BARS
    training_minimum_trades = 12 if short_history else 30
    marked_gaps = [bar["time"] for bar in clean if bar.get("gap_before")]

    trial_rows: dict[str, list[dict[str, Any]]] = {}
    definitions: dict[str, tuple[Policy, int]] = {}
    excluded_windows: list[dict[str, Any]] = []
    for policy in POLICIES:
        for horizon in dict.fromkeys(horizons):
            name = f"{policy.name}_h{horizon}"
            definitions[name] = (policy, horizon)
            rows = []
            feature_excluded, holding_excluded = 0, 0
            for index in range(60, len(clean) - horizon):
                feature_start = index - max(14, policy.lookback)
                if _window_has_gap(clean, feature_start, index):
                    feature_excluded += 1
                    continue
                direction, strength, atr = _signal(clean, index, policy)
                if direction:
                    if _window_has_gap(clean, index, index + horizon):
                        holding_excluded += 1
                        continue
                    row = simulate_trade(
                        pair, clean, index, direction, atr * policy.stop_atr, horizon
                    )
                    row.update(
                        {
                            "policy": name,
                            "strength": strength,
                            "horizon_end_time": clean[index + horizon]["time"],
                            "feature_start_index": feature_start,
                            "feature_start_time": clean[feature_start]["time"],
                        }
                    )
                    rows.append(row)
            trial_rows[name] = rows
            excluded_windows.append(
                {
                    "trial": name,
                    "feature_gap_windows": feature_excluded,
                    "signal_holding_gap_windows": holding_excluded,
                    "usable_label_count": len(rows),
                }
            )

    folds: list[dict[str, Any]] = []
    heldout: list[dict[str, Any]] = []
    test_start = training_bars + calibration_bars + 2 * EMBARGO
    while test_start + 20 < len(clean):
        cal_end, cal_start = test_start - EMBARGO, test_start - EMBARGO - calibration_bars
        train_end = cal_start - EMBARGO
        test_end = min(len(clean), test_start + test_bars)
        selected, trials = _selection(trial_rows, 60, train_end, training_minimum_trades)
        fold_id = len(folds) + 1
        predictions: list[dict[str, Any]] = []
        cal_rows: list[dict[str, Any]] = []
        base_rates: dict[str, float | None] = {"BUY": None, "SELL": None}
        if selected is not None:
            cal_rows = _cohort(trial_rows[selected], cal_start, cal_end)
            training = _cohort(trial_rows[selected], 60, train_end)
            base_rates = {side: _direction_base_rate(training, side) for side in ("BUY", "SELL")}
            for row in _cohort(trial_rows[selected], test_start, test_end):
                probability, matching = _calibrate(
                    cal_rows, float(row["strength"]), str(row["direction"])
                )
                base_rate = base_rates[str(row["direction"])]
                if base_rate is None:
                    probability = None
                predictions.append(
                    {
                        **row,
                        "fold": fold_id,
                        "predicted_probability": probability,
                        "probability_sample_count": len(matching),
                        "training_base_rate": base_rate,
                        "probability_conditioning": "POLICY_DIRECTION_STRENGTH_BUCKET",
                    }
                )
            heldout.extend(predictions)
        folds.append(
            {
                "fold": fold_id,
                "train_start": clean[60]["time"],
                "train_end": clean[train_end - 1]["time"],
                "calibration_start": clean[cal_start]["time"],
                "calibration_end": clean[cal_end - 1]["time"],
                "test_start": clean[test_start]["time"],
                "test_end": clean[test_end - 1]["time"],
                "embargo_bars": EMBARGO,
                "selected_trial": selected,
                "training_trials": trials,
                "calibration_sample_count": len(cal_rows),
                "direction_training_base_rates": base_rates,
                "test_summary": _summary(predictions),
            }
        )
        test_start = test_end

    cal_end = len(clean) - EMBARGO
    cal_start = cal_end - calibration_bars
    train_end = cal_start - EMBARGO
    selected, final_trials = _selection(trial_rows, 60, train_end, training_minimum_trades)
    calibration = _calibration_check(heldout)
    selected_policy_heldout = [row for row in heldout if row["policy"] == selected]
    selected_policy_calibration = _calibration_check(selected_policy_heldout)
    selected_policy_summary = {"policy": selected, **_summary(selected_policy_heldout)}
    direction_evidence = {
        side: {
            "summary": _summary(
                [row for row in selected_policy_heldout if row["direction"] == side]
            ),
            "calibration": _calibration_check(
                [row for row in selected_policy_heldout if row["direction"] == side]
            ),
            "strength_buckets": {
                str(bucket): {
                    "summary": _summary(
                        [
                            row
                            for row in selected_policy_heldout
                            if row["direction"] == side
                            and _bucket(float(row["strength"])) == bucket
                        ]
                    ),
                    "calibration": _calibration_check(
                        [
                            row
                            for row in selected_policy_heldout
                            if row["direction"] == side
                            and _bucket(float(row["strength"])) == bucket
                        ]
                    ),
                }
                for bucket in range(3)
            },
        }
        for side in ("BUY", "SELL")
    }
    calibration["selected_policy"] = selected
    calibration["selected_policy_check"] = selected_policy_calibration
    summary = _summary(heldout)
    candidate = _empty(pair, "No selected policy.")["candidate"]
    candidate["as_of"] = clean[-1]["time"]
    if selected:
        policy, horizon = definitions[selected]
        direction, strength, atr = _signal(clean, len(clean) - 1, policy)
        cal_rows = _cohort(trial_rows[selected], cal_start, cal_end)
        side = "BUY" if direction > 0 else "SELL" if direction < 0 else "NONE"
        probability, matching = _calibrate(cal_rows, strength, side)
        own_direction = direction_evidence.get(
            side, {"summary": _summary([]), "calibration": {"passes": False, "sample_count": 0}}
        )
        own_cell = own_direction.get("strength_buckets", {}).get(
            str(_bucket(strength)),
            {"summary": _summary([]), "calibration": {"passes": False, "sample_count": 0}},
        )
        direction_calibration = own_cell["calibration"]
        reasons = ["Price-only baseline; historical macro/news have not been validated."]
        if short_history:
            reasons.append("Short-history cohort has limited training and held-out evidence.")
        qualified = bool(direction_calibration["passes"] and probability is not None)
        if not direction_calibration["passes"]:
            reasons.append(
                "Held-out probability calibration for this policy, direction and strength bucket "
                "has not passed."
            )
        if len(matching) < 20:
            reasons.append(
                "Fewer than 20 same-direction trades in the comparable calibration bucket."
            )
        if sum(row["direction"] == side for row in cal_rows) < 40:
            reasons.append("Fewer than 40 matured calibration trades in this direction.")
        empirical = _summary(matching)
        positive_ev = _positive_ev_for_policy(
            empirical, own_cell["summary"], int(direction_calibration["sample_count"])
        )
        if not positive_ev:
            reasons.append(
                "Positive net expectancy is not established in comparable calibration "
                "and this selected policy's same-direction, same-bucket heldout results."
            )
        if not direction:
            reasons.append("The selected policy has no completed-bar signal today.")
        if _window_has_gap(clean, len(clean) - 1 - max(14, policy.lookback), len(clean) - 1):
            reasons.append("Latest feature window crosses a quarantined observation; abstain.")
        if probability is None or probability < 0.60:
            reasons.append("The requested 60% net-profitable threshold is not established.")
        entry = float(clean[-1]["close"])
        risk = atr * policy.stop_atr
        eligible = (
            qualified
            and positive_ev
            and bool(direction)
            and bool(probability is not None and probability >= 0.60)
        )
        candidate = {
            "status": "RESEARCH_CANDIDATE" if eligible else "ABSTAIN",
            "direction": "BUY" if direction > 0 else "SELL" if direction < 0 else None,
            "entry": entry if direction else None,
            "entry_basis": "Reference last close; actual next-session open is unknown.",
            "stop": entry - direction * risk if direction else None,
            "tp1": entry + direction * risk if direction else None,
            "tp2": entry + direction * 3 * risk if direction else None,
            "holding_days": horizon,
            "policy": selected,
            "probability": probability if qualified and direction else None,
            "probability_sample_count": len(matching),
            "probability_conditioning": (
                "Empirical selected-policy, BUY/SELL direction and strength bucket. "
                "Only matured trades in today's direction support this estimate."
            ),
            "probability_same_direction_sample_count": sum(
                row["direction"] == ("BUY" if direction > 0 else "SELL") for row in matching
            )
            if direction
            else 0,
            "probability_direction_specific_validated": qualified,
            "direction_heldout_evidence": own_direction,
            "probability_strength_bucket": _bucket(strength),
            "probability_heldout_cell": own_cell,
            "probability_ci95": wilson_interval(
                sum(bool(row["profitable"]) for row in matching), len(matching)
            )
            if qualified and direction
            else None,
            "expected_r": empirical["net_ev_r"] if qualified and direction else None,
            "expected_r_sample_count": len(matching),
            "expected_r_ci95_approx": empirical.get("net_ev_ci95_approx") if qualified else None,
            "reasons": reasons,
            "as_of": clean[-1]["time"],
            "manual_technical_confirmation_required": True,
        }
    equity = []
    cumulative = 0.0
    for row in sorted(heldout, key=lambda item: item["exit_time"]):
        cumulative += float(row["net_r"])
        equity.append({"time": row["exit_time"], "cumulative_r": cumulative})
    return {
        "pair": pair,
        "data_coverage": {
            "bar_count": len(clean),
            "first_bar": clean[0]["time"],
            "last_bar": clean[-1]["time"],
            "interval": "1d",
            "status": "VALID",
            "marked_gap_count": len(marked_gaps),
            "marked_gaps": marked_gaps,
            "gap_policy": (
                "Exclude every feature and complete signal-to-horizon window crossing a gap."
            ),
        },
        "backtest": {
            "method_version": METHOD_VERSION,
            "status": "PROVISIONAL_SHORT_HISTORY" if short_history else "PROVISIONAL_PRICE_ONLY",
            "history_mode": "SHORT_HISTORY" if short_history else "STANDARD_HISTORY",
            "window_bars": {
                "minimum_training": training_bars,
                "calibration": calibration_bars,
                "maximum_test": test_bars,
                "minimum_training_trades": training_minimum_trades,
            },
            "trade_count": len(heldout),
            "summary": summary,
            "selected_policy_summary": selected_policy_summary,
            "selected_policy_direction_evidence": direction_evidence,
            "calibration": calibration,
            "folds": folds,
            "trials": [
                {"trial": name, "policy": asdict(policy), "holding_days": horizon}
                for name, (policy, horizon) in definitions.items()
            ],
            "latest_training_trials": final_trials,
            "excluded_windows": excluded_windows,
            "trades": heldout,
            "assumptions": {
                "costs": asdict(Costs()),
                "pip_size": 0.01 if pair.endswith("JPY") else 0.0001,
                "entry": "Next daily open after completed-bar signal.",
                "partial_exit": "50% at +1R; remaining stop at entry and target +3R.",
                "maximum_full_target_gross_r": 2.0,
                "intrabar_order": "Adverse outcome when daily high/low ordering is unknown.",
                "embargo_bars": EMBARGO,
                "gap_policy": (
                    "No interpolation: actual momentum/ATR input window and complete "
                    "signal-to-final-horizon path must be contiguous FX weekdays."
                ),
                "trial_selection": (
                    "Highest training-only lower approximate EV bound; "
                    f"{training_minimum_trades} training trades minimum."
                ),
                "probability_gates": (
                    "100 heldout predictions for selected policy, direction and strength bucket; "
                    "Brier <= same-direction training baseline; ECE <= 0.10; "
                    "40 same-direction calibration trades and 20 in the strength bucket."
                ),
                "candidate_ev_gate": (
                    "Positive lower EV bounds for comparable calibration and the selected "
                    "policy's same-direction, same-bucket heldout trades, "
                    "with 100 matured predictions."
                ),
                "probability_conditioning": (
                    "Policy, BUY/SELL direction and absolute signal-strength bucket. "
                    "Opposite-direction results cannot qualify the current probability or EV."
                ),
                "cohort_entries": (
                    "Each policy cohort waits its full horizon before another signal."
                ),
                "equity_unit": "Cumulative R per heldout call, without portfolio position sizing.",
            },
            "limitations": [
                (
                    "Short-history cohort: small samples cannot establish a stable trading edge."
                    if short_history
                    else "Longer history does not establish predictive validity."
                ),
                "No point-in-time fundamentals or historical AI/news inputs in this baseline.",
                "Fixed cost assumptions are not witnessed broker fills or swap rates.",
                "Daily candles cannot identify an optimized London/New York entry session.",
                "EV intervals are approximate; dependence and repeated selection remain risks.",
                "Training performance and selection scores are not out-of-sample results.",
                "Three/five-day horizons count observed daily bars, not guaranteed calendar days.",
                ("Results depend on valid contiguous provider windows; missingness may bias them."),
            ],
        },
        "candidate": candidate,
        "chart": {"recent_ohlc": clean[-120:], "equity": equity},
        "session": {"status": "UNAVAILABLE", "reason": "Intraday session evidence is absent."},
    }


REFERENCE_POLICIES = (
    ("momentum5", 5, False, 0.50),
    ("momentum20", 20, False, 0.70),
    ("reversion5", 5, True, 1.00),
)
REFERENCE_ROUNDTRIP_COST_BP = 2.0


def _validate_reference(series: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    previous: datetime | None = None
    for row in series:
        stamp = str(row["time"])
        day = _day(stamp)
        close = float(row["close"])
        if previous is not None and day <= previous:
            raise ValueError("Reference timestamps must be unique and increasing.")
        if not math.isfinite(close) or close <= 0:
            raise ValueError("Reference values must be finite and positive.")
        if previous is not None and (day - previous).days > 7:
            raise ValueError("Reference history has a gap above seven calendar days.")
        result.append({"time": stamp, "close": close})
        previous = day
    return result


def _reference_signal(
    series: list[dict[str, Any]], index: int, lookback: int, contrarian: bool, threshold: float
) -> tuple[int, float]:
    if index < 30:
        return 0, 0.0
    log_moves = [
        math.log(series[i]["close"] / series[i - 1]["close"]) for i in range(index - 19, index + 1)
    ]
    mean_move = _mean(log_moves)
    variance = sum((move - mean_move) ** 2 for move in log_moves) / 19
    if variance <= 1e-16:
        return 0, 0.0
    momentum = math.log(series[index]["close"] / series[index - lookback]["close"])
    strength = abs(momentum) / math.sqrt(variance * lookback)
    if strength < threshold:
        return 0, strength
    direction = 1 if momentum > 0 else -1
    return (-direction if contrarian else direction), strength


def _reference_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"sample_count": 0, "directional_hit_rate": None, "net_ev_bp": None}
    count = len(rows)
    wins = sum(bool(row["direction_correct"]) for row in rows)
    net = [float(row["net_return_bp"]) for row in rows]
    mean = _mean(net)
    variance = sum((value - mean) ** 2 for value in net) / max(1, count - 1)
    error = 1.96 * math.sqrt(variance / count)
    cumulative, peak, drawdown = 0.0, 0.0, 0.0
    for value in net:
        cumulative += value
        peak = max(peak, cumulative)
        drawdown = max(drawdown, peak - cumulative)
    return {
        "sample_count": count,
        "directional_hit_rate": wins / count,
        "directional_hit_ci95": wilson_interval(wins, count),
        "net_profitable_rate": sum(value > 0 for value in net) / count,
        "gross_ev_bp": _mean([float(row["gross_return_bp"]) for row in rows]),
        "net_ev_bp": mean,
        "net_ev_ci95_approx_bp": [mean - error, mean + error],
        "total_net_bp": cumulative,
        "max_drawdown_bp": drawdown,
    }


def _reference_selection(
    trial_rows: dict[str, list[dict[str, Any]]], train_end: int, minimum_trades: int
) -> tuple[str | None, list[dict[str, Any]]]:
    trials = []
    for name, rows in trial_rows.items():
        summary = _reference_summary(_cohort(rows, 30, train_end))
        score = (
            summary["net_ev_ci95_approx_bp"][0]
            if summary["sample_count"] >= minimum_trades
            else None
        )
        trials.append({"trial": name, "selection_lower_net_ev_bp": score, **summary})
    available = [row for row in trials if row["selection_lower_net_ev_bp"] is not None]
    best = max(available, key=lambda row: row["selection_lower_net_ev_bp"]) if available else None
    return str(best["trial"]) if best else None, trials


def analyze_reference_pair(pair: str, series: list[dict[str, Any]]) -> dict[str, Any]:
    """Separate direction research from reference closes; no manufactured OHLC or R.

    Entry is the next reference observation and exit is three/five subsequent
    reference observations later. Reference publications are indicative, so the
    basis-point returns below are a descriptive cost scenario, not broker fills.
    """
    limitations = [
        "Reference closes are indicative observations, not executable OHLC or broker fills.",
        "No stop/target path, 1R reward, session timing or partial-exit results can be inferred.",
        "A fixed 2bp roundtrip cost excludes financing and is only a descriptive scenario.",
        "Current macro and AI news are absent from historical features and labels.",
        "Observed historical hit rates are not a calibrated current trade probability.",
        "Return intervals are approximate; repeated trials and market dependence remain risks.",
    ]
    empty: dict[str, Any] = {
        "pair": pair,
        "status": "UNAVAILABLE",
        "data_coverage": {"observation_count": len(series), "status": "UNAVAILABLE"},
        "backtest": {
            "status": "UNAVAILABLE",
            "summary": _reference_summary([]),
            "trials": [],
            "folds": [],
            "trades": [],
            "abstentions": 0,
        },
        "candidate": {
            "status": "ABSTAIN",
            "direction": None,
            "probability": None,
            "holding_days": None,
            "reasons": [],
            "as_of": None,
        },
        "chart": {"reference_closes": [], "equity_bp": []},
        "limitations": limitations,
    }
    if pair not in UNIVERSE:
        empty["candidate"]["reasons"] = ["Unknown reference research pair."]
        return empty
    try:
        clean = _validate_reference(series)
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        empty["candidate"]["reasons"] = [f"Invalid reference capture: {exc}"]
        return empty
    if len(clean) < 400:
        empty["candidate"]["reasons"] = ["At least 400 reference observations are required."]
        return empty
    short = len(clean) < 860
    training_bars, validation_bars, test_bars = (150, 150, 80) if short else (400, 400, 250)
    minimum_trades = 12 if short else 30
    trial_rows: dict[str, list[dict[str, Any]]] = {}
    definitions: dict[str, tuple[int, bool, float, int]] = {}
    for name, lookback, contrarian, threshold in REFERENCE_POLICIES:
        for horizon in (3, 5):
            trial = f"reference_{name}_h{horizon}"
            definitions[trial] = (lookback, contrarian, threshold, horizon)
            rows = []
            for index in range(30, len(clean) - horizon - 1):
                direction, strength = _reference_signal(
                    clean, index, lookback, contrarian, threshold
                )
                if direction:
                    entry_index, end_index = index + 1, index + 1 + horizon
                    entry, exit_price = clean[entry_index]["close"], clean[end_index]["close"]
                    gross = direction * (exit_price / entry - 1) * 10000
                    rows.append(
                        {
                            "pair": pair,
                            "policy": trial,
                            "signal_index": index,
                            "end_index": end_index,
                            "signal_time": clean[index]["time"],
                            "entry_time": clean[entry_index]["time"],
                            "exit_time": clean[end_index]["time"],
                            "entry_reference": entry,
                            "exit_reference": exit_price,
                            "direction": "BUY" if direction > 0 else "SELL",
                            "direction_correct": gross > 0,
                            "holding_days": horizon,
                            "strength": strength,
                            "gross_return_bp": gross,
                            "cost_assumption_bp": REFERENCE_ROUNDTRIP_COST_BP,
                            "net_return_bp": gross - REFERENCE_ROUNDTRIP_COST_BP,
                        }
                    )
            trial_rows[trial] = rows

    heldout: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    test_start = training_bars + validation_bars + 2 * EMBARGO
    abstentions = 0
    while test_start + 20 < len(clean):
        validation_end = test_start - EMBARGO
        validation_start = validation_end - validation_bars
        train_end = validation_start - EMBARGO
        test_end = min(test_start + test_bars, len(clean))
        selected, training_trials = _reference_selection(trial_rows, train_end, minimum_trades)
        validation, test = [], []
        if selected:
            validation = _cohort(trial_rows[selected], validation_start, validation_end)
            test = [
                {**row, "fold": len(folds) + 1}
                for row in _cohort(trial_rows[selected], test_start, test_end)
            ]
            lookback, contrarian, threshold, horizon = definitions[selected]
            abstentions += sum(
                _reference_signal(clean, index, lookback, contrarian, threshold)[0] == 0
                for index in range(test_start, test_end - horizon - 1)
            )
        else:
            abstentions += test_end - test_start
        heldout.extend(test)
        folds.append(
            {
                "fold": len(folds) + 1,
                "selected_trial": selected,
                "train_start": clean[30]["time"],
                "train_end": clean[train_end - 1]["time"],
                "validation_start": clean[validation_start]["time"],
                "validation_end": clean[validation_end - 1]["time"],
                "test_start": clean[test_start]["time"],
                "test_end": clean[test_end - 1]["time"],
                "embargo_bars": EMBARGO,
                "training_trials": training_trials,
                "validation_summary": _reference_summary(validation),
                "test_summary": _reference_summary(test),
            }
        )
        test_start = test_end
    latest_train_end = len(clean) - validation_bars - 2 * EMBARGO
    selected, final_trials = _reference_selection(trial_rows, latest_train_end, minimum_trades)
    candidate = {
        "status": "ABSTAIN",
        "direction": None,
        "probability": None,
        "holding_days": None,
        "as_of": clean[-1]["time"],
        "reasons": ["No current signal from a selected reference-close policy."],
    }
    if selected:
        lookback, contrarian, threshold, horizon = definitions[selected]
        direction, _strength = _reference_signal(
            clean, len(clean) - 1, lookback, contrarian, threshold
        )
        candidate = {
            "status": "DESCRIPTIVE_BIAS" if direction else "ABSTAIN",
            "direction": "BUY" if direction > 0 else "SELL" if direction < 0 else None,
            "holding_days": horizon,
            "policy": selected,
            "probability": None,
            "as_of": clean[-1]["time"],
            "reasons": [
                "Reference-close directional research requires independent confirmation.",
                "Its historical hit rate cannot qualify the partial-exit trading strategy.",
            ],
        }
    cumulative = 0.0
    equity = []
    for row in sorted(heldout, key=lambda trade: trade["exit_time"]):
        cumulative += float(row["net_return_bp"])
        equity.append({"time": row["exit_time"], "cumulative_bp": cumulative})
    return {
        "pair": pair,
        "status": "PROVISIONAL_REFERENCE_DIRECTIONAL",
        "data_coverage": {
            "status": "VALID",
            "observation_count": len(clean),
            "first_observation": clean[0]["time"],
            "last_observation": clean[-1]["time"],
            "interval": "1d",
            "price_type": "INDICATIVE_REFERENCE_CLOSE",
        },
        "backtest": {
            "status": "PROVISIONAL_REFERENCE_DIRECTIONAL",
            "summary": _reference_summary(heldout),
            "trade_count": len(heldout),
            "folds": folds,
            "trades": heldout,
            "abstentions": abstentions,
            "abstention_definition": (
                "Completed test dates with no threshold signal or no trained policy; "
                "cooldown dates are excluded from trades, not counted as abstentions."
            ),
            "history_mode": "SHORT_HISTORY" if short else "STANDARD_HISTORY",
            "trials": [
                {
                    "trial": trial,
                    "lookback": values[0],
                    "contrarian": values[1],
                    "minimum_strength": values[2],
                    "holding_days": values[3],
                }
                for trial, values in definitions.items()
            ],
            "latest_training_trials": final_trials,
            "window_bars": {
                "minimum_training": training_bars,
                "validation": validation_bars,
                "maximum_test": test_bars,
                "embargo": EMBARGO,
            },
            "assumptions": {
                "entry": "Next published reference observation after a completed-reference signal.",
                "exit": "Three/five subsequent reference observations after entry.",
                "roundtrip_cost_bp": REFERENCE_ROUNDTRIP_COST_BP,
                "selection": "Highest training-only lower approximate net-bp return bound.",
                "minimum_training_trades": minimum_trades,
                "probability": "UNAVAILABLE: current reference probabilities are not calibrated.",
                "equity_unit": "Cumulative basis points per nonoverlapping descriptive call.",
            },
        },
        "candidate": candidate,
        "chart": {"reference_closes": clean[-120:], "equity_bp": equity},
        "limitations": limitations,
    }
