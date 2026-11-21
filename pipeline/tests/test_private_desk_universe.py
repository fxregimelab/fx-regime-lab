"""JPY quote orientation, cost scale and complete current-universe controls."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.private_desk import data
from src.private_desk.data import PAIRS as DATA_PAIRS
from src.private_desk.data import _reference_rows
from src.private_desk.engine import UNIVERSE, Costs, simulate_trade
from src.private_desk.readiness import PAIRS as READINESS_PAIRS
from src.private_desk.readiness import assess_readiness
from src.private_desk.report import PAIRS as REPORT_PAIRS
from src.private_desk.universe import LEGACY_PAIRS, PAIRS


def test_all_current_consumers_include_jpy_and_retained_cross() -> None:
    assert len(PAIRS) == 8 and "USDJPY" in PAIRS and "EURGBP" in PAIRS
    assert DATA_PAIRS == READINESS_PAIRS == REPORT_PAIRS == UNIVERSE == PAIRS


def test_jpy_partial_exit_and_pip_cost_scale() -> None:
    bars = [
        {"time": f"2026-09-{day:02d}", "open": 150.0, "high": 150.3, "low": 149.9, "close": 150.2}
        for day in (28, 29, 30)
    ]
    jpy = simulate_trade("USDJPY", bars, 0, 1, 1.0, 2, costs=Costs(1.2, 0.2, 0.0))
    ordinary = simulate_trade("EURUSD", bars, 0, 1, 1.0, 2, costs=Costs(1.2, 0.2, 0.0))
    assert jpy["cost_r"] == pytest.approx(0.016)
    assert jpy["cost_r"] == pytest.approx(100 * ordinary["cost_r"])
    assert jpy["net_r"] == pytest.approx(jpy["gross_r"] - jpy["cost_r"])


def test_reference_jpy_is_quote_per_us_dollar() -> None:
    payload = {"base": "EUR", "amount": 1.0, "rates": {"2026-09-30": {"USD": 1.2, "JPY": 180.0}}}
    assert _reference_rows(payload, "USDJPY", "2026-09-30")[0]["close"] == 150.0


def test_jpy_capture_names_the_actual_provider_symbol(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(data, "_now", lambda: datetime(2026, 10, 1, 16, tzinfo=UTC))
    monkeypatch.setattr(
        data,
        "_download",
        lambda *args: [
            {"time": "2026-09-30", "open": 150.0, "high": 151.0, "low": 149.0, "close": 150.5}
        ],
    )
    _, meta = data.load_history("USDJPY", cache_dir=tmp_path, refresh=True)
    assert meta["provider_symbol"] == "JPY=X"
    assert "/JPY%3DX/history/" in meta["source_url"]


def test_legacy_seven_pair_report_cannot_claim_current_coverage() -> None:
    report = {
        "schema_version": "private-fx-v1",
        "universe": list(LEGACY_PAIRS),
        "generated_at": "2026-10-01T12:00:00Z",
        "current_context_updated_at": "2026-10-01T12:00:00Z",
        "pair_reports": [
            {
                "pair": p,
                "candidate": {"as_of": "2026-09-30"},
                "data_coverage": {"status": "VALID", "interval": "1d", "last_bar": "2026-09-30"},
            }
            for p in LEGACY_PAIRS
        ],
    }
    result = assess_readiness(report, now=datetime(2026, 10, 1, 16, tzinfo=UTC))
    assert result["status"] == "HOLD"
    assert any(r["code"] == "INVALID_UNIVERSE" for r in result["reasons"])
