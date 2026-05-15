"""USDJPY pair-specific data fetcher and signal pipeline."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from src.fetchers.cot import fetch_cot
from src.fetchers.cross_asset import fetch_cross_asset
from src.fetchers.fx_spot import fetch_fx_spot
from src.fetchers.yields import fetch_yields
from src.fx_types import SpotBar
from src.logic.layer3_execution import (
    average_daily_range,
    mie_proxy_points,
    stop_buffer_and_level,
)
from src.pairs.base import (
    PairPipeline,
    _data_quality_score,
    _fred_latest,
    _percentile_of_score,
    _retry_with_backoff,
    _yf_latest,
)
from src.signals.volatility import compute_realized_vol_rank_from_closes

logger = logging.getLogger(__name__)


class USDJPYFetcher(PairPipeline):
    """USDJPY data fetcher with BoJ rate, Japan CPI, and intervention proximity."""

    pair = "USDJPY"

    def __init__(self, lookback_days: int = 30) -> None:
        super().__init__(lookback_days)

    # -- Existing sources ----------------------------------------------------

    def _fetch_spot_bars(self) -> list[SpotBar]:
        data = fetch_fx_spot(lookback_days=self.lookback_days)
        bars = data.get("USDJPY", [])
        return bars

    def _fetch_spot(self) -> float | None:
        bars = self._fetch_spot_bars()
        if bars:
            return bars[-1].close
        return _retry_with_backoff(_yf_latest, "USDJPY=X", f"{self.lookback_days}d")

    def _fetch_yields(self) -> dict[str, float | None]:
        return fetch_yields(lookback_days=self.lookback_days)

    def _fetch_cot(self) -> dict[str, Any]:
        try:
            rows = fetch_cot()
        except Exception as exc:  # noqa: BLE001
            logger.warning("COT fetch failed for USDJPY: %s", exc)
            return {"net_long": None, "open_interest": None, "percentile": None}
        pair_rows = [r for r in rows if r.pair == "USDJPY"]
        if not pair_rows:
            return {"net_long": None, "open_interest": None, "percentile": None}
        latest = pair_rows[-1]
        net_longs = [r.net_long for r in pair_rows]
        pct = _percentile_of_score(net_longs, latest.net_long)
        return {
            "net_long": latest.net_long,
            "open_interest": latest.open_interest,
            "percentile": pct,
        }

    def _fetch_cross_asset(self) -> dict[str, Any]:
        return fetch_cross_asset(lookback_days=self.lookback_days)

    # -- NEW sources ---------------------------------------------------------

    def _fetch_boj_rate(self) -> float | None:
        """BoJ policy rate (%). FRED: INTDSRJPM193N."""
        return _retry_with_backoff(_fred_latest, "INTDSRJPM193N")

    def _fetch_japan_cpi(self) -> float | None:
        """Japan CPI all items (2015=100). FRED: JPNCPIALLMINMEI."""
        return _retry_with_backoff(_fred_latest, "JPNCPIALLMINMEI")

    def _compute_intervention_proximity(self, spot: float | None) -> dict[str, float | None]:
        """Score proximity to historical BoJ intervention level (~150)."""
        if spot is None:
            return {
                "spot": None,
                "distance_from_150": None,
                "proximity_score": None,
            }
        distance = abs(spot - 150.0)
        score = max(0.0, 100.0 - distance * 5.0)
        return {
            "spot": spot,
            "distance_from_150": distance,
            "proximity_score": score,
        }

    # -- Orchestration -------------------------------------------------------

    def fetch_all(self) -> dict[str, Any]:
        spot_bars = self._fetch_spot_bars()
        return {
            "spot": self._fetch_spot(),
            "spot_bars": spot_bars,
            "yields": self._fetch_yields(),
            "cot": self._fetch_cot(),
            "cross_asset": self._fetch_cross_asset(),
            "boj_rate": self._fetch_boj_rate(),
            "japan_cpi": self._fetch_japan_cpi(),
            "intervention": self._compute_intervention_proximity(
                self._fetch_spot()
            ),
        }

    def fetch_data(self) -> dict[str, Any]:
        data = self.fetch_all()
        data["data_quality_score"] = _data_quality_score(data)
        data["pair"] = self.pair
        data["date"] = date.today()
        return data

    # -- Signal computation --------------------------------------------------

    def compute_signals(self, data: dict[str, Any]) -> dict[str, Any]:
        yields = data.get("yields") or {}
        cot = data.get("cot") or {}
        cross = data.get("cross_asset") or {}
        intervention = data.get("intervention") or {}

        us_10y = yields.get("us_10y")
        jp_10y = yields.get("jp_10y")
        rate_diff = None
        if us_10y is not None and jp_10y is not None:
            rate_diff = us_10y - jp_10y

        rate_signal = "NEUTRAL"
        if rate_diff is not None:
            rate_signal = (
                "BULLISH_USD"
                if rate_diff > 3.0
                else "BEARISH_USD"
                if rate_diff < 2.0
                else "NEUTRAL"
            )

        # BoJ hawkishness (positive rate) is JPY-positive = USDJPY-negative
        boj_rate = data.get("boj_rate")
        if boj_rate is not None and boj_rate > 0.0:
            rate_signal = "BEARISH_USD"

        cot_pct = cot.get("percentile")
        cot_signal = "NEUTRAL"
        if cot_pct is not None:
            cot_signal = (
                "CROWDED_LONG" if cot_pct > 75 else "CROWDED_SHORT" if cot_pct < 25 else "NEUTRAL"
            )

        # OI signal from COT open interest change
        oi_current = cot.get("open_interest")
        oi_signal = "NEUTRAL"
        oi_delta = None
        if oi_current is not None:
            # Simple heuristic: OI increase = more participation
            # For proper OI delta we need historical COT, but this is a start
            oi_delta = float(oi_current)
            if oi_delta > 0:
                oi_signal = "INCREASING"
            elif oi_delta < 0:
                oi_signal = "DECREASING"

        vix = cross.get("vix")
        vol_signal = "NEUTRAL"
        rv_rank = None
        if vix is not None:
            vol_signal = "HIGH_VOL" if vix > 25 else "LOW_VOL" if vix < 15 else "NEUTRAL"

        # Compute pair-specific realized vol rank from spot bars
        spot_bars = data.get("spot_bars", [])
        rv_rank = None
        realized_vol_20d = None
        day_change_pct = None
        if spot_bars:
            closes = [float(b.close) for b in spot_bars if b.close is not None]
            rv_rank = compute_realized_vol_rank_from_closes(closes)
            if rv_rank is not None:
                vol_signal = (
                    "HIGH_VOL"
                    if rv_rank > 0.88
                    else "LOW_VOL"
                    if rv_rank < 0.30
                    else "NEUTRAL"
                )
            # Compute actual 21d annualized realized vol for RR proxy
            if len(closes) >= 22:
                import numpy as np
                arr = np.asarray(closes, dtype=np.float64)
                lr = np.diff(np.log(arr))
                realized_vol_20d = float(np.std(lr[-21:], ddof=0) * np.sqrt(252.0) * 100.0)
            if len(closes) >= 2:
                day_change_pct = float((closes[-1] - closes[-2]) / closes[-2] * 100.0)

        prox = intervention.get("proximity_score")
        special_val = 0.0
        special_label = "NEUTRAL"
        if prox is not None and prox > 70:
            special_val = -0.5
            special_label = "INTERVENTION_RISK"

        cpi = data.get("japan_cpi")
        if cpi is not None and cpi > 105.0:
            special_val -= 0.2
            special_label = f"{special_label}_HIGH_CPI"

        stress = "HIGH" if vix is not None and vix > 30 else "NORMAL"

        score = 0.0
        if rate_signal == "BULLISH_USD":
            score += 1.0
        elif rate_signal == "BEARISH_USD":
            score -= 1.0
        if cot_signal == "CROWDED_SHORT":
            score += 0.5
        elif cot_signal == "CROWDED_LONG":
            score -= 0.5
        score += special_val

        pred = "BULLISH" if score > 0.5 else "BEARISH" if score < -0.5 else "NEUTRAL"
        bias = "LONG" if pred == "BULLISH" else "SHORT" if pred == "BEARISH" else "NEUTRAL"
        conv = max(
            1,
            min(
                3
                + (2 if rate_signal != "NEUTRAL" else 0)
                + (1 if cot_signal != "NEUTRAL" else 0)
                - (1 if vol_signal == "HIGH_VOL" else 0)
                + (1 if abs(special_val) > 0.3 else 0),
                10,
            ),
        )
        primary = (
            "SPECIAL"
            if "INTERVENTION" in special_label
            else "VOLATILITY"
            if vol_signal == "HIGH_VOL"
            else "RATES"
            if rate_signal != "NEUTRAL"
            else "COT"
            if cot_signal != "NEUTRAL"
            else "RATES"
        )

        return {
            "rate_signal": rate_signal,
            "rate_diff": rate_diff,
            "cot_signal": cot_signal,
            "cot_percentile": cot_pct,
            "vol_signal": vol_signal,
            "vix": vix,
            "special_signal_value": special_val,
            "special_signal_label": special_label,
            "intervention_proximity": prox,
            "spot_bars": spot_bars,
            "oi_signal": oi_signal,
            "oi_delta": oi_delta,
            "realized_vol_rank": rv_rank,
            "realized_vol_20d": realized_vol_20d,
            "day_change_pct": day_change_pct,
            "stress_level": stress,
            "primary_driver": primary,
            "predicted_direction": pred,
            "directional_bias": bias,
            "conviction": conv,
        }

    def compute_composite(self, signals: dict[str, Any]) -> float:
        rate_diff = signals.get("rate_diff")
        cot_pct = signals.get("cot_percentile")
        special = signals.get("special_signal_value", 0.0)
        vix = signals.get("vix")

        score = 0.0
        if rate_diff is not None:
            score += max(-1.0, min(1.0, rate_diff / 4.0)) * 0.40
        if cot_pct is not None:
            score += ((cot_pct - 50) / 50) * 0.20
        score += special * 0.25
        if vix is not None:
            score -= max(0, (vix - 20) / 20) * 0.15
        return max(-1.0, min(1.0, score))

    def classify_regime(self, composite: float, signals: dict[str, Any]) -> str:
        vol = signals.get("vol_signal")
        if vol == "HIGH_VOL":
            if composite > 0.3:
                return "BULLISH_VOLATILE"
            if composite < -0.3:
                return "BEARISH_VOLATILE"
            return "RANGING_VOLATILE"
        if composite > 0.5:
            return "BULLISH"
        if composite > 0.2:
            return "BULLISH_WEAK"
        if composite < -0.5:
            return "BEARISH"
        if composite < -0.2:
            return "BEARISH_WEAK"
        return "RANGING"

    def compute_execution(self, regime: str, signals: dict[str, Any]) -> dict[str, Any]:
        vol = signals.get("vol_signal")
        bias = signals.get("directional_bias", "NEUTRAL")
        entry = "ENTER" if "VOLATILE" not in regime else "WAIT"
        size = "HALF" if vol == "HIGH_VOL" else "FULL"

        # Compute stop levels from spot bars if available
        spot_bars = signals.get("spot_bars", [])
        adr = None
        mie = None
        buf = None
        stop_px = None
        if spot_bars:
            adr = average_daily_range(spot_bars, 20)
            mie = mie_proxy_points(spot_bars, bias, 20)
            spot = signals.get("spot")
            buf, stop_px = stop_buffer_and_level(spot, bias, adr, mie)

        # Synthetic risk-reversal proxy (realized vol × directional bias)
        rr_z = None
        rv20 = signals.get("realized_vol_20d")
        dcp = signals.get("day_change_pct")
        if rv20 is not None and dcp is not None:
            rr_z = rv20 * 0.3 * (1.0 if dcp > 0 else -1.0 if dcp < 0 else 0.0)

        return {
            "entry_timing": entry,
            "position_size": size,
            "stop_level": stop_px,
            "realized_vol_rank": signals.get("realized_vol_rank"),
            "skew_alignment": 0,
            "skew_reversal_flag": False,
            "risk_reversal_z": rr_z,
            "adr": adr,
            "mie_proxy": mie,
            "stop_buffer": buf,
        }
