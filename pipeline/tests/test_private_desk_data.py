"""Source timing, integrity and failure regressions without external networking."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import requests
import yfinance as yf

from src.private_desk import boj_current, data

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def fixed_time(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(data, "_now", lambda: NOW)
    monkeypatch.setattr(data, "_DEFAULT_CACHE_DIR", tmp_path)
    def unavailable_boj(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("BOJ fixture source unavailable")

    monkeypatch.setattr(boj_current, "capture_source", unavailable_boj)


def bar(time: str, **values: Any) -> dict[str, Any]:
    return {"time": time, "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.15, **values}


def test_history_capture_and_verified_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rows = [bar("2026-09-29"), bar("2026-09-30"), bar("2026-10-01")]
    calls = []

    def download(*args: Any) -> list[dict[str, Any]]:
        calls.append(args)
        return rows

    monkeypatch.setattr(data, "_download", download)
    result, meta = data.load_history("EURUSD", cache_dir=tmp_path)
    assert len(result) == 2
    assert meta["first_bar"] == "2026-09-29"
    assert meta["last_bar"] == "2026-09-30"
    assert meta["incomplete_bars_omitted"] == 1
    assert meta["research_status"] == "PROVISIONAL_QUARANTINED"
    assert meta["point_in_time"] is False
    captured = Path(meta["capture_path"]).read_bytes()
    assert json.loads(captured)["raw_bars"] == rows
    cached, cached_meta = data.load_history("EURUSD", cache_dir=tmp_path)
    assert cached == result and cached_meta["from_cache"] is True
    assert cached_meta["sha256"] == meta["sha256"] and len(calls) == 1
    assert Path(meta["capture_path"]).read_bytes() == captured


@pytest.mark.parametrize(
    "rows",
    [
        [bar("2026-09-30"), bar("2026-09-29")],
        [bar("2026-09-30"), bar("2026-09-30")],
        [bar("2026-10-02")],
        [bar("2026-09-30", close=float("nan"))],
        [bar("2026-09-30", low=1.18)],
        [bar("2026-09-30", open=0.0)],
    ],
)
def test_invalid_history_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, rows: list[dict[str, Any]]
) -> None:
    monkeypatch.setattr(data, "_download", lambda *args: rows)
    result, meta = data.load_history("GBPUSD", interval="1h", cache_dir=tmp_path)
    assert result == [] and meta["errors"] == ["invalid_provider_bars"]
    assert not list(tmp_path.rglob("latest.json"))


def test_hourly_uses_only_completed_bars(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    rows = [bar("2026-10-01T09:00:00+00:00"), bar("2026-10-01T11:00:00+00:00")]
    monkeypatch.setattr(data, "_download", lambda *args: rows)
    result, meta = data.load_history("AUDUSD", interval="1h", cache_dir=tmp_path)
    assert len(result) == 1 and meta["incomplete_bars_omitted"] == 1


def test_tampered_cache_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(data, "_download", lambda *args: [bar("2026-09-30")])
    _, meta = data.load_history("NZDUSD", cache_dir=tmp_path)
    Path(meta["capture_path"]).write_text("{}", encoding="utf-8")
    result, failure = data.load_history("NZDUSD", cache_dir=tmp_path)
    assert result == [] and failure["errors"] == ["cache_integrity_failure"]


def test_history_cache_age_is_explicit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(data, "_download", lambda *args: [bar("2026-09-30")])
    data.load_history("USDCAD", cache_dir=tmp_path)
    monkeypatch.setattr(data, "_now", lambda: NOW + timedelta(days=3))
    _, meta = data.load_history("USDCAD", cache_dir=tmp_path)
    assert meta["stale"] is True and meta["cache_age_hours"] == 72


def test_immutable_refresh_keeps_previous_capture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(data, "_download", lambda *args: [bar("2026-09-30")])
    _, first = data.load_history("USDCHF", cache_dir=tmp_path)
    old = Path(first["capture_path"]).read_bytes()
    monkeypatch.setattr(data, "_now", lambda: NOW + timedelta(minutes=1))
    _, second = data.load_history("USDCHF", cache_dir=tmp_path, refresh=True)
    assert second["sha256"] != first["sha256"]
    assert Path(first["capture_path"]).read_bytes() == old


def test_provider_errors_are_bounded_and_sanitized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []

    def broken(*args: Any) -> list[dict[str, Any]]:
        calls.append(args)
        raise RuntimeError("secret-key=do-not-display")

    monkeypatch.setattr(data, "_download", broken)
    result, meta = data.load_history("EURGBP", interval="1h", cache_dir=tmp_path)
    assert result == [] and len(calls) == 2
    assert "do-not-display" not in json.dumps(meta)


@pytest.mark.parametrize(
    "pair,interval,start",
    [
        ("USDINR", "1d", "1997-01-01"),
        ("EURUSD", "1m", "1997-01-01"),
        ("EURUSD", "1d", "broken"),
        ("EURUSD", "1d", "2027-01-01"),
    ],
)
def test_unsupported_requests_fail_before_network(
    tmp_path: Path, pair: str, interval: str, start: str
) -> None:
    result, meta = data.load_history(pair, interval=interval, start=start, cache_dir=tmp_path)
    assert result == [] and meta["status"] == "UNAVAILABLE"


def test_download_actual_provider_shape_and_hourly_retention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments: dict[str, Any] = {}

    class Ticker:
        def history(self, **kwargs: Any) -> pd.DataFrame:
            arguments.update(kwargs)
            return pd.DataFrame(
                [{"Open": 1.1, "High": 1.2, "Low": 1.0, "Close": 1.15}],
                index=pd.DatetimeIndex(["2026-09-30T09:00:00Z"]),
            )

    monkeypatch.setattr(yf, "Ticker", lambda pair: Ticker())
    result = data._download("EURUSD", "1h", "1997-01-01", NOW)
    assert result[0]["time"] == "2026-09-30T09:00:00+00:00"
    assert arguments["start"] == (NOW - timedelta(days=729)).date().isoformat()
    assert arguments["timeout"] == 12 and arguments["auto_adjust"] is False


FEED = """<rss><channel>
<item><title>Official policy headline</title>
<link>https://www.federalreserve.gov/newsevents/pressreleases/monetary.htm</link>
<pubDate>Wed, 30 Sep 2026 14:00:00 GMT</pubDate>
<description>Must not reach output</description></item>
<item><title>Future headline</title><link>https://bbc.com/news/future</link>
<pubDate>Fri, 02 Oct 2026 14:00:00 GMT</pubDate></item>
<item><title>Unsafe link</title><link>javascript:bad()</link>
<pubDate>Wed, 30 Sep 2026 14:00:00 GMT</pubDate></item>
<item><title>No date</title><link>https://bbc.com/news/undated</link></item>
</channel></rss>"""


def test_news_has_attribution_witnessed_time_no_article_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(data, "_FEEDS", (("Federal Reserve", "https://fed.example/rss"),))
    monkeypatch.setattr(data, "_get_text", lambda url: FEED)
    items = data.fetch_news()
    assert len(items) == 1 and items[0]["published_at"] == "2026-09-30T14:00:00+00:00"
    assert items[0]["source"] == "Federal Reserve" and items[0]["sha256"]
    assert "Must not reach output" not in json.dumps(items)
    assert items[0]["content_scope"] == "attributed_headline_only"
    assert len(list((tmp_path / "news").glob("*.json"))) == 1


def test_news_feed_failure_produces_no_fiction(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(url: str) -> str:
        raise ValueError("network failure")

    monkeypatch.setattr(data, "_get_text", unavailable)
    assert data.fetch_news() == []


def test_current_policy_csv_is_not_historical_availability(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def csv_source(url: str) -> str:
        if "fred.stlouisfed.org" not in url:
            raise ValueError("source unavailable")
        series = url.split("id=")[1].split("&")[0]
        return f"observation_date,{series}\n2026-09-29,.\n2026-09-30,2.5\n2027-01-01,99\n"

    monkeypatch.setattr(data, "_get_text", csv_source)
    result = data.fetch_fundamentals(tmp_path)
    assert result["research_status"] == "CURRENT_DESCRIPTIVE_ONLY"
    assert result["missing_currencies"] == ["GBP", "AUD", "NZD", "CAD", "CHF", "JPY"]
    assert len(result["indicators"]) == 9
    available = [item for item in result["indicators"].values() if item["status"] == "AVAILABLE"]
    assert len(available) == 3
    for indicator in available:
        assert indicator["value"] == 2.5 and indicator["observation_date"] == "2026-09-30"
        assert indicator["published_at"] is None and indicator["point_in_time"] is False
        assert Path(indicator["capture_path"]).exists()


def test_unavailable_policy_has_no_proxy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(data, "_get_text", lambda url: "<html>unavailable</html>")
    result = data.fetch_fundamentals(tmp_path)
    assert all(
        item["status"] == "UNAVAILABLE" and item["value"] is None
        for item in result["indicators"].values()
    )


def test_requests_bound_retries_and_hide_exception_text(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def failure(*args: Any, **kwargs: Any) -> Any:
        calls.append(kwargs)
        raise requests.Timeout("confidential-token")

    monkeypatch.setattr(requests, "get", failure)
    with pytest.raises(ValueError, match="source request unavailable") as error:
        data._get_text("https://fred.stlouisfed.org/series/ECBDFR")
    assert len(calls) == 2 and calls[0]["timeout"] == (5, 12)
    assert "confidential-token" not in str(error.value)


def hourly_session(end_utc: datetime) -> list[dict[str, Any]]:
    return [bar((end_utc - timedelta(hours=24 - index)).isoformat()) for index in range(24)]


def test_fx_friday_session_and_dst_do_not_drop_friday() -> None:
    # Friday closes at 21:00 UTC in summer and 22:00 UTC in winter.
    summer = hourly_session(datetime(2026, 9, 25, 21, tzinfo=UTC))
    winter = hourly_session(datetime(2026, 1, 9, 22, tzinfo=UTC))
    for rows, date in ((summer, "2026-09-25"), (winter, "2026-01-09")):
        daily, metadata = data._aggregate_hourly(rows, NOW)
        assert len(daily) == 1 and daily[0]["time"] == date
        assert daily[0]["hour_count"] == 24 and daily[0]["gap_before"] is False
        assert metadata["session_timezone"] == "America/New_York"


def test_partial_fx_session_is_omitted_and_gap_marked() -> None:
    monday = hourly_session(datetime(2026, 9, 21, 21, tzinfo=UTC))
    tuesday_partial = hourly_session(datetime(2026, 9, 22, 21, tzinfo=UTC))[:-1]
    wednesday = hourly_session(datetime(2026, 9, 23, 21, tzinfo=UTC))
    rows, metadata = data._aggregate_hourly([*monday, *tuesday_partial, *wednesday], NOW)
    assert [row["time"] for row in rows] == ["2026-09-21", "2026-09-23"]
    assert rows[-1]["gap_before"] is True
    assert metadata["missing_weekdays"] == ["2026-09-22"]


def test_invalid_daily_is_retained_before_hourly_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def provider(pair: str, interval: str, start: str, now: datetime) -> list[dict[str, Any]]:
        if interval == "1d":
            return [bar("2026-09-25", low=1.19)]
        return hourly_session(datetime(2026, 9, 25, 21, tzinfo=UTC))

    def stooq(pair: str, start: str) -> Any:
        raise ValueError("unavailable")

    monkeypatch.setattr(data, "_download", provider)
    monkeypatch.setattr(data, "_stooq_bars", stooq)
    rows, metadata = data.load_history("EURUSD", cache_dir=tmp_path)
    assert rows[0]["time"] == "2026-09-25" and metadata["status"] == "AVAILABLE"
    assert "New York" in metadata["source"]
    assert metadata["coverage_years"] == 0 and metadata["point_in_time"] is False
    rejected = json.loads(Path(metadata["rejected_capture_path"]).read_text("utf-8"))
    assert rejected["validation_status"] == "REJECTED"
    assert rejected["raw_bars"][0]["low"] == 1.19
    cached, _ = data.load_history("EURUSD", cache_dir=tmp_path)
    assert cached[0]["gap_before"] is False and cached[0]["hour_count"] == 24


def reference_payload() -> dict[str, Any]:
    return {
        "amount": 1.0,
        "base": "EUR",
        "rates": {
            "2026-09-29": {
                "USD": 1.2,
                "GBP": 0.8,
                "AUD": 1.6,
                "NZD": 2.0,
                "CAD": 1.5,
                "CHF": 0.9,
                "JPY": 180.0,
            },
            "2026-09-30": {
                "USD": 1.2,
                "GBP": 0.8,
                "AUD": 1.6,
                "NZD": 2.0,
                "CAD": 1.5,
                "CHF": 0.9,
                "JPY": 180.0,
            },
        },
    }


def test_reference_derives_all_seven_from_same_fix_and_shares_verified_capture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []

    def source(url: str) -> str:
        calls.append(url)
        return json.dumps(reference_payload())

    monkeypatch.setattr(data, "_get_text", source)
    expected = {
        "EURUSD": 1.2,
        "GBPUSD": 1.5,
        "AUDUSD": 0.75,
        "NZDUSD": 0.6,
        "USDCAD": 1.25,
        "USDCHF": 0.75,
        "USDJPY": 150.0,
        "EURGBP": 0.8,
    }
    captures = []
    for pair, close in expected.items():
        rows, metadata = data.load_reference_history(pair, cache_dir=tmp_path)
        assert rows[-1]["close"] == pytest.approx(close)
        assert set(rows[-1]) == {"time", "close"}
        assert metadata["research_status"] == "REFERENCE_DIRECTION_ONLY"
        assert metadata["executable_ohlc"] is False and metadata["published_at"] is None
        captures.append(metadata["sha256"])
    assert len(calls) == 1 and len(set(captures)) == 1
    assert "2026-09-30" in calls[0]


@pytest.mark.parametrize("mutation", ["future", "missing_leg", "wrong_base", "zero_leg"])
def test_invalid_reference_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mutation: str
) -> None:
    payload = reference_payload()
    if mutation == "future":
        payload["rates"]["2026-10-01"] = payload["rates"]["2026-09-30"]
    elif mutation == "missing_leg":
        del payload["rates"]["2026-09-30"]["CHF"]
    elif mutation == "wrong_base":
        payload["base"] = "USD"
    else:
        payload["rates"]["2026-09-30"]["AUD"] = 0
    monkeypatch.setattr(data, "_get_text", lambda url: json.dumps(payload))
    rows, metadata = data.load_reference_history("EURUSD", cache_dir=tmp_path)
    assert rows == [] and metadata["status"] == "UNAVAILABLE"


def test_reference_shared_capture_tampering_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(data, "_get_text", lambda url: json.dumps(reference_payload()))
    _, metadata = data.load_reference_history("EURUSD", cache_dir=tmp_path)
    Path(metadata["capture_path"]).write_text("{}", encoding="utf-8")
    rows, rejected = data.load_reference_history("GBPUSD", cache_dir=tmp_path)
    assert rows == [] and rejected["status"] == "UNAVAILABLE"


def test_daily_provider_calendar_label_survives_positive_timezone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Ticker:
        def history(self, **kwargs: Any) -> pd.DataFrame:
            return pd.DataFrame(
                [{"Open": 1.1, "High": 1.2, "Low": 1.0, "Close": 1.15}],
                index=pd.DatetimeIndex(["2026-10-01T00:00:00+01:00"]),
            )

    monkeypatch.setattr(yf, "Ticker", lambda pair: Ticker())
    rows = data._download("EURUSD", "1d", "1997-01-01", NOW)
    assert rows[0]["time"] == "2026-10-01"
    complete, omitted = data._validate_bars(rows, "1d", NOW)
    assert complete == [] and omitted == 1


def test_fx_weekend_does_not_create_missing_weekday_gap() -> None:
    friday = hourly_session(datetime(2026, 9, 25, 21, tzinfo=UTC))
    monday = hourly_session(datetime(2026, 9, 28, 21, tzinfo=UTC))
    rows, metadata = data._aggregate_hourly([*friday, *monday], NOW)
    assert [row["time"] for row in rows] == ["2026-09-25", "2026-09-28"]
    assert rows[-1]["gap_before"] is False and metadata["gap_count"] == 0


@pytest.mark.parametrize(
    "bad_values",
    [
        {"low": 1.19},
        {"close": float("nan")},
        {"open": 0.0},
        {"high": float("inf")},
    ],
)
def test_quarantine_preserves_valid_prices_and_marks_gap_without_compressed_horizon(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bad_values: dict[str, float]
) -> None:
    rows = [bar("2026-09-28"), bar("2026-09-29", **bad_values), bar("2026-09-30")]
    monkeypatch.setattr(data, "_download", lambda *args: rows)
    result, metadata = data.load_history("EURUSD", cache_dir=tmp_path)
    assert [row["time"] for row in result] == ["2026-09-28", "2026-09-30"]
    assert result[0]["close"] == rows[0]["close"]
    assert result[-1]["gap_before"] is True
    assert metadata["invalid_row_count"] == 1 and metadata["invalid_dates"] == ["2026-09-29"]
    assert metadata["missing_weekdays"] == ["2026-09-29"]
    assert metadata["source_status"] == "PROVISIONAL_QUARANTINED"
    assert Path(metadata["rejected_capture_path"]).exists()
    cached, _ = data.load_history("EURUSD", cache_dir=tmp_path)
    assert cached[-1]["gap_before"] is True


@pytest.mark.parametrize(
    "rows",
    [
        [bar("2026-09-30"), bar("2026-09-29")],
        [bar("2026-09-30"), bar("2026-09-30")],
        [bar("2026-09-30"), bar("2026-10-02")],
    ],
)
def test_quarantine_does_not_hide_unusable_timestamp_identity(rows: list[dict[str, Any]]) -> None:
    with pytest.raises(ValueError, match="unusable daily date identity"):
        data._quarantine_daily(rows, NOW)


def test_stale_last_observation_remains_stale_in_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(data, "_download", lambda *args: [bar("2026-09-21")])
    _, first = data.load_history("EURUSD", cache_dir=tmp_path)
    _, cached = data.load_history("EURUSD", cache_dir=tmp_path)
    assert first["stale"] is True and cached["stale"] is True


RBA_POLICY = """F1 INTEREST RATES AND YIELDS - MONEY MARKET
Title,Cash Rate Target,Interbank Overnight Cash Rate
30-Sep-2026,4.60,4.59
01-Oct-2026,,4.61
02-Oct-2026,99,99
"""
BOE_POLICY = """Current official Bank Rate 3.75%
| Date Changed | Rate |
| --- | --- |
| 18 Dec 25 | 3.75 |
"""
RBNZ_POLICY = (
    "Official Cash Rate 2.75 % Updated: 2:00pm, 02 Sep 2026 Next update: 2:00pm, 28 Oct 2026"
)
SNB_POLICY = "<div>SNB policy rate 0.00% valid from 20.06.2025</div><div>SARON -0.04%</div>"


def boc_policy_payload(label: str = "Target for the overnight rate (business daily)") -> str:
    return json.dumps(
        {
            "seriesDetail": {"V39079": {"label": label}},
            "observations": [
                {"d": "2026-09-29", "V39079": {"v": "2.25"}},
                {"d": "2026-10-02", "V39079": {"v": "99"}},
            ],
        }
    )


def test_policy_target_parsers_do_not_use_interbank_or_saron_rates() -> None:
    assert data._rba_policy(RBA_POLICY, NOW)["value"] == 4.6
    assert data._rba_policy(RBA_POLICY, NOW)["observation_date"] == "2026-09-30"
    assert data._boc_policy(boc_policy_payload(), NOW)["value"] == 2.25
    with pytest.raises(ValueError, match="unverified"):
        data._boc_policy(boc_policy_payload("Interbank market overnight rate"), NOW)
    assert data._snb_policy(SNB_POLICY, NOW)["value"] == 0.0
    with pytest.raises(ValueError):
        data._snb_policy("SARON -0.04% valid from 20.06.2025", NOW)


def test_current_page_dates_are_separate_from_policy_effective_dates() -> None:
    boe = data._boe_policy(BOE_POLICY, NOW)
    snb = data._snb_policy(SNB_POLICY, NOW)
    assert boe["observation_date"] == "2026-10-01" and boe["effective_from"] == "2025-12-18"
    assert snb["observation_date"] == "2026-10-01" and snb["effective_from"] == "2025-06-20"
    rbnz = data._rbnz_policy(RBNZ_POLICY, NOW)
    assert rbnz["policy_updated_date"] == "2026-09-02"
    assert rbnz["next_policy_update_date"] == "2026-10-28"
    assert "UNKNOWN" in rbnz["publication_timing"]


def test_policy_parser_conflict_future_and_scheduled_staleness() -> None:
    with pytest.raises(ValueError, match="conflicting"):
        data._boe_policy(BOE_POLICY.replace("18 Dec 25 | 3.75", "18 Dec 25 | 4.00"), NOW)
    with pytest.raises(ValueError, match="future"):
        data._rbnz_policy(RBNZ_POLICY.replace("02 Sep 2026", "02 Nov 2026"), NOW)
    stale = data._rbnz_policy(RBNZ_POLICY.replace("28 Oct 2026", "30 Sep 2026"), NOW)
    assert stale["status"] == "STALE"


def test_all_policy_sources_with_explicit_public_reader_transport(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def source(url: str) -> str:
        if "fred.stlouisfed.org" in url:
            series = url.split("id=")[1].split("&")[0]
            return f"observation_date,{series}\n2026-09-30,2.5\n"
        if "rba.gov.au" in url:
            return RBA_POLICY
        if "bankofcanada.ca" in url:
            return boc_policy_payload()
        if "snb.ch" in url:
            return SNB_POLICY
        if "bankofengland.co.uk" in url:
            if not url.startswith("https://r.jina.ai/"):
                raise ValueError("direct official source blocked")
            official = url.removeprefix("https://r.jina.ai/")
            return f"URL Source: {official}\n{BOE_POLICY}"
        if "rbnz.govt.nz" in url:
            return RBNZ_POLICY
        raise ValueError("unexpected source")

    monkeypatch.setattr(data, "_get_text", source)
    monkeypatch.setattr(
        boj_current, "capture_source",
        lambda *args, **kwargs: (
            '<section class="policy"><h3>Guideline</h3>'
            '<a href="/en/mopo/mpmdeci/state_2026/index.htm">'
            'The Bank will encourage the uncollateralized overnight call rate '
            'to remain at around 1.25 percent.</a></section>',
            {"received_at": NOW.isoformat()},
        ),
    )
    result = data.fetch_fundamentals(tmp_path)
    assert result["missing_currencies"] == [] and result["policy_status"] == "COMPLETE"
    assert result["status"] == "PARTIAL" and result["research_status"] == "CURRENT_DESCRIPTIVE_ONLY"
    assert result["indicators"]["gbp_bank_rate"]["transport"] == "PUBLIC_READER_OF_OFFICIAL_PAGE"
    for indicator in result["indicators"].values():
        assert indicator["published_at"] is None and indicator["point_in_time"] is False
        assert indicator["sha256"] and Path(indicator["capture_path"]).exists()


def test_public_reader_source_identity_must_match(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def source(url: str) -> str:
        if url.startswith("https://r.jina.ai/"):
            return f"URL Source: https://unrelated.example/\n{BOE_POLICY}"
        raise ValueError("source unavailable")

    monkeypatch.setattr(data, "_get_text", source)
    indicators = data._extra_policy_sources(tmp_path, NOW)
    assert indicators["gbp_bank_rate"]["status"] == "UNAVAILABLE"
    assert indicators["gbp_bank_rate"]["value"] is None


def test_daily_policy_observation_staleness_is_explicit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        data, "_EXTRA_POLICY", {"aud_cash_rate_target": data._EXTRA_POLICY["aud_cash_rate_target"]}
    )
    monkeypatch.setattr(
        data, "_get_text", lambda url: RBA_POLICY.replace("30-Sep-2026", "01-Jun-2026")
    )
    result = data._extra_policy_sources(tmp_path, NOW)
    assert result["aud_cash_rate_target"]["status"] == "STALE"


def test_rss_one_namespace_dates_and_verified_central_bank_links() -> None:
    raw = """<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
    <item><title>Official policy decision</title>
    <link>https://www.rba.gov.au/media-releases/2026/example.html</link>
    <dc:date>2026-09-30T14:30:00+10:00</dc:date></item></rdf:RDF>"""
    result = data._parse_feed(raw, "Reserve Bank of Australia", NOW)
    assert len(result) == 1 and result[0]["published_at"] == "2026-09-30T04:30:00+00:00"


def test_rba_supported_client_and_utf8_bom_regression(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        content = b"\xef\xbb\xbf" + RBA_POLICY.encode("utf-8")

        def __init__(self, accepted: bool) -> None:
            self.accepted = accepted

        def raise_for_status(self) -> None:
            if not self.accepted:
                raise requests.HTTPError("public source rejects unsupported custom identifier")

    def request(url: str, **kwargs: Any) -> Response:
        return Response(kwargs["headers"]["User-Agent"] == requests.utils.default_user_agent())

    monkeypatch.setattr(requests, "get", request)
    raw = data._get_text("https://www.rba.gov.au/statistics/tables/csv/f1-data.csv")
    assert data._rba_policy(raw, NOW)["value"] == 4.6
