"""Layer 2 directional conviction: COT percentile, crowding ramp, conviction
multiplier, Marcus B clash, composite-informed direction.
"""

from __future__ import annotations

from src.types import Layer2DirectionalBias, Layer2DirectionalOutput

_CROWD_SOFT_HI = 90.0
_CROWD_SOFT_LO = 10.0
_CROWD_VETO_HI = 97.0
_CROWD_VETO_LO = 3.0
_Z_EPS = 0.12
_POS_DEADBAND = 5.0
_COMPOSITE_STRONG = 0.30


def _phi_upper_tail(pi: float) -> float:
    """Smooth unit ramp from 90th → 100th percentile (upper crowding)."""

    if pi <= _CROWD_SOFT_HI:
        return 0.0
    return min(1.0, (pi - _CROWD_SOFT_HI) / 10.0)


def _phi_lower_tail(pi: float) -> float:
    """Smooth unit ramp from 10th → 0th percentile (lower tail / crowded short)."""

    if pi >= _CROWD_SOFT_LO:
        return 0.0
    return min(1.0, (_CROWD_SOFT_LO - pi) / 10.0)


def crowding_metrics_pi(pi: float | None) -> tuple[float, bool, bool]:
    """Return ``(p_crowd, crowd_flag, crowd_veto)`` for positioning percentile ``pi``."""

    if pi is None:
        return 0.0, False, False
    p_crowd = max(_phi_upper_tail(float(pi)), _phi_lower_tail(float(pi)))
    crowd_flag = float(pi) >= _CROWD_SOFT_HI or float(pi) <= _CROWD_SOFT_LO
    crowd_veto = float(pi) >= _CROWD_VETO_HI or float(pi) <= _CROWD_VETO_LO
    return float(p_crowd), bool(crowd_flag), bool(crowd_veto)


def marcus_b_rate_positioning_clash(rate_sign: int, pos_sign: int) -> bool:
    """Marcus B (clash veto): strong rate view vs strong opposing positioning."""

    if rate_sign == 0 or pos_sign == 0:
        return False
    return rate_sign * pos_sign < 0


def composite_rate_clash(composite: float | None, rate_sign: int) -> bool:
    """Marcus C: composite strongly disagrees with rate direction."""

    if composite is None or rate_sign == 0:
        return False
    comp_sign = 1 if composite > _COMPOSITE_STRONG else (
        -1 if composite < -_COMPOSITE_STRONG else 0
    )
    if comp_sign == 0:
        return False
    return comp_sign * rate_sign < 0


def effective_rate_sign(
    rate_direction: str,
    z_tactical: float | None,
    z_structural: float | None,
) -> int:
    """Prefer clipped robust Z when informative; otherwise futures-style BULLISH/BEARISH string."""

    z = z_tactical if z_tactical is not None else z_structural
    if z is not None:
        zf = float(z)
        if zf > _Z_EPS:
            return 1
        if zf < -_Z_EPS:
            return -1
    rd = rate_direction.strip().upper()
    if rd == "BULLISH":
        return 1
    if rd == "BEARISH":
        return -1
    return 0


def positioning_sign_pi(pi: float | None) -> int:
    """Discrete positioning tilt from median (dead band around 50 avoids twitch)."""

    if pi is None:
        return 0
    pf = float(pi)
    if pf > 50.0 + _POS_DEADBAND:
        return 1
    if pf < 50.0 - _POS_DEADBAND:
        return -1
    return 0


def conviction_multiplier_pi(
    pi: float | None,
    p_crowd: float,
    rate_sign: int,
    pos_sign: int,
) -> float:
    """Conviction multiplier m_π: penalizes crowding and misalignment."""

    if rate_sign == 0 or pos_sign == 0:
        align = 1.0
    else:
        align = 1.0 if rate_sign == pos_sign else 0.72
    m = (1.0 - 0.48 * float(p_crowd)) * align
    if pi is None:
        m *= 0.88
    return float(max(0.52, min(1.08, m)))


def _bias_label_from_sign(sign: int) -> Layer2DirectionalBias:
    if sign > 0:
        return "LONG"
    if sign < 0:
        return "SHORT"
    return "NEUTRAL"


def run_layer2_directional(
    *,
    composite: float | None,
    z_tactical: float | None,
    z_structural: float | None,
    rate_direction: str,
    positioning_percentile: float | None,
    layer1_invalidated: bool,
) -> Layer2DirectionalOutput:
    """Chamber 1 Layer 2: π, crowding, m_π, integer conviction, Marcus B bias.

    Direction logic (v2):
      1. If Layer1 invalidated / crowd veto / Marcus B clash / composite-rate clash → NEUTRAL.
      2. If composite is materially non-zero (|S| > 0.30), composite drives direction.
      3. Otherwise rate sign drives direction.
      4. If both composite and rate are neutral → NEUTRAL.

    This prevents the model from making directional calls when the composite
    (which subsumes rate, COT, vol, OI) strongly disagrees with the rate signal alone.
    """

    p_crowd, crowd_flag, crowd_veto = crowding_metrics_pi(positioning_percentile)
    if layer1_invalidated:
        rate_s = 0
    else:
        rate_s = effective_rate_sign(rate_direction, z_tactical, z_structural)
    pos_s = positioning_sign_pi(positioning_percentile)
    clash_b = marcus_b_rate_positioning_clash(rate_s, pos_s)
    clash_c = composite_rate_clash(composite, rate_s)
    m_pi = conviction_multiplier_pi(positioning_percentile, p_crowd, rate_s, pos_s)

    if composite is not None:
        comp_clip = max(-2.0, min(2.0, float(composite)))
        base_c = 3.0 + comp_clip
    else:
        base_c = 2.35

    c_float = float(base_c) * float(m_pi)
    if layer1_invalidated or crowd_veto or clash_b or clash_c:
        c_float = min(c_float, 3.0)
    c_float = max(1.0, min(5.0, c_float))
    conviction = int(round(c_float))
    conviction = max(1, min(5, conviction))

    # Direction: composite wins when strong; otherwise rate; clash → neutral.
    bias: Layer2DirectionalBias
    if layer1_invalidated or crowd_veto or clash_b or clash_c:
        bias = "NEUTRAL"
    elif composite is not None and abs(composite) > _COMPOSITE_STRONG:
        bias = _bias_label_from_sign(1 if composite > 0 else -1)
    elif rate_s > 0:
        bias = "LONG"
    elif rate_s < 0:
        bias = "SHORT"
    else:
        bias = "NEUTRAL"

    out: Layer2DirectionalOutput = {
        "positioning_percentile": positioning_percentile,
        "crowd_flag": crowd_flag,
        "crowd_penalty": p_crowd,
        "crowd_veto": crowd_veto,
        "conviction_multiplier": m_pi,
        "conviction": conviction,
        "directional_bias": bias,
        "rate_positioning_clash": clash_b,
    }
    return out
