"""Immutable private research decisions and later, explicitly hypothetical outcomes."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.private_desk.engine import METHOD_VERSION, Costs, simulate_trade, validate_bars
from src.private_desk.universe import PAIRS, UNIVERSE_VERSION

METHOD = "private-outcomes-v1"
SOURCE_FAILURES = {
    "SOURCE_FILE_MISSING": "Restore the exact saved source or capture a new version.",
    "SOURCE_READ_FAILED": "Check local source access and retry with the original retained.",
    "SOURCE_HASH_MISMATCH": "Investigate altered bytes; never silently reuse this receipt.",
    "SOURCE_IDENTITY_MISMATCH": "Capture the correct pair and daily interval.",
    "RECEIPT_CLOCK_INVALID": "Repair the receipt binding; do not invent a historical clock.",
    "SOURCE_PATH_INVALID": "Use a saved capture inside the private state directory.",
    "BAR_SCHEMA_INVALID": "Check original OHLC and quarantine malformed observations.",
    "SOURCE_CAPTURE_INVALID": "Inspect the original source schema and receipt.",
}
LIMITS = [
    "Hypothetical daily-price benchmarks; actual executions are NOT_RECORDED.",
    "Provider reconstruction and assumed costs; not executable broker fills.",
    "BUY and SELL are frozen separately; the better later result is not a prediction.",
    "Repeated report versions and overlapping horizons are not independent trials.",
    "Pending or unavailable outcomes are excluded from result averages, not treated as losses.",
    "This journal does not qualify forecasts, learn automatically or change thresholds.",
    "Local hashes detect accidental alteration; no external notarization or tamper-proof claim.",
]


class SourceFailureError(ValueError):
    """A bounded source failure code, without provider or exception text."""


def _failure(exc: Exception) -> str:
    if isinstance(exc, SourceFailureError) and str(exc) in SOURCE_FAILURES:
        return str(exc)
    if isinstance(exc, FileNotFoundError):
        return "SOURCE_FILE_MISSING"
    if isinstance(exc, OSError):
        return "SOURCE_READ_FAILED"
    return "SOURCE_CAPTURE_INVALID"


def _json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _clock(now: datetime | None) -> datetime:
    value = datetime.now(UTC) if now is None else now
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Journal clocks must include a timezone")
    return value.astimezone(UTC)


def _stamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Source clock is missing")
    return _clock(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _next_weekday(day: date) -> date:
    result = day + timedelta(days=1)
    while result.weekday() >= 5:
        result += timedelta(days=1)
    return result


def _put(path: Path, raw: bytes) -> None:
    """Publish a complete file using a no-overwrite hard link on the same filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("." + uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            if path.read_bytes() != raw:
                raise ValueError("Immutable journal identity has conflicting bytes") from None
    finally:
        temp.unlink(missing_ok=True)


def _envelope(payload: dict[str, Any]) -> bytes:
    return _json({"payload": payload, "sha256": _hash(_json(payload))})


def _read(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError("Journal event exceeds size bound")
    value = json.loads(raw)
    if not isinstance(value, dict) or not isinstance(value.get("payload"), dict):
        raise ValueError("Malformed journal event")
    payload: dict[str, Any] = value["payload"]
    if value.get("sha256") != _hash(_json(payload)) or payload.get("method") != METHOD:
        raise ValueError("Journal event hash or method is invalid")
    return payload


def _rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(report, dict):
        raise ValueError("Report must be an object")
    rows = report.get("pair_reports")
    if (
        report.get("universe_version") != UNIVERSE_VERSION
        or report.get("universe") != list(PAIRS)
        or not isinstance(rows, list)
        or len(rows) != len(PAIRS)
        or any(not isinstance(row, dict) or row.get("pair") not in PAIRS for row in rows)
        or len({row["pair"] for row in rows}) != len(PAIRS)
    ):
        raise ValueError("Journal requires the complete versioned eight-pair universe")
    if any(
        not isinstance(row.get(key, {}), dict)
        for row in rows
        for key in ("candidate", "source_metadata", "backtest")
    ):
        raise ValueError("Candidate, source receipt and backtest must be objects")
    return {row["pair"]: row for row in rows}


def _history(
    row: dict[str, Any], state_dir: Path, now: datetime, *, snapshot: bool = False
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta = row.get("source_metadata")
    if not isinstance(meta, dict) or meta.get("pair") != row["pair"]:
        raise SourceFailureError("SOURCE_IDENTITY_MISMATCH")
    original = Path(meta["capture_path"]).resolve()
    if not original.is_relative_to(state_dir.resolve()):
        raise SourceFailureError("SOURCE_PATH_INVALID")
    digest = meta.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)
    ):
        raise SourceFailureError("SOURCE_HASH_MISMATCH")
    path = state_dir / "journal" / "sources" / (digest + ".json") if snapshot else original
    raw = path.read_bytes()
    if _hash(raw) != meta.get("sha256"):
        raise SourceFailureError("SOURCE_HASH_MISMATCH")
    try:
        received = _stamp(meta.get("received_at", meta.get("retrieved_at")))
    except (ValueError, TypeError):
        raise SourceFailureError("RECEIPT_CLOCK_INVALID") from None
    if received > now or meta.get("interval") != "1d":
        raise SourceFailureError("RECEIPT_CLOCK_INVALID")
    capture = json.loads(raw)
    if capture.get("pair") != row["pair"] or capture.get("interval") != "1d":
        raise SourceFailureError("SOURCE_IDENTITY_MISMATCH")
    embedded = capture.get("metadata", {})
    if _stamp(embedded.get("received_at", embedded.get("retrieved_at"))) != received:
        raise SourceFailureError("RECEIPT_CLOCK_INVALID")
    try:
        bars = validate_bars(capture["bars"])
    except (ValueError, TypeError, KeyError):
        raise SourceFailureError("BAR_SCHEMA_INVALID") from None
    if any(
        len(bar["time"]) != 10 or date.fromisoformat(bar["time"]).weekday() >= 5 for bar in bars
    ):
        raise SourceFailureError("BAR_SCHEMA_INVALID")
    cutoff = min(now.date(), received.date()).isoformat()
    return [bar for bar in bars if bar["time"] < cutoff], meta


def _risk(bars: list[dict[str, Any]], as_of: Any) -> float | None:
    if not isinstance(as_of, str):
        return None
    available = [bar for bar in bars if bar["time"] <= as_of]
    if len(available) < 15 or available[-1]["time"] != as_of:
        return None
    window = available[-15:]
    if any(bar.get("gap_before") for bar in window[1:]):
        return None
    ranges = [
        max(
            bar["high"] - bar["low"],
            abs(bar["high"] - previous["close"]),
            abs(bar["low"] - previous["close"]),
        )
        for previous, bar in zip(window, window[1:], strict=False)
    ]
    risk = 1.5 * sum(ranges) / 14
    return risk if math.isfinite(risk) and risk > 0 else None


def _candidate_risk(candidate: dict[str, Any]) -> float | None:
    side = candidate.get("direction")
    values: list[Any] = [candidate.get(key) for key in ("entry", "stop", "tp1", "tp2")]
    if side not in ("BUY", "SELL") or any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
        for value in values
    ):
        return None
    entry, stop, tp1, tp2 = (float(value) for value in values)
    sign = 1 if side == "BUY" else -1
    risk = sign * (entry - stop)
    if (
        risk <= 0
        or not math.isclose(sign * (tp1 - entry), risk, rel_tol=1e-8)
        or not math.isclose(sign * (tp2 - entry), 3 * risk, rel_tol=1e-8)
    ):
        return None
    return risk


def record_report(
    state_dir: Path, report_path: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    """Freeze all decisions at the real recording time; identical reports are idempotent."""
    stamp = _clock(now)
    raw = report_path.read_bytes()
    report_hash = _hash(raw)
    directory = state_dir / "journal"
    target = directory / "decisions" / (report_hash + ".json")
    if target.exists():
        prior = _read(target)
        if prior.get("report_sha256") != report_hash:
            raise ValueError("Journal report identity changed")
        if _hash((directory / "reports" / (report_hash + ".json")).read_bytes()) != report_hash:
            raise ValueError("Journal report snapshot changed")
        return prior
    report = json.loads(raw)
    rows = _rows(report)
    if _stamp(report["generated_at"]) > stamp:
        raise ValueError("Cannot record a report from the future")
    first_entry = _next_weekday(stamp.date())
    decisions = []
    for pair in PAIRS:
        row = rows[pair]
        candidate = row.get("candidate", {})
        if not isinstance(candidate, dict):
            raise ValueError("Candidate must be an object")
        risk = None
        evidence_error = None
        try:
            bars, _ = _history(row, state_dir, stamp)
            risk = _risk(bars, candidate.get("as_of"))
            meta = row["source_metadata"]
            source_raw = Path(meta["capture_path"]).read_bytes()
            if _hash(source_raw) != meta["sha256"]:
                raise ValueError("Source changed during journal recording")
            _put(directory / "sources" / (meta["sha256"] + ".json"), source_raw)
        except (KeyError, OSError, ValueError, TypeError) as exc:
            evidence_error = _failure(exc)
        horizon = candidate.get("holding_days")
        if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon not in (3, 5):
            horizon = None
        decisions.append(
            {
                "decision_id": _hash((report_hash + ":" + pair).encode()),
                "observation_id": _hash(
                    _json(
                        {
                            "universe_version": UNIVERSE_VERSION,
                            "pair": pair,
                            "candidate": candidate,
                            "source_sha256": row.get("source_metadata", {}).get("sha256"),
                            "engine_method": row.get("backtest", {}).get(
                                "method_version", METHOD_VERSION
                            ),
                        }
                    )
                ),
                "pair": pair,
                "recorded_at": stamp.isoformat(),
                "earliest_entry_date": first_entry.isoformat(),
                "candidate": candidate,
                "source_metadata": row.get("source_metadata", {}),
                "engine_method": row.get("backtest", {}).get("method_version", METHOD_VERSION),
                "execution_state": "NOT_RECORDED",
                "forecast_qualification": "UNQUALIFIED",
                "benchmark": {
                    "directions": ["BUY", "SELL"],
                    "holding_days": horizon,
                    "risk_distance": risk,
                    "candidate_risk_distance": _candidate_risk(candidate)
                    if risk is not None
                    else None,
                    "risk_basis": "1.5 times 14-day ATR ending at the frozen observation date",
                    "costs": asdict(Costs()),
                    "partial_exit": "50% +1R; remainder stop to entry, target +3R",
                    "source_error": evidence_error,
                    "kind": "COUNTERFACTUAL_RESEARCH",
                },
            }
        )
    payload = {
        "method": METHOD,
        "kind": "REPORT_DECISIONS",
        "recorded_at": stamp.isoformat(),
        "report_sha256": report_hash,
        "report_generated_at": report["generated_at"],
        "universe_version": UNIVERSE_VERSION,
        "decisions": decisions,
    }
    _put(directory / "reports" / (report_hash + ".json"), raw)
    try:
        _put(target, _envelope(payload))
    except ValueError:
        # A concurrent recording of these exact report bytes owns the first clock.
        if target.exists():
            prior = _read(target)
            if prior.get("report_sha256") == report_hash:
                return prior
        raise
    return payload


def commit_publication(state_dir: Path, report_path: Path, *, now: datetime | None = None) -> None:
    """Count a publication only after its exact bytes are verified in the current projection."""
    raw = report_path.read_bytes()
    digest = _hash(raw)
    if (state_dir / "report.json").read_bytes() != raw:
        raise ValueError("Report was not made current; its journal decision remains unpublished")
    decision = _read(state_dir / "journal" / "decisions" / (digest + ".json"))
    stamp = _clock(now)
    if stamp < _stamp(decision["recorded_at"]):
        raise ValueError("Publication precedes recording")
    target = state_dir / "journal" / "publications" / (digest + ".json")
    if target.exists():
        value = _read(target)
        if value.get("report_sha256") != digest or value.get("kind") != "PUBLICATION_VERIFIED":
            raise ValueError("Publication identity changed")
        return
    _put(
        target,
        _envelope(
            {
                "method": METHOD,
                "kind": "PUBLICATION_VERIFIED",
                "report_sha256": digest,
                "verified_at": stamp.isoformat(),
            }
        ),
    )


def _records(state_dir: Path, *, include_unpublished: bool = False) -> list[dict[str, Any]]:
    directory = state_dir / "journal"
    result = []
    for path in sorted((directory / "decisions").glob("*.json")):
        value = _read(path)
        report_hash = value.get("report_sha256")
        if path.stem != report_hash:
            raise ValueError("Decision filename does not match its report")
        report_raw = (directory / "reports" / path.name).read_bytes()
        if _hash(report_raw) != report_hash:
            raise ValueError("Journal report snapshot changed")
        original = _rows(json.loads(report_raw))
        rows = value.get("decisions", [])
        if len(rows) != len(PAIRS) or [d.get("pair") for d in rows] != list(PAIRS):
            raise ValueError("Incomplete journal decisions")
        for decision in rows:
            pair = decision["pair"]
            if (
                decision["candidate"] != original[pair].get("candidate", {})
                or decision["decision_id"] != _hash((report_hash + ":" + pair).encode())
                or decision["recorded_at"] != value["recorded_at"]
                or decision["earliest_entry_date"]
                != _next_weekday(_stamp(value["recorded_at"]).date()).isoformat()
            ):
                raise ValueError("Frozen decision does not match the original report")
            if decision["source_metadata"] != original[pair].get("source_metadata", {}):
                raise ValueError("Frozen daily receipt changed")
            expected_observation = _hash(
                _json(
                    {
                        "universe_version": UNIVERSE_VERSION,
                        "pair": pair,
                        "candidate": original[pair].get("candidate", {}),
                        "source_sha256": original[pair].get("source_metadata", {}).get("sha256"),
                        "engine_method": original[pair]
                        .get("backtest", {})
                        .get("method_version", METHOD_VERSION),
                    }
                )
            )
            if decision["observation_id"] != expected_observation:
                raise ValueError("Observation identity changed")
            benchmark = decision["benchmark"]
            expected_candidate_risk = (
                _candidate_risk(decision["candidate"])
                if benchmark["risk_distance"] is not None
                else None
            )
            if benchmark.get("candidate_risk_distance") != expected_candidate_risk:
                raise ValueError("Frozen candidate risk changed")
            if (
                benchmark["directions"] != ["BUY", "SELL"]
                or benchmark["costs"] != asdict(Costs())
                or benchmark["kind"] != "COUNTERFACTUAL_RESEARCH"
                or decision["execution_state"] != "NOT_RECORDED"
                or decision["forecast_qualification"] != "UNQUALIFIED"
            ):
                raise ValueError("Frozen benchmark contract changed")
            if benchmark["source_error"] is None:
                bars, _ = _history(
                    original[pair], state_dir, _stamp(value["recorded_at"]), snapshot=True
                )
                if benchmark["risk_distance"] != _risk(bars, decision["candidate"].get("as_of")):
                    raise ValueError("Frozen risk does not replay from its source")
        publication = directory / "publications" / path.name
        if publication.exists():
            receipt = _read(publication)
            if (
                receipt.get("kind") != "PUBLICATION_VERIFIED"
                or receipt.get("report_sha256") != report_hash
                or _stamp(receipt["verified_at"]) < _stamp(value["recorded_at"])
            ):
                raise ValueError("Invalid publication receipt")
            result.append(value)
        elif include_unpublished:
            result.append(value)
    return sorted(result, key=lambda item: (item["recorded_at"], item["report_sha256"]))


def _evaluate(
    decision: dict[str, Any], bars: list[dict[str, Any]], now: datetime
) -> dict[str, Any]:
    benchmark = decision["benchmark"]
    horizon, risk = benchmark["holding_days"], benchmark["risk_distance"]
    if horizon not in (3, 5) or risk is None or benchmark["source_error"]:
        return {"status": "UNAVAILABLE", "reason": "FROZEN_BENCHMARK_UNAVAILABLE", "outcomes": []}
    if benchmark["directions"] != ["BUY", "SELL"]:
        raise ValueError("Benchmark directions changed")
    dates = [date.fromisoformat(decision["earliest_entry_date"])]
    for _ in range(horizon - 1):
        dates.append(_next_weekday(dates[-1]))
    if dates[-1] >= now.date():
        return {"status": "PENDING", "reason": "FULL_HORIZON_NOT_COMPLETED", "outcomes": []}
    by_date = {bar["time"]: bar for bar in bars}
    keys = [day.isoformat() for day in dates]
    if any(key not in by_date for key in keys):
        return {"status": "UNAVAILABLE", "reason": "MISSING_HOLDING_OBSERVATION", "outcomes": []}
    future = [by_date[key] for key in keys]
    if any(bar.get("gap_before") for bar in future):
        return {"status": "UNAVAILABLE", "reason": "QUARANTINED_HOLDING_WINDOW", "outcomes": []}
    prior = dates[0] - timedelta(days=1)
    while prior.weekday() >= 5:
        prior -= timedelta(days=1)
    anchor = {"time": prior.isoformat(), **dict.fromkeys(("open", "high", "low", "close"), 1.0)}
    outcomes = []
    for side, sign in (("BUY", 1), ("SELL", -1)):
        trade = simulate_trade(
            decision["pair"],
            [anchor, *future],
            0,
            sign,
            risk,
            horizon,
            costs=Costs(**benchmark["costs"]),
        )
        outcomes.append({"benchmark_direction": side, "kind": "COUNTERFACTUAL_RESEARCH", **trade})
    return {
        "status": "EVALUATED",
        "reason": "PROVISIONAL_SOURCE_PRICE_BENCHMARK",
        "horizon_end_date": keys[-1],
        "outcomes": outcomes,
        "candidate_plan_outcome": (
            {
                "kind": "FROZEN_CANDIDATE_COUNTERFACTUAL",
                "qualification": "UNQUALIFIED",
                "entry_basis": "Later observed open, with the frozen reference risk distance",
                **simulate_trade(
                    decision["pair"],
                    [anchor, *future],
                    0,
                    1 if decision["candidate"].get("direction") == "BUY" else -1,
                    benchmark["candidate_risk_distance"],
                    horizon,
                    costs=Costs(**benchmark["costs"]),
                ),
            }
            if benchmark.get("candidate_risk_distance") is not None
            else None
        ),
    }


def evaluate_pending(state_dir: Path, report_path: Path, *, now: datetime | None = None) -> int:
    """Append outcomes/attempts from saved later sources; never fetch or place orders."""
    stamp = _clock(now)
    report_raw = report_path.read_bytes()
    rows = _rows(json.loads(report_raw))
    records = _records(state_dir, include_unpublished=True)
    added = 0
    for record in records:
        for decision in record["decisions"]:
            if _stamp(decision["recorded_at"]) > stamp:
                raise ValueError("Evaluation precedes recording")
            row = rows[decision["pair"]]
            source_hash = row.get("source_metadata", {}).get("sha256")
            try:
                bars, meta = _history(row, state_dir, stamp)
                source_stamp = _stamp(meta.get("received_at", meta.get("retrieved_at")))
                result = _evaluate(decision, bars, min(stamp, source_stamp))
                if result["status"] == "PENDING" and source_stamp.date() < stamp.date():
                    result["reason"] = "SOURCE_NOT_YET_READY"
                source_hash = meta["sha256"]
                source_received = _stamp(
                    meta.get("received_at", meta.get("retrieved_at"))
                ).isoformat()
                source_raw = Path(meta["capture_path"]).read_bytes()
                if _hash(source_raw) != meta["sha256"]:
                    raise ValueError("Source changed during outcome recording")
                _put(state_dir / "journal" / "sources" / (meta["sha256"] + ".json"), source_raw)
            except (KeyError, OSError, ValueError, TypeError) as exc:
                code = _failure(exc)
                result = {
                    "status": "UNAVAILABLE",
                    "reason": code,
                    "source_error": code,
                    "outcomes": [],
                }
                source_received = None
            identity = {
                "decision_id": decision["decision_id"],
                "source_sha256": source_hash,
                "result": result,
            }
            target = state_dir / "journal" / "evaluations" / (_hash(_json(identity)) + ".json")
            if target.exists():
                prior = _read(target)
                if any(prior.get(key) != item for key, item in identity.items()):
                    raise ValueError("Evaluation identity changed")
                continue
            event = {
                "method": METHOD,
                "kind": "OUTCOME_EVALUATION",
                "evaluated_at": stamp.isoformat(),
                "source_received_at": source_received,
                "evaluation_report_sha256": _hash(report_raw),
                "execution_state": "NOT_RECORDED",
                **identity,
            }
            _put(state_dir / "journal" / "reports" / (_hash(report_raw) + ".json"), report_raw)
            _put(target, _envelope(event))
            added += 1
    return added


def journal_view(state_dir: Path) -> dict[str, Any]:
    """Read verified decisions and evaluations with separate benchmark aggregates."""
    records = _records(state_dir)
    rows = [dict(d, report_sha256=r["report_sha256"]) for r in records for d in r["decisions"]]
    decisions = {row["decision_id"]: row for row in rows}
    latest: dict[str, dict[str, Any]] = {}
    count = 0
    for path in sorted((state_dir / "journal" / "evaluations").glob("*.json")):
        event = _read(path)
        decision_id = event.get("decision_id")
        if not isinstance(decision_id, str):
            raise ValueError("Outcome requires a decision identity")
        if event.get("kind") != "OUTCOME_EVALUATION":
            raise ValueError("Orphan or invalid evaluation")
        if decision_id not in decisions:
            continue  # An uncommitted report artifact cannot become a displayed suggestion.
        identity = {key: event[key] for key in ("decision_id", "source_sha256", "result")}
        if path.stem != _hash(_json(identity)):
            raise ValueError("Evaluation filename does not match its identity")
        if _stamp(event["evaluated_at"]) < _stamp(decisions[decision_id]["recorded_at"]):
            raise ValueError("Outcome clock precedes the decision")
        evaluation_raw = (
            state_dir / "journal" / "reports" / (event["evaluation_report_sha256"] + ".json")
        ).read_bytes()
        if _hash(evaluation_raw) != event["evaluation_report_sha256"]:
            raise ValueError("Outcome report snapshot changed")
        result = event["result"]
        if event.get("execution_state") != "NOT_RECORDED":
            raise ValueError("Hypothetical outcomes cannot become executions")
        if not result.get("source_error"):
            source_row = _rows(json.loads(evaluation_raw))[decisions[decision_id]["pair"]]
            bars, meta = _history(
                source_row, state_dir, _stamp(event["evaluated_at"]), snapshot=True
            )
            source_stamp = _stamp(meta.get("received_at", meta.get("retrieved_at")))
            event_stamp = _stamp(event["evaluated_at"])
            replay = _evaluate(decisions[decision_id], bars, min(event_stamp, source_stamp))
            if replay["status"] == "PENDING" and source_stamp.date() < event_stamp.date():
                replay["reason"] = "SOURCE_NOT_YET_READY"
            if meta["sha256"] != event["source_sha256"] or replay != result:
                raise ValueError("Outcome does not replay from its original source")
            if event["source_received_at"] != source_stamp.isoformat():
                raise ValueError("Evaluation source clock changed")
        elif (
            result["status"] != "UNAVAILABLE"
            or result["outcomes"]
            or result["source_error"] not in SOURCE_FAILURES
        ):
            raise ValueError("Unverified source cannot supply outcomes")
        count += 1
        prior = latest.get(decision_id)
        # A later failed/stale attempt cannot erase a completed, source-backed result.
        completed = result["status"] == "EVALUATED"
        rank = (
            completed,
            event.get("source_received_at") or "" if completed else event["evaluated_at"],
            event["evaluated_at"],
            path.name,
        )
        prior_completed = prior["result"]["status"] == "EVALUATED" if prior else False
        prior_rank = (
            (
                prior_completed,
                prior.get("source_received_at") or "" if prior_completed else prior["evaluated_at"],
                prior["evaluated_at"],
                prior["event_file"],
            )
            if prior
            else None
        )
        if prior_rank is None or rank > prior_rank:
            latest[decision_id] = {**event, "event_file": path.name}
    gates: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"observations": 0, "direction_outcomes": [], "candidate_outcomes": []}
    )
    first_observation: dict[str, str] = {}
    for row in rows:
        observation_id = row["observation_id"]
        row["primary_decision_id"] = first_observation.setdefault(
            observation_id, row["decision_id"]
        )
        row["repeated_publication"] = row["primary_decision_id"] != row["decision_id"]
        row["primary_entry_date"] = decisions[row["primary_decision_id"]]["earliest_entry_date"]
        row["evaluation"] = latest.get(
            row["decision_id"],
            {"result": {"status": "PENDING", "reason": "NOT_YET_EVALUATED", "outcomes": []}},
        )
        candidate = row["candidate"]
        direction = candidate.get("direction")
        result = row["evaluation"]["result"]
        selected = next(
            (o for o in result["outcomes"] if o["benchmark_direction"] == direction), None
        )
        row["frozen_direction_benchmark"] = selected
        reasons = candidate.get("reasons", [])
        if not isinstance(reasons, list):
            reasons = ["REASONS_UNAVAILABLE"]
        if row["repeated_publication"]:
            row["publication_evaluation"] = row["evaluation"]
            row["evaluation"] = decisions[row["primary_decision_id"]]["evaluation"]
            row["frozen_direction_benchmark"] = decisions[row["primary_decision_id"]][
                "frozen_direction_benchmark"
            ]
            row["evaluation_basis"] = (
                "PRIMARY_OBSERVATION; own publication attempt retained separately"
            )
            continue
        for reason in {str(item) for item in reasons} or {"NO_RECORDED_REJECTION_REASON"}:
            group = gates[reason]
            group["observations"] += 1
            if selected is not None:
                group["direction_outcomes"].append(selected["net_r"])
            plan = result.get("candidate_plan_outcome")
            if plan is not None:
                group["candidate_outcomes"].append(plan["net_r"])
    groups = []
    for reason, group in sorted(gates.items()):
        outcomes = group["direction_outcomes"]
        groups.append(
            {
                "reason": reason,
                "observations": group["observations"],
                "evaluated_frozen_direction_count": len(outcomes),
                "mean_frozen_direction_benchmark_net_r": sum(outcomes) / len(outcomes)
                if outcomes
                else None,
                "interpretation": "Overlapping reason groups; not causal filter attribution.",
                "evaluated_candidate_plan_count": len(group["candidate_outcomes"]),
                "mean_candidate_plan_net_r": (
                    sum(group["candidate_outcomes"]) / len(group["candidate_outcomes"])
                    if group["candidate_outcomes"]
                    else None
                ),
            }
        )
    unique_rows = [row for row in rows if not row["repeated_publication"]]
    return {
        "method": METHOD,
        "status": "RECORDED" if rows else "EMPTY",
        "report_count": len(records),
        "decision_count": len(rows),
        "evaluation_event_count": count,
        "decision_status_counts": dict(
            Counter(r["candidate"].get("status", "UNKNOWN") for r in unique_rows)
        ),
        "outcome_status_counts": dict(
            Counter(r["evaluation"]["result"]["status"] for r in unique_rows)
        ),
        "publication_row_status_counts": dict(
            Counter(r["candidate"].get("status", "UNKNOWN") for r in rows)
        ),
        "unique_pair_observation_dates": len(
            {(r["pair"], r["candidate"].get("as_of")) for r in rows}
        ),
        "unique_observation_count": len(first_observation),
        "repeated_publication_count": sum(r["repeated_publication"] for r in rows),
        "unpublished_report_count": len(list((state_dir / "journal" / "decisions").glob("*.json")))
        - len(records),
        "execution_state": "NOT_RECORDED",
        "forecast_qualification": "UNQUALIFIED",
        "reason_groups": groups,
        "rows": list(reversed(rows)),
        "limitations": LIMITS,
        "source_failure_actions": SOURCE_FAILURES,
    }


def sync_journal(
    state_dir: Path, report_path: Path, *, now: datetime | None = None
) -> dict[str, Any]:
    stamp = _clock(now)
    record_report(state_dir, report_path, now=stamp)
    commit_publication(state_dir, report_path, now=stamp)
    evaluate_pending(state_dir, report_path, now=stamp)
    return journal_view(state_dir)
