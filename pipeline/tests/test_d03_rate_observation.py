"""Deterministic D03 rate timing and provenance controls; no provider network."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from src.core.ingestion_snapshot import IngestionSnapshot
from src.fetchers import yields
from src.fetchers.buffer_keys import (
    KEY_FX_SPOT,
    KEY_RATE_DECISION_AT,
    KEY_YIELD_OBSERVATIONS,
    KEY_YIELDS,
)
from src.scheduler.orchestrator import _rate_spread_2y_for_pair
from src.signals import rate_inputs
from src.signals.rate_observation import (
    RateObservation,
    qualified_rate_value,
    qualified_two_year_spread,
)
from src.staged.stages.signal_stage import _rate_spread_2y
from src.types import SpotBar
from src.validation.ingestion_buffer import _rates_bucket_freshness

AS_OF = datetime(2026, 9, 29, 15, tzinfo=UTC)
EUR_ID = "FIXTURE_EUR_2Y"
DEFINITIONS = {
    **rate_inputs.SOURCE_DEFINITIONS,
    EUR_ID: rate_inputs.RateInstrument("EUR", 2, "government_yield", "daily"),
}
SOURCE_IDS = (EUR_ID, "DGS2")


def _observation(
    source_id: str,
    value: float | None,
    *,
    observed_on: date = date(2026, 9, 29),
    available_at: datetime | None = datetime(2026, 9, 29, 13, tzinfo=UTC),
    vintage: str | None = "2026-09-29",
    missing_reason: str | None = None,
) -> RateObservation:
    return RateObservation(
        source_id=source_id,
        instrument=DEFINITIONS[source_id],
        observed_on=observed_on,
        available_at=available_at,
        retrieved_at=datetime(2026, 9, 29, 14, tzinfo=UTC),
        vintage=vintage,
        value=value,
        unit="percent",
        missing_reason=missing_reason,
    )


def _observations(stale: bool = False) -> dict[str, RateObservation]:
    return {
        EUR_ID: _observation(
            EUR_ID,
            2.0,
            observed_on=date(2026, 9, 1) if stale else date(2026, 9, 29),
        ),
        "DGS2": _observation("DGS2", 4.0),
    }


def test_stale_spot_negative_control(monkeypatch: pytest.MonkeyPatch) -> None:
    # Old scalar boundary had no rate date; a fresh spot made the stale leg usable.
    scalar = {EUR_ID: 2.0, "DGS2": 4.0}
    spot = SpotBar(
        date=AS_OF.date(), pair="EURUSD", open=1.1, high=1.1,
        low=1.1, close=1.1, volume=1.0,
    )
    snapshot = IngestionSnapshot.from_buffer(
        AS_OF.date(),
        {
            KEY_FX_SPOT: {"EURUSD": [spot]},
            KEY_YIELDS: scalar,
            KEY_YIELD_OBSERVATIONS: _observations(stale=True),
        },
        rate_decision_at=AS_OF,
    )
    assert snapshot.today_bar_for("EURUSD") == spot
    assert snapshot.rate_observations[EUR_ID].observed_on == date(2026, 9, 1)
    universe = {"EURUSD": {
        "class": "FX", "tickers": {"yield_base": EUR_ID, "yield_quote": "DGS2"},
    }}
    assert _rates_bucket_freshness(
        {
            KEY_FX_SPOT: {"EURUSD": [spot]},
            KEY_YIELDS: scalar,
            KEY_YIELD_OBSERVATIONS: snapshot.rate_observations,
            KEY_RATE_DECISION_AT: AS_OF,
        }, universe, AS_OF.date(),
    ) == 0.1
    assert (
        rate_inputs.two_year_spread("EURUSD", scalar, SOURCE_IDS, definitions=DEFINITIONS) == -2.0
    )
    monkeypatch.setitem(rate_inputs.SOURCE_DEFINITIONS, EUR_ID, DEFINITIONS[EUR_ID])
    assert (
        qualified_two_year_spread(
            "EURUSD",
            snapshot.rate_observations,
            decision_at=snapshot.rate_decision_at,
            source_ids=SOURCE_IDS,
        )
        is None
    )


def test_timely_zero_missing_monthly_and_unknown_availability() -> None:
    assert (
        qualified_two_year_spread(
            "EURUSD",
            _observations(),
            decision_at=AS_OF,
            source_ids=SOURCE_IDS,
            definitions=DEFINITIONS,
        )
        == -2.0
    )
    zero = _observation(EUR_ID, 0.0)
    assert (
        qualified_rate_value(zero, source_id=EUR_ID, decision_at=AS_OF, definitions=DEFINITIONS)
        == 0.0
    )
    for bad in (
        _observation(EUR_ID, None, missing_reason="provider_missing_value"),
        _observation(EUR_ID, 2.0, observed_on=date(2026, 8, 1)),
        _observation(EUR_ID, 2.0, available_at=None),
        _observation(EUR_ID, 2.0, vintage=None),
    ):
        assert (
            qualified_rate_value(bad, source_id=EUR_ID, decision_at=AS_OF, definitions=DEFINITIONS)
            is None
        )
    assert (
        qualified_rate_value(
            _observation(EUR_ID, 2.0),
            source_id=EUR_ID,
            decision_at=AS_OF - timedelta(days=1),
            definitions=DEFINITIONS,
        )
        is None
    )


def test_acquisition_fred_async_preserves_observation_and_unknown_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRED_API_KEY", "fixture-only")
    body = json.dumps(
        {
            "observations": [
                {
                    "date": "2026-09-26",
                    "realtime_start": "2026-09-28",
                    "realtime_end": "9999-12-31",
                    "value": "0",
                }
            ]
        }
    ).encode()
    sink: dict[str, RateObservation] = {}
    fetcher = MagicMock(fetch_with_retry=AsyncMock(return_value=(200, body)))
    assert asyncio.run(yields._fred_latest_async("DGS2", MagicMock(), fetcher, sink)) == 0.0
    obs = sink["DGS2"]
    assert (obs.source_id, obs.observed_on, obs.vintage, obs.value, obs.unit) == (
        "DGS2",
        date(2026, 9, 26),
        None,
        0.0,
        "percent",
    )
    assert obs.provider_realtime_start == "2026-09-28"
    assert obs.provider_realtime_end == "9999-12-31"
    assert obs.retrieved_at is not None and obs.available_at is None
    assert qualified_rate_value(obs, source_id="DGS2", decision_at=AS_OF) is None

    missing_body = json.dumps({"observations": [{
        "date": "2026-09-26", "realtime_start": "2026-09-28", "value": ".",
    }]}).encode()
    missing_fetcher = MagicMock(fetch_with_retry=AsyncMock(return_value=(200, missing_body)))
    missing_value = asyncio.run(
        yields._fred_latest_async("DGS2", MagicMock(), missing_fetcher, sink)
    )
    assert missing_value is None
    assert sink["DGS2"].missing_reason == "provider_missing_value"


def test_acquisition_sync_and_fallback_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    series = pd.Series([4.0], index=pd.to_datetime(["2026-09-25"]))
    sink: dict[str, RateObservation] = {}
    fred = SimpleNamespace(get_series_latest_release=lambda _id: series)
    assert yields._fred_leg(fred, ("DGS2",), "US 2Y", sink, "us_2y") == 4.0
    assert sink["us_2y"].source_id == "DGS2"
    assert sink["us_2y"].observed_on == date(2026, 9, 25)
    assert sink["us_2y"].available_at is None

    async def fred_missing(
        _id: str,
        _session: object,
        _fetcher: object,
        observations: dict[str, RateObservation] | None = None,
    ) -> None:
        return None

    async def yahoo_value(
        _id: str,
        _period: str,
        _fetcher: object,
        observations: dict[str, RateObservation] | None = None,
    ) -> float:
        yields._record_observation(
            observations,
            "^UST2Y",
            "^UST2Y",
            4.1,
            date(2026, 9, 29),
            AS_OF,
        )
        return 4.1

    monkeypatch.setattr(yields, "_fred_latest_async", fred_missing)
    monkeypatch.setattr(yields, "_yahoo_yield_latest_async", yahoo_value)
    sink.clear()
    key, value = asyncio.run(
        yields._fetch_yield_leg_async("^UST2Y", MagicMock(), MagicMock(), "5d", sink)
    )
    assert (key, value, sink[key].source_id) == ("^UST2Y", 4.1, "^UST2Y")


def test_live_staged_replay_qualification_agree(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(rate_inputs.SOURCE_DEFINITIONS, EUR_ID, DEFINITIONS[EUR_ID])
    monkeypatch.setitem(rate_inputs.CONFIGURED_RATE_SOURCES, "EURUSD", SOURCE_IDS)
    universe = {
        "EURUSD": {
            "tickers": {
                "yield_base": EUR_ID,
                "yield_quote": "DGS2",
            }
        }
    }
    observations = _observations()
    values: dict[str, float | None] = {EUR_ID: 2.0, "DGS2": 4.0}
    assert _rates_bucket_freshness(
        {
            KEY_YIELDS: values,
            KEY_YIELD_OBSERVATIONS: observations,
            KEY_RATE_DECISION_AT: AS_OF,
        }, universe, AS_OF.date(),
    ) == 1.0
    live = _rate_spread_2y_for_pair("EURUSD", universe, values, observations, AS_OF)
    staged = _rate_spread_2y("EURUSD", values, observations, AS_OF)
    replay = qualified_two_year_spread("EURUSD", observations, decision_at=AS_OF)
    assert (live, staged, replay) == (-2.0, -2.0, -2.0)
    stale = _observations(stale=True)
    assert _rate_spread_2y_for_pair("EURUSD", universe, values, stale, AS_OF) is None
    assert _rate_spread_2y("EURUSD", values, stale, AS_OF) is None
    assert qualified_two_year_spread("EURUSD", stale, decision_at=AS_OF) is None
    assert qualified_two_year_spread("EURUSD", observations, decision_at=None) is None
