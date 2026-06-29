"""Unit tests for signal family adapters."""

from __future__ import annotations

import datetime

import pytest

from src.staged.contracts import IngestionSnapshot
from src.staged.signals.cot_family import CotFamily
from src.staged.signals.rate_family import RateFamily
from src.staged.signals.rate_history import SinglePointFallbackProvider
from src.staged.signals.special_family import SpecialFamily
from src.staged.signals.types import FamilyOutput
from src.staged.signals.vol_family import VolFamily
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


def _trading_dates(start: datetime.date, days: int) -> list[datetime.date]:
    dates: list[datetime.date] = []
    current = start
    while len(dates) < days:
        if current.weekday() < 5:
            dates.append(current)
        current += datetime.timedelta(days=1)
    return dates


@pytest.fixture
def eurusd_snapshot() -> IngestionSnapshot:
    as_of = datetime.date(2026, 5, 20)
    dates = _trading_dates(datetime.date(2026, 3, 30), 40)
    bars = tuple(
        _spot_bar("EURUSD", d, round(1.0800 + i * 0.0005, 4))
        for i, d in enumerate(dates)
    )
    cot_rows = [
        CotRow(
            date=datetime.date(2026, 3, 17) + datetime.timedelta(weeks=i),
            pair="EURUSD",
            net_long=10_000 + i * 500,
            open_interest=50_000 + i * 1_000,
            asset_mgr_net=6_000 + i * 300,
            lev_money_net=-2_000 - i * 100,
        )
        for i in range(10)
    ]
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
        macro={"ecb_balance_sheet": 7000.0, "bund_btp_spread": 1.5},
        dqs_score=0.95,
        stress_level="GREEN",
    )


def test_rate_family_produces_spreads_and_norms(eurusd_snapshot: IngestionSnapshot) -> None:
    vol = VolFamily().compute("EURUSD", eurusd_snapshot)
    rv20 = vol.vol.rv20 if vol.vol else None
    out = RateFamily(history_provider=SinglePointFallbackProvider()).compute(
        "EURUSD", eurusd_snapshot, rv20=rv20
    )
    assert out.rate is not None
    assert out.rate.spread_2y == pytest.approx(2.0)
    assert out.rate.spread_10y == pytest.approx(2.0)
    assert out.rate.spread_10y_real == pytest.approx(0.0)
    assert out.rate.norm_z.z_tactical is not None
    assert out.rate.direction in ("BULLISH", "BEARISH", "NEUTRAL")


def test_cot_family_produces_percentile_and_oi(eurusd_snapshot: IngestionSnapshot) -> None:
    out = CotFamily().compute("EURUSD", eurusd_snapshot)
    assert out.cot is not None
    assert out.cot.percentile is not None
    assert out.cot.norm is not None
    assert out.cot.days_since_cot >= 0
    assert out.cot.net_pos is not None


def test_vol_family_produces_rv_and_rank(eurusd_snapshot: IngestionSnapshot) -> None:
    out = VolFamily().compute("EURUSD", eurusd_snapshot)
    assert out.vol is not None
    assert out.vol.rv20 is not None
    assert out.vol.rv5 is not None
    assert out.vol.vol_norm is not None


def test_special_family_eurusd(eurusd_snapshot: IngestionSnapshot) -> None:
    out = SpecialFamily().compute("EURUSD", eurusd_snapshot)
    assert out.special is not None
    assert out.special.signal is not None


def test_family_output_merge() -> None:
    from src.signals.rate import RateNormZ
    from src.staged.signals.types import CotFamilyOutput, RateFamilyOutput

    merged = FamilyOutput.merge(
        FamilyOutput(
            rate=RateFamilyOutput(
                spread_2y=2.0,
                spread_10y=2.0,
                spread_10y_real=0.0,
                norm_z=RateNormZ(z_tactical=0.0, z_structural=0.0, z_blended=0.0),
                direction="NEUTRAL",
                risk_adjusted_carry=1.0,
                breakeven_inflation_10y=2.0,
            ),
            cot=None,
            vol=None,
            special=None,
        ),
        FamilyOutput(
            rate=None,
            cot=CotFamilyOutput(
                percentile=0.5,
                norm=0.0,
                oi_norm=0.0,
                oi_delta=0,
                net_pos=100,
                asset_mgr_net=50,
                lev_money_net=-50,
                days_since_cot=3,
            ),
            vol=None,
            special=None,
            health_notes=("note_a",),
        ),
    )
    assert merged.rate is not None
    assert merged.cot is not None
    assert merged.health_notes == ("note_a",)
