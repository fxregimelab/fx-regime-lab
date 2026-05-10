"""Confidence score from composite magnitude and signal agreement.

Confidence is NOT a probability of being correct. It is an internal consistency
metric: how strong and coherent the composite signal is. Stronger composites
with agreeing sub-signals receive higher confidence. Mixed or weak signals
receive lower confidence.

Formula (v2):
  base = |composite| / 2.0                     # signal strength in [0, 1]
  align_bonus = +0.05 if rate/cot agree        # directional alignment
  strength_bonus = +0.05 if both |rate|,|cot| > 0.3  # both materially non-zero
  pair_adj = pair-specific adjustment          # e.g. JPY carry, INR oil
  raw = clip(base + align_bonus + strength_bonus + pair_adj, 0.30, 0.95)
  confidence = clip(raw - 0.03, 0.30, 0.90)   # institutional -3pp haircut
"""

from __future__ import annotations

import numpy as np

from src.types import normalize_fx_pair_key


def compute_confidence(
    composite: float,
    rate_norm: float | None,
    cot_norm: float | None,
    *,
    pair: str | None = None,
    special_signal: float | None = None,
    commodity_components_agree: bool | None = None,
    wti_wcs_agree: bool | None = None,
    brent_above_p80: bool | None = None,
) -> float:
    """Return confidence in [0.30, 0.90] from composite strength and signal coherence."""
    # Base confidence = signal strength (|composite| / 2.0).
    # Composite is clipped to [-2, 2] upstream; typical range is [-1, 1].
    base_conf = float(np.clip(abs(float(composite)) / 2.0, 0.10, 0.90))

    # Alignment bonus: rate and COT point the same way.
    bonus = 0.0
    if rate_norm is not None and cot_norm is not None:
        if (rate_norm > 0 and cot_norm > 0) or (rate_norm < 0 and cot_norm < 0):
            bonus += 0.05
        if abs(rate_norm) > 0.3 and abs(cot_norm) > 0.3:
            bonus += 0.05

    pair_adj = 0.0
    key = normalize_fx_pair_key(pair)
    if key == "USDJPY":
        if special_signal is not None and special_signal > 0.5:
            pair_adj += 0.05
    elif key == "GBPUSD":
        if special_signal is not None and special_signal > 0.5:
            pair_adj -= 0.05
    elif key == "AUDUSD":
        if commodity_components_agree is True:
            pair_adj += 0.05
    elif key == "USDCAD":
        if wti_wcs_agree is True:
            pair_adj += 0.05
    elif key == "USDCHF":
        if special_signal is not None and abs(special_signal) > 0.5:
            pair_adj -= 0.10
    elif key == "USDINR":
        if brent_above_p80 is True:
            pair_adj -= 0.05

    raw = float(np.clip(base_conf + bonus + pair_adj, 0.30, 0.95))
    # Institutional −3pp haircut (under-promise / over-deliver).
    return float(np.clip(raw - 0.03, 0.30, 0.90))
