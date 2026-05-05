from __future__ import annotations

from datetime import date, timedelta


def add_trading_days(start_date: date, n: int) -> date:
    """Add n trading days to start_date, skipping weekends (Sat/Sun).

    FX markets trade Mon-Fri. For T+5 and T+20 horizons, we skip weekends.
    n must be >= 0.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    current = start_date
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri
            added += 1
    return current
