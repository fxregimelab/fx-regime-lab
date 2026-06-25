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
    """Empirical CDF rank of ``value`` on a strictly causal ``history``.

    ``history`` must contain ONLY past observations (the current print must NOT
    be included). Returns a percentile in ``[0, 1]``, or ``None`` if the sample
    is too thin or invalid.
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


def _scalar_eur_btp(bund_btp_spread: float | None) -> float | None:
    """Map Bund-BTP spread to [-1, +1]; negative spread = fragmentation = EUR weakness.

    Returns the same convention as normalize_special_signal: negative when
    spread is wide (EUR weak / USD strong) so that -n_btp in the caller
    yields a positive contribution.
    """
    if bund_btp_spread is None:
        return None
    # Typical range: -3 to +2.  Negative = BTP wider = EUR weakness.
    # Match normalize_special_signal convention: low/negative for extreme weakness.
    return float(max(-1.0, min(1.0, (bund_btp_spread + 0.5) / 2.5)))


def _scalar_eur_ecb(ecb_balance_sheet: float | None) -> float | None:
    """Map ECB balance sheet (billions EUR) to [-1, +1]; high = QE = USD strength."""
    if ecb_balance_sheet is None:
        return None
    # Typical range: 4000-9000.  High = EUR weakness.
    return float(max(-1.0, min(1.0, (ecb_balance_sheet - 6000.0) / 3000.0)))


def compute_special_signal(
    pair: str,
    cross_asset_data: dict[str, Any],
    *,
    bund_btp_spread: float | None = None,
    ecb_balance_sheet: float | None = None,
) -> float | None:
    """Blend cross-asset proxies into a USD-strength score in ``[-1, +1]``.

    Requires ``cross_asset_data["hist"]`` from
    ``fetch_cross_asset(..., percentile_lookback=60)`` (or compatible length).
    Placeholder pairs return ``0.0``. Unknown pairs return ``None``.

    EURUSD accepts ``bund_btp_spread`` and ``ecb_balance_sheet`` as scalar
    overrides when history is unavailable.

    Real special signals available for: EURUSD, USDJPY, USDINR.
    """

    key = normalize_fx_pair_key(pair)
    if key is None:
        return None

    # --- EURUSD: fragmentation risk + ECB balance sheet expansion.
    if key == "EURUSD":
        # Try history-based percentiles first; fall back to scalar mapping.
        bund_btp = _tail_hist(cross_asset_data, "bund_btp_spread")
        ecb_bs = _tail_hist(cross_asset_data, "ecb_balance_sheet")
        n_btp: float | None = None
        n_ecb: float | None = None
        if bund_btp is not None and len(bund_btp) >= _MIN_RANK_SAMPLE + 1:
            n_btp = _norm_from_hist(bund_btp[-1], bund_btp[:-1])
        if ecb_bs is not None and len(ecb_bs) >= _MIN_RANK_SAMPLE + 1:
            n_ecb = _norm_from_hist(ecb_bs[-1], ecb_bs[:-1])
        # History unavailable → use scalar kwargs.
        if n_btp is None:
            n_btp = _scalar_eur_btp(bund_btp_spread)
        if n_ecb is None:
            n_ecb = _scalar_eur_ecb(ecb_balance_sheet)
        if n_btp is None and n_ecb is None:
            return None
        # bund_btp: negative spread = low percentile = negative n_btp → negate for USD strength
        # ecb_bs: high = high percentile = positive n_ecb → keep for USD strength
        btp_contrib = -n_btp if n_btp is not None else 0.0
        ecb_contrib = n_ecb if n_ecb is not None else 0.0
        available = (1.0 if n_btp is not None else 0.0) + (1.0 if n_ecb is not None else 0.0)
        if available == 0.0:
            return None
        composite = (btp_contrib + ecb_contrib) / available
        return float(max(-1.0, min(1.0, composite)))

    if not isinstance(cross_asset_data.get("hist"), dict):
        return None

    # --- USDJPY: funding stress proxy via VIX (high vol → JPY bid → USD weakness).
    if key == "USDJPY":
        vix = _tail_hist(cross_asset_data, "vix")
        if vix is None or not vix:
            return None
        n_vix = _norm_from_hist(vix[-1], vix[:-1])
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
        n_oil = _norm_from_hist(oil[-1], oil[:-1])
        n_dxy = _norm_from_hist(dxy[-1], dxy[:-1])
        if n_oil is None or n_dxy is None:
            return None
        n_em = 0.5 * (n_oil + n_dxy)
        return float(0.40 * n_oil + 0.35 * n_dxy + 0.25 * n_em)

    return None
