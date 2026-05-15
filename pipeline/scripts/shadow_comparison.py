"""Generate daily shadow comparison reports (v2 vs v3).

Usage:
    python -m scripts.shadow_comparison --date 2026-05-12
    python -m scripts.shadow_comparison --last 7
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.db import writer

logger = logging.getLogger(__name__)


def _get_comparison_rows(target_date: date) -> list[dict[str, Any]]:
    """Fetch v2 and v3 regime calls for *target_date* and return comparison rows.

    v2 legacy pipeline writes for the latest available spot-data date
    (often T-1), whereas v3 writes for the explicit run date.  The
    function still accepts *target_date* so callers can request a
    specific calendar day, but if no overlap exists on that day it
    falls back to the latest date where both model versions have data.
    """
    client = writer._client()

    # Helper: fetch rows for a given date
    def _fetch(date_str: str) -> list[dict[str, Any]]:
        return (
            client.table("regime_calls")
            .select("pair,regime,confidence,signal_composite,primary_driver,model_version")
            .eq("date", date_str)
            .execute()
            .data
            or []
        )

    rows = _fetch(target_date.isoformat())

    # Determine whether the target date has a meaningful v2+v3 overlap.
    # We need ALL 3 pairs with both versions present for a complete daily
    # comparison (3-pair lock: EURUSD, USDJPY, USDINR).
    pair_models: dict[str, set[str]] = {}
    for r in rows:
        pair = r["pair"]
        mv = r.get("model_version") or "v2"
        pair_models.setdefault(pair, set()).add("v3" if mv == "v3" else "v2")
    has_overlap = (
        len(pair_models) >= 3
        and all({"v2", "v3"} <= models for models in pair_models.values())
    )

    # If no overlap on the requested date, try the latest date where
    # both v2 and v3 exist for all 3 pairs.
    if not has_overlap:
        dates_res = (
            client.table("regime_calls")
            .select("date,model_version")
            .order("date", desc=True)
            .limit(500)
            .execute()
        )
        date_versions: dict[str, set[str]] = {}
        for r in dates_res.data or []:
            d = str(r["date"])[:10]
            mv = r.get("model_version") or "v2"
            date_versions.setdefault(d, set()).add("v3" if mv == "v3" else "v2")

        for d in sorted(date_versions.keys(), reverse=True):
            if {"v2", "v3"} <= date_versions[d]:
                candidate_rows = _fetch(d)
                cand_models: dict[str, set[str]] = {}
                for r in candidate_rows:
                    p = r["pair"]
                    mv = r.get("model_version") or "v2"
                    cand_models.setdefault(p, set()).add("v3" if mv == "v3" else "v2")
                if (
                    len(cand_models) >= 3
                    and all({"v2", "v3"} <= models for models in cand_models.values())
                ):
                    rows = candidate_rows
                    target_date = date.fromisoformat(d)
                    logger.info("Shadow comparison: using latest overlap date %s", d)
                    break

    # Group by pair
    by_pair: dict[str, dict[str, dict[str, Any]]] = {}
    for r in rows:
        pair = r["pair"]
        mv = r.get("model_version") or "v2"
        model = "v3" if mv == "v3" else "v2"
        by_pair.setdefault(pair, {})[model] = r

    results: list[dict[str, Any]] = []
    for pair in sorted(by_pair):
        v2 = by_pair[pair].get("v2", {})
        v3 = by_pair[pair].get("v3", {})
        results.append(
            {
                "date": target_date.isoformat(),
                "pair": pair,
                "v2_regime": v2.get("regime"),
                "v3_regime": v3.get("regime"),
                "v2_confidence": v2.get("confidence"),
                "v3_confidence": v3.get("confidence"),
                "v2_score": v2.get("signal_composite"),
                "v3_score": v3.get("signal_composite"),
                "regime_match": (v2.get("regime") == v3.get("regime"))
                if v2 and v3
                else None,
                "direction_match": (
                    (v2.get("primary_driver") or "")[0:3]
                    == (v3.get("primary_driver") or "")[0:3]
                )
                if v2 and v3
                else None,
            }
        )
    return results


def _daily_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate stats from comparison rows."""
    total = len(rows)
    if total == 0:
        return {"total_pairs": 0, "regime_match_rate": None, "avg_score_delta": None}

    regime_matches = sum(1 for r in rows if r.get("regime_match") is True)
    score_deltas = [
        (r["v3_score"] or 0.0) - (r["v2_score"] or 0.0)
        for r in rows
        if r.get("v2_score") is not None and r.get("v3_score") is not None
    ]
    return {
        "total_pairs": total,
        "regime_match_rate": regime_matches / total,
        "avg_score_delta": sum(score_deltas) / len(score_deltas) if score_deltas else None,
    }


def generate_report(
    start_date: date,
    end_date: date,
    *,
    output_dir: str | None = None,
) -> Path:
    """Generate a JSON report comparing v2 vs v3 across *start_date* to *end_date*."""
    out = Path(output_dir) if output_dir else Path(__file__).resolve().parent.parent / "reports"
    out.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, Any]] = []
    daily_summaries: dict[str, dict[str, Any]] = {}

    current = start_date
    seen_keys: set[tuple[str, str]] = set()
    while current <= end_date:
        rows = _get_comparison_rows(current)
        # Deduplicate by (date, pair) when multiple days fall back to the same overlap date
        for r in rows:
            key = (r["date"], r["pair"])
            if key not in seen_keys:
                seen_keys.add(key)
                all_rows.append(r)
        # Use the actual data date (may differ from *current* if fallback kicked in)
        effective_date = rows[0]["date"] if rows else current.isoformat()
        daily_summaries[effective_date] = _daily_summary(rows)
        current += timedelta(days=1)

    report = {
        "model_version": {
            "generated_at": date.today().isoformat(),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "daily_summaries": daily_summaries,
        "pair_details": all_rows,
    }

    tag = f"{start_date.isoformat()}_{end_date.isoformat()}"
    path = out / f"shadow_comparison_{tag}.json"
    path.write_text(json.dumps(report, indent=2, default=str))
    logger.info("Shadow comparison report written to %s", path)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V2 vs V3 shadow comparison report")
    parser.add_argument("--date", help="Single date (YYYY-MM-DD)")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--last", type=int, help="Last N days")
    parser.add_argument("--output-dir", help="Output directory")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    if args.date:
        start = end = date.fromisoformat(args.date)
    elif args.start and args.end:
        start = date.fromisoformat(args.start)
        end = date.fromisoformat(args.end)
    elif args.last:
        end = date.today()
        start = end - timedelta(days=args.last - 1)
    else:
        end = date.today()
        start = end - timedelta(days=6)

    try:
        path = generate_report(start, end, output_dir=args.output_dir)
        print(path)
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
