"""Point-in-time spot history cannot depend on future or malformed rows."""

from __future__ import annotations

import datetime
import math

import pytest

from src.core.spot_history import SpotHistoryError, select_spot_history, strict_date
from src.staged.contracts import IngestionSnapshot
from src.staged.stages.signal_stage import SignalStage
from src.types import SpotBar


def _bar(
    day: int,
    close: float,
    *,
    pair: str = "EURUSD",
    high: float | None = None,
    low: float | None = None,
    volume: float = 1.0,
) -> SpotBar:
    return SpotBar(
        date=datetime.date(2026, 1, day),
        pair=pair,
        open=close,
        high=close if high is None else high,
        low=close if low is None else low,
        close=close,
        volume=volume,
    )


def test_selection_is_sorted_deduplicated_and_causally_fenced() -> None:
    earlier = _bar(13, 1.0)
    latest = _bar(15, 1.2)
    future = _bar(16, 9.0)

    selected = select_spot_history(
        (future, latest, earlier, earlier),
        pair="EURUSD",
        as_of=datetime.date(2026, 1, 15),
    )

    assert selected == (earlier, latest)
    assert selected[0] is earlier
    assert selected[1] is latest


@pytest.mark.parametrize(
    "bars",
    [
        (_bar(15, math.nan),),
        (_bar(15, 1.0, high=0.9),),
        (_bar(15, 1.0, volume=-1.0),),
        (_bar(15, 1.0, pair="USDJPY"),),
    ],
)
def test_invalid_or_mismatched_rows_fail_closed(bars: tuple[SpotBar, ...]) -> None:
    with pytest.raises(SpotHistoryError):
        select_spot_history(
            bars,
            pair="EURUSD",
            as_of=datetime.date(2026, 1, 15),
        )


def test_conflicting_same_day_rows_fail_closed_in_any_order() -> None:
    first = _bar(15, 1.0)
    second = _bar(15, 1.1)

    for bars in ((first, second), (second, first)):
        with pytest.raises(SpotHistoryError, match="Conflicting EURUSD spot rows"):
            select_spot_history(
                bars,
                pair="EURUSD",
                as_of=datetime.date(2026, 1, 15),
            )


@pytest.mark.parametrize(
    "value",
    [
        "2026-01-15T00:00:00Z",
        "2026-01-15 trailing text",
        datetime.datetime(2026, 1, 15),
    ],
)
def test_strict_date_rejects_timestamps_and_trailing_text(value: object) -> None:
    with pytest.raises(SpotHistoryError, match="exact YYYY-MM-DD"):
        strict_date(value)


def test_signal_stage_uses_only_ordered_rows_through_as_of() -> None:
    as_of = datetime.date(2026, 1, 15)
    snapshot = IngestionSnapshot(
        date=as_of,
        spots={
            "EURUSD": (
                _bar(16, 9.0),
                _bar(15, 1.2),
                _bar(14, 1.0),
            )
        },
        yields={},
        cot_rows=[],
        cross_asset={},
        macro={"ecb_balance_sheet": 7000.0},
    )

    result = SignalStage().run("EURUSD", snapshot)

    assert result.signal_row.spot == 1.2
    assert result.signal_row.day_change == pytest.approx(0.2)
    assert result.signal_row.day_change_pct == pytest.approx(20.0)


def test_signal_stage_rejects_missing_earlier_observation() -> None:
    as_of = datetime.date(2026, 1, 15)
    snapshot = IngestionSnapshot(
        date=as_of,
        spots={"EURUSD": (_bar(15, 1.2), _bar(16, 9.0))},
        yields={},
        cot_rows=[],
        cross_asset={},
    )

    with pytest.raises(ValueError, match="two causal spot observations"):
        SignalStage().run("EURUSD", snapshot)
