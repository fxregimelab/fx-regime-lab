"""Invalid FPI values must never become maximum directional signals."""
from typing import Any

import pytest

from src.signals.direction import directional_inputs
from src.signals.fpi import normalize_fpi_signal


@pytest.mark.parametrize("case", [
    "nan_latest", "inf_latest", "negative_inf_latest", "bool_latest",
    "string_latest", "huge_latest", "nan_history", "inf_history",
    "bool_history", "string_history", "huge_history", "none_history_item",
    "window_zero", "window_negative", "window_bool", "window_float",
    "window_string", "arithmetic_overflow", "positive_below_median",
    "observed_zero", "missing", "last_window", "numpy_sequence",
])
def test_fpi_numeric_contract(case: str) -> None:
    import numpy as np

    prior = [float(i) for i in range(20)]
    if case.startswith("window_"):
        invalid: Any = {
            "zero": 0, "negative": -1, "bool": True, "float": 20.0, "string": "20",
        }[case.removeprefix("window_")]
        with pytest.raises(ValueError, match="positive integer"):
            normalize_fpi_signal(12.0, prior, window=invalid)
    elif case.endswith("_latest") or case.endswith("_history") or case == "none_history_item":
        key = case.split("_latest")[0].split("_history")[0]
        invalid = {
            "nan": float("nan"), "inf": float("inf"), "negative_inf": -float("inf"),
            "bool": True, "string": "12.0", "huge": 10**1000, "none": None,
        }[key]
        if case.endswith("_latest"):
            assert normalize_fpi_signal(invalid, prior) is None
        else:
            bad_history = [*prior[:-1], invalid]
            assert normalize_fpi_signal(12.0, bad_history) is None
    elif case == "arithmetic_overflow":
        assert normalize_fpi_signal(1e308, [-1e308] * 10 + [1e308] * 10) is None
    elif case == "positive_below_median":
        # Median 19.5, median absolute deviation 5. A positive cash inflow of
        # 18 is below the reference level, not an outright cash outflow.
        history = [float(i) for i in range(10, 30)]
        result = normalize_fpi_signal(18.0, history)
        assert result == pytest.approx(-1.5 / (1.4826 * 5))
        assert directional_inputs("USDINR", rate=None, cot=None, special=None, fpi=result).fpi == (
            pytest.approx(1.5 / (1.4826 * 5))
        )
        assert history == [float(i) for i in range(10, 30)]
    elif case == "observed_zero":
        assert normalize_fpi_signal(0.0, [float(i) for i in range(-5, 6)]) == 0.0
    elif case == "missing":
        assert normalize_fpi_signal(None, prior) is None
        assert normalize_fpi_signal(0.0, None) is None
    elif case == "last_window":
        # Latest 10 prior values are 10..19: median 14.5, MAD 2.5.
        assert normalize_fpi_signal(15.0, prior, window=10) == pytest.approx(0.5 / (1.4826 * 2.5))
        assert prior == [float(i) for i in range(20)]
    else:
        array: Any = np.arange(20, dtype=float)
        assert normalize_fpi_signal(10.0, array) == pytest.approx(0.5 / (1.4826 * 5))
