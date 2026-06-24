"""Recorded EUR/USD ingestion snapshot fixture for staged pipeline tests.

This fixture mirrors the shape returned by the production fetcher on a real
run date (2026-02-20). It is deterministic and free of external network calls.
"""

from __future__ import annotations

import datetime

from src.staged.contracts import IngestionSnapshot
from src.types import CotRow, SpotBar


def _spot_bar(pair: str, d: datetime.date, close: float) -> SpotBar:
    return SpotBar(
        date=d,
        pair=pair,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000_000.0,
    )


def _trading_date_range(start: datetime.date, days: int) -> list[datetime.date]:
    """Return ``days`` trading dates (Mon-Fri) starting from ``start``."""

    dates: list[datetime.date] = []
    current = start
    while len(dates) < days:
        if current.weekday() < 5:
            dates.append(current)
        current += datetime.timedelta(days=1)
    return dates


def make_recorded_eurusd_snapshot() -> IngestionSnapshot:
    """Return a recorded EUR/USD snapshot with enough history for signal math."""

    as_of = datetime.date(2026, 2, 20)
    start = datetime.date(2025, 12, 30)
    dates = _trading_date_range(start, 40)
    base = 1.0500
    bars: tuple[SpotBar, ...] = tuple(
        _spot_bar("EURUSD", d, round(base + i * 0.0005, 4))
        for i, d in enumerate(dates)
    )

    cot_rows: list[CotRow] = []
    cot_start = datetime.date(2025, 12, 16)
    for i in range(10):
        report_date = cot_start + datetime.timedelta(weeks=i)
        cot_rows.append(
            CotRow(
                date=report_date,
                pair="EURUSD",
                net_long=10_000 + i * 500,
                open_interest=50_000 + i * 1_000,
                asset_mgr_net=6_000 + i * 300,
                lev_money_net=-2_000 - i * 100,
            )
        )

    return IngestionSnapshot(
        date=as_of,
        spots={"EURUSD": bars},
        yields={
            "DGS2": 4.0,
            "ECBDFR": 2.0,
            "us_10y": 4.5,
            "de_10y": 2.5,
            "T10YIE": 2.0,
        },
        cot_rows=cot_rows,
        cross_asset={
            "vix": 18.0,
            "dxy": 104.0,
            "oil": 75.0,
            "gold": 2000.0,
            "copper": 4.0,
            "stoxx": 4500.0,
        },
        macro={
            "ecb_balance_sheet": 7000.0,
            "bund_btp_spread": 1.5,
        },
        dqs_score=0.95,
        stress_level="GREEN",
    )
