"""Typed snapshot of all fetched market and macro inputs for a single pipeline date."""

from __future__ import annotations

import datetime
import math
from collections.abc import Sequence
from dataclasses import MISSING, dataclass, field, fields
from typing import Any, cast

from src.core.spot_history import SpotHistoryError, select_spot_history, strict_date
from src.fetchers.buffer_keys import (
    KEY_COT,
    KEY_CROSS_ASSET,
    KEY_FX_SPOT,
    KEY_RATE_DECISION_AT,
    KEY_YIELD_OBSERVATIONS,
    KEY_YIELDS,
)
from src.signals.rate_observation import RateObservation
from src.types import CotRow, SpotBar


@dataclass(frozen=True)
class IngestionSnapshot:
    """All fetched market and macro inputs for a single pipeline date.

    This object isolates fetcher outputs from signal logic and downstream
    regime-call assembly. ``frozen=True`` prevents attribute rebinding, while
    the contained dictionaries and history lists remain mutable. Ingestion
    detaches accepted history from the raw provider payload; callers must still
    treat snapshot contents as read-only.
    """

    date: datetime.date
    spots: dict[str, Sequence[SpotBar]]
    yields: dict[str, float | None]
    cot_rows: list[CotRow]
    cross_asset: dict[str, Any]
    macro: dict[str, Any] | None = None
    dqs_score: float | None = None
    stress_level: str | None = None
    rate_observations: dict[str, RateObservation] = field(default_factory=dict)
    rate_decision_at: datetime.datetime | None = None

    @classmethod
    def from_buffer(
        cls,
        as_of: datetime.date,
        buffer: dict[str, Any],
        *,
        macro: dict[str, Any] | None = None,
        dqs_score: float | None = None,
        stress_level: str | None = None,
        rate_decision_at: datetime.datetime | None = None,
    ) -> IngestionSnapshot:
        """Build a snapshot from the raw fetcher ``buffer``.

        Missing or malformed fetcher outputs are normalized to safe defaults
        (empty containers / ``None``) so downstream signal math can fail
        gracefully rather than crashing during ingestion.
        """

        spots_any = buffer.get(KEY_FX_SPOT)
        spots = _coerce_spots(spots_any, as_of=as_of)

        yields_any = buffer.get(KEY_YIELDS)
        yields = _coerce_yields(yields_any)
        rate_observations = _coerce_rate_observations(buffer.get(KEY_YIELD_OBSERVATIONS))

        cot_any = buffer.get(KEY_COT)
        cot_rows = _coerce_cot_rows(cot_any, as_of=as_of)

        cross_any = buffer.get(KEY_CROSS_ASSET)
        cross = _coerce_cross_asset(cross_any)

        return cls(
            date=as_of,
            spots=spots,
            yields=yields,
            cot_rows=cot_rows,
            cross_asset=cross,
            macro=macro,
            dqs_score=dqs_score,
            stress_level=stress_level,
            rate_observations=rate_observations,
            rate_decision_at=rate_decision_at
            or (
                buffer.get(KEY_RATE_DECISION_AT)
                if isinstance(buffer.get(KEY_RATE_DECISION_AT), datetime.datetime)
                else None
            ),
        )

    def spot_bars_for(self, pair: str) -> Sequence[SpotBar]:
        """Return validated, ordered bars for ``pair`` through ``snapshot.date``."""

        return select_spot_history(self.spots.get(pair, ()), pair=pair, as_of=self.date)

    def today_bar_for(self, pair: str) -> SpotBar | None:
        """Return the latest valid bar on or before ``snapshot.date``."""

        bars = self.spot_bars_for(pair)
        if not bars:
            return None
        return bars[-1]

    def yesterday_bar_for(self, pair: str) -> SpotBar | None:
        """Return the bar immediately preceding ``today_bar_for(pair)``."""

        bars = self.spot_bars_for(pair)
        return bars[-2] if len(bars) >= 2 else None

    def macro_value(self, key: str) -> Any | None:
        """Safely read a macro value from the optional macro payload."""

        if self.macro is None:
            return None
        return self.macro.get(key)


def _coerce_spots(spots_any: Any, *, as_of: datetime.date) -> dict[str, Sequence[SpotBar]]:
    """Normalize raw spot buffer to ``dict[pair, Sequence[SpotBar]]``.

    Dict bars, malformed rows, and missing close values are dropped.
    """

    if not isinstance(spots_any, dict):
        return {}

    out: dict[str, Sequence[SpotBar]] = {}
    for pair, bars_any in spots_any.items():
        if not isinstance(bars_any, list | tuple):
            continue
        bars: list[SpotBar] = []
        for item in bars_any:
            bar = _coerce_spot_bar(item)
            if bar is not None:
                bars.append(bar)
        if bars:
            pair_name = str(pair)
            out[pair_name] = select_spot_history(bars, pair=pair_name, as_of=as_of)
    return out


def _coerce_spot_bar(item: Any) -> SpotBar | None:
    """Coerce a complete provider row without inventing price fields."""

    if isinstance(item, SpotBar):
        return item
    if isinstance(item, dict):
        d_raw = item.get("date")
        if d_raw is None:
            return None
        try:
            d = strict_date(d_raw, field="spot.date")
        except SpotHistoryError:
            return None
        prices = {
            name: _strict_spot_number(item, name, positive=True)
            for name in ("open", "high", "low", "close")
        }
        volume = _strict_spot_number(item, "volume", positive=False, default=0.0)
        pair = str(item.get("pair", ""))
        normalized: dict[str, Any] = {
            "date": d,
            "pair": pair,
            **prices,
            "volume": volume,
        }
        # Copy every current/future SpotBar field present in the provider row.
        # Missing optional fields keep their dataclass defaults.
        values: dict[str, Any] = {}
        for field in fields(SpotBar):
            if field.name in normalized:
                values[field.name] = normalized[field.name]
            elif field.name in item:
                values[field.name] = item[field.name]
            elif field.default is MISSING and field.default_factory is MISSING:
                return None
        return cast(SpotBar, cast(Any, SpotBar)(**values))
    return None


def _strict_spot_number(
    item: dict[str, Any],
    name: str,
    *,
    positive: bool,
    default: float | None = None,
) -> float:
    if name not in item or item[name] is None:
        if default is not None:
            return default
        raise SpotHistoryError(f"spot.{name} is required")
    raw = item[name]
    if isinstance(raw, bool):
        raise SpotHistoryError(f"spot.{name} must be a finite number")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise SpotHistoryError(f"spot.{name} must be a finite number") from exc
    if not math.isfinite(value):
        raise SpotHistoryError(f"spot.{name} must be a finite number")
    if positive and value <= 0:
        raise SpotHistoryError(f"spot.{name} must be positive")
    if not positive and value < 0:
        raise SpotHistoryError(f"spot.{name} must be nonnegative")
    return value


def _coerce_yields(yields_any: Any) -> dict[str, float | None]:
    """Normalize raw yields buffer; non-float values become ``None``."""

    if not isinstance(yields_any, dict):
        return {}
    out: dict[str, float | None] = {}
    for k, v in yields_any.items():
        if v is None:
            out[str(k)] = None
        else:
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                out[str(k)] = None
    return out


def _coerce_rate_observations(raw: Any) -> dict[str, RateObservation]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, RateObservation)}


def _coerce_cot_rows(cot_any: Any, *, as_of: datetime.date) -> list[CotRow]:
    """Normalize raw COT buffer; malformed rows are dropped.

    Rows missing a date field inherit ``as_of`` so partial fetcher output still
    produces a usable snapshot rather than silently disappearing.
    """

    if not isinstance(cot_any, list | tuple):
        return []
    rows: list[CotRow] = []
    for item in cot_any:
        if isinstance(item, CotRow):
            rows.append(item)
            continue
        if isinstance(item, dict):
            d_raw = item.get("date")
            try:
                d = datetime.date.fromisoformat(str(d_raw)[:10]) if d_raw is not None else as_of
            except ValueError:
                continue
            pair = str(item.get("pair", ""))
            try:
                net_long = int(item.get("net_long", 0))
                open_interest = int(item.get("open_interest", 0))
                asset_mgr_raw = item.get("asset_mgr_net")
                asset_mgr_net = int(asset_mgr_raw) if asset_mgr_raw is not None else None
                lev_money_raw = item.get("lev_money_net")
                lev_money_net = int(lev_money_raw) if lev_money_raw is not None else None
            except (TypeError, ValueError):
                continue
            rows.append(
                CotRow(
                    date=d,
                    pair=pair,
                    net_long=net_long,
                    open_interest=open_interest,
                    asset_mgr_net=asset_mgr_net,
                    lev_money_net=lev_money_net,
                )
            )
    return rows


def _coerce_cross_asset(cross_any: Any) -> dict[str, Any]:
    """Normalize known scalar legs and detach complete finite history legs.

    A malformed value rejects its whole history leg. Dropping only that value
    would shorten the series and silently change the chronology used by rank
    calculations.
    """

    out: dict[str, Any] = {
        "vix": None,
        "dxy": None,
        "oil": None,
        "gold": None,
        "copper": None,
        "stoxx": None,
    }
    if not isinstance(cross_any, dict):
        return out
    for leg in out:
        val = cross_any.get(leg)
        if val is None:
            out[leg] = None
        elif isinstance(val, bool):
            out[leg] = None
        else:
            try:
                number = float(val)
            except (TypeError, ValueError, OverflowError):
                out[leg] = None
            else:
                out[leg] = number if math.isfinite(number) else None

    raw_hist = cross_any.get("hist")
    if not isinstance(raw_hist, dict):
        return out

    history: dict[str, list[float]] = {}
    supported_history_legs = (
        "vix",
        "dxy",
        "oil",
        "gold",
        "copper",
        "iron_ore",
        "stoxx",
        "bund_btp_spread",
        "ecb_balance_sheet",
    )
    for leg in supported_history_legs:
        raw_values = raw_hist.get(leg)
        if not isinstance(raw_values, list) or not raw_values:
            continue
        copied_values: list[float] = []
        for value in raw_values:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                break
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError):
                break
            if not math.isfinite(number):
                break
            copied_values.append(number)
        else:
            history[leg] = copied_values

    if history:
        out["hist"] = history
    return out
