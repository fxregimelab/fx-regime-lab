"""Read-only rescore audit for validation_log.

Recomputes T+5/T+20 metrics from ``historical_prices`` with the canonical
scorer (``src.validation.calculator.compute_horizon_metrics``) and diffs them
against the stored ``validation_log`` values, categorizing discrepancies:

- ``cross_pair_corrupt`` — stored gross return is implausibly large
  (|>2000| bps T+5, |>3000| bps T+20) and differs from the recomputed value
- ``gross_mismatch`` — gross return differs but stays within plausible bounds
- ``flag_mismatch`` — stored ``correct_t*`` disagrees with the recomputed flag
- ``net_mismatch`` — stored net bps / ``correct_net_t*`` disagrees
- ``brier_mismatch`` — stored Brier score disagrees
- ``cost_mismatch`` — stored ``cost_bps_t*`` disagrees with the canonical table
- ``no_prices`` — a scored horizon cannot be recomputed because no price
  observation exists at/before the target date (e.g. the live window sits
  beyond current ``historical_prices`` coverage)

READ-ONLY: this module issues SELECT queries only. It never writes to the
database. Credentials come from the process environment or repo-root
``.env.local`` (values are never printed). Price loading and spot resolution
are shared with ``_bulk_backfill_validation_rest`` so the audit resolves spots
exactly like the repaired backfill (pair-filtered rows, backward fill only, no
lookahead).

Usage (from ``pipeline/``)::

    .venv\\Scripts\\python.exe scripts\\audit_validation_rescore.py
    .venv\\Scripts\\python.exe scripts\\audit_validation_rescore.py \\
        --out ../reports/desk/research/rescore
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "pipeline") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "pipeline"))

from scripts._bulk_backfill_validation_rest import _get_spot, _load_prices  # noqa: E402
from src.db import writer  # noqa: E402
from src.validation.calculator import HorizonMetrics, compute_horizon_metrics  # noqa: E402
from src.validation.calendar import add_trading_days  # noqa: E402

T5 = "t5"
T20 = "t20"
_HORIZONS: tuple[str, ...] = (T5, T20)
_HORIZON_DAYS: dict[str, int] = {T5: 5, T20: 20}

# Plausibility bounds for stored gross log returns (T5, T20).
_CROSS_PAIR_LIMITS_BPS: dict[str, float] = {T5: 2000.0, T20: 3000.0}

GROSS_TOL_BPS = 0.05
NET_TOL_BPS = 0.05
BRIER_TOL = 1e-6
COST_TOL = 1e-6

CROSS_PAIR_CORRUPT = "cross_pair_corrupt"
GROSS_MISMATCH = "gross_mismatch"
FLAG_MISMATCH = "flag_mismatch"
NET_MISMATCH = "net_mismatch"
BRIER_MISMATCH = "brier_mismatch"
COST_MISMATCH = "cost_mismatch"
NO_PRICES = "no_prices"

CATEGORY_ORDER: tuple[str, ...] = (
    CROSS_PAIR_CORRUPT,
    GROSS_MISMATCH,
    FLAG_MISMATCH,
    NET_MISMATCH,
    BRIER_MISMATCH,
    COST_MISMATCH,
    NO_PRICES,
)

_VALIDATION_COLUMNS: tuple[str, ...] = (
    "id",
    "pair",
    "call_date",
    "date",
    "confidence",
    "predicted_direction",
    "call_id",
    "is_superseded",
    "log_return_t5_bps",
    "correct_t5",
    "brier_score_t5",
    "log_return_net_bps_t5",
    "correct_net_t5",
    "cost_bps_t5",
    "log_return_t20_bps",
    "correct_t20",
    "brier_score_t20",
    "log_return_net_bps_t20",
    "correct_net_t20",
    "cost_bps_t20",
)

_NOT_SUPERSEDED = "is_superseded.is.null,is_superseded.eq.false"


# ---------------------------------------------------------------------------
# Pure comparison / classification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HorizonRecompute:
    """Outcome of recomputing one horizon for a stored row."""

    metrics: HorizonMetrics | None
    not_due: bool = False


@dataclass(frozen=True)
class HorizonDiff:
    """Stored-vs-recomputed detail for one horizon."""

    horizon: str
    stored_gross_bps: float | None
    recomputed_gross_bps: float | None
    gross_diff_bps: float | None
    stored_correct: bool | None
    recomputed_correct: bool | None
    stored_net_bps: float | None
    recomputed_net_bps: float | None
    stored_correct_net: bool | None
    recomputed_correct_net: bool | None
    stored_cost_bps: float | None
    recomputed_cost_bps: float | None
    stored_brier: float | None
    recomputed_brier: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RowAudit:
    """Classification of one stored validation row."""

    row_id: Any
    pair: str
    call_date: str
    prediction: str
    categories: tuple[str, ...]
    diffs: tuple[HorizonDiff, ...]

    @property
    def worst_abs_gross_diff_bps(self) -> float:
        values = [abs(d.gross_diff_bps) for d in self.diffs if d.gross_diff_bps is not None]
        return max(values, default=0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "pair": self.pair,
            "call_date": self.call_date,
            "prediction": self.prediction,
            "categories": list(self.categories),
            "worst_abs_gross_diff_bps": self.worst_abs_gross_diff_bps,
            "diffs": [d.to_dict() for d in self.diffs],
        }


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def classify_row(
    stored: Mapping[str, Any],
    recomputed: Mapping[str, HorizonRecompute],
) -> RowAudit:
    """Compare one stored row against recomputed horizons (pure, no I/O).

    Only fields present in the stored row are compared. Flag/Brier comparisons
    require a prediction on the stored row; rows without one still compare
    gross/net bps and cost.
    """
    prediction = str(stored.get("predicted_direction") or "")
    flags_comparable = prediction.strip() != ""
    categories: list[str] = []
    diffs: list[HorizonDiff] = []

    for horizon in _HORIZONS:
        stored_gross = _as_float(stored.get(f"log_return_{horizon}_bps"))
        stored_correct = _as_bool(stored.get(f"correct_{horizon}"))
        stored_brier = _as_float(stored.get(f"brier_score_{horizon}"))
        if stored_gross is None and stored_correct is None and stored_brier is None:
            continue  # horizon not scored in the stored row

        result = recomputed.get(horizon)
        if result is None or result.not_due:
            continue  # nothing to compare against (or horizon not due yet)

        stored_net = _as_float(stored.get(f"log_return_net_bps_{horizon}"))
        stored_correct_net = _as_bool(stored.get(f"correct_net_{horizon}"))
        stored_cost = _as_float(stored.get(f"cost_bps_{horizon}"))
        metrics = result.metrics

        if metrics is None:
            categories.append(NO_PRICES)
            diffs.append(
                HorizonDiff(
                    horizon=horizon,
                    stored_gross_bps=stored_gross,
                    recomputed_gross_bps=None,
                    gross_diff_bps=None,
                    stored_correct=stored_correct,
                    recomputed_correct=None,
                    stored_net_bps=stored_net,
                    recomputed_net_bps=None,
                    stored_correct_net=stored_correct_net,
                    recomputed_correct_net=None,
                    stored_cost_bps=stored_cost,
                    recomputed_cost_bps=None,
                    stored_brier=stored_brier,
                    recomputed_brier=None,
                )
            )
            continue

        gross_diff = None if stored_gross is None else stored_gross - metrics.log_return_bps
        net_diff = None if stored_net is None else stored_net - metrics.log_return_net_bps

        if (
            stored_gross is not None
            and gross_diff is not None
            and abs(gross_diff) > GROSS_TOL_BPS
        ):
            if abs(stored_gross) > _CROSS_PAIR_LIMITS_BPS[horizon]:
                categories.append(CROSS_PAIR_CORRUPT)
            else:
                categories.append(GROSS_MISMATCH)
        if (
            flags_comparable
            and stored_correct is not None
            and stored_correct != metrics.correct
        ):
            categories.append(FLAG_MISMATCH)
        if (net_diff is not None and abs(net_diff) > NET_TOL_BPS) or (
            flags_comparable
            and stored_correct_net is not None
            and stored_correct_net != metrics.correct_net
        ):
            categories.append(NET_MISMATCH)
        recomputed_brier = metrics.brier_score
        if (
            flags_comparable
            and stored_brier is not None
            and (recomputed_brier is None or abs(stored_brier - recomputed_brier) > BRIER_TOL)
        ):
            categories.append(BRIER_MISMATCH)
        if stored_cost is not None and abs(stored_cost - metrics.cost_bps) > COST_TOL:
            categories.append(COST_MISMATCH)

        diffs.append(
            HorizonDiff(
                horizon=horizon,
                stored_gross_bps=stored_gross,
                recomputed_gross_bps=metrics.log_return_bps,
                gross_diff_bps=gross_diff,
                stored_correct=stored_correct,
                recomputed_correct=metrics.correct if flags_comparable else None,
                stored_net_bps=stored_net,
                recomputed_net_bps=metrics.log_return_net_bps,
                stored_correct_net=stored_correct_net,
                recomputed_correct_net=metrics.correct_net if flags_comparable else None,
                stored_cost_bps=stored_cost,
                recomputed_cost_bps=metrics.cost_bps,
                stored_brier=stored_brier,
                recomputed_brier=recomputed_brier if flags_comparable else None,
            )
        )

    return RowAudit(
        row_id=stored.get("id"),
        pair=str(stored.get("pair") or ""),
        call_date=str(stored.get("call_date") or stored.get("date") or ""),
        prediction=prediction,
        categories=tuple(dict.fromkeys(categories)),
        diffs=tuple(diffs),
    )


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value[:10])
    return None


def recompute_horizons(
    stored: Mapping[str, Any],
    prices: Mapping[date, float],
    as_of: date,
) -> dict[str, HorizonRecompute]:
    """Recompute T+5/T+20 for one stored row from its pair's prices (pure)."""
    call_date = _parse_date(stored.get("call_date") or stored.get("date"))
    if call_date is None:
        return {horizon: HorizonRecompute(metrics=None) for horizon in _HORIZONS}

    prediction = str(stored.get("predicted_direction") or "")
    confidence = float(stored.get("confidence") or 0.0)
    pair = str(stored.get("pair") or "")
    s0 = _get_spot(prices, call_date)

    out: dict[str, HorizonRecompute] = {}
    for horizon in _HORIZONS:
        target = add_trading_days(call_date, _HORIZON_DAYS[horizon])
        if as_of < target:
            out[horizon] = HorizonRecompute(metrics=None, not_due=True)
            continue
        if s0 is None:
            out[horizon] = HorizonRecompute(metrics=None)
            continue
        sh = _get_spot(prices, target)
        out[horizon] = HorizonRecompute(
            metrics=compute_horizon_metrics(s0, sh, prediction, confidence, pair)
        )
    return out


# ---------------------------------------------------------------------------
# Read-only loading
# ---------------------------------------------------------------------------


def _missing_column(message: str) -> str | None:
    """Extract a column name from a PostgREST unknown-column error, if any."""
    marker = "Could not find the '"
    if marker in message:
        return message.split(marker, 1)[1].split("'", 1)[0]
    marker2 = "column validation_log."
    if marker2 in message:
        return message.split(marker2, 1)[1].split(" ", 1)[0]
    return None


def _fetch_pages(
    client: Any,
    table: str,
    columns: Sequence[str],
    or_filter: str | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    page_size = 1000
    while True:
        query: Any = client.table(table).select(",".join(columns))
        if or_filter is not None:
            query = query.or_(or_filter)
        res = query.order("id").range(start, start + page_size - 1).execute()
        page = cast(list[dict[str, Any]], res.data or [])
        if not page:
            break
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return rows


def _fetch_rows(
    table: str,
    columns: Sequence[str],
    *,
    or_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Paginated SELECT that strips columns the live schema does not have."""
    client = writer._client()
    working = list(columns)
    while True:
        try:
            return _fetch_pages(client, table, working, or_filter)
        except Exception as exc:
            message = str(getattr(exc, "message", "")) or str(exc)
            missing = _missing_column(message)
            if missing is not None and missing in working:
                working.remove(missing)
                continue
            raise


def _load_call_predictions() -> dict[Any, str]:
    """Map regime_calls.id → prediction, used when a validation row lacks one."""
    rows = _fetch_rows("regime_calls", ("id", "predicted_direction", "rate_signal"))
    predictions: dict[Any, str] = {}
    for row in rows:
        call_id = row.get("id")
        if call_id is None:
            continue
        predictions[call_id] = str(
            row.get("predicted_direction") or row.get("rate_signal") or ""
        )
    return predictions


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def build_report(as_of: date) -> dict[str, Any]:
    """Run the read-only audit and return the report payload."""
    prices = _load_prices()
    rows = _fetch_rows("validation_log", _VALIDATION_COLUMNS, or_filter=_NOT_SUPERSEDED)
    predictions = _load_call_predictions()

    checked = 0
    unscored = 0
    issues: list[RowAudit] = []
    for row in rows:
        if not row.get("predicted_direction") and row.get("call_id") in predictions:
            row["predicted_direction"] = predictions[row["call_id"]]

        pair = str(row.get("pair") or "")
        recomputed = recompute_horizons(row, prices.get(pair, {}), as_of)

        scored = any(
            row.get(f"log_return_{horizon}_bps") is not None
            or row.get(f"correct_{horizon}") is not None
            or row.get(f"brier_score_{horizon}") is not None
            for horizon in _HORIZONS
        )
        if not scored:
            unscored += 1
            continue
        checked += 1

        entry = classify_row(row, recomputed)
        if entry.categories:
            issues.append(entry)

    category_counts = Counter(cat for entry in issues for cat in entry.categories)
    worst = sorted(
        issues,
        key=lambda entry: (
            -entry.worst_abs_gross_diff_bps,
            -len(entry.categories),
            entry.call_date,
        ),
    )[:20]
    coverage = {
        pair: max(series).isoformat() for pair, series in prices.items() if series
    }

    return {
        "as_of": as_of.isoformat(),
        "read_only": True,
        "rows_loaded_non_superseded": len(rows),
        "rows_checked_scored": checked,
        "rows_unscored": unscored,
        "rows_with_issues": len(issues),
        "category_counts": {cat: category_counts.get(cat, 0) for cat in CATEGORY_ORDER},
        "price_coverage_end": coverage,
        "worst": [entry.to_dict() for entry in worst],
        "issues": [entry.to_dict() for entry in issues],
    }


def _fmt_bps(value: Any) -> str:
    if value is None:
        return "—"
    return f"{float(value):.2f}"


def _diff_for(entry: Mapping[str, Any], horizon: str) -> Mapping[str, Any] | None:
    for diff in entry.get("diffs", []):
        if diff.get("horizon") == horizon:
            return cast(Mapping[str, Any], diff)
    return None


def _print_summary(report: Mapping[str, Any]) -> None:
    print(f"as_of: {report['as_of']} (read-only audit)")
    print(
        f"non-superseded rows loaded: {report['rows_loaded_non_superseded']} | "
        f"scored rows checked: {report['rows_checked_scored']} | "
        f"unscored skipped: {report['rows_unscored']}"
    )
    print(f"rows with at least one issue: {report['rows_with_issues']}")
    print("price coverage end:", report["price_coverage_end"])
    print("category counts:")
    for cat in CATEGORY_ORDER:
        print(f"  {cat}: {report['category_counts'][cat]}")
    print("worst 20 rows (by |gross diff|):")
    for entry in report["worst"]:
        detail = []
        for horizon in _HORIZONS:
            diff = _diff_for(entry, horizon)
            if diff is None or (
                diff["stored_gross_bps"] is None and diff["recomputed_gross_bps"] is None
            ):
                continue
            detail.append(
                f"{horizon} stored={_fmt_bps(diff['stored_gross_bps'])} "
                f"recomputed={_fmt_bps(diff['recomputed_gross_bps'])}"
            )
        print(
            f"  id={entry['row_id']} {entry['pair']} {entry['call_date']} "
            f"pred={entry['prediction']} cats={','.join(entry['categories'])} "
            f"| {' ; '.join(detail)}"
        )


def _render_markdown(report: Mapping[str, Any]) -> str:
    lines: list[str] = [
        f"# Validation rescore audit — {report['as_of']}",
        "",
        "Read-only audit (`pipeline/scripts/audit_validation_rescore.py`): stored "
        "non-superseded `validation_log` rows recomputed from `historical_prices` "
        "with the canonical scorer (`src/validation/calculator.py`). No database "
        "writes were performed.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Non-superseded rows loaded | {report['rows_loaded_non_superseded']} |",
        f"| Scored rows checked | {report['rows_checked_scored']} |",
        f"| Unscored rows skipped | {report['rows_unscored']} |",
        f"| Rows with at least one issue | {report['rows_with_issues']} |",
        "",
        "Price coverage end (max `historical_prices` date per pair):",
        "",
    ]
    for pair, day in sorted(report["price_coverage_end"].items()):
        lines.append(f"- {pair}: {day}")
    lines.extend(
        [
            "",
            "## Category counts",
            "",
            "| Category | Rows |",
            "| --- | --- |",
        ]
    )
    for cat in CATEGORY_ORDER:
        lines.append(f"| `{cat}` | {report['category_counts'][cat]} |")
    lines.extend(
        [
            "",
            "## Worst 20 rows",
            "",
            "| id | pair | call_date | prediction | categories | T+5 stored bps | "
            "T+5 recomputed bps | T+20 stored bps | T+20 recomputed bps |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for entry in report["worst"]:
        d5 = _diff_for(entry, T5)
        d20 = _diff_for(entry, T20)
        lines.append(
            f"| {entry['row_id']} | {entry['pair']} | {entry['call_date']} | "
            f"{entry['prediction']} | {', '.join(entry['categories'])} | "
            f"{_fmt_bps(d5['stored_gross_bps']) if d5 else '—'} | "
            f"{_fmt_bps(d5['recomputed_gross_bps']) if d5 else '—'} | "
            f"{_fmt_bps(d20['stored_gross_bps']) if d20 else '—'} | "
            f"{_fmt_bps(d20['recomputed_gross_bps']) if d20 else '—'} |"
        )
    lines.append("")
    return "\n".join(lines)


def _resolve_out_paths(out: str) -> tuple[Path, Path]:
    path = Path(out)
    if path.is_dir() or out.endswith(("/", "\\")):
        base = path / "validation_rescore_audit"
    elif path.suffix in {".json", ".md"}:
        base = path.with_suffix("")
    else:
        base = path
    return base.with_suffix(".json"), base.with_suffix(".md")


def _load_env_local() -> None:
    """Populate ``os.environ`` from repo-root ``.env.local`` (values never printed)."""
    path = REPO_ROOT / ".env.local"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name.startswith("export "):
            name = name[len("export ") :].strip()
        if name and name not in os.environ:
            os.environ[name] = value.strip().strip('"').strip("'")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only validation_log rescore audit")
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "Optional report path prefix or directory. Writes <out>.json and <out>.md "
            "(defaults to validation_rescore_audit.* inside a directory target)."
        ),
    )
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        help="Evaluation date (default: today)",
    )
    args = parser.parse_args(argv)

    _load_env_local()
    as_of = args.as_of or date.today()
    report = build_report(as_of)
    _print_summary(report)

    if args.out:
        json_path, md_path = _resolve_out_paths(str(args.out))
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        md_path.write_text(_render_markdown(report), encoding="utf-8")
        print(f"wrote {json_path}")
        print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
