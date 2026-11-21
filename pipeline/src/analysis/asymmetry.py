"""Provisional crowding descriptions with explicit evidence limits."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date
from typing import Any, NoReturn

from src.core.spot_history import SpotHistoryError, select_spot_history, strict_date
from src.types import CotRow, SpotBar

_PAIR_ALIASES = {
    "EURUSD": "EURUSD",
    "EUR/USD": "EURUSD",
    "USDJPY": "USDJPY",
    "USD/JPY": "USDJPY",
    "USDINR": "USDINR",
    "USD/INR": "USDINR",
}
_DIRECTIONS = frozenset(("BULLISH", "BEARISH", "NEUTRAL"))
_MAX_SAFE_INTEGER = 9_007_199_254_740_991


def _normalize_pair(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("pair must be one of EURUSD, USDJPY, or USDINR")
    normalized = _PAIR_ALIASES.get(value.upper())
    if normalized is None:
        raise ValueError("pair must be one of EURUSD, USDJPY, or USDINR")
    return normalized


def _validate_contract_count(value: object) -> int:
    if type(value) is not int or abs(value) > _MAX_SAFE_INTEGER:
        raise ValueError("contract count must be a JavaScript-safe Python integer")
    return value


def _unavailable_cot(*reasons: str) -> dict[str, Any]:
    return {
        "status": "UNAVAILABLE",
        "report_date": None,
        "report_age_days": None,
        "net_long": None,
        "asset_mgr_net": None,
        "lev_money_net": None,
        "pair_direction": None,
        "alignment": "UNAVAILABLE",
        "series_definition": "UNKNOWN",
        "release_status": "UNVERIFIED",
        "rank_percentile": None,
        "reasons": list(reasons),
    }


def _alignment_for(*, predicted_direction: str | None, pair_direction: int) -> str:
    if predicted_direction is None:
        return "UNAVAILABLE"
    if predicted_direction == "NEUTRAL":
        return "ABSTAINED"
    if pair_direction == 0:
        return "FLAT_REPORTED_NET"
    call_direction = 1 if predicted_direction == "BULLISH" else -1
    return "ALIGNED" if call_direction == pair_direction else "OPPOSED"


def _cot_rows_identical(left: CotRow, right: CotRow) -> bool:
    fields = (
        "date",
        "pair",
        "net_long",
        "open_interest",
        "asset_mgr_net",
        "lev_money_net",
    )
    return all(
        type(getattr(left, field)) is type(getattr(right, field))
        and getattr(left, field) == getattr(right, field)
        for field in fields
    )


def _cot_component(
    *,
    pair: str,
    as_of: date,
    predicted_direction: str | None,
    rows: Sequence[CotRow],
) -> dict[str, Any]:
    if pair == "USDINR":
        return _unavailable_cot(
            "UNSUPPORTED_COT_PAIR",
            "CATEGORY_PROVENANCE_UNAVAILABLE",
        )

    try:
        eligible: dict[date, CotRow] = {}
        conflicts: set[date] = set()
        for row in rows:
            if not isinstance(row, CotRow):
                return _unavailable_cot(
                    "INVALID_COT_ROW",
                    "CATEGORY_PROVENANCE_UNAVAILABLE",
                )
            if _PAIR_ALIASES.get(row.pair.upper()) != pair:
                continue
            report_date = strict_date(row.date, field="cot.date")
            if report_date > as_of:
                continue
            prior = eligible.get(report_date)
            if prior is None:
                eligible[report_date] = row
            elif not _cot_rows_identical(prior, row):
                conflicts.add(report_date)
    except (AttributeError, TypeError, ValueError, SpotHistoryError):
        return _unavailable_cot(
            "INVALID_COT_ROW",
            "CATEGORY_PROVENANCE_UNAVAILABLE",
        )

    if not eligible:
        return _unavailable_cot(
            "COT_REPORT_UNAVAILABLE",
            "CATEGORY_PROVENANCE_UNAVAILABLE",
        )

    report_date = max(eligible)
    if report_date in conflicts:
        unavailable = _unavailable_cot(
            "CONFLICTING_LATEST_COT_REPORT",
            "CATEGORY_PROVENANCE_UNAVAILABLE",
        )
        unavailable["report_date"] = report_date.isoformat()
        unavailable["report_age_days"] = (as_of - report_date).days
        return unavailable

    anchor = eligible[report_date]
    reasons = ["CATEGORY_PROVENANCE_UNAVAILABLE", "RELEASE_METADATA_UNAVAILABLE"]
    try:
        net_long = _validate_contract_count(anchor.net_long)
    except ValueError:
        unavailable = _unavailable_cot("INVALID_NET_LONG", *reasons)
        unavailable["report_date"] = report_date.isoformat()
        unavailable["report_age_days"] = (as_of - report_date).days
        return unavailable

    category_values: dict[str, int | None] = {}
    for field_name, missing_reason, invalid_reason in (
        ("asset_mgr_net", "ASSET_MGR_NET_UNAVAILABLE", "INVALID_ASSET_MGR_NET"),
        ("lev_money_net", "LEV_MONEY_NET_UNAVAILABLE", "INVALID_LEV_MONEY_NET"),
    ):
        raw = getattr(anchor, field_name)
        if raw is None:
            category_values[field_name] = None
            reasons.append(missing_reason)
            continue
        try:
            category_values[field_name] = _validate_contract_count(raw)
        except ValueError:
            category_values[field_name] = None
            reasons.append(invalid_reason)

    source_direction = 0 if net_long == 0 else (1 if net_long > 0 else -1)
    pair_direction = source_direction if pair == "EURUSD" else -source_direction
    alignment = _alignment_for(
        predicted_direction=predicted_direction,
        pair_direction=pair_direction,
    )
    if predicted_direction is None:
        reasons.append("PREDICTED_DIRECTION_UNAVAILABLE")

    return {
        "status": "PROVISIONAL",
        "report_date": report_date.isoformat(),
        "report_age_days": (as_of - report_date).days,
        "net_long": net_long,
        "asset_mgr_net": category_values["asset_mgr_net"],
        "lev_money_net": category_values["lev_money_net"],
        "pair_direction": pair_direction,
        "alignment": alignment,
        "series_definition": "UNKNOWN",
        "release_status": "UNVERIFIED",
        "rank_percentile": None,
        "reasons": reasons,
    }


def _price_component(
    *, pair: str, as_of: date, bars: Sequence[SpotBar]
) -> dict[str, Any]:
    unavailable: dict[str, Any] = {
        "status": "UNAVAILABLE",
        "latest_date": None,
        "spot": None,
        "mean_close_40": None,
        "observation_count": 0,
        "relative_to_mean_pct": None,
        "reasons": [],
    }
    try:
        selected = select_spot_history(bars, pair=pair, as_of=as_of)
    except (SpotHistoryError, TypeError, ValueError, OverflowError):
        unavailable["reasons"] = ["INVALID_SPOT_HISTORY"]
        return unavailable

    if not selected:
        unavailable["reasons"] = ["SPOT_HISTORY_UNAVAILABLE"]
        return unavailable

    window = selected[-40:]
    count = len(window)
    latest = window[-1]
    spot = float(latest.close)
    reasons = ["REPORT_DATE_ONLY"]
    status = "PROVISIONAL"
    mean: float | None = None
    relative: float | None = None
    if count < 40:
        reasons.append("INSUFFICIENT_PRICE_OBSERVATIONS")
    else:
        mean = sum(float(bar.close) / 40.0 for bar in window)
        if not math.isfinite(mean) or mean <= 0.0:
            reasons.append("INVALID_PRICE_ARITHMETIC")
            status = "UNAVAILABLE"
            mean = None
        else:
            relative = 100.0 * (spot / mean - 1.0)
            if not math.isfinite(relative):
                reasons.append("INVALID_PRICE_ARITHMETIC")
                status = "UNAVAILABLE"
                mean = None
                relative = None

    return {
        "status": status,
        "latest_date": latest.date.isoformat(),
        "spot": spot,
        "mean_close_40": mean,
        "observation_count": count,
        "relative_to_mean_pct": relative,
        "reasons": reasons,
    }


def compute_crowding_diagnostic(
    *,
    pair: str,
    as_of_date: date,
    predicted_direction: str | None,
    cot_rows: Sequence[CotRow],
    spot_bars: Sequence[SpotBar],
    call_id: int | None = None,
) -> dict[str, Any]:
    """Describe supplied positioning and prices without estimating loss or squeeze."""

    normalized_pair = _normalize_pair(pair)
    try:
        cutoff = strict_date(as_of_date, field="as_of_date")
    except SpotHistoryError as exc:
        raise ValueError(str(exc)) from exc
    if predicted_direction is not None and (
        not isinstance(predicted_direction, str)
        or predicted_direction not in _DIRECTIONS
    ):
        raise ValueError("predicted_direction must be BULLISH, BEARISH, NEUTRAL, or None")
    if call_id is not None and (
        type(call_id) is not int
        or call_id <= 0
        or call_id > _MAX_SAFE_INTEGER
    ):
        raise ValueError("call_id must be a positive JavaScript-safe Python integer or None")

    cot = _cot_component(
        pair=normalized_pair,
        as_of=cutoff,
        predicted_direction=predicted_direction,
        rows=cot_rows,
    )
    price = _price_component(pair=normalized_pair, as_of=cutoff, bars=spot_bars)
    return {
        "version": "crowding-description-v1",
        "pair": normalized_pair,
        "call_id": call_id,
        "as_of_date": cutoff.isoformat(),
        "predicted_direction": predicted_direction,
        "cot": cot,
        "price": price,
        "participant_loss_estimate": None,
        "squeeze_probability": None,
        "point_in_time_qualified": False,
    }


def compute_pain_index(*args: Any, **kwargs: Any) -> NoReturn:
    """Retired: participant pain is not identified by COT and close histories."""

    raise RuntimeError(
        "compute_pain_index is retired; use compute_crowding_diagnostic for "
        "provisional reported-position and price descriptions"
    )
