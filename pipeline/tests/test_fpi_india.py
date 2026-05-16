"""Tests for SEBI FPI India scraper."""

from __future__ import annotations

from datetime import date

from src.fetchers.fpi_india import _parse_inr_crores, _parse_sebi_date, fetch_fpi_flows


def test_parse_inr_crores():
    assert _parse_inr_crores("1,234.56") == 1234.56
    assert _parse_inr_crores("-1,234.56 Cr") == -1234.56
    assert _parse_inr_crores("(1,234.56)") == -1234.56
    assert _parse_inr_crores("—") is None
    assert _parse_inr_crores("") is None


def test_parse_sebi_date():
    assert _parse_sebi_date("15-May-2026") == date(2026, 5, 15)
    assert _parse_sebi_date("01-Jan-2024") == date(2024, 1, 1)
    assert _parse_sebi_date("2026-05-15") == date(2026, 5, 15)
    assert _parse_sebi_date("invalid") is None


def test_fetch_fpi_flows_smoke():
    """Smoke test: should return None or a dict without crashing."""
    result = fetch_fpi_flows(date(2026, 5, 1))
    assert result is None or isinstance(result, dict)
    if result:
        assert "date" in result
        assert "fpi_equity_net_cr" in result
        assert "fpi_debt_net_cr" in result
        assert "fpi_total_net_cr" in result
        assert "source" in result
