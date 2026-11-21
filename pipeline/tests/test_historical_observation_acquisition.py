"""Historical Yahoo acquisition remains append-only provider evidence."""

from __future__ import annotations

import runpy
import traceback
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from src.backfill import historical_fetcher, orchestrator
from src.db import writer
from src.fetchers import cross_asset
from src.scheduler import orchestrator as scheduler_orchestrator
from src.types import SpotBar


def _bar(day: date, *, receipt: datetime) -> SpotBar:
    return SpotBar(
        date=day,
        pair="EURUSD",
        open=1.0,
        high=1.2,
        low=0.9,
        close=1.1,
        volume=0.0,
        provider="yahoo",
        instrument="EURUSD=X",
        retrieved_at=receipt,
        provider_metadata={
            "date_label_policy": "provider_date",
            "raw_index": day.isoformat(),
            "index_timezone": None,
            "adjusted": False,
        },
        volume_source="yahoo",
        volume_instrument="EURUSD=X",
    )


def test_legacy_historical_writer_rejects_before_client_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    touched = False

    def unexpected_client() -> Any:
        nonlocal touched
        touched = True
        raise AssertionError("legacy rejection must happen before client access")

    monkeypatch.setattr(writer, "_client", unexpected_client)

    writer.write_historical_prices([])
    with pytest.raises(RuntimeError, match="source-qualification policy.*migration"):
        writer.write_historical_prices([{"pair": "EURUSD"}], source="yfinance")

    assert touched is False


def test_yahoo_download_uses_unadjusted_strict_parser_and_keeps_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-03"], tz="UTC")
    frame = pd.DataFrame(
        {
            "Open": [1.0, None],
            "High": [1.2, 1.2],
            "Low": [0.9, 0.9],
            "Close": [1.1, 1.1],
            "Volume": [0.0, 0.0],
        },
        index=index,
    )
    provider = MagicMock()
    provider.download.return_value = frame
    monkeypatch.setattr(historical_fetcher, "_yfinance", lambda: provider)

    before = datetime.now(UTC)
    bars = historical_fetcher.fetch_historical_spot_yfinance(
        "EURUSD", date(2024, 1, 2), date(2024, 1, 3)
    )
    after = datetime.now(UTC)

    assert len(bars) == 1
    assert bars[0].date == date(2024, 1, 2)
    assert bars[0].provider == "yahoo" and bars[0].instrument == "EURUSD=X"
    assert bars[0].provider_metadata["adjusted"] is False
    assert bars[0].session_timezone == "UTC"
    assert bars[0].retrieved_at is not None
    assert before <= bars[0].retrieved_at <= after
    provider.download.assert_called_once_with(
        "EURUSD=X",
        start="2024-01-02",
        end="2024-01-04",
        progress=False,
        auto_adjust=False,
        ignore_tz=False,
    )


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        (date(2024, 1, 2), date(2024, 1, 1), "must not follow"),
        (datetime(2024, 1, 1, tzinfo=UTC), date(2024, 1, 2), "calendar dates"),
        (date(2024, 1, 1), date(2999, 1, 1), "future"),
    ],
)
def test_invalid_date_bounds_fail_before_provider_io(
    monkeypatch: pytest.MonkeyPatch,
    start: date,
    end: date,
    message: str,
) -> None:
    touched = False

    def unexpected_provider() -> Any:
        nonlocal touched
        touched = True
        return MagicMock()

    monkeypatch.setattr(historical_fetcher, "_yfinance", unexpected_provider)
    with pytest.raises((TypeError, ValueError), match=message):
        historical_fetcher.fetch_historical_spot_yfinance("EURUSD", start, end)
    assert touched is False


def test_provider_failure_propagates_without_echoing_exception_payload(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_payload = "https://query.example/?crumb=secret"
    provider = MagicMock()
    provider.download.side_effect = RuntimeError(secret_payload)
    monkeypatch.setattr(historical_fetcher, "_yfinance", lambda: provider)

    with pytest.raises(RuntimeError, match="RuntimeError") as caught:
        historical_fetcher.fetch_historical_spot_yfinance(
            "EURUSD", date(2024, 1, 1), date(2024, 1, 2)
        )

    assert secret_payload not in str(caught.value)
    assert secret_payload not in caplog.text
    rendered = "".join(traceback.format_exception(caught.value))
    assert secret_payload not in rendered


def test_locked_pair_rejection_precedes_universe_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lookup = MagicMock(side_effect=AssertionError("universe lookup must not run"))
    monkeypatch.setattr(historical_fetcher, "spot_tickers_from_universe", lookup)

    with pytest.raises(ValueError, match="outside the locked universe"):
        historical_fetcher.fetch_historical_spot_yfinance(
            "GBPUSD", date(2024, 1, 1), date(2024, 1, 2)
        )

    lookup.assert_not_called()


def test_archival_chunks_at_5000_and_preserves_provider_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = datetime(2026, 9, 27, 8, tzinfo=UTC)
    start = date(2010, 1, 1)
    bars = [_bar(start + timedelta(days=index), receipt=receipt) for index in range(5001)]
    chunks: list[list[dict[str, Any]]] = []

    monkeypatch.setattr(
        historical_fetcher,
        "fetch_historical_spot_yfinance",
        lambda pair, first, last: bars,
    )

    def archive(rows: Any) -> dict[str, Any]:
        payload = [dict(row) for row in rows]
        chunks.append(payload)
        return {
            "observation_ids": list(range(1, len(payload) + 1)),
            "inserted_count": len(payload),
            "existing_count": 0,
        }

    monkeypatch.setattr(writer, "archive_price_observations", archive)
    count = historical_fetcher.backfill_spot_for_pair(
        "EURUSD", start, bars[-1].date
    )

    assert count == 5001
    assert [len(chunk) for chunk in chunks] == [5000, 1]
    assert chunks[0][0]["provider"] == "yahoo"
    assert chunks[0][0]["instrument"] == "EURUSD=X"
    assert chunks[0][0]["retrieved_at"] == receipt.isoformat()
    assert chunks[0][0]["provider_metadata"]["adjusted"] is False
    assert all("validation_eligible" not in row for chunk in chunks for row in chunk)


def test_archive_failure_propagates_instead_of_returning_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = datetime(2024, 1, 3, tzinfo=UTC)
    monkeypatch.setattr(
        historical_fetcher,
        "fetch_historical_spot_yfinance",
        lambda pair, start, end: [_bar(start, receipt=receipt)],
    )
    monkeypatch.setattr(
        writer,
        "archive_price_observations",
        MagicMock(side_effect=RuntimeError("archive unavailable")),
    )

    with pytest.raises(RuntimeError, match="archive unavailable"):
        historical_fetcher.backfill_spot_for_pair(
            "EURUSD", date(2024, 1, 2), date(2024, 1, 2)
        )


def test_unsafe_replay_range_rejects_before_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acquisition = MagicMock(side_effect=AssertionError("must not acquire before rejection"))
    monkeypatch.setattr(orchestrator, "backfill_spots", acquisition)

    with pytest.raises(RuntimeError, match="not replay-ready canonical closes"):
        orchestrator.run_backfill_range(date(2024, 1, 1), date(2024, 1, 5))

    acquisition.assert_not_called()


@pytest.mark.parametrize("target", [date(2024, 1, 2), datetime.now(UTC).date()])
def test_direct_replay_entrypoint_never_calls_daily_scheduler(
    monkeypatch: pytest.MonkeyPatch,
    target: date,
) -> None:
    run_daily = AsyncMock(side_effect=AssertionError("retired replay must not call scheduler"))
    monkeypatch.setattr(scheduler_orchestrator, "run_daily", run_daily)

    with pytest.raises(RuntimeError, match="point-in-time replay contract"):
        orchestrator.replay_pipeline_for_date(target)

    run_daily.assert_not_awaited()


@pytest.mark.parametrize(
    ("pairs", "message"),
    [
        (["EURUSD", "GBPUSD"], "outside the locked universe"),
        (["EURUSD", "EURUSD"], "duplicates"),
        ([], "at least one"),
    ],
)
def test_archive_pair_list_is_validated_before_any_acquisition(
    monkeypatch: pytest.MonkeyPatch,
    pairs: list[str],
    message: str,
) -> None:
    acquisition = MagicMock(side_effect=AssertionError("pair validation must run first"))
    monkeypatch.setattr(orchestrator, "backfill_spot_for_pair", acquisition)

    with pytest.raises(ValueError, match=message):
        orchestrator.backfill_spots(date(2024, 1, 1), date(2024, 1, 2), pairs)

    acquisition.assert_not_called()


@pytest.mark.parametrize("years_back", [True, 0, -1, 2.5, "30"])
def test_fetch_max_history_rejects_invalid_span_before_io(
    monkeypatch: pytest.MonkeyPatch,
    years_back: Any,
) -> None:
    delegated = MagicMock()
    monkeypatch.setattr(cross_asset, "backfill_spot_for_pair", delegated)
    with pytest.raises(ValueError, match="positive integer"):
        cross_asset.fetch_max_history("EURUSD", years_back)
    delegated.assert_not_called()


def test_fetch_max_history_delegates_utc_calendar_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed = datetime(2026, 9, 27, 23, 30, tzinfo=UTC)
    fake_datetime = SimpleNamespace(now=lambda zone: fixed)
    delegated = MagicMock(return_value=17)
    monkeypatch.setattr(cross_asset, "datetime", fake_datetime)
    monkeypatch.setattr(cross_asset, "backfill_spot_for_pair", delegated)

    assert cross_asset.fetch_max_history("USDJPY", 30) == 17
    delegated.assert_called_once_with("USDJPY", date(1996, 1, 1), date(2026, 9, 27))


def test_population_cli_help_exits_before_acquisition(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    acquisition = MagicMock(side_effect=AssertionError("help must not acquire"))
    monkeypatch.setattr(orchestrator, "backfill_spot_for_pair", acquisition)
    path = Path(__file__).parents[1] / "scripts" / "populate_historical_prices.py"
    namespace = runpy.run_path(str(path), run_name="historical_population_script")

    with pytest.raises(SystemExit) as stopped:
        namespace["main"](["--help"])

    assert stopped.value.code == 0
    help_text = capsys.readouterr().out
    normalized_help = " ".join(help_text.split())
    assert "Archive Yahoo provider observations" in normalized_help
    assert "does not populate qualified validation closes" in normalized_help
    acquisition.assert_not_called()


def test_population_cli_rejects_duplicate_pairs_before_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acquisition = MagicMock(side_effect=AssertionError("duplicate validation must run first"))
    monkeypatch.setattr(orchestrator, "backfill_spot_for_pair", acquisition)
    path = Path(__file__).parents[1] / "scripts" / "populate_historical_prices.py"
    namespace = runpy.run_path(str(path), run_name="historical_population_script")

    with pytest.raises(ValueError, match="duplicates"):
        namespace["main"](
            [
                "--start", "2024-01-01",
                "--end", "2024-01-02",
                "--pairs", "EURUSD", "EURUSD",
            ]
        )

    acquisition.assert_not_called()
