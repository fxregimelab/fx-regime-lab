"""Volatility signal family adapter."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from src.signals.volatility import (
    compute_realized_vol_rank_from_closes,
    compute_vol_signal,
    is_vol_expanding,
    realized_vol21_series_annualized_pct,
)
from src.staged.contracts import IngestionSnapshot
from src.staged.signals.types import FamilyOutput, VolFamilyOutput


def _realized_vols(spot_closes: Sequence[float]) -> tuple[float | None, float | None]:
    arr: npt.NDArray[np.float64] = np.asarray(list(spot_closes), dtype=np.float64)
    if arr.size < 22 or np.any(arr <= 0):
        return None, None
    series = realized_vol21_series_annualized_pct(arr)
    tail = series[21:]
    if tail.size < 5:
        return None, None
    rv20 = float(np.nanmean(tail[-20:])) if tail.size >= 20 else float(tail[-1])
    rv5 = float(np.nanmean(tail[-5:]))
    return rv20, rv5


def _vol_threshold_90(spot_closes: Sequence[float]) -> float | None:
    arr: npt.NDArray[np.float64] = np.asarray(list(spot_closes), dtype=np.float64)
    if arr.size < 22 or np.any(arr <= 0):
        return None
    series = realized_vol21_series_annualized_pct(arr)
    tail = series[21:]
    clean = tail[np.isfinite(tail)]
    if clean.size < 30:
        return None
    return float(np.percentile(clean, 90))


class VolFamily:
    """Compute realized vol, rank, and expansion flag."""

    def compute(self, pair: str, snapshot: IngestionSnapshot) -> FamilyOutput:
        bars = snapshot.spots.get(pair, ())
        spot_closes = tuple(float(b.close) for b in bars if b.close is not None)

        rv20, rv5 = _realized_vols(spot_closes)
        threshold_90 = _vol_threshold_90(spot_closes)
        vol_norm = compute_vol_signal(rv5, rv20, threshold_90)
        vol_expanding = (
            is_vol_expanding(float(rv5), float(threshold_90))
            if rv5 is not None and threshold_90 is not None
            else False
        )
        rv_rank = compute_realized_vol_rank_from_closes(spot_closes)

        return FamilyOutput(
            rate=None,
            cot=None,
            vol=VolFamilyOutput(
                rv20=rv20,
                rv5=rv5,
                vol_norm=vol_norm,
                vol_expanding=vol_expanding,
                implied_vol_30d=None,
                realized_vol_rank=rv_rank,
            ),
            special=None,
        )
