"""D04: deterministic COT acquisition across a January year boundary."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import date, timedelta

import pytest

from src.fetchers import cot
from src.signals.cot import COT_PERCENTILE_WINDOW_REPORTS, compute_cot_percentile

MARKETS = {
    "EURUSD": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
    "USDJPY": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
    "USDINR": "INDIAN RUPEE - CHICAGO MERCANTILE EXCHANGE",
}
FIELDS = [
    "Market and Exchange Names",
    "As of Date in Form YYMMDD",
    "Noncommercial Positions-Long (All)",
    "Noncommercial Positions-Short (All)",
    "Open Interest (All)",
    "Asset Mgr Positions Long All",
    "Asset Mgr Positions Short All",
    "Lev Money Positions Long All",
    "Lev Money Positions Short All",
]


def _row(pair: str, report: date, *, long: int = 100) -> dict[str, str]:
    return dict(zip(FIELDS, [
        MARKETS[pair], report.strftime("%y%m%d"), str(long), "10", "1000",
        "80", "20", "50", "30",
    ], strict=True))


def _payload(rows: list[dict[str, str]], *, zipped: bool) -> bytes:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    data = stream.getvalue().encode()
    if not zipped:
        return data
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("financial.txt", data)
    return out.getvalue()


def _sources(monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, str]], *,
             fail: tuple[str, ...] = ()) -> list[str]:
    calls: list[str] = []

    def download(url: str) -> bytes:
        calls.append(url)
        if any(fragment in url for fragment in fail):
            raise OSError("fixture source unavailable")
        if "FinFutWk" in url:
            selected = [row for row in rows if row["As of Date in Form YYMMDD"].startswith("26")]
            return _payload(selected, zipped=False)
        for year in range(2023, 2027):
            if f"_{year}.zip" in url:
                selected = [
                    row for row in rows
                    if row["As of Date in Form YYMMDD"].startswith(str(year)[2:])
                ]
                return _payload(selected, zipped=True)
        return _payload([], zipped=False)

    monkeypatch.setattr(cot, "_download_cot_bytes", download)
    return calls


def _history(*pairs: str, count: int = 158) -> list[dict[str, str]]:
    start = date(2023, 1, 3)
    return [
        _row(pair, start + timedelta(weeks=i), long=100 + i)
        for pair in pairs for i in range(count)
    ]


def test_january_joins_three_prior_years_and_weekly_for_all_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _sources(monkeypatch, _history(*MARKETS))
    rows = cot.fetch_cot(year=2026)
    for pair in MARKETS:
        matching = [row for row in rows if row.pair == pair]
        assert len(matching) >= COT_PERCENTILE_WINDOW_REPORTS
        assert matching[-1].date.year == 2026
        assert matching[-1].asset_mgr_net == 60
        assert matching[-1].lev_money_net == 20
    assert any("_2023.zip" in url for url in calls)
    assert any("FinFutWk" in url for url in calls)


def test_insufficient_distinct_history_is_excluded(monkeypatch: pytest.MonkeyPatch) -> None:
    _sources(monkeypatch, _history("EURUSD", count=155))
    assert cot.fetch_cot(year=2026) == []


def test_equal_duplicate_report_is_counted_once(monkeypatch: pytest.MonkeyPatch) -> None:
    history = _history("EURUSD")
    history.append(history[-1].copy())
    _sources(monkeypatch, history)
    rows = cot.fetch_cot(year=2026)
    assert len({row.date for row in rows}) == len(rows)
    assert len(rows) >= COT_PERCENTILE_WINDOW_REPORTS


def test_conflicting_duplicate_rejects_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    history = _history("EURUSD", "USDJPY")
    conflict = next(
        row.copy() for row in history
        if row["Market and Exchange Names"] == MARKETS["EURUSD"]
    )
    conflict["Noncommercial Positions-Long (All)"] = "999"
    history.append(conflict)
    _sources(monkeypatch, history)
    rows = cot.fetch_cot(year=2026)
    assert {row.pair for row in rows} == {"USDJPY"}


def test_current_archive_failure_falls_back_to_weekly(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _sources(monkeypatch, _history("EURUSD"), fail=("_2026.zip",))
    rows = cot.fetch_cot(year=2026)
    assert len(rows) >= COT_PERCENTILE_WINDOW_REPORTS
    assert rows[-1].date.year == 2026
    assert any("FinFutWk" in url for url in calls)


def test_missing_prior_year_is_explicit_partial_history(monkeypatch: pytest.MonkeyPatch,
                                                        caplog: pytest.LogCaptureFixture) -> None:
    _sources(monkeypatch, _history("EURUSD"), fail=("_2024.zip",))
    assert cot.fetch_cot(year=2026) == []
    assert "insufficient" in caplog.text.lower()


def test_missing_middle_year_cannot_fill_rolling_window_from_old_reports(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    # 208 weekly dates through December 2026 leave 156 after the 2025 archive fails.
    calls = _sources(monkeypatch, _history("EURUSD", count=208), fail=("_2025.zip",))
    rows = cot.fetch_cot(year=2026)
    assert any("_2025.zip" in url for url in calls)
    assert rows == []
    assert compute_cot_percentile(rows, "EURUSD") is None
    assert "gap" in caplog.text.lower()


def test_short_missing_week_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    history = _history("EURUSD", count=158)
    del history[80]
    _sources(monkeypatch, history)
    rows = cot.fetch_cot(year=2026)
    assert len(rows) == COT_PERCENTILE_WINDOW_REPORTS
    assert max((right.date - left.date).days for left, right in zip(rows, rows[1:])) == 14


def test_repeated_short_gaps_cannot_extend_three_year_window(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    history = [row for index, row in enumerate(_history("EURUSD", count=208))
               if index % 4 != 0]
    assert len(history) == COT_PERCENTILE_WINDOW_REPORTS
    _sources(monkeypatch, history)
    rows = cot.fetch_cot(year=2026)
    assert rows == []
    assert compute_cot_percentile(rows, "EURUSD") is None
    assert "span" in caplog.text.lower()
