"""COT positioning signal."""

from __future__ import annotations

from src.types import CotRow


def compute_cot_percentile(rows: list[CotRow], pair: str, window: int = 52) -> float | None:
    filtered = [r for r in rows if r.pair == pair]
    filtered.sort(key=lambda r: r.date)
    if len(filtered) < 4:
        return None
    window_rows = filtered[-window:]
    vals = [r.net_long for r in window_rows]
    last = vals[-1]
    pct = 100.0 * sum(1 for v in vals if v <= last) / float(len(vals))
    return float(pct)


def normalize_cot_signal(percentile: float) -> float:
    return float((percentile - 50.0) / 50.0)
