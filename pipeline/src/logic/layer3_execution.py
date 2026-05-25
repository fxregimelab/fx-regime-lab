"""Layer 3 execution HUD: vol rank, risk-reversal skew, entry timing, sizing, stops (Chamber 1).

**Volatility:** ``q^σ_t`` is the empirical CDF of 21d annualized realized vol vs a trailing
3y (756 session) causal window (computed upstream — see ``compute_realized_vol_rank_from_closes``).

**Skew / RR:** 25Δ risk reversal in vol points (bps of implied vol). Causal z-scores use only
``t-252 … t-1`` (cap 252) for ``(μ, σ)``; today's observation is scored out-of-sample against
that window. ``A_t ∈ {-1, 0, +1}`` aligns directional bias with ``sign(z_t)``.
``R_t`` (skew reversal) fires on a sign change in consecutive causal z-scores with both legs
material (|z| > ``_REVERSAL_Z_MIN``).

**Marcus rule (ENTER / WAIT):** No entry on neutral bias, low conviction, extreme realized-vol
rank, skew reversal, or strong directional skew contradiction unless conviction is high enough
to absorb the options-market disagreement.

**Lena rule + Chen dampener (FULL / HALF):** Full size only on elevated conviction, moderate
vol rank, non-negative skew alignment, and absence of crowding pressure (Chen dampener trims
size when crowding is active or the crowding penalty is material).

**Stop level:** Price level is ``S_t ∓ max(1.5 · ADR_{20}, MIE_proxy)`` where ADR is the mean
daily ``high - low`` and MIE proxy is the worst adverse excursion from the **open** against
the directional bias over the same 20-day lookback (long → ``open - low``; short → ``high - open``;
neutral → symmetric intraday envelope for the buffer input only — still no trade stop if bias is
neutral).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from src.types import (
    Layer2DirectionalBias,
    Layer2DirectionalOutput,
    Layer3EntryTiming,
    Layer3ExecutionOutput,
    Layer3PositionSize,
    SpotBar,
)

_VOL_RANK_ENTER_MAX = 0.88
_VOL_RANK_FULL_MAX = 0.70
_CONVICTION_ENTER_MIN = 3
_CONVICTION_FULL_MIN = 4
_REVERSAL_Z_MIN = 0.35
_STRONG_CONTRA_Z = 1.0
_CHEN_CROWD_PENALTY_HALF = 0.35
_RR_WINDOW = 252
_RR_MIN_CALIB = 30
_ADR_MIE_LOOKBACK = 20


def _mean(xs: list[float]) -> float:
    return math.fsum(xs) / len(xs)


def _std_pop(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = math.fsum((x - m) ** 2 for x in xs) / len(xs)
    return float(math.sqrt(var))


def causal_rr_z_pair(rr_series_ending_today: list[float]) -> tuple[float | None, float | None]:
    """v2.1: Returns None when real RR data is unavailable."""
    if not rr_series_ending_today or all(r is None for r in rr_series_ending_today):
        return None, None
    if len(rr_series_ending_today) < _RR_MIN_CALIB + 2:
        return None, None

    def z_at_end(vals: list[float]) -> float | None:
        if len(vals) < _RR_MIN_CALIB + 1:
            return None
        cur = vals[-1]
        past = vals[:-1]
        win = past[-_RR_WINDOW:] if len(past) >= _RR_WINDOW else past
        if len(win) < _RR_MIN_CALIB:
            return None
        sig = _std_pop(win)
        if sig <= 1e-12:
            return None
        return (cur - _mean(win)) / sig

    z_t = z_at_end(rr_series_ending_today)
    z_y = z_at_end(rr_series_ending_today[:-1])
    return z_t, z_y


def skew_bias_alignment(bias: Layer2DirectionalBias, rr_z: float | None) -> int:
    """``A_t`` per Chamber 1: ``sign(b) · sign(z)`` mapped to ``{-1, 0, +1}``."""

    if bias == "NEUTRAL" or rr_z is None:
        return 0
    b = 1 if bias == "LONG" else -1
    zf = float(rr_z)
    if abs(zf) < 1e-12:
        return 0
    s = 1 if zf > 0 else -1
    prod = b * s
    return 1 if prod > 0 else -1


def skew_reversal_flag(rr_z_t: float | None, rr_z_y: float | None) -> bool:
    """``R_t``: sign flip across sessions in causal RR z-scores (both legs material)."""

    if rr_z_t is None or rr_z_y is None:
        return False
    if abs(rr_z_t) <= _REVERSAL_Z_MIN or abs(rr_z_y) <= _REVERSAL_Z_MIN:
        return False
    return rr_z_t * rr_z_y < 0


def average_daily_range(spot_bars: Sequence[SpotBar], lookback: int) -> float | None:
    if not spot_bars:
        return None
    n = min(lookback, len(spot_bars))
    recent = spot_bars[-n:]
    ranges = [max(0.0, float(b.high) - float(b.low)) for b in recent]
    if not ranges:
        return None
    return math.fsum(ranges) / len(ranges)


def mie_proxy_points(
    spot_bars: Sequence[SpotBar],
    bias: Layer2DirectionalBias,
    lookback: int,
) -> float | None:
    """MIE proxy (price points): worst case intraday move **against** a
    directional from the open."""

    if not spot_bars:
        return None
    n = min(lookback, len(spot_bars))
    recent = spot_bars[-n:]
    adverse: list[float] = []
    for b in recent:
        o, hi, lo = float(b.open), float(b.high), float(b.low)
        if bias == "LONG":
            adverse.append(max(0.0, o - lo))
        elif bias == "SHORT":
            adverse.append(max(0.0, hi - o))
        else:
            adverse.append(max(max(0.0, o - lo), max(0.0, hi - o)))
    return max(adverse) if adverse else None


def stop_buffer_and_level(
    spot: float | None,
    bias: Layer2DirectionalBias,
    adr: float | None,
    mie: float | None,
) -> tuple[float | None, float | None]:
    """``max(1.5·ADR, MIE)`` buffer and stop **price** (long below, short above)."""

    if spot is None or bias == "NEUTRAL":
        return None, None
    parts: list[float] = []
    if adr is not None and adr > 0:
        parts.append(1.5 * adr)
    if mie is not None and mie > 0:
        parts.append(mie)
    if not parts:
        return None, None
    buf = max(parts)
    s = float(spot)
    if bias == "LONG":
        return buf, s - buf
    return buf, s + buf


def run_layer3_execution(
    *,
    layer2: Layer2DirectionalOutput,
    spot: float | None,
    spot_bars: Sequence[SpotBar],
    realized_vol_rank: float | None,
    risk_reversal_series_bps: tuple[float, ...],
) -> Layer3ExecutionOutput:
    """Compose Layer 3 from Layer 2 plus vol / RR / microstructure inputs."""

    bias: Layer2DirectionalBias = layer2["directional_bias"]
    conviction = int(layer2["conviction"])

    rr_list = list(risk_reversal_series_bps)
    z_t, z_y = causal_rr_z_pair(rr_list) if len(rr_list) >= _RR_MIN_CALIB + 2 else (None, None)
    align = skew_bias_alignment(bias, z_t)
    rev = skew_reversal_flag(z_t, z_y)

    adr = average_daily_range(spot_bars, _ADR_MIE_LOOKBACK)
    mie = mie_proxy_points(spot_bars, bias, _ADR_MIE_LOOKBACK)
    buf, stop_px = stop_buffer_and_level(spot, bias, adr, mie)

    strong_contra = (
        z_t is not None
        and align == -1
        and abs(float(z_t)) > _STRONG_CONTRA_Z
        and conviction < _CONVICTION_FULL_MIN
    )

    vol_too_hot = realized_vol_rank is None or float(realized_vol_rank) > _VOL_RANK_ENTER_MAX

    # v2.1: No RR data available — skip skew-based rules
    if z_t is None:
        enter_ok = (
            bias != "NEUTRAL"
            and conviction >= _CONVICTION_ENTER_MIN
            and not vol_too_hot
        )
    else:
        enter_ok = (
            bias != "NEUTRAL"
            and conviction >= _CONVICTION_ENTER_MIN
            and not vol_too_hot
            and not rev
            and not strong_contra
        )
    timing: Layer3EntryTiming = "ENTER" if enter_ok else "WAIT"

    chen_trim = bool(layer2["crowd_flag"]) or (
        float(layer2["crowd_penalty"]) > _CHEN_CROWD_PENALTY_HALF
    )
    # v2.1: Without RR data, skip alignment check
    if z_t is None:
        full_ok = (
            timing == "ENTER"
            and conviction >= _CONVICTION_FULL_MIN
            and realized_vol_rank is not None
            and float(realized_vol_rank) <= _VOL_RANK_FULL_MAX
            and not chen_trim
        )
    else:
        full_ok = (
            timing == "ENTER"
            and conviction >= _CONVICTION_FULL_MIN
            and realized_vol_rank is not None
            and float(realized_vol_rank) <= _VOL_RANK_FULL_MAX
            and align >= 0
            and not chen_trim
        )
    size: Layer3PositionSize = "FULL" if full_ok else "HALF"

    out: Layer3ExecutionOutput = {
        "entry_timing": timing,
        "position_size": size,
        "stop_level": stop_px,
        "realized_vol_rank": realized_vol_rank,
        "skew_alignment": align,
        "skew_reversal_flag": rev,
        "risk_reversal_z": z_t,
        "adr": adr,
        "mie_proxy": mie,
        "stop_buffer": buf,
    }
    return out
