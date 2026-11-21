"""Tests for SEBI FPI India scraper."""

from __future__ import annotations

from datetime import date

import pytest
import requests

from src.fetchers.fpi_india import (
    _parse_inr_crores,
    _parse_sebi_date,
    fetch_fpi_flows,
    fetch_fpi_history,
)


def test_parse_inr_crores() -> None:
    assert _parse_inr_crores("1,234.56") == 1234.56
    assert _parse_inr_crores("-1,234.56 Cr") == -1234.56
    assert _parse_inr_crores("(1,234.56)") == -1234.56
    assert _parse_inr_crores("—") is None
    assert _parse_inr_crores("") is None
    assert _parse_inr_crores("NaN") is None
    assert _parse_inr_crores("Inf") is None
    assert _parse_inr_crores("-Infinity") is None


def test_parse_sebi_date() -> None:
    assert _parse_sebi_date("15-May-2026") == date(2026, 5, 15)
    assert _parse_sebi_date("01-Jan-2024") == date(2024, 1, 1)
    assert _parse_sebi_date("2026-05-15") == date(2026, 5, 15)
    assert _parse_sebi_date("invalid") is None
    assert _parse_sebi_date("31-Feb-2026") is None
    assert _parse_sebi_date("15-May-2026 trailing text") is None


def test_retired_fpi_fetchers_reject_before_network_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[tuple[object, ...]] = []

    def fail_if_called(*args: object, **_kwargs: object) -> None:
        attempts.append(args)
        raise AssertionError("retired FPI fetcher attempted network I/O")

    monkeypatch.setattr(requests.Session, "request", fail_if_called)

    with pytest.raises(RuntimeError, match="Unqualified FPI source is retired"):
        fetch_fpi_flows(date(2026, 5, 1))
    with pytest.raises(RuntimeError, match="Unqualified FPI source is retired"):
        fetch_fpi_history(date(2026, 5, 1), date(2026, 5, 2))

    assert attempts == []
