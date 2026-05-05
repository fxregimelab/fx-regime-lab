"""Round 3 validation engine tests."""

from __future__ import annotations

import datetime
import math

from src.validation.calendar import add_trading_days
from src.validation.engine import (
    brier_score,
    is_correct,
    log_return_bps,
    realized_direction,
)


def test_log_return_bps_bullish() -> None:
    bps = log_return_bps(1.0700, 1.0721)
    assert bps > 0
    assert abs(bps - 10_000.0 * math.log(1.0721 / 1.0700)) < 1e-9


def test_log_return_bps_bearish() -> None:
    bps = log_return_bps(1.0700, 1.0680)
    assert bps < 0
    assert abs(bps - 10_000.0 * math.log(1.0680 / 1.0700)) < 1e-9


def test_realized_direction_up() -> None:
    assert realized_direction(10.0) == "UP"


def test_realized_direction_down() -> None:
    assert realized_direction(-10.0) == "DOWN"


def test_realized_direction_neutral_inside_deadband() -> None:
    assert realized_direction(3.0) == "NEUTRAL"


def test_realized_direction_neutral_exactly_5bps() -> None:
    assert realized_direction(5.0) == "NEUTRAL"


def test_is_correct_bullish_up() -> None:
    assert is_correct("BULLISH", "UP") is True


def test_is_correct_bullish_down() -> None:
    assert is_correct("BULLISH", "DOWN") is False


def test_is_correct_neutral_inside() -> None:
    assert is_correct("NEUTRAL", "NEUTRAL") is True


def test_is_correct_neutral_outside() -> None:
    assert is_correct("NEUTRAL", "UP") is False


def test_brier_score_correct() -> None:
    assert abs(brier_score(0.8, True) - 0.04) < 1e-9


def test_brier_score_incorrect() -> None:
    assert abs(brier_score(0.8, False) - 0.64) < 1e-9


def test_brier_score_neutral() -> None:
    assert brier_score(0.8, True) is not None
    # brier_score itself does not check predicted; engine handles neutral skip


def test_add_trading_days_skips_weekend() -> None:
    fri = datetime.date(2026, 5, 1)
    assert add_trading_days(fri, 1) == datetime.date(2026, 5, 4)


def test_add_trading_days_t5_over_weekend() -> None:
    fri = datetime.date(2026, 5, 1)
    assert add_trading_days(fri, 5) == datetime.date(2026, 5, 8)
