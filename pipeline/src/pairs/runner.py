"""Pair-specific pipeline runner.

Usage:
    python -m src.pairs.runner --pair EURUSD --date 2026-05-12
    python -m src.pairs.runner --all --date 2026-05-12
    python -m src.pairs.runner --pair EURUSD --backtest --start 2024-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Any

from src.db import writer
from src.fx_types import RegimeCall, SignalRow
from src.monitoring.portfolio_risk import PortfolioRiskManager
from src.monitoring.stress_controls import assess_stress_mode
from src.pairs.eurusd.composite import EURUSDComposite

# Pair-specific imports
from src.pairs.eurusd.fetcher import EURUSDFetcher
from src.pairs.usdinr.composite import USDINRComposite
from src.pairs.usdinr.fetcher import USDINRFetcher
from src.pairs.usdjpy.composite import USDJPYComposite
from src.pairs.usdjpy.fetcher import USDJPYFetcher
from src.regime.confidence import compute_confidence
from src.validation.engine import run_validation

logger = logging.getLogger(__name__)

_ALLOWED_PAIRS: tuple[str, ...] = ("EURUSD", "USDJPY", "USDINR")


def _pair_fetcher(pair: str) -> EURUSDFetcher | USDJPYFetcher | USDINRFetcher:
    if pair == "EURUSD":
        return EURUSDFetcher()
    if pair == "USDJPY":
        return USDJPYFetcher()
    if pair == "USDINR":
        return USDINRFetcher()
    raise ValueError(f"Unknown pair: {pair}")


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
    # High vol = negative score, low vol = positive score
    if vix > 30:
        return -1.0
    if vix > 25:
        return -0.5
    if vix < 15:
        return 0.5
    return 0.0


def _normalize_vol_signal_from_rv_rank(rv_rank: float | None) -> float | None:
    """Map realized-vol empirical CDF rank to [-1, 1] normalized score.

    High realized-vol rank (top decile) = negative score (-1.0).
    Low realized-vol rank (bottom decile) = positive score (+0.5).
    """
    if rv_rank is None:
        return None
    if rv_rank > 0.90:
        return -1.0
    if rv_rank > 0.75:
        return -0.5
    if rv_rank < 0.10:
        return 0.5
    return 0.0


def _rr_signal_from_z(z: float | None) -> str | None:
    """Map risk-reversal z-score to signal string."""
    if z is None:
        return None
    if z > 1.0:
        return "BULLISH"
    if z < -1.0:
        return "BEARISH"
    return "NEUTRAL"


def _normalize_oi_signal(oi_delta: float | None) -> float | None:
    """Map OI delta to [-1, 1] normalized score.

    Uses a heuristic scaling: ±100k OI change = full ±1.0 signal.
    Returns None when OI delta is unavailable.
    """
    if oi_delta is None:
        return None
    scaler = 100_000.0
    return max(-1.0, min(1.0, float(oi_delta) / scaler))


def _compute_v3_composite(
    pair: str,
    signals: dict[str, Any],
    vol_regime: str = "NEUTRAL",
    rate_regime: str = "NEUTRAL",
) -> float | None:
    """Compute v3 composite using pair-specific composite class."""
    rate_norm = _normalize_rate_signal(signals.get("rate_diff"), pair)
    cot_norm = _normalize_cot_signal(signals.get("cot_percentile"))
    # Prefer pair-specific realized-vol rank over equity VIX
    rv_rank = signals.get("realized_vol_rank")
    vol_norm = (
        _normalize_vol_signal_from_rv_rank(rv_rank)
        if rv_rank is not None
        else _normalize_vol_signal(signals.get("vix"))
    )
    oi_delta = signals.get("oi_delta")
    oi_norm = _normalize_oi_signal(oi_delta)

    if pair == "EURUSD":
        comp = EURUSDComposite(vol_regime=vol_regime, rate_regime=rate_regime)
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
        comp = USDJPYComposite(vol_regime=vol_regime, rate_regime=rate_regime)
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
        comp = USDINRComposite(vol_regime=vol_regime, rate_regime=rate_regime)
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


def _generate_ai_brief(
    pair: str,
    regime: str,
    confidence: float,
    composite: float,
    signals: dict[str, Any],
    date_str: str,
    dry_run: bool = False,
) -> str | None:
    """Generate AI brief unless dry-run or stress mode."""
    if dry_run:
        logger.info("[DRY-RUN] Skipping AI brief for %s", pair)
        return None

    try:
        from src.ai.client import generate_brief

        # Build a minimal SignalRow for the brief generator
        signal_row = SignalRow(
            pair=pair,
            date=date.fromisoformat(date_str),
            rate_diff_2y=signals.get("rate_diff"),
            rate_diff_10y=None,
            cot_percentile=signals.get("cot_percentile"),
            realized_vol_20d=signals.get("realized_vol_20d"),
            realized_vol_5d=None,
            implied_vol_30d=None,
            spot=None,
            day_change=None,
            day_change_pct=signals.get("day_change_pct"),
            cross_asset_vix=signals.get("cross_asset_vix"),
            cross_asset_dxy=signals.get("cross_asset_dxy"),
            cross_asset_oil=signals.get("cross_asset_oil"),
            cross_asset_us10y=None,
            cross_asset_gold=signals.get("cross_asset_gold"),
            cross_asset_copper=signals.get("cross_asset_copper"),
            cross_asset_stoxx=signals.get("cross_asset_stoxx"),
            oi_delta=signals.get("oi_delta"),
        )
        brief = generate_brief(
            pair=pair,
            regime=regime,
            confidence=confidence,
            composite=composite,
            signal_row=signal_row,
            date_str=date_str,
            primary_driver=signals.get("primary_driver"),
            polymarket_context="",
            dollar_dominance_pct=None,
            polymarket_odds_json="[]",
        )
        return brief
    except Exception as exc:
        logger.warning("AI brief generation failed for %s: %s", pair, exc)
        return None


def _write_to_db(
    call: RegimeCall,
    signals: dict[str, Any],
    brief: str | None,
    date_str: str,
    dry_run: bool = False,
    correlation_id: str | None = None,
) -> None:
    """Persist signals, regime call, and brief to the database."""
    if dry_run:
        logger.info("[DRY-RUN] Would write regime call for %s: %s", call.pair, call.regime)
        return

    # Write signal row (minimal — pair pipelines compute their own signals)
    signal_row = SignalRow(
        pair=call.pair,
        date=call.date,
        rate_diff_2y=signals.get("rate_diff"),
        rate_diff_10y=None,
        cot_percentile=signals.get("cot_percentile"),
        realized_vol_20d=signals.get("realized_vol_20d"),
        realized_vol_5d=None,
        implied_vol_30d=None,
        spot=None,
        day_change=None,
        day_change_pct=signals.get("day_change_pct"),
        cross_asset_vix=signals.get("cross_asset_vix"),
        cross_asset_dxy=signals.get("cross_asset_dxy"),
        cross_asset_oil=signals.get("cross_asset_oil"),
        cross_asset_us10y=None,
        cross_asset_gold=signals.get("cross_asset_gold"),
        cross_asset_copper=signals.get("cross_asset_copper"),
        cross_asset_stoxx=signals.get("cross_asset_stoxx"),
        oi_delta=signals.get("oi_delta"),
    )
    try:
        writer.write_signal_row(signal_row)
    except Exception as exc:
        logger.warning("Failed to write signal row for %s: %s", call.pair, exc)

    # Write regime call
    write_hash = writer.compute_write_hash(
        {
            "pair": call.pair,
            "date": date_str,
            "regime": call.regime,
            "composite": call.signal_composite,
            "signals": signals,
        }
    )
    try:
        writer.write_regime_call(
            call, correlation_id=correlation_id, write_hash=write_hash, model_version="v3"
        )
    except Exception as exc:
        logger.warning("Failed to write regime call for %s: %s", call.pair, exc)

    # Write brief if available
    if brief:
        try:
            writer.write_brief(
                date_str=date_str,
                pair=call.pair,
                regime=call.regime,
                confidence=call.confidence,
                composite=call.signal_composite,
                analysis=brief,
                primary_driver=call.primary_driver,
            )
        except Exception as exc:
            logger.warning("Failed to write brief for %s: %s", call.pair, exc)


def _run_validation_safe(as_of_date: date | None = None) -> None:
    try:
        run_validation(as_of_date=as_of_date)
    except Exception as exc:
        logger.warning("Validation run failed: %s", exc)


def _run_single_pair(
    pair: str,
    run_date: date,
    *,
    dry_run: bool = False,
    correlation_id: str | None = None,
    portfolio_manager: PortfolioRiskManager | None = None,
    stress_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the full pair-specific pipeline for one pair.

    Returns a result dict with keys: pair, success, regime, composite_v2,
    composite_v3, error, skipped.
    """
    result: dict[str, Any] = {
        "pair": pair,
        "success": False,
        "regime": None,
        "composite_v2": None,
        "composite_v3": None,
        "error": None,
        "skipped": False,
    }

    logger.info("Starting pipeline for %s on %s", pair, run_date.isoformat())
    t0 = time.perf_counter()

    try:
        fetcher = _pair_fetcher(pair)

        # 1. Fetch data
        data = fetcher.fetch_data()
        dqs = data.get("data_quality_score", 0.0)
        logger.info("%s data quality score: %.1f%%", pair, dqs)

        if dqs < 30.0:
            logger.warning("%s DQS %.1f%% too low — skipping", pair, dqs)
            result["skipped"] = True
            result["error"] = f"DQS {dqs:.1f}% below threshold"
            return result

        # 2. Compute signals
        signals = fetcher.compute_signals(data)

        # 2b. Enrich with cross-asset data for SignalRow / brief
        try:
            from src.fetchers.cross_asset import fetch_cross_asset
            cross = fetch_cross_asset(lookback_days=5)
            signals["cross_asset_vix"] = cross.get("vix")
            signals["cross_asset_dxy"] = cross.get("dxy")
            signals["cross_asset_oil"] = cross.get("oil")
            signals["cross_asset_gold"] = cross.get("gold")
            signals["cross_asset_copper"] = cross.get("copper")
            signals["cross_asset_stoxx"] = cross.get("stoxx")
        except Exception as exc:
            logger.debug("Cross-asset enrichment failed for %s: %s", pair, exc)

        # 3. Compute v2 composite (fetcher native)
        composite_v2 = fetcher.compute_composite(signals)
        result["composite_v2"] = composite_v2

        # 4. Compute v3 composite (pair-specific with interactions)
        vol_regime = "HIGH_VOL" if signals.get("vol_signal") == "HIGH_VOL" else "NEUTRAL"
        composite_v3 = _compute_v3_composite(pair, signals, vol_regime=vol_regime)
        result["composite_v3"] = composite_v3

        # Use v3 for regime classification if available, else v2
        composite_for_regime = composite_v3 if composite_v3 is not None else composite_v2

        # 5. Classify regime
        regime = fetcher.classify_regime(composite_for_regime, signals)
        result["regime"] = regime

        # Apply stress-mode overrides
        if stress_result and stress_result.get("is_stress"):
            conviction_cap = stress_result.get("conviction_cap", 5)
            current_conviction = signals.get("conviction", 3)
            if current_conviction > conviction_cap:
                signals["conviction"] = conviction_cap
                logger.info(
                    "%s conviction capped from %s to %s (stress mode)",
                    pair,
                    current_conviction,
                    conviction_cap,
                )

        # 6. Compute execution
        execution = fetcher.compute_execution(regime, signals)

        # Portfolio risk check
        if portfolio_manager is not None:
            risk_amount = 0.01 if execution.get("position_size") == "FULL" else 0.005
            if execution.get("entry_timing") != "ENTER":
                risk_amount = 0.0
            if risk_amount > 0.0 and not portfolio_manager.can_add_position(pair, risk_amount):
                logger.warning(
                    "%s rejected: would exceed portfolio heat (%.3f + %.3f)",
                    pair,
                    sum(portfolio_manager.positions.values()),
                    risk_amount,
                )
                execution["position_size"] = "HALF"
                execution["entry_timing"] = "WAIT"
            else:
                portfolio_manager.add_position(pair, risk_amount)

        # Compute confidence using v2-validated formula (0.30–0.90 scale)
        _rate_norm = _normalize_rate_signal(signals.get("rate_diff"), pair)
        _cot_norm = _normalize_cot_signal(signals.get("cot_percentile"))
        v3_confidence = compute_confidence(
            composite_for_regime,
            _rate_norm,
            _cot_norm,
            pair=pair,
            special_signal=signals.get("special_signal_value"),
        )

        # Build RegimeCall
        call = RegimeCall(
            pair=pair,
            date=run_date,
            regime=regime,
            confidence=v3_confidence,
            signal_composite=composite_for_regime,
            rate_signal=signals.get("rate_signal", "NEUTRAL"),
            primary_driver=signals.get("primary_driver"),
            entry_timing=execution.get("entry_timing"),
            position_size=execution.get("position_size"),
            stop_level=execution.get("stop_level"),
            data_quality_score=dqs / 100.0,
            stress_level=signals.get("stress_level"),
            predicted_direction=signals.get("predicted_direction"),
            directional_bias=signals.get("directional_bias"),
            conviction=signals.get("conviction"),
            cot_signal=signals.get("cot_signal"),
            vol_signal=signals.get("vol_signal"),
            oi_signal=signals.get("oi_signal"),
            rr_signal=_rr_signal_from_z(execution.get("risk_reversal_z")),
            special_signal_value=signals.get("special_signal_value"),
            special_signal_label=signals.get("special_signal_label"),
            model_version="v3",
        )

        # 7. Generate AI brief
        skip_ai = stress_result.get("skip_ai_briefs", False) if stress_result else False
        brief = None
        if not skip_ai:
            brief = _generate_ai_brief(
                pair,
                regime,
                call.confidence,
                composite_for_regime,
                signals,
                run_date.isoformat(),
                dry_run=dry_run,
            )

        # 8. Write to DB
        _write_to_db(
            call,
            signals,
            brief,
            run_date.isoformat(),
            dry_run=dry_run,
            correlation_id=correlation_id,
        )

        result["success"] = True
        logger.info(
            "%s complete: regime=%s v2=%.3f v3=%.3f (%.2fs)",
            pair,
            regime,
            composite_v2 or 0.0,
            composite_v3 or 0.0,
            time.perf_counter() - t0,
        )

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        result["error"] = error_msg
        logger.error("Pipeline failed for %s: %s", pair, error_msg)
        logger.debug(traceback.format_exc())
        if not dry_run:
            try:
                writer.write_pipeline_error(
                    step=f"pair_pipeline_{pair}",
                    error_type=type(exc).__name__,
                    message=str(exc),
                    traceback_str=traceback.format_exc(),
                    correlation_id=correlation_id,
                )
            except Exception:
                pass

    return result


def _assess_stress_safe() -> dict[str, Any]:
    """Run stress mode assessment with safe fallbacks."""
    try:
        from src.fetchers.cross_asset import fetch_cross_asset

        cross = fetch_cross_asset(lookback_days=5)
        vix = cross.get("vix")
        _ = cross.get("dxy")  # noqa: F841
        # Approximate overnight DXY move from cross_asset (not ideal but safe)
        dxy_move = None
        return assess_stress_mode(vix=vix, dxy_overnight_pct=dxy_move, max_pair_overnight_pct=None)
    except Exception as exc:
        logger.warning("Stress assessment failed: %s", exc)
        return {
            "active_modes": [],
            "max_position_size": 0.01,
            "conviction_cap": 5,
            "skip_ai_briefs": False,
            "reduce_existing": 0.0,
            "is_stress": False,
        }


def _run_backtest_mode(
    pair: str | None,
    start_str: str,
    end_str: str,
    verbose: bool = False,
) -> None:
    """Delegate to the backtest module."""
    from src.pairs.backtest import run_backtest

    run_backtest(
        pair=pair,
        start_date=date.fromisoformat(start_str),
        end_date=date.fromisoformat(end_str),
        verbose=verbose,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pair-specific pipeline runner")
    parser.add_argument("--pair", choices=_ALLOWED_PAIRS, help="Pair to run")
    parser.add_argument("--all", action="store_true", help="Run all pairs")
    parser.add_argument("--date", default=date.today().isoformat(), help="Run date (YYYY-MM-DD)")
    parser.add_argument("--backtest", action="store_true", help="Run backtest mode")
    parser.add_argument("--start", help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="Backtest end date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to DB")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--workers", type=int, default=3, help="Parallel workers for --all")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Backtest mode
    if args.backtest:
        if not args.start or not args.end:
            parser.error("--backtest requires --start and --end")
        pair = args.pair if args.pair else None
        _run_backtest_mode(pair, args.start, args.end, verbose=args.verbose)
        return 0

    # Normal pipeline mode
    run_date = date.fromisoformat(args.date)
    pairs_to_run: list[str] = []
    if args.all:
        pairs_to_run = list(_ALLOWED_PAIRS)
    elif args.pair:
        pairs_to_run = [args.pair]
    else:
        parser.error("Specify --pair or --all")

    correlation_id = str(uuid.uuid4())
    logger.info(
        "Pair pipeline start: date=%s pairs=%s cid=%s",
        run_date.isoformat(),
        pairs_to_run,
        correlation_id,
    )

    # Stress assessment
    stress_result = _assess_stress_safe()
    if stress_result.get("is_stress"):
        logger.warning(
            "Stress mode active: %s — max_position=%.4f conviction_cap=%s skip_ai=%s",
            stress_result["active_modes"],
            stress_result["max_position_size"],
            stress_result["conviction_cap"],
            stress_result["skip_ai_briefs"],
        )

    # Portfolio risk manager
    portfolio_manager = PortfolioRiskManager(max_portfolio_heat=0.03)

    results: list[dict[str, Any]] = []

    if len(pairs_to_run) == 1:
        # Sequential for single pair
        result = _run_single_pair(
            pairs_to_run[0],
            run_date,
            dry_run=args.dry_run,
            correlation_id=correlation_id,
            portfolio_manager=portfolio_manager,
            stress_result=stress_result,
        )
        results.append(result)
    else:
        # Parallel execution for --all
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    _run_single_pair,
                    pair,
                    run_date,
                    dry_run=args.dry_run,
                    correlation_id=correlation_id,
                    portfolio_manager=portfolio_manager,
                    stress_result=stress_result,
                ): pair
                for pair in pairs_to_run
            }
            for future in as_completed(futures):
                pair = futures[future]
                try:
                    result = future.result(timeout=300)
                except Exception as exc:
                    result = {
                        "pair": pair,
                        "success": False,
                        "error": f"Thread exception: {exc}",
                    }
                results.append(result)

    # Summary
    successes = [r for r in results if r.get("success")]
    failures = [r for r in results if not r.get("success") and not r.get("skipped")]
    skipped = [r for r in results if r.get("skipped")]

    logger.info(
        "Pipeline complete: %d success, %d failed, %d skipped",
        len(successes),
        len(failures),
        len(skipped),
    )

    for r in failures:
        logger.error("  FAILED %s: %s", r["pair"], r.get("error"))
    for r in skipped:
        logger.warning("  SKIPPED %s: %s", r["pair"], r.get("error"))

    # Write pipeline run record
    if not args.dry_run:
        try:
            writer.write_pipeline_run(
                {
                    "correlation_id": correlation_id,
                    "date": run_date.isoformat(),
                    "status": "COMPLETE" if not failures else "PARTIAL",
                    "pairs_processed": len(successes),
                    "pairs_skipped": len(skipped),
                    "ai_calls_made": len(successes),
                    "ai_calls_failed": 0,
                    "errors": [f"{r['pair']}: {r.get('error')}" for r in failures + skipped],
                }
            )
        except Exception as exc:
            logger.warning("Failed to write pipeline run record: %s", exc)

    # Run validation (non-blocking)
    _run_validation_safe(as_of_date=run_date)

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
