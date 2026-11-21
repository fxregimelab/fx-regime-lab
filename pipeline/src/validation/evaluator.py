"""Pure orchestration for call-bound validation price evidence."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from copy import deepcopy
from datetime import date, datetime
from typing import Any

from src.validation.calculator import (
    EVALUATION_VERSION,
    calculate_horizon,
    normalize_predicted_direction,
    validate_price,
    validate_probability,
)
from src.validation.calendar import add_trading_days

logger = logging.getLogger(__name__)

ReadEntry = Callable[[int], Mapping[str, Any] | None]
ReadPrice = Callable[[str, date], Mapping[str, Any] | None]

_HORIZON_FIELDS = {
    "t5": (
        "log_return_t5_bps",
        "correct_t5",
        "brier_score_t5",
        "actual_direction_t5",
        "actual_return_5d",
        "correct_5d",
        "brier_5d",
        "log_return_net_bps_t5",
        "correct_net_t5",
        "cost_bps_t5",
        "price_evidence_t5",
    ),
    "t20": (
        "log_return_t20_bps",
        "correct_t20",
        "brier_score_t20",
        "actual_direction_t20",
        "actual_return_20d",
        "correct_20d",
        "brier_20d",
        "log_return_net_bps_t20",
        "correct_net_t20",
        "cost_bps_t20",
        "price_evidence_t20",
    ),
}


def _strict_date(raw: Any, label: str) -> date:
    if isinstance(raw, datetime):
        raise ValueError(f"{label} must be an ISO calendar date without a time")
    if isinstance(raw, date):
        return raw
    if not isinstance(raw, str) or len(raw) != 10:
        raise ValueError(f"{label} must be an ISO calendar date")
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO calendar date") from exc
    if parsed.isoformat() != raw:
        raise ValueError(f"{label} must be an ISO calendar date")
    return parsed


def normalize_call_id(call: Mapping[str, Any]) -> int:
    raw_id = call.get("id")
    raw_call_id = call.get("call_id")
    if raw_id is not None and raw_call_id is not None and raw_id != raw_call_id:
        raise ValueError("id and call_id must agree")
    value = raw_call_id if raw_call_id is not None else raw_id
    if isinstance(value, bool):
        raise ValueError("call_id must be a positive integer")
    if isinstance(value, int):
        call_id = value
    elif isinstance(value, str) and value.isascii() and value.isdigit():
        call_id = int(value)
    else:
        raise ValueError("call_id must be a positive integer")
    if call_id <= 0:
        raise ValueError("call_id must be a positive integer")
    return call_id


def _pair(raw: Any) -> str:
    pair = str(raw).strip().upper() if raw is not None else ""
    if pair not in {"EURUSD", "USDJPY", "USDINR"}:
        raise ValueError("call pair is unsupported")
    return pair


def _existing_horizon_complete(existing: Mapping[str, Any] | None, horizon: str) -> bool:
    return bool(existing and existing.get(f"log_return_{horizon}_bps") is not None)


def _copy_existing_horizon(
    payload: dict[str, Any], existing: Mapping[str, Any], horizon: str
) -> None:
    evidence_key = f"price_evidence_{horizon}"
    if evidence_key not in existing:
        raise ValueError(f"completed {horizon} is missing price evidence")
    for key in _HORIZON_FIELDS[horizon]:
        if key in existing:
            payload[key] = deepcopy(existing[key])


def _evidence_price(
    evidence: Mapping[str, Any], *, kind: str, pair: str, target: date, source: str
) -> float:
    expected_keys = {"kind", "pair", "date", "price", "source"}
    if set(evidence) != expected_keys:
        raise ValueError("price evidence has unexpected fields")
    if (
        evidence.get("kind") != kind
        or evidence.get("pair") != pair
        or evidence.get("source") != source
        or _strict_date(evidence.get("date"), "evidence date") != target
    ):
        raise ValueError("price evidence identity does not match the call")
    return validate_price(evidence.get("price"), "evidence price")


def _entry_evidence(
    signal: Mapping[str, Any], *, call_id: int, pair: str, call_date: date
) -> tuple[float, dict[str, Any]]:
    if signal.get("pair") != pair or _strict_date(signal.get("date"), "signal date") != call_date:
        raise ValueError("publication signal identity does not match the call")
    price = validate_price(signal.get("spot"), "publication spot")
    return price, {
        "kind": "publication_signal",
        "pair": pair,
        "date": call_date.isoformat(),
        "price": price,
        "source": "publication_evidence.signal_payload.spot",
        "call_id": call_id,
    }


def _existing_entry_evidence(
    existing: Mapping[str, Any], *, call_id: int, pair: str, call_date: date
) -> tuple[float, dict[str, Any]]:
    raw = existing.get("entry_price_evidence")
    if not isinstance(raw, Mapping):
        raise ValueError("existing evaluation is missing entry price evidence")
    expected_keys = {"kind", "pair", "date", "price", "source", "call_id"}
    if set(raw) != expected_keys or raw.get("call_id") != call_id:
        raise ValueError("entry price evidence identity does not match the call")
    price = _evidence_price(
        {key: raw[key] for key in expected_keys if key != "call_id"},
        kind="publication_signal",
        pair=pair,
        target=call_date,
        source="publication_evidence.signal_payload.spot",
    )
    return price, deepcopy(dict(raw))


def _endpoint_evidence(
    row: Mapping[str, Any], *, pair: str, target: date
) -> tuple[float, dict[str, Any]]:
    if row.get("pair") != pair or _strict_date(row.get("date"), "price date") != target:
        raise ValueError("historical price identity does not match the requested horizon")
    price = validate_price(row.get("close"), "historical close")
    return price, {
        "kind": "historical_close",
        "pair": pair,
        "date": target.isoformat(),
        "price": price,
        "source": "historical_prices.close",
    }


def _add_horizon(
    payload: dict[str, Any], stats: Mapping[str, Any], horizon: str, evidence: dict[str, Any]
) -> None:
    days = "5d" if horizon == "t5" else "20d"
    payload[f"log_return_{horizon}_bps"] = stats["log_return_bps"]
    payload[f"correct_{horizon}"] = stats["correct"]
    payload[f"brier_score_{horizon}"] = stats["brier_score"]
    payload[f"actual_direction_{horizon}"] = stats["realized_direction"]
    payload[f"actual_return_{days}"] = stats["log_return_bps"] / 10_000.0
    payload[f"correct_{days}"] = stats["correct"]
    payload[f"brier_{days}"] = stats["brier_score"]
    payload[f"log_return_net_bps_{horizon}"] = stats["log_return_net_bps"]
    payload[f"correct_net_{horizon}"] = stats["correct_net"]
    payload[f"cost_bps_{horizon}"] = stats["cost_bps"]
    payload[f"price_evidence_{horizon}"] = evidence


def evaluate_call(
    call: Mapping[str, Any],
    as_of: date,
    existing: Mapping[str, Any] | None,
    *,
    read_entry: ReadEntry,
    read_price: ReadPrice,
) -> dict[str, Any] | None:
    """Evaluate matured horizons from immutable entry and exact close evidence.

    Invalid or unavailable evidence fails closed and returns ``None``. Exceptions
    raised by either reader are deliberately allowed to propagate.
    """
    try:
        call_id = normalize_call_id(call)
        pair = _pair(call.get("pair"))
        call_date = _strict_date(call.get("date"), "call date")
        evaluation_date = _strict_date(as_of, "as_of")
        predicted = normalize_predicted_direction(call.get("predicted_direction"))
        confidence_raw = call.get("confidence")
        confidence = None if confidence_raw is None else validate_probability(confidence_raw)
        if predicted != "NEUTRAL" and confidence is None:
            raise ValueError("confidence is required for a directional call")
        if existing is not None and (
            existing.get("call_id") != call_id
            or existing.get("evaluation_version") != EVALUATION_VERSION
        ):
            raise ValueError("existing evaluation identity or version does not match")
        t5_date = add_trading_days(call_date, 5)
        t20_date = add_trading_days(call_date, 20)
    except (TypeError, ValueError) as exc:
        logger.warning("Validation call unavailable: %s", exc)
        return None

    t5_complete = _existing_horizon_complete(existing, "t5")
    t20_complete = _existing_horizon_complete(existing, "t20")
    if evaluation_date < t5_date:
        return None
    if t5_complete and (evaluation_date < t20_date or t20_complete):
        return None

    payload: dict[str, Any] = {
        "call_id": call_id,
        "call_date": call_date.isoformat(),
        "date": call_date.isoformat(),
        "pair": pair,
        "evaluation_version": EVALUATION_VERSION,
        "predicted_direction": predicted,
        "predicted_regime": call.get("regime"),
        "confidence": confidence,
    }
    for metadata_key in ("strategy_version", "model_version", "data_source"):
        if call.get(metadata_key) is not None:
            payload[metadata_key] = call[metadata_key]

    try:
        if existing is not None:
            entry_price, entry_evidence = _existing_entry_evidence(
                existing, call_id=call_id, pair=pair, call_date=call_date
            )
            if t5_complete:
                _copy_existing_horizon(payload, existing, "t5")
            if t20_complete:
                _copy_existing_horizon(payload, existing, "t20")
        else:
            entry_evidence = None
            entry_price = None
    except (TypeError, ValueError) as exc:
        logger.warning("Validation call unavailable: %s", exc)
        return None

    if existing is None:
        signal = read_entry(call_id)
        if signal is None:
            logger.warning(
                "Validation call unavailable: publication signal evidence is unavailable"
            )
            return None
        try:
            entry_price, entry_evidence = _entry_evidence(
                signal, call_id=call_id, pair=pair, call_date=call_date
            )
        except (TypeError, ValueError) as exc:
            logger.warning("Validation call unavailable: %s", exc)
            return None
    assert entry_price is not None and entry_evidence is not None
    payload["entry_price_evidence"] = entry_evidence

    wrote_new = False
    for horizon, target in (("t5", t5_date), ("t20", t20_date)):
        if evaluation_date < target or _existing_horizon_complete(existing, horizon):
            continue
        price_row = read_price(pair, target)
        if price_row is None:
            logger.warning(
                "Validation horizon unavailable: no exact %s close for call %s on %s",
                pair,
                call_id,
                target.isoformat(),
            )
            continue
        try:
            endpoint, evidence = _endpoint_evidence(price_row, pair=pair, target=target)
            stats = calculate_horizon(entry_price, endpoint, predicted, confidence, pair)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Validation horizon unavailable for call %s on %s: %s",
                call_id,
                target.isoformat(),
                exc,
            )
            continue
        _add_horizon(payload, stats, horizon, evidence)
        wrote_new = True

    return payload if wrote_new else None
