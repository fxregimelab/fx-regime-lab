"""Typed snapshot of all fetched market and macro inputs for a single pipeline date."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from src.fetchers.buffer_keys import KEY_COT, KEY_CROSS_ASSET, KEY_FX_SPOT, KEY_YIELDS
from src.types import CotRow, SpotBar


@dataclass(frozen=True)
class IngestionSnapshot:
    """All fetched market and macro inputs for a single pipeline date.

    This object isolates fetcher outputs from signal logic and downstream
    regime-call assembly. It is intentionally flat and immutable so that
    signal builders can depend on a stable contract.
    """

    date: datetime.date
    spots: dict[str, Sequence[SpotBar]]
    yields: dict[str, float | None]
    cot_rows: list[CotRow]
    cross_asset: dict[str, float | None]
    macro: dict[str, Any] | None = None
    dqs_score: float | None = None
    stress_level: str | None = None

    @classmethod
    def from_buffer(
        cls,
        as_of: datetime.date,
        buffer: dict[str, Any],
        *,
        macro: dict[str, Any] | None = None,
        dqs_score: float | None = None,
        stress_level: str | None = None,
    ) -> IngestionSnapshot:
        """Build a snapshot from the raw fetcher ``buffer``.

        Missing or malformed fetcher outputs are normalized to safe defaults
        (empty containers / ``None``) so downstream signal math can fail
        gracefully rather than crashing during ingestion.
        """

        spots_any = buffer.get(KEY_FX_SPOT)
        spots = _coerce_spots(spots_any)

        yields_any = buffer.get(KEY_YIELDS)
        yields = _coerce_yields(yields_any)

        cot_any = buffer.get(KEY_COT)
        cot_rows = _coerce_cot_rows(cot_any)

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
        )

    def spot_bars_for(self, pair: str) -> Sequence[SpotBar]:
        """Return the spot bar sequence for ``pair`` (empty if missing)."""

        return self.spots.get(pair, ())

    def today_bar_for(self, pair: str) -> SpotBar | None:
        """Return the bar matching ``snapshot.date`` for ``pair``, or the latest bar."""

        bars = self.spot_bars_for(pair)
        if not bars:
            return None
        for bar in bars:
            if bar.date == self.date:
                return bar
        return bars[-1]

    def yesterday_bar_for(self, pair: str) -> SpotBar | None:
        """Return the bar immediately preceding ``today_bar_for(pair)``."""

        bars = self.spot_bars_for(pair)
        today = self.today_bar_for(pair)
        if today is None:
            return None
        for idx, bar in enumerate(bars):
            if bar is today or bar.date == today.date:
                return bars[idx - 1] if idx >= 1 else today
        return None

    def macro_value(self, key: str) -> Any | None:
        """Safely read a macro value from the optional macro payload."""

        if self.macro is None:
            return None
        return self.macro.get(key)


def _coerce_spots(spots_any: Any) -> dict[str, Sequence[SpotBar]]:
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
            out[str(pair)] = tuple(bars)
    return out


def _coerce_spot_bar(item: Any) -> SpotBar | None:
    """Coerce a dict or SpotBar into a SpotBar with valid close."""

    if isinstance(item, SpotBar):
        if item.close is None or item.close <= 0:
            return None
        return item
    if isinstance(item, dict):
        d_raw = item.get("date")
        if d_raw is None:
            return None
        try:
            d = datetime.date.fromisoformat(str(d_raw)[:10])
        except ValueError:
            return None
        close_raw = item.get("close")
        try:
            close = float(close_raw) if close_raw is not None else 0.0
        except (TypeError, ValueError):
            close = 0.0
        if close <= 0:
            return None
        open_ = float(item.get("open", close)) if item.get("open") is not None else close
        high = float(item.get("high", close)) if item.get("high") is not None else close
        low = float(item.get("low", close)) if item.get("low") is not None else close
        volume = float(item.get("volume", 0.0)) if item.get("volume") is not None else 0.0
        pair = str(item.get("pair", ""))
        return SpotBar(
            date=d, pair=pair, open=open_, high=high, low=low, close=close, volume=volume
        )
    return None


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


def _coerce_cot_rows(cot_any: Any) -> list[CotRow]:
    """Normalize raw COT buffer; malformed rows are dropped."""

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
                if d_raw is not None:
                    d = datetime.date.fromisoformat(str(d_raw)[:10])
                else:
                    d = datetime.date.today()
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


def _coerce_cross_asset(cross_any: Any) -> dict[str, float | None]:
    """Normalize cross-asset buffer; keep known legs, coerce to float or None."""

    out: dict[str, float | None] = {
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
        else:
            try:
                out[leg] = float(val)
            except (TypeError, ValueError):
                out[leg] = None
    return out
