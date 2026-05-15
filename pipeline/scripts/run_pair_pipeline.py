#!/usr/bin/env python3
"""Run pair-specific FX regime pipeline for a single pair or all pairs.

Usage:
    python scripts/run_pair_pipeline.py --pair EURUSD --date 2026-05-12
    python scripts/run_pair_pipeline.py --pair USDJPY
    python scripts/run_pair_pipeline.py --pair USDINR --backtest --start 2025-01-01 --end 2026-05-01
    python scripts/run_pair_pipeline.py --pair ALL --output results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Any

# Ensure pipeline/src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.monitoring.stress_controls import assess_stress_mode
from src.pairs.eurusd.composite import EURUSDComposite
from src.pairs.eurusd.fetcher import EURUSDFetcher
from src.pairs.usdinr.composite import USDINRComposite
from src.pairs.usdinr.fetcher import USDINRFetcher
from src.pairs.usdjpy.composite import USDJPYComposite
from src.pairs.usdjpy.fetcher import USDJPYFetcher

logger = logging.getLogger(__name__)

_ALLOWED_PAIRS: tuple[str, ...] = ("EURUSD", "USDJPY", "USDINR")

_PAIR_FETCHERS: dict[str, type[EURUSDFetcher | USDJPYFetcher | USDINRFetcher]] = {
    "EURUSD": EURUSDFetcher,
    "USDJPY": USDJPYFetcher,
    "USDINR": USDINRFetcher,
}

_PAIR_COMPOSITES: dict[str, type[EURUSDComposite | USDJPYComposite | USDINRComposite]] = {
    "EURUSD": EURUSDComposite,
    "USDJPY": USDJPYComposite,
    "USDINR": USDINRComposite,
}


def _normalize_rate_signal(rate_diff: float | None, pair: str) -> float | None:
    """Map raw rate differential to a [-1, 1] normalized score."""
    if rate_diff is None:
        return None
    scaler = {"EURUSD": 2.0, "USDJPY": 4.0, "USDINR": 5.0}.get(pair, 3.0)
    return max(-1.0, min(1.0, rate_diff / scaler))


def _normalize_cot_signal(cot_percentile: float | None) -> float | None:
    if cot_percentile is None:
        return None
    return (cot_percentile - 50.0) / 50.0


def _normalize_vol_signal(vix: float | None) -> float | None:
    if vix is None:
        return None
    if vix > 30:
        return -1.0
    if vix > 25:
        return -0.5
    if vix < 15:
        return 0.5
    return 0.0


def _compute_v3_composite(
    pair: str,
    signals: dict[str, Any],
    vol_regime: str = "NEUTRAL",
    rate_regime: str = "NEUTRAL",
) -> float | None:
    """Compute v3 composite using pair-specific composite class."""
    rate_norm = _normalize_rate_signal(signals.get("rate_diff"), pair)
    cot_norm = _normalize_cot_signal(signals.get("cot_percentile"))
    vol_norm = _normalize_vol_signal(signals.get("vix"))
    oi_norm = None

    comp_cls = _PAIR_COMPOSITES[pair]
    comp = comp_cls(vol_regime=vol_regime, rate_regime=rate_regime)

    if pair == "EURUSD":
        return comp.score(
            rate_norm,
            cot_norm,
            vol_norm,
            oi_norm,
            ecb_bs_trajectory=None,
            bund_btp_spread=signals.get("btp_spread"),
            eu_hy_oas=signals.get("special_signal_value"),
        )
    if pair == "USDJPY":
        prox = signals.get("intervention_proximity")
        return comp.score(
            rate_norm,
            cot_norm,
            vol_norm,
            oi_norm,
            boj_intervention_proximity=prox / 100.0 if prox is not None else None,
            jpy_swap_stress=None,
            vix=vol_norm,
        )
    if pair == "USDINR":
        em = signals.get("em_stress_composite")
        reserves = signals.get("rbi_fx_reserves")
        return comp.score(
            rate_norm,
            cot_norm,
            vol_norm,
            oi_norm,
            rbi_reserves=(reserves - 600.0) / 100.0 if reserves is not None else None,
            fpi_flow=None,
            oil=None,
            dxy=None,
            em_stress=(em - 50.0) / 50.0 if em is not None else None,
            forward_premium=None,
        )
    return None


def run_single_pair(pair: str, run_date: date, *, dry_run: bool = True) -> dict[str, Any]:
    """Run the complete pair-specific pipeline for one pair."""
    result: dict[str, Any] = {
        "pair": pair,
        "date": run_date.isoformat(),
        "success": False,
        "composite_v2": None,
        "composite_v3": None,
        "regime": None,
        "execution": None,
        "stress_mode": None,
        "signals": None,
        "data_fetched": None,
        "error": None,
    }

    fetcher_cls = _PAIR_FETCHERS.get(pair)
    if fetcher_cls is None:
        result["error"] = f"Unknown pair: {pair}"
        return result

    logger.info("Running %s pipeline for %s", pair, run_date.isoformat())

    try:
        fetcher = fetcher_cls()

        # 1. Fetch data
        data = fetcher.fetch_data()
        dqs = data.get("data_quality_score", 0.0)
        result["data_fetched"] = list(data.keys())
        logger.info("%s data quality score: %.1f%%", pair, dqs)

        if dqs < 30.0:
            logger.warning("%s DQS %.1f%% too low — skipping", pair, dqs)
            result["error"] = f"DQS {dqs:.1f}% below threshold"
            return result

        # 2. Assess stress mode
        cross = data.get("cross_asset", {})
        stress = assess_stress_mode(
            vix=cross.get("vix"),
            dxy_overnight_pct=None,
            max_pair_overnight_pct=None,
        )
        result["stress_mode"] = stress

        # 3. Compute signals
        signals = fetcher.compute_signals(data)
        result["signals"] = signals

        # 4. Compute v2 composite (fetcher native)
        composite_v2 = fetcher.compute_composite(signals)
        result["composite_v2"] = composite_v2

        # 5. Compute v3 composite (pair-specific with interactions)
        vol_regime = "HIGH_VOL" if signals.get("vol_signal") == "HIGH_VOL" else "NEUTRAL"
        composite_v3 = _compute_v3_composite(pair, signals, vol_regime=vol_regime)
        result["composite_v3"] = composite_v3

        # Use v3 for regime classification if available, else v2
        composite_for_regime = composite_v3 if composite_v3 is not None else composite_v2

        # 6. Classify regime
        regime = fetcher.classify_regime(composite_for_regime, signals)
        result["regime"] = regime

        # 7. Compute execution
        execution = fetcher.compute_execution(regime, signals)
        result["execution"] = execution

        result["success"] = True
        logger.info(
            "%s result: composite_v2=%.3f composite_v3=%.3f regime=%s",
            pair, composite_v2 or 0, composite_v3 or 0, regime,
        )

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        result["error"] = error_msg
        logger.error("Pipeline failed for %s: %s", pair, error_msg)

    return result


def run_all_pairs(run_date: date, *, dry_run: bool = True) -> dict[str, Any]:
    """Run all three pairs in parallel."""
    results: dict[str, Any] = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(run_single_pair, pair, run_date, dry_run=dry_run): pair
            for pair in _ALLOWED_PAIRS
        }
        for future in as_completed(futures):
            pair = futures[future]
            try:
                results[pair] = future.result(timeout=300)
            except Exception as exc:
                results[pair] = {"pair": pair, "error": str(exc), "success": False}

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pair-specific FX pipeline")
    parser.add_argument(
        "--pair",
        choices=[*_ALLOWED_PAIRS, "ALL"],
        default="ALL",
        help="Pair to run (default: ALL)",
    )
    parser.add_argument("--date", default=date.today().isoformat(), help="Date to run (YYYY-MM-DD)")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--backtest", action="store_true", help="Run backtest mode")
    parser.add_argument("--start", help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="Backtest end date (YYYY-MM-DD)")
    parser.add_argument("--write-db", action="store_true", help="Write results to database")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Backtest mode delegates to the backtest module
    if args.backtest:
        if not args.start or not args.end:
            parser.error("--backtest requires --start and --end")
        from src.pairs.backtest import run_backtest

        run_backtest(
            pair=args.pair if args.pair != "ALL" else None,
            start_date=date.fromisoformat(args.start),
            end_date=date.fromisoformat(args.end),
            verbose=args.verbose,
        )
        return 0

    run_date = date.fromisoformat(args.date)
    dry_run = not args.write_db

    if args.pair == "ALL":
        results = run_all_pairs(run_date, dry_run=dry_run)
    else:
        results = {args.pair: run_single_pair(args.pair, run_date, dry_run=dry_run)}

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {args.output}")
    else:
        print(json.dumps(results, indent=2, default=str))

    return 0 if all(r.get("success") for r in results.values() if isinstance(r, dict)) else 1


if __name__ == "__main__":
    sys.exit(main())
