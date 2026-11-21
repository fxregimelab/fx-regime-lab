"""
@agent_context: Calculates Commitment of Traders (COT) positioning signals
using percentile ranking and normalization.
@allowed_imports: [src.types]
@forbidden_imports: [src.db, src.ai]
@obsidian_link: [[Signal Generation#COT Positioning]]
"""

from __future__ import annotations

from datetime import date

from src.types import CotRow

# ~3 years of weekly COT reports (Chamber 1 / Phase 2 spec).
COT_PERCENTILE_WINDOW_REPORTS: int = 156
COT_PERCENTILE_MIN_REPORTS: int = 8


def compute_cot_percentile(
    rows: list[CotRow],
    pair: str,
    *,
    window_reports: int = COT_PERCENTILE_WINDOW_REPORTS,
    as_of: date | None = None,
    min_reports: int = COT_PERCENTILE_MIN_REPORTS,
) -> float | None:
    """Strictly causal empirical percentile of the latest **net long** vs trailing COT history.

    Uses the last ``window_reports`` distinct report dates for ``pair`` (default 156 ≈ 3Y weekly).
    The current observation is excluded from the reference distribution (strictly causal).
    Missing publication weeks simply shorten the effective calendar span; only reports with
    ``date <= as_of`` enter the window when ``as_of`` is set (no look-ahead). If ``as_of`` is
    ``None``, all rows are eligible and the anchor row is the latest available date for the pair.
    """

    filtered = [r for r in rows if r.pair == pair]
    if as_of is not None:
        filtered = [r for r in filtered if r.date <= as_of]
    if not filtered:
        return None
    # Collapse duplicate report dates: last write wins (institutional tie-break).
    by_report_date: dict[date, CotRow] = {}
    for r in filtered:
        by_report_date[r.date] = r
    chronological = [by_report_date[d] for d in sorted(by_report_date)]
    window_rows = chronological[-window_reports:]
    # Need min_reports historical points AFTER excluding the current observation.
    if len(window_rows) < min_reports + 1:
        return None
    vals = [r.net_long for r in window_rows]
    last = vals[-1]
    hist = vals[:-1]  # Exclude current observation
    n = len(hist)
    if n == 0:
        return None
    pct = 100.0 * sum(1 for v in hist if v <= last) / float(n)
    return float(pct)


def compute_cot_smart_spread_percentile(
    rows: list[CotRow],
    pair: str,
    *,
    window_reports: int = COT_PERCENTILE_WINDOW_REPORTS,
    as_of: date | None = None,
    min_reports: int = COT_PERCENTILE_MIN_REPORTS,
) -> float | None:
    """Causal percentile of Asset Manager net minus Leveraged Money net.

    The latest eligible report is the current observation and is excluded
    from the reference distribution. Reports without both categories are not
    substituted with another positioning measure.
    """

    filtered = [r for r in rows if r.pair == pair]
    if as_of is not None:
        filtered = [r for r in filtered if r.date <= as_of]
    if not filtered:
        return None
    by_report_date: dict[date, tuple[int | None, int | None]] = {}
    conflicting_dates: set[date] = set()
    for r in filtered:
        category_values = (r.asset_mgr_net, r.lev_money_net)
        if r.date in by_report_date and by_report_date[r.date] != category_values:
            conflicting_dates.add(r.date)
        else:
            by_report_date[r.date] = category_values

    window_dates = sorted(by_report_date)[-window_reports:]
    if not window_dates or any(d in conflicting_dates for d in window_dates):
        return None

    current_am, current_lm = by_report_date[window_dates[-1]]
    if current_am is None or current_lm is None:
        return None

    hist: list[float] = []
    for report_date in window_dates[:-1]:
        am, lm = by_report_date[report_date]
        if am is not None and lm is not None:
            hist.append(float(am) - float(lm))

    if not hist or len(hist) < min_reports:
        return None

    last = float(current_am) - float(current_lm)
    n = len(hist)
    pct = 100.0 * sum(1 for v in hist if v <= last) / float(n)
    return float(pct)


def normalize_cot_signal(percentile: float | None) -> float | None:
    """Map percentile to roughly [-1, 1] around the median; ``None`` in → ``None`` out."""

    if percentile is None:
        return None
    return float((percentile - 50.0) / 50.0)
