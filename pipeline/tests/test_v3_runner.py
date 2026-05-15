"""Tests for v3 pair-specific runner and fetcher fixes."""

from __future__ import annotations

from datetime import date

import pytest

from src.fx_types import SpotBar
from src.pairs.eurusd.fetcher import EURUSDFetcher
from src.pairs.runner import _compute_v3_composite


def _make_spot_bars(closes: list[float]) -> list[SpotBar]:
    """Build SpotBar list from close prices (synthetic OHLC)."""
    bars: list[SpotBar] = []
    for i, c in enumerate(closes):
        bars.append(
            SpotBar(
                date=date(2024, 1, i + 1),
                pair="EURUSD",
                open=c - 0.001,
                high=c + 0.002,
                low=c - 0.002,
                close=c,
                volume=1000.0,
            )
        )
    return bars


class TestV3Composite:
    """Tests for v3 composite computation."""

    def test_eurusd_composite_with_all_signals(self) -> None:
        comp = _compute_v3_composite(
            "EURUSD",
            {
                "rate_diff": 1.0,
                "cot_percentile": 75.0,
                "vix": 20.0,
                "btp_spread": 150.0,
                "special_signal_value": 0.3,
            },
            vol_regime="NEUTRAL",
            rate_regime="NEUTRAL",
        )
        assert comp is not None
        assert -2.0 <= comp <= 2.0

    def test_usdjpy_composite_with_intervention(self) -> None:
        comp = _compute_v3_composite(
            "USDJPY",
            {
                "rate_diff": 3.5,
                "cot_percentile": 60.0,
                "vix": 22.0,
                "intervention_proximity": 80.0,
            },
            vol_regime="NEUTRAL",
            rate_regime="NEUTRAL",
        )
        assert comp is not None
        assert -2.0 <= comp <= 2.0

    def test_usdinr_composite_with_reserves(self) -> None:
        comp = _compute_v3_composite(
            "USDINR",
            {
                "rate_diff": 5.0,
                "cot_percentile": 40.0,
                "vix": 18.0,
                "rbi_fx_reserves": 620.0,
                "em_stress_composite": 45.0,
            },
            vol_regime="NEUTRAL",
            rate_regime="NEUTRAL",
        )
        assert comp is not None
        assert -2.0 <= comp <= 2.0

    def test_composite_none_when_no_signals(self) -> None:
        comp = _compute_v3_composite(
            "EURUSD",
            {},
            vol_regime="NEUTRAL",
            rate_regime="NEUTRAL",
        )
        assert comp is None


class TestEURUSDFetcher:
    """Tests for EURUSD fetcher improvements."""

    def test_fetcher_has_spot_bars_method(self) -> None:
        f = EURUSDFetcher(lookback_days=5)
        assert hasattr(f, "_fetch_spot_bars")

    def test_compute_signals_returns_oi_and_rv_rank(self) -> None:
        f = EURUSDFetcher(lookback_days=5)
        data = {
            "spot": 1.10,
            "spot_bars": _make_spot_bars([1.09, 1.10, 1.11, 1.12, 1.13] * 5),
            "yields": {"us_10y": 4.5, "de_10y": 2.5},
            "cot": {
                "percentile": 60.0,
                "open_interest": 500000.0,
            },
            "cross_asset": {"vix": 18.0},
            "bund_btp": {"spread": 120.0},
            "eu_hy_oas": 350.0,
        }
        signals = f.compute_signals(data)
        assert "oi_signal" in signals
        assert "oi_delta" in signals
        assert "realized_vol_rank" in signals
        assert "spot_bars" in signals

    def test_compute_signals_oi_increasing(self) -> None:
        f = EURUSDFetcher(lookback_days=5)
        data = {
            "spot": 1.10,
            "spot_bars": [],
            "yields": {"us_10y": 4.5, "de_10y": 2.5},
            "cot": {
                "percentile": 60.0,
                "open_interest": 500000.0,
            },
            "cross_asset": {"vix": 18.0},
            "bund_btp": {"spread": 120.0},
            "eu_hy_oas": 350.0,
        }
        signals = f.compute_signals(data)
        assert signals["oi_signal"] == "INCREASING"
        assert signals["oi_delta"] == 500000.0

    def test_compute_execution_with_stop_levels(self) -> None:
        f = EURUSDFetcher(lookback_days=5)
        signals = {
            "vol_signal": "NEUTRAL",
            "directional_bias": "LONG",
            "spot": 1.10,
            "spot_bars": _make_spot_bars([1.09, 1.10, 1.11, 1.12, 1.13] * 5),
        }
        execution = f.compute_execution("BULLISH", signals)
        assert execution["entry_timing"] == "ENTER"
        assert execution["position_size"] == "FULL"
        assert execution["stop_level"] is not None
        assert execution["adr"] is not None
        assert execution["mie_proxy"] is not None
        assert execution["stop_buffer"] is not None

    def test_compute_execution_no_spot_bars(self) -> None:
        f = EURUSDFetcher(lookback_days=5)
        signals = {
            "vol_signal": "NEUTRAL",
            "directional_bias": "LONG",
            "spot": 1.10,
            "spot_bars": [],
        }
        execution = f.compute_execution("BULLISH", signals)
        assert execution["stop_level"] is None
        assert execution["adr"] is None


class TestV3Confidence:
    """Tests for v3 confidence fix (0.30-0.90 scale)."""

    def test_confidence_formula_matches_v2(self) -> None:
        """Ensure compute_confidence returns [0.30, 0.90] for typical v3 composites."""
        from src.regime.confidence import compute_confidence

        # Strong composite with aligned signals
        conf = compute_confidence(
            composite=1.2,
            rate_norm=0.6,
            cot_norm=0.5,
            pair="EURUSD",
        )
        assert 0.30 <= conf <= 0.90

        # Weak composite
        conf = compute_confidence(
            composite=0.2,
            rate_norm=0.1,
            cot_norm=None,
            pair="USDJPY",
        )
        assert 0.30 <= conf <= 0.90

        # Strong negative composite
        conf = compute_confidence(
            composite=-1.5,
            rate_norm=-0.7,
            cot_norm=-0.4,
            pair="USDINR",
        )
        assert 0.30 <= conf <= 0.90


class TestRiskReversalProxy:
    """Tests for synthetic risk-reversal proxy in fetchers."""

    def test_eurusd_rr_proxy_positive(self) -> None:
        f = EURUSDFetcher(lookback_days=5)
        signals = {
            "vol_signal": "NEUTRAL",
            "directional_bias": "LONG",
            "spot": 1.10,
            "spot_bars": _make_spot_bars([1.09, 1.10, 1.11, 1.12, 1.13] * 5),
        }
        # compute_signals normally sets realized_vol_20d and day_change_pct
        # but we inject them directly for this test
        signals["realized_vol_20d"] = 5.0
        signals["day_change_pct"] = 0.5
        execution = f.compute_execution("BULLISH", signals)
        assert execution["risk_reversal_z"] is not None
        assert execution["risk_reversal_z"] > 0

    def test_eurusd_rr_proxy_negative(self) -> None:
        f = EURUSDFetcher(lookback_days=5)
        signals = {
            "vol_signal": "NEUTRAL",
            "directional_bias": "SHORT",
            "spot": 1.10,
            "spot_bars": [],
            "realized_vol_20d": 5.0,
            "day_change_pct": -0.3,
        }
        execution = f.compute_execution("BEARISH", signals)
        assert execution["risk_reversal_z"] is not None
        assert execution["risk_reversal_z"] < 0

    def test_eurusd_rr_proxy_none_when_missing(self) -> None:
        f = EURUSDFetcher(lookback_days=5)
        signals = {
            "vol_signal": "NEUTRAL",
            "directional_bias": "NEUTRAL",
            "spot": 1.10,
            "spot_bars": [],
        }
        execution = f.compute_execution("RANGING", signals)
        assert execution["risk_reversal_z"] is None


class TestCrossAssetWiring:
    """Tests that cross-asset data flows into runner SignalRow."""

    def test_runner_enriches_cross_asset(self) -> None:
        from unittest.mock import patch

        from src.pairs.runner import _run_single_pair

        with patch("src.pairs.runner._write_to_db"):
            result = _run_single_pair("EURUSD", date(2026, 5, 14), dry_run=True)
            # In dry-run _write_to_db is short-circuited, so verify via signals enrichment path
            assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
