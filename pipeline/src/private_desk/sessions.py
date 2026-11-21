"""Separate recent-hourly session study; no borrowed daily probability."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from src.private_desk.engine import Costs, simulate_trade, validate_bars, wilson_interval


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    wins = sum(float(row["net_r"]) > 0 for row in rows)
    return {
        "trade_count": n,
        "win_rate": wins / n if n else None,
        "net_ev_r": sum(float(row["net_r"]) for row in rows) / n if n else None,
        "win_rate_ci95": wilson_interval(wins, n) if n else None,
        "ambiguous_bars": sum(int(row["ambiguous_bars"]) for row in rows),
    }


def session_study(pair: str, bars: list[dict[str, Any]]) -> dict[str, Any]:
    if len(bars) < 1000:
        return {"status": "UNAVAILABLE", "reason": "Fewer than 1,000 valid completed hourly bars"}
    clean = validate_bars(bars)
    times = [datetime.fromisoformat(str(bar["time"]).replace("Z", "+00:00")) for bar in clean]
    times = [
        stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp.astimezone(UTC)
        for stamp in times
    ]
    fx_zone = ZoneInfo("America/New_York")
    gap_prefix = [0] * len(times)
    for index in range(1, len(times)):
        cursor = times[index - 1] + timedelta(hours=1)
        missing_open_hour = False
        while cursor < times[index]:
            local = cursor.astimezone(fx_zone)
            closed = (
                local.weekday() == 5
                or (local.weekday() == 4 and local.hour >= 17)
                or (local.weekday() == 6 and local.hour < 17)
            )
            if not closed:
                missing_open_hour = True
                break
            cursor += timedelta(hours=1)
        gap_prefix[index] = gap_prefix[index - 1] + int(missing_open_hour)
    split = int(len(clean) * 0.65)
    comparisons: list[dict[str, Any]] = []
    for name, timezone in (("London", "Europe/London"), ("New York", "America/New_York")):
        zone = ZoneInfo(timezone)
        for horizon in (3, 5):
            cohorts: dict[str, list[dict[str, Any]]] = {"train": [], "test": []}
            excluded_windows = 0
            last_exit = -1
            for i in range(120, len(clean) - 120):
                stamp = times[i].astimezone(zone)
                if stamp.hour != 8 or stamp.minute != 0 or stamp.weekday() > 4 or i <= last_exit:
                    continue
                # Use completed pre-session prices only; fixed 24h trend rule.
                move = clean[i - 1]["close"] - clean[i - 25]["close"]
                ranges = [clean[j]["high"] - clean[j]["low"] for j in range(i - 24, i)]
                risk = max(sum(ranges) / 24 * 4, abs(move) * 0.5)
                if risk <= 0 or abs(move) < risk * 0.5:
                    continue
                end = times[i]
                days = 0
                while days < horizon:
                    end += timedelta(days=1)
                    if end.weekday() < 5:
                        days += 1
                end_index = next(
                    (j for j in range(i + 1, min(i + 200, len(clean))) if times[j] >= end), None
                )
                if end_index is None:
                    continue
                if gap_prefix[end_index] != gap_prefix[i - 25]:
                    excluded_windows += 1
                    continue
                # Holding labels never cross the train/test embargo boundary.
                if i < split and end_index >= split - 120:
                    continue
                if split <= i < split + 120:
                    continue
                row = simulate_trade(
                    pair,
                    clean,
                    i - 1,
                    1 if move > 0 else -1,
                    risk,
                    end_index - i + 1,
                    costs=Costs(),
                    bar_interval="1h",
                )
                row["weekday"] = stamp.strftime("%A")
                cohort = "train" if i < split else "test"
                cohorts[cohort].append(row)
                # Simulate non-overlapping calls within each trial.
                last_exit = next(
                    (j for j in range(i, end_index + 1) if clean[j]["time"] == row["exit_time"]),
                    end_index,
                )
            comparisons.append(
                {
                    "session": name,
                    "horizon": horizon,
                    "local_entry": "08:00",
                    "timezone": timezone,
                    "train": _summary(cohorts["train"]),
                    "test": _summary(cohorts["test"]),
                    "excluded_missing_hour_windows": excluded_windows,
                    "trades": cohorts,
                    "weekdays": [
                        {
                            "weekday": day,
                            **_summary([r for r in cohorts["test"] if r["weekday"] == day]),
                        }
                        for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
                    ],
                }
            )
    train_eligible = [r for r in comparisons if r["train"]["trade_count"] >= 30]
    selected = max(train_eligible, key=lambda r: r["train"]["net_ev_r"]) if train_eligible else None
    return {
        "status": "MEASURED_PROVISIONAL",
        "interval": "1h",
        "comparisons": comparisons,
        "selected_review_window": selected["session"]
        + " 08:00 local / "
        + str(selected["horizon"])
        + " business-day maximum"
        if selected
        else None,
        "selection_basis": "Training EV only; fixed four trials. Separate held-out test shown.",
        "coverage": {
            "first_bar": clean[0]["time"],
            "last_bar": clean[-1]["time"],
            "bar_count": len(clean),
        },
        "probability": None,
        "execution_status": "UNQUALIFIED",
        "limitations": [
            "Recent reconstructed midprice hourly candles, not executable broker bid/ask.",
            "Daily probabilities do not apply to this distinct session strategy.",
            "Weekday counts are descriptive; no weekday was tuned or certified.",
            "Weekday calendar approximates FX sessions; market holidays remain unverified.",
            "Four trials overlap across session policies; no portfolio performance claim.",
            "Feature and maximum holding windows with missing open-market hours are excluded.",
        ],
    }
