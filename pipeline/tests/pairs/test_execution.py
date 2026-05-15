"""Tests for pair-specific execution modules."""

from __future__ import annotations

import datetime

import pytest

from src.fx_types import SpotBar
from src.pairs.eurusd.execution import (
    average_daily_range as eurusd_adr,
)
from src.pairs.eurusd.execution import (
    compute_eurusd_position_size,
    get_eurusd_execution_params,
)
from src.pairs.eurusd.execution import (
    compute_kelly_size as eurusd_kelly,
)
from src.pairs.eurusd.execution import (
    compute_stop_level as eurusd_stop,
)
from src.pairs.eurusd.execution import (
    mie_proxy_points as eurusd_mie,
)
from src.pairs.usdinr.execution import (
    compute_kelly_size as usdinr_kelly,
)
from src.pairs.usdinr.execution import (
    compute_usdinr_position_size,
    get_usdinr_execution_params,
)
from src.pairs.usdjpy.execution import (
    compute_kelly_size as usdjpy_kelly,
)
from src.pairs.usdjpy.execution import (
    compute_stop_level as usdjpy_stop,
)
from src.pairs.usdjpy.execution import (
    compute_usdjpy_position_size,
    get_usdjpy_execution_params,
)


def _make_bars(
    n: int, open_val: float = 1.0, high: float = 1.2, low: float = 0.8, close: float = 1.1
) -> list[SpotBar]:
    """Generate simple SpotBar sequence."""
    base = datetime.date(2025, 1, 1)
    bars = []
    for i in range(n):
        bars.append(
            SpotBar(
                date=base + datetime.timedelta(days=i),
                pair="TEST",
                open=open_val,
                high=high,
                low=low,
                close=close,
            )
        )
    return bars


# ---------------------------------------------------------------------------
# Kelly sizing
# ---------------------------------------------------------------------------


class TestKellySizing:
    def test_eurusd_kelly_typical(self) -> None:
        result = eurusd_kelly(0.6, 30.0, 20.0)
        assert result > 0.0
        assert result <= 0.01

    def test_usdjpy_kelly_zero_loss(self) -> None:
        assert usdjpy_kelly(0.6, 30.0, 0.0) == 0.0

    def test_usdinr_kelly_negative_kelly(self) -> None:
        result = usdinr_kelly(0.3, 10.0, 20.0)
        assert result == 0.0


# ---------------------------------------------------------------------------
# ATR-based stops
# ---------------------------------------------------------------------------


class TestATRBasedStops:
    def test_eurusd_stop_long(self) -> None:
        buf, stop = eurusd_stop(1.1000, "LONG", 0.0100, None, None)
        assert buf is not None
        assert stop == pytest.approx(1.1000 - buf)

    def test_eurusd_stop_short(self) -> None:
        buf, stop = eurusd_stop(1.1000, "SHORT", 0.0100, None, None)
        assert buf is not None
        assert stop == pytest.approx(1.1000 + buf)

    def test_eurusd_stop_neutral(self) -> None:
        assert eurusd_stop(1.1000, "NEUTRAL", 0.0100, None, None) == (None, None)

    def test_eurusd_stop_none_spot(self) -> None:
        assert eurusd_stop(None, "LONG", 0.0100, None, None) == (None, None)

    def test_eurusd_stop_adr_only(self) -> None:
        buf, stop = eurusd_stop(1.1000, "LONG", 0.0100, None, None, adr_multiplier=1.3)
        assert buf == pytest.approx(0.0130)

    def test_eurusd_stop_mie_only(self) -> None:
        buf, stop = eurusd_stop(1.1000, "LONG", None, 0.0050, None, mie_multiplier=1.0)
        assert buf == pytest.approx(0.0050)

    def test_eurusd_stop_atr_only(self) -> None:
        buf, stop = eurusd_stop(1.1000, "LONG", None, None, 0.0080)
        assert buf == pytest.approx(0.0080)

    def test_eurusd_stop_max_of_parts(self) -> None:
        buf, _ = eurusd_stop(1.1000, "LONG", 0.0100, 0.0050, 0.0200)
        assert buf == pytest.approx(0.0200)

    def test_no_parts_returns_none(self) -> None:
        assert eurusd_stop(1.1000, "LONG", None, None, None) == (None, None)


# ---------------------------------------------------------------------------
# Intervention-aware stops (USDJPY)
# ---------------------------------------------------------------------------


class TestInterventionAwareStops:
    def test_active_widens_buffer(self) -> None:
        buf_normal, _ = usdjpy_stop(150.0, "LONG", 1.0, None, None, "DORMANT")
        buf_active, _ = usdjpy_stop(150.0, "LONG", 1.0, None, None, "ACTIVE")
        assert buf_active is not None
        assert buf_normal is not None
        assert buf_active > buf_normal

    def test_proximal_widens_buffer(self) -> None:
        buf_normal, _ = usdjpy_stop(150.0, "LONG", 1.0, None, None, "DORMANT")
        buf_prox, _ = usdjpy_stop(150.0, "LONG", 1.0, None, None, "PROXIMAL")
        assert buf_prox is not None
        assert buf_normal is not None
        assert buf_prox > buf_normal

    def test_intervention_mult_factor(self) -> None:
        # ACTIVE multiplier is 1.4, PROXIMAL is 1.2
        buf_dorm, _ = usdjpy_stop(150.0, "LONG", 1.0, None, None, "DORMANT")
        buf_active, _ = usdjpy_stop(150.0, "LONG", 1.0, None, None, "ACTIVE")
        assert buf_active == pytest.approx(buf_dorm * 1.4)


# ---------------------------------------------------------------------------
# Position sizing
# ---------------------------------------------------------------------------


class TestPositionSizing:
    def test_eurusd_position_size(self) -> None:
        size = compute_eurusd_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
        )
        assert size > 0.0
        assert size <= 100.0 * 0.01

    def test_usdjpy_intervention_discount_active(self) -> None:
        size = compute_usdjpy_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            boj_regime="ACTIVE",
        )
        size_dormant = compute_usdjpy_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            boj_regime="DORMANT",
        )
        assert size == pytest.approx(size_dormant * 0.60)

    def test_usdjpy_intervention_discount_proximal(self) -> None:
        size = compute_usdjpy_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            boj_regime="PROXIMAL",
        )
        size_dormant = compute_usdjpy_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            boj_regime="DORMANT",
        )
        assert size == pytest.approx(size_dormant * 0.80)

    def test_usdinr_rbi_active_defence_discount(self) -> None:
        size = compute_usdinr_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            rbi_regime="ACTIVE_DEFENCE",
        )
        size_light = compute_usdinr_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            rbi_regime="LIGHT_TOUCH",
        )
        assert size == pytest.approx(size_light * 0.55)

    def test_usdinr_rbi_accumulation_discount(self) -> None:
        size = compute_usdinr_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            rbi_regime="ACCUMULATION",
        )
        size_light = compute_usdinr_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            rbi_regime="LIGHT_TOUCH",
        )
        assert size == pytest.approx(size_light * 0.85)


# ---------------------------------------------------------------------------
# Execution params bundles
# ---------------------------------------------------------------------------


class TestExecutionParams:
    def test_eurusd_bundle_keys(self) -> None:
        bars = _make_bars(25)
        params = get_eurusd_execution_params(1.1000, "LONG", bars)
        assert "adr" in params
        assert "mie_proxy" in params
        assert "atr" in params
        assert "stop_buffer" in params
        assert "stop_level" in params
        assert params["adr"] is not None

    def test_usdjpy_bundle_detects_boj(self) -> None:
        bars = _make_bars(25)
        params = get_usdjpy_execution_params(
            150.0, "LONG", bars, last_intervention_high=150.0, days_since_last_intervention=10
        )
        assert params["boj_regime"] == "ACTIVE"

    def test_usdinr_bundle_detects_rbi(self) -> None:
        bars = _make_bars(25)
        params = get_usdinr_execution_params(83.0, "LONG", bars, reserves_mom_pct=-5.0)
        assert params["rbi_regime"] == "ACTIVE_DEFENCE"


# ---------------------------------------------------------------------------
# ADR / MIE helpers
# ---------------------------------------------------------------------------


class TestAdrMie:
    def test_empty_bars(self) -> None:
        assert eurusd_adr([]) is None
        assert eurusd_mie([], "LONG") is None

    def test_adr_computation(self) -> None:
        bars = _make_bars(5, high=1.2, low=0.8)
        adr = eurusd_adr(bars)
        assert adr == pytest.approx(0.4)

    def test_mie_long(self) -> None:
        bars = [
            SpotBar(datetime.date(2025, 1, 1), "TEST", 1.0, 1.1, 0.9, 1.05),
            SpotBar(datetime.date(2025, 1, 2), "TEST", 1.0, 1.2, 0.95, 1.1),
        ]
        mie = eurusd_mie(bars, "LONG")
        # adverse for long: max(0, open - low)
        # bar1: 1.0 - 0.9 = 0.1
        # bar2: 1.0 - 0.95 = 0.05
        assert mie == pytest.approx(0.1)

    def test_mie_short(self) -> None:
        bars = [
            SpotBar(datetime.date(2025, 1, 1), "TEST", 1.0, 1.1, 0.9, 1.05),
            SpotBar(datetime.date(2025, 1, 2), "TEST", 1.0, 1.2, 0.95, 1.1),
        ]
        mie = eurusd_mie(bars, "SHORT")
        # adverse for short: max(0, high - open)
        # bar1: 1.1 - 1.0 = 0.1
        # bar2: 1.2 - 1.0 = 0.2
        assert mie == pytest.approx(0.2)

    def test_mie_neutral(self) -> None:
        bars = [
            SpotBar(datetime.date(2025, 1, 1), "TEST", 1.0, 1.1, 0.9, 1.05),
        ]
        mie = eurusd_mie(bars, "NEUTRAL")
        assert mie == pytest.approx(0.1)
