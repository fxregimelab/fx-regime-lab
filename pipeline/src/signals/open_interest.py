"""Open interest signal from COT-derived OI percentile."""


def compute_oi_signal(oi_percentile: float | None) -> float | None:
    """
    Normalize OI percentile (0-100) to [-1, +1].
    High OI (>80th pct) → crowded, contrarian signal → negative.
    Low OI (<20th pct) → low conviction → near 0.
    Returns None when no data.
    """
    if oi_percentile is None:
        return None
    normalized = (oi_percentile - 50.0) / 50.0  # maps 0-100 → -1 to +1
    return float(max(-1.0, min(1.0, -normalized)))  # invert: high OI = crowded = bearish signal
