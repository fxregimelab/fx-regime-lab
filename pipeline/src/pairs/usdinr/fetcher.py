"""USDINR pair-specific data fetcher and signal pipeline."""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

import requests
from bs4 import BeautifulSoup

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
    _percentile_of_score,
    _retry_with_backoff,
    _yf_history,
    _yf_latest,
)
from src.signals.volatility import compute_realized_vol_rank_from_closes

logger = logging.getLogger(__name__)


class USDINRFetcher(PairPipeline):
    """USDINR data fetcher with RBI reserves, FPI, India VIX, forward premium, EM stress."""

    pair = "USDINR"

    def __init__(self, lookback_days: int = 30) -> None:
        super().__init__(lookback_days)

    # -- Existing sources ----------------------------------------------------

    def _fetch_spot_bars(self) -> list[SpotBar]:
        data = fetch_fx_spot(lookback_days=self.lookback_days)
        bars = data.get("USDINR", [])
        return bars

    def _fetch_spot(self) -> float | None:
        bars = self._fetch_spot_bars()
        if bars:
            return bars[-1].close
        return _retry_with_backoff(_yf_latest, "USDINR=X", f"{self.lookback_days}d")

    def _fetch_yields(self) -> dict[str, float | None]:
        return fetch_yields(lookback_days=self.lookback_days)

    def _fetch_cot(self) -> dict[str, Any]:
        try:
            rows = fetch_cot()
        except Exception as exc:  # noqa: BLE001
            logger.warning("COT fetch failed for USDINR: %s", exc)
            return {"net_long": None, "open_interest": None, "percentile": None}
        pair_rows = [r for r in rows if r.pair == "USDINR"]
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

    def _fetch_rbi_fx_reserves(self) -> float | None:
        """Scrape RBI FX reserves from latest press release page.

        TODO: RBI website structure changes frequently. Monitor and update XPath.
        """
        try:
            url = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            # Look for $ XXX.XX billion pattern
            m = re.search(r"\$\s*([0-9,]+\.?\d*)\s*billion", text, re.IGNORECASE)
            if m:
                return float(m.group(1).replace(",", ""))
            # Fallback: any large number with billion/crore
            m = re.search(r"([0-9,]+)\s*(billion|crore)", text, re.IGNORECASE)
            if m:
                return float(m.group(1).replace(",", ""))
            logger.warning("RBI reserves value not found in page text")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("RBI FX reserves fetch failed: %s", exc)
            return None

    def _fetch_fpi_flows(self) -> dict[str, Any]:
        """Fetch FPI flows from NSDL.

        TODO: NSDL page uses ASP.NET ViewState. Requires form POST.
        Consider manual CSV download or API if available in future.
        """
        return {
            "equity": None,
            "debt": None,
            "total": None,
            "note": "TODO: implement ASP.NET scraper for NSDL FPIS.aspx",
        }

    def _fetch_india_vix(self) -> float | None:
        """Fetch India VIX from NSE India API."""
        try:
            url = "https://www.nseindia.com/api/allIndices"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.nseindia.com/market-data/live-equity-market",
            }
            session = requests.Session()
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            resp = session.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            payload = resp.json()
            for item in payload.get("data", []):
                if item.get("index", "").upper() == "INDIA VIX":
                    return float(item.get("last", 0))
            logger.warning("India VIX not found in NSE response")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("India VIX fetch failed: %s", exc)
            return None

    def _fetch_inr_forward_premium(self) -> float | None:
        """Fetch INR forward premium from RBI reference rate archive.

        TODO: RBI archive requires form submission for date-specific data.
        """
        try:
            url = "https://www.rbi.org.in/scripts/ReferenceRateArchive.aspx"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            tables = soup.find_all("table")
            for table in tables:
                text = table.get_text(separator=" ", strip=True)
                if "USD" in text and "INR" in text:
                    m = re.search(r"([0-9]+\.?[0-9]*)", text)
                    if m:
                        return float(m.group(1))
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("INR forward premium fetch failed: %s", exc)
            return None

    def _fetch_em_stress_index(self) -> dict[str, Any]:
        """Composite EM stress index from BRL, ZAR, TRY vs USD (yfinance)."""
        tickers = {"BRL": "USDBRL=X", "ZAR": "USDZAR=X", "TRY": "USDTRY=X"}
        returns: dict[str, float | None] = {}
        for name, ticker in tickers.items():
            hist = _yf_history(ticker, period="5d")
            if hist is not None and len(hist) >= 2:
                try:
                    latest = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2])
                    returns[name] = (latest - prev) / prev * 100.0
                except Exception:  # noqa: BLE001
                    returns[name] = None
            else:
                returns[name] = None

        valid = [v for v in returns.values() if v is not None]
        if not valid:
            return {
                "components": returns,
                "composite": None,
                "stress_level": "UNKNOWN",
            }

        avg_return = sum(valid) / len(valid)
        composite = min(100.0, max(0.0, 50.0 + avg_return * 10.0))
        stress = "HIGH" if composite > 70 else "ELEVATED" if composite > 55 else "LOW"
        return {
            "components": returns,
            "composite": composite,
            "stress_level": stress,
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
            "rbi_fx_reserves": self._fetch_rbi_fx_reserves(),
            "fpi_flows": self._fetch_fpi_flows(),
            "india_vix": self._fetch_india_vix(),
            "inr_forward_premium": self._fetch_inr_forward_premium(),
            "em_stress": self._fetch_em_stress_index(),
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
        em_stress = data.get("em_stress") or {}

        us_10y = yields.get("us_10y")
        in_10y = yields.get("in_10y")
        rate_diff = None
        if us_10y is not None and in_10y is not None:
            rate_diff = us_10y - in_10y

        rate_signal = "NEUTRAL"
        if rate_diff is not None:
            rate_signal = (
                "BULLISH_USD"
                if rate_diff > 4.0
                else "BEARISH_USD"
                if rate_diff < 3.0
                else "NEUTRAL"
            )

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

        special_val = 0.0
        special_label = "NEUTRAL"

        # India VIX: local vol spike = INR stress = USDINR up
        india_vix = data.get("india_vix")
        if india_vix is not None and india_vix > 20:
            special_val -= 0.3
            special_label = "INDIA_VOL_SPIKE"

        # EM stress: high stress = EM outflows = INR weak
        em_comp = em_stress.get("composite")
        if em_comp is not None:
            if em_comp > 70:
                special_val -= 0.4
                special_label = f"{special_label}_EM_STRESS"
            elif em_comp < 40:
                special_val += 0.2
                special_label = f"{special_label}_EM_CALM"

        # RBI reserves drop = INR vulnerability
        reserves = data.get("rbi_fx_reserves")
        if reserves is not None and reserves < 550:
            special_val -= 0.3
            special_label = f"{special_label}_LOW_RESERVES"

        # FPI outflows
        fpi = data.get("fpi_flows") or {}
        fpi_total = fpi.get("total")
        if fpi_total is not None and fpi_total < 0:
            special_val -= 0.2
            special_label = f"{special_label}_FPI_OUTFLOW"

        stress = "HIGH" if vix is not None and vix > 30 else "NORMAL"
        if em_comp is not None and em_comp > 70:
            stress = "HIGH"

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
            if "STRESS" in special_label or "SPIKE" in special_label
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
            "em_stress_composite": em_comp,
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
            score += max(-1.0, min(1.0, rate_diff / 5.0)) * 0.40
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
