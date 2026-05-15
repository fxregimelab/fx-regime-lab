"""Pair-specific pipeline base class and shared utilities."""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import date
from typing import Any, TypeVar

import pandas as pd
from fredapi import Fred

from src.fx_types import RegimeCall

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Shared retry logic
# ---------------------------------------------------------------------------


def _retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    **kwargs: Any,
) -> T | None:
    """Call ``func`` with exponential-backoff retry on failure."""
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "%s failed (attempt %s/%s): %s",
                func.__name__,
                attempt,
                max_attempts,
                exc,
            )
            if attempt < max_attempts:
                sleep_time = base_delay * (2 ** (attempt - 1))
                logger.info("Retrying %s in %.3fs", func.__name__, sleep_time)
                time.sleep(sleep_time)
    return None


# ---------------------------------------------------------------------------
# Shared data quality scoring
# ---------------------------------------------------------------------------


def _data_quality_score(data: dict[str, Any]) -> float:
    """Score data completeness as percentage of non-None leaf values."""
    if not data:
        return 0.0

    def _leaves(obj: Any) -> tuple[int, int]:
        if obj is None:
            return 0, 1
        if isinstance(obj, dict):
            present = total = 0
            for v in obj.values():
                p, t = _leaves(v)
                present += p
                total += t
            return present, total
        if isinstance(obj, (list, tuple)) and not isinstance(obj, (str, bytes)):
            present = total = 0
            for item in obj:
                p, t = _leaves(item)
                present += p
                total += t
            return present, total
        return 1, 1

    present, total = _leaves(data)
    return (present / total * 100.0) if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Shared FRED / yfinance helpers
# ---------------------------------------------------------------------------


def _fred_latest(series_id: str, api_key: str | None = None) -> float | None:
    """Fetch the latest observation from a FRED series."""
    key = api_key or os.environ.get("FRED_API_KEY")
    if not key:
        logger.warning("FRED_API_KEY not set — skipping %s", series_id)
        return None
    try:
        fred = Fred(api_key=key)
        series = fred.get_series_latest_release(series_id)
        if series is None or series.empty:
            logger.warning("FRED %s returned empty series", series_id)
            return None
        clean = series.dropna()
        if clean.empty:
            logger.warning("FRED %s returned NaN-only series", series_id)
            return None
        return float(clean.iloc[-1])
    except Exception as exc:  # noqa: BLE001
        logger.warning("FRED %s fetch failed: %s", series_id, exc)
        return None


def _yfinance() -> Any:
    import yfinance as yf

    return yf


def _yf_latest(ticker: str, period: str = "5d") -> float | None:
    """Fetch the latest close from yfinance."""
    try:
        history = _yfinance().Ticker(ticker).history(period=period)
        if history is None or history.empty or "Close" not in history:
            logger.warning("yfinance %s returned empty history", ticker)
            return None
        closes = history["Close"].dropna()
        if closes.empty:
            logger.warning("yfinance %s returned empty close series", ticker)
            return None
        return float(closes.iloc[-1])
    except Exception as exc:  # noqa: BLE001
        logger.warning("yfinance %s fetch failed: %s", ticker, exc)
        return None


def _yf_history(ticker: str, period: str = "5d") -> pd.DataFrame | None:
    """Fetch a yfinance history frame."""
    try:
        df = _yfinance().Ticker(ticker).history(period=period)
        if df is None or df.empty:
            return None
        return df
    except Exception as exc:  # noqa: BLE001
        logger.warning("yfinance history %s failed: %s", ticker, exc)
        return None


def _percentile_of_score(series: list[float], score: float) -> float | None:
    """Simple percentile of a score within a series."""
    if not series:
        return None
    below = sum(1 for s in series if s < score)
    return (below / len(series)) * 100.0


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class PairPipeline(ABC):
    """Abstract base class for pair-specific regime pipelines."""

    pair: str = ""

    def __init__(self, lookback_days: int = 30) -> None:
        self.lookback_days = lookback_days
        self.logger = logging.getLogger(self.__class__.__name__)

    # -- Data ingestion ------------------------------------------------------

    @abstractmethod
    def fetch_data(self) -> dict[str, Any]:
        """Fetch all raw inputs for this pair."""

    @abstractmethod
    def fetch_all(self) -> dict[str, Any]:
        """Fetch all pair-specific data sources (raw dict only)."""

    # -- Signal computation --------------------------------------------------

    @abstractmethod
    def compute_signals(self, data: dict[str, Any]) -> dict[str, Any]:
        """Compute individual signal families from raw data."""

    @abstractmethod
    def compute_composite(self, signals: dict[str, Any]) -> float:
        """Blend signals into a single composite score."""

    @abstractmethod
    def classify_regime(self, composite: float, signals: dict[str, Any]) -> str:
        """Map composite score to a regime label."""

    @abstractmethod
    def compute_execution(self, regime: str, signals: dict[str, Any]) -> dict[str, Any]:
        """Produce execution HUD (entry timing, sizing, stop)."""

    # -- Orchestration -------------------------------------------------------

    def run(self) -> RegimeCall:
        """Execute the full pipeline and return a ``RegimeCall``."""
        data = self.fetch_data()
        signals = self.compute_signals(data)
        composite = self.compute_composite(signals)
        regime = self.classify_regime(composite, signals)
        execution = self.compute_execution(regime, signals)

        # Use v2-validated confidence formula for consistency
        from src.regime.confidence import compute_confidence

        rate_norm = signals.get("rate_norm")
        cot_norm = signals.get("cot_norm")
        conf = compute_confidence(
            composite,
            rate_norm,
            cot_norm,
            pair=self.pair,
            special_signal=signals.get("special_signal_value"),
        )

        return RegimeCall(
            pair=self.pair,
            date=date.today(),
            regime=regime,
            confidence=conf,
            signal_composite=composite,
            rate_signal=signals.get("rate_signal", "NEUTRAL"),
            primary_driver=signals.get("primary_driver"),
            entry_timing=execution.get("entry_timing"),
            position_size=execution.get("position_size"),
            stop_level=execution.get("stop_level"),
            data_quality_score=data.get("data_quality_score"),
            stress_level=signals.get("stress_level"),
            predicted_direction=signals.get("predicted_direction"),
            directional_bias=signals.get("directional_bias"),
            conviction=signals.get("conviction"),
            cot_signal=signals.get("cot_signal"),
            vol_signal=signals.get("vol_signal"),
            oi_signal=signals.get("oi_signal"),
            rr_signal=signals.get("rr_signal"),
            special_signal_value=signals.get("special_signal_value"),
            special_signal_label=signals.get("special_signal_label"),
        )
