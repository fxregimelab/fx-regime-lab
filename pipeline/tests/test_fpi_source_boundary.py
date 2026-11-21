"""Unqualified flow amounts cannot become current signal evidence."""

from datetime import date

import pytest

from src.core.ingestion_snapshot import IngestionSnapshot
from src.core.regime_call_builder import RegimeCallBuilder
from src.signals.fpi import normalize_fpi_signal
from src.types import SpotBar


@pytest.mark.parametrize("pair", ["EURUSD", "USDJPY", "USDINR"])
@pytest.mark.parametrize("case", ["raw", "score", "absent", "flat", "flat_extreme"])
def test_fpi_source_boundary(pair: str, case: str) -> None:
    if case.startswith("flat"):
        latest = 42.0 if case == "flat" else 1000000.0
        assert normalize_fpi_signal(latest, [42.0] * 20) is None
        return
    day = date(2026, 9, 25)
    bar = SpotBar(date=day, pair=pair, open=1, high=1, low=1, close=1, volume=0)
    builder = RegimeCallBuilder(
        IngestionSnapshot(date=day, spots={pair: [bar]}, yields={}, cot_rows=[], cross_asset={})
    )
    if case == "absent":
        assert builder.build_signal_row(pair).fpi_flow is None
    elif case == "raw":
        with pytest.raises(ValueError, match="qualified dated source evidence"):
            builder.build_signal_row(pair, fpi_raw={"fpi_total_net_cr": 0.0})
    else:
        with pytest.raises(ValueError, match="qualified dated source evidence"):
            builder.build_signal_row(pair, fpi_signal=0.0)
