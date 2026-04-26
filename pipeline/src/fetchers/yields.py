"""FRED-only yield and policy-rate legs for the pipeline (no yfinance)."""

from __future__ import annotations

import logging
import os
from datetime import date

from fredapi import Fred

from src.types import RawYields

logger = logging.getLogger(__name__)


def fetch_yields(lookback_days: int = 5) -> list[RawYields]:
    """Latest levels from FRED only: DGS2 (US 2Y), ECBDFR, IRSTJP01JPM156N, INTDSRINM193N.

    ``Fred(api_key=os.environ["FRED_API_KEY"]).get_series`` for each; non-US legs log
    a warning and become ``None`` on failure. ``lookback_days`` is kept for API compatibility.
    """
    _ = lookback_days
    today = date.today()
    try:
        fred = Fred(api_key=os.environ["FRED_API_KEY"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("FRED init failed: %s", exc)
        logger.warning("US 2Y missing; returning empty yields list")
        return []

    us_2y: float | None = None
    try:
        us_2y = float(fred.get_series("DGS2").dropna().iloc[-1])
    except Exception as exc:  # noqa: BLE001
        logger.warning("FRED DGS2 fetch failed: %s", exc)

    def _leg(series_id: str, label: str) -> float | None:
        try:
            series = fred.get_series(series_id)
            return float(series.dropna().iloc[-1])
        except Exception as exc:  # noqa: BLE001
            logger.warning("FRED %s (%s) failed: %s", label, series_id, exc)
            return None

    def _jp2y(fred: Fred) -> float | None:
        def _try_sid(sid: str) -> float | None:
            try:
                return float(fred.get_series(sid).dropna().iloc[-1])
            except Exception:  # noqa: BLE001
                return None

        v = _try_sid("IRSTJP01JPM156N")
        if v is not None:
            return v
        v = _try_sid("INTDSRJPM193N")
        if v is not None:
            return v
        logger.warning("JP policy-rate series IRSTJP01JPM156N and INTDSRJPM193N both unavailable")
        return None

    de_2y = _leg("ECBDFR", "DE proxy (ECB deposit facility)")
    jp_2y = _jp2y(fred)
    in_2y = _leg("INTDSRINM193N", "IN RBI repo rate")

    if us_2y is None:
        logger.warning("US 2Y missing; returning empty yields list")
        return []

    return [
        RawYields(
            date=today,
            us_2y=us_2y,
            de_2y=de_2y,
            jp_2y=jp_2y,
            in_2y=in_2y,
        )
    ]
