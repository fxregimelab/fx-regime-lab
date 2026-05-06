"""
Cross-asset special signals for composite inputs (commodity / risk / USD-basket proxies).

Each raw input is percentile-ranked on a causal window (including the current print),
then mapped to [-1, +1]. Output convention: +1 = USD strength vs the quote currency.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from src.types import normalize_fx_pair_key

# 60 trading days is the target window; allow sparse calendars from yfinance.
_SPECIAL_RANK_WINDOW = 60
_MIN_RANK_SAMPLE = 30


def percentile_rank(value: float | None, history: Sequence[float] | None) -> float | None:
    """Empirical CDF rank of ``value`` on ``history`` (must include the current print).

    Returns a percentile in ``[0, 1]``, or ``None`` if the sample is too thin or invalid.
    """

    if value is None or not history:
        return None
    raw: list[float] = []
    for x in history:
        if x is None:
            continue
        fv = float(x)
        if np.isfinite(fv):
            raw.append(fv)
    sample = np.array(raw, dtype=np.float64)
    if sample.size < _MIN_RANK_SAMPLE:
        return None
    return float(np.mean(sample <= float(value)))


def normalize_special_signal(percentile: float) -> float:
    """Map an empirical percentile in ``[0, 1]`` to ``[-1, +1]``."""

    return float(2.0 * percentile - 1.0)


def _norm_from_hist(value: float | None, hist: Sequence[float] | None) -> float | None:
    p = percentile_rank(value, hist)
    if p is None:
        return None
    return normalize_special_signal(p)


def _get_hist(cross_asset_data: dict[str, Any], key: str) -> list[float] | None:
    raw = cross_asset_data.get("hist")
    if not isinstance(raw, dict):
        return None
    v = raw.get(key)
    if not isinstance(v, list) or not v:
        return None
    return [float(x) for x in v if isinstance(x, (int, float)) and np.isfinite(x)]


def _tail_hist(cross_asset_data: dict[str, Any], key: str) -> list[float] | None:
    """Last ``_SPECIAL_RANK_WINDOW`` closes (or shorter if data is sparse)."""

    full = _get_hist(cross_asset_data, key)
    if full is None:
        return None
    if len(full) > _SPECIAL_RANK_WINDOW:
        return full[-_SPECIAL_RANK_WINDOW :]
    return full


def compute_special_signal(pair: str, cross_asset_data: dict[str, Any]) -> float | None:
    """Blend cross-asset proxies into a USD-strength score in ``[-1, +1]``.

    Requires ``cross_asset_data["hist"]`` from
    ``fetch_cross_asset(..., percentile_lookback=60)`` (or compatible length).
    Placeholder pairs return ``0.0``. Unknown pairs return ``None``.
    """

    key = normalize_fx_pair_key(pair)
    if key is None:
        return None

    if key in {"EURUSD", "GBPUSD"}:
        return 0.0

    if not isinstance(cross_asset_data.get("hist"), dict):
        return None

    # --- AUDUSD: commodity beta (AUD). High metals → AUD bid → USD weakness vs AUD.
    if key == "AUDUSD":
        iore = _tail_hist(cross_asset_data, "iron_ore")
        cup = _tail_hist(cross_asset_data, "copper")
        gld = _tail_hist(cross_asset_data, "gold")
        if iore is None or cup is None or gld is None:
            return None
        n_io = _norm_from_hist(iore[-1], iore)
        n_cu = _norm_from_hist(cup[-1], cup)
        n_au = _norm_from_hist(gld[-1], gld)
        if n_io is None or n_cu is None or n_au is None:
            return None
        composite = 0.40 * n_io + 0.35 * n_cu + 0.25 * n_au
        return float(-composite)

    # --- USDCAD: oil beta. Strong oil → CAD bid → USD weakness vs CAD.
    if key == "USDCAD":
        oil = _tail_hist(cross_asset_data, "oil")
        if oil is None or len(oil) < _MIN_RANK_SAMPLE + 1:
            return None
        n_wti = _norm_from_hist(oil[-1], oil)
        chg: list[float] = []
        for i in range(1, len(oil)):
            chg.append(float(oil[i]) - float(oil[i - 1]))
        if len(chg) < _MIN_RANK_SAMPLE:
            return None
        n_wcs = _norm_from_hist(chg[-1], chg)
        if n_wti is None or n_wcs is None:
            return None
        composite = 0.70 * n_wti + 0.30 * n_wcs
        return float(-composite)

    # --- USDCHF: EUR/CHF & SNB placeholders from USD basket geometry.
    if key == "USDCHF":
        dxy = _tail_hist(cross_asset_data, "dxy")
        if dxy is None or not dxy:
            return None
        clean = [float(x) for x in dxy if float(x) > 0.0]
        if len(clean) < _MIN_RANK_SAMPLE:
            return None
        latest = clean[-1]
        inv_hist = [1.0 / x for x in clean]
        inv_latest = 1.0 / latest
        n_eurchf = _norm_from_hist(inv_latest, inv_hist)
        n_snb = _norm_from_hist(latest, clean)
        if n_eurchf is None or n_snb is None:
            return None
        return float(0.60 * n_eurchf + 0.40 * n_snb)

    # --- USDJPY: funding stress proxy via VIX (high vol → JPY bid → USD weakness).
    if key == "USDJPY":
        vix = _tail_hist(cross_asset_data, "vix")
        if vix is None or not vix:
            return None
        n_vix = _norm_from_hist(vix[-1], vix)
        if n_vix is None:
            return None
        return float(-n_vix)

    # --- USDINR: crude + broad USD pressure on EM (Brent → WTI; RBI/EM → DXY & oil).
    if key == "USDINR":
        oil = _tail_hist(cross_asset_data, "oil")
        dxy = _tail_hist(cross_asset_data, "dxy")
        if oil is None or dxy is None:
            return None
        if len(oil) < _MIN_RANK_SAMPLE or len(dxy) < _MIN_RANK_SAMPLE:
            return None
        n_oil = _norm_from_hist(oil[-1], oil)
        n_dxy = _norm_from_hist(dxy[-1], dxy)
        if n_oil is None or n_dxy is None:
            return None
        n_em = 0.5 * (n_oil + n_dxy)
        return float(0.40 * n_oil + 0.35 * n_dxy + 0.25 * n_em)

    return None
