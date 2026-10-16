"""Deep quant audit of validation_log and validation_stats."""
from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env.local")

from src.db import writer  # noqa: E402
from src.validation.calculator import COST_BPS_ROUND_TRIP  # noqa: E402

rows = writer.get_validation_log_for_stats()
today = date.today()
print(f"Loaded {len(rows)} validation_log rows")

# Basic counts
pred_counts = Counter(r["predicted_direction"] for r in rows)
pair_counts = Counter(r["pair"] for r in rows)
print("\nPrediction distribution:", dict(pred_counts))
print("Pair distribution:", dict(pair_counts))

# Data quality scan
future_rows = []
invalid_pairs = []
invalid_brier = []
invalid_conf = []
brier_mismatch = []
cost_mismatch = []
return_sign_mismatch_t5 = []
return_sign_mismatch_t20 = []
neutral_wrong_correct = []
neutral_nonzero_return = []
duplicate_keys = []

seen = set()
cost_map = COST_BPS_ROUND_TRIP
for r in rows:
    key = (r.get("date"), r.get("pair"))
    if key in seen:
        duplicate_keys.append(key)
    seen.add(key)
    d = r.get("date")
    if isinstance(d, str) and d > today.isoformat():
        future_rows.append(r)
    if r.get("pair") not in ("EURUSD", "USDJPY", "USDINR"):
        invalid_pairs.append(r)
    for h in ["t5", "t20"]:
        b = r.get(f"brier_score_{h}")
        if b is not None and (b < 0 or b > 1):
            invalid_brier.append((r, h, b))
    c = r.get("confidence")
    if c is not None and (c < 0 or c > 1):
        invalid_conf.append((r, c))
    pred = (r.get("predicted_direction") or "").upper()
    actual_t5 = (r.get("actual_direction_t5") or "").upper()
    conf = r.get("confidence")
    brier_t5 = r.get("brier_score_t5")
    if (
        pred in ("BULLISH", "BEARISH")
        and conf is not None
        and actual_t5 in ("UP", "DOWN")
        and brier_t5 is not None
    ):
        outcome = (
            1.0
            if (pred == "BULLISH" and actual_t5 == "UP")
            or (pred == "BEARISH" and actual_t5 == "DOWN")
            else 0.0
        )
        expected = (conf - outcome) ** 2
        if abs(expected - brier_t5) > 1e-6:
            brier_mismatch.append((r, expected, brier_t5))
    for h in ["t5", "t20"]:
        cost = r.get(f"cost_bps_{h}")
        if cost is not None and abs(cost - cost_map.get(r["pair"], cost)) > 1e-6:
            cost_mismatch.append((r, h, cost))
    lr_t5 = r.get("log_return_t5_bps")
    if lr_t5 is not None and actual_t5:
        if (actual_t5 == "UP" and lr_t5 <= 0) or (actual_t5 == "DOWN" and lr_t5 >= 0):
            return_sign_mismatch_t5.append(r)
    actual_t20 = (r.get("actual_direction_t20") or "").upper()
    lr_t20 = r.get("log_return_t20_bps")
    if lr_t20 is not None and actual_t20:
        if (actual_t20 == "UP" and lr_t20 <= 0) or (actual_t20 == "DOWN" and lr_t20 >= 0):
            return_sign_mismatch_t20.append(r)
    if pred == "NEUTRAL":
        # A NEUTRAL prediction is only legitimately "correct" when the realized
        # direction for that exact horizon is NEUTRAL. Flag mismatches separately.
        actual_t5 = (r.get("actual_direction_t5") or "").upper()
        actual_t20 = (r.get("actual_direction_t20") or "").upper()
        if (
            (r.get("correct_t5") is True and actual_t5 != "NEUTRAL")
            or (r.get("correct_t20") is True and actual_t20 != "NEUTRAL")
        ):
            neutral_wrong_correct.append(r)
        if (lr_t5 is not None and abs(lr_t5) > 1e-6) or (lr_t20 is not None and abs(lr_t20) > 1e-6):
            neutral_nonzero_return.append(r)

print("\n=== Data-quality issues ===")
print(f"Duplicate (date,pair) keys: {len(duplicate_keys)}")
print(f"Rows with date > today: {len(future_rows)}")
for r in future_rows[:5]:
    print("  future row:", r.get("date"), r.get("pair"), r.get("predicted_direction"))
print(f"Invalid pair values: {len(invalid_pairs)}")
print(f"Brier scores outside [0,1]: {len(invalid_brier)}")
print(f"Confidence outside [0,1]: {len(invalid_conf)}")
print(f"Brier recomputation mismatches (directional): {len(brier_mismatch)}")
if brier_mismatch:
    print("  sample:", brier_mismatch[0])
print(f"Cost bps mismatches vs pair table: {len(cost_mismatch)}")
print(f"T+5 return sign vs actual_direction mismatches: {len(return_sign_mismatch_t5)}")
print(f"T+20 return sign vs actual_direction mismatches: {len(return_sign_mismatch_t20)}")
print(f"NEUTRAL rows marked correct=True: {len(neutral_wrong_correct)}")
print(f"NEUTRAL rows with non-zero log_return: {len(neutral_nonzero_return)}")


def compute_metrics(name: str, subset: list[dict[str, Any]], horizon: str) -> dict[str, Any]:
    correct_key = f"correct_{horizon}"
    correct_net_key = f"correct_net_{horizon}"
    brier_key = f"brier_score_{horizon}"
    ret_key = f"log_return_{horizon}_bps"
    directional = [r for r in subset if (r.get("predicted_direction") or "").upper() != "NEUTRAL"]
    n_dir = len(directional)
    wins = sum(1 for r in directional if r.get(correct_key) is True)
    net_wins = sum(1 for r in directional if r.get(correct_net_key) is True)
    wr = wins / n_dir if n_dir else None
    net_wr = net_wins / n_dir if n_dir else None
    briers = [float(r[brier_key]) for r in directional if r.get(brier_key) is not None]
    mean_brier = statistics.mean(briers) if briers else None
    brier_skill = (0.25 - mean_brier) / 0.25 if mean_brier is not None else None
    returns = [float(r[ret_key]) for r in directional if r.get(ret_key) is not None]
    mean_ret = statistics.mean(returns) if returns else None
    std_ret = statistics.stdev(returns) if len(returns) > 1 else None
    sharpe = mean_ret / std_ret if mean_ret is not None and std_ret and std_ret != 0 else None
    mdd = None
    if returns:
        cum = 0.0
        peak = 0.0
        dd = 0.0
        for x in returns:
            cum += x
            peak = max(peak, cum)
            dd = max(dd, peak - cum)
        mdd = dd
    pval = None
    if n_dir > 0 and wr is not None:
        se = math.sqrt(0.25 / n_dir)
        z = (wr - 0.5) / se if se else 0.0
        pval = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return {
        "name": name,
        "n": len(subset),
        "n_dir": n_dir,
        "wins": wins,
        "wr": wr,
        "net_wins": net_wins,
        "net_wr": net_wr,
        "mean_brier": mean_brier,
        "brier_skill": brier_skill,
        "mean_ret": mean_ret,
        "sharpe": sharpe,
        "mdd": mdd,
        "pval": pval,
    }


print("\n=== Directional track record (T+5) ===")
for p in ["EURUSD", "USDJPY", "USDINR", "ALL"]:
    subset = rows if p == "ALL" else [r for r in rows if r["pair"] == p]
    m = compute_metrics(p, subset, "t5")
    print(
        f"{m['name']}: n={m['n']}, dir={m['n_dir']}, wins={m['wins']}, "
        f"WR={m['wr']:.4f}, net_WR={m['net_wr']:.4f}, brier={m['mean_brier']:.4f}, "
        f"skill={m['brier_skill']:.4f}, mean_ret={m['mean_ret']:.2f}bps, "
        f"sharpe={m['sharpe']:.3f}, MDD={m['mdd']:.2f}bps, p(>50%)={m['pval']:.4f}"
    )

print("\n=== Directional track record (T+20) ===")
for p in ["EURUSD", "USDJPY", "USDINR", "ALL"]:
    subset = rows if p == "ALL" else [r for r in rows if r["pair"] == p]
    m = compute_metrics(p, subset, "t20")
    print(
        f"{m['name']}: n={m['n']}, dir={m['n_dir']}, wins={m['wins']}, "
        f"WR={m['wr']:.4f}, net_WR={m['net_wr']:.4f}, brier={m['mean_brier']:.4f}, "
        f"skill={m['brier_skill']:.4f}, mean_ret={m['mean_ret']:.2f}bps, "
        f"sharpe={m['sharpe']:.3f}, MDD={m['mdd']:.2f}bps, p(>50%)={m['pval']:.4f}"
    )


def confusion(subset: list[dict[str, Any]], horizon: str) -> dict[tuple[str, str], int]:
    actual_key = f"actual_direction_{horizon}"
    cm: defaultdict[tuple[str, str], int] = defaultdict(int)
    for r in subset:
        pred = (r.get("predicted_direction") or "").upper()
        if pred not in ("BULLISH", "BEARISH"):
            continue
        act = (r.get(actual_key) or "").upper()
        if act not in ("UP", "DOWN"):
            continue
        cm[(pred, act)] += 1
    return cm


print("\n=== Confusion matrices T+5 (pred vs actual) ===")
for p in ["EURUSD", "USDJPY", "USDINR"]:
    subset = [r for r in rows if r["pair"] == p]
    cm = confusion(subset, "t5")
    print(
        f"{p}: BULLISH->UP {cm[('BULLISH','UP')]} BULLISH->DOWN {cm[('BULLISH','DOWN')]} "
        f"BEARISH->UP {cm[('BEARISH','UP')]} BEARISH->DOWN {cm[('BEARISH','DOWN')]}")

print("\n=== Confusion matrices T+20 (pred vs actual) ===")
for p in ["EURUSD", "USDJPY", "USDINR"]:
    subset = [r for r in rows if r["pair"] == p]
    cm = confusion(subset, "t20")
    print(
        f"{p}: BULLISH->UP {cm[('BULLISH','UP')]} BULLISH->DOWN {cm[('BULLISH','DOWN')]} "
        f"BEARISH->UP {cm[('BEARISH','UP')]} BEARISH->DOWN {cm[('BEARISH','DOWN')]}")


def calibration(subset: list[dict[str, Any]], horizon: str) -> list[tuple[str, int, float, float]]:
    correct_key = f"correct_{horizon}"
    bins = [
        (0.0, 0.5),
        (0.5, 0.55),
        (0.55, 0.6),
        (0.6, 0.65),
        (0.65, 0.7),
        (0.7, 0.8),
        (0.8, 1.0),
    ]
    out = []
    for lo, hi in bins:
        bucket = [
            r
            for r in subset
            if lo <= r.get("confidence", 0) < hi
            and (r.get("predicted_direction") or "").upper() != "NEUTRAL"
        ]
        if not bucket:
            continue
        avg_conf = statistics.mean([r["confidence"] for r in bucket])
        acc = sum(1 for r in bucket if r.get(correct_key) is True) / len(bucket)
        out.append((f"{lo:.2f}-{hi:.2f}", len(bucket), avg_conf, acc))
    return out


print("\n=== Calibration T+5 (avg confidence vs observed accuracy) ===")
for p in ["EURUSD", "USDJPY", "USDINR", "ALL"]:
    subset = rows if p == "ALL" else [r for r in rows if r["pair"] == p]
    print(p)
    for b in calibration(subset, "t5"):
        print(f"  bin {b[0]} n={b[1]} avg_conf={b[2]:.3f} obs_acc={b[3]:.3f}")

print("\n=== Calibration T+20 (avg confidence vs observed accuracy) ===")
for p in ["EURUSD", "USDJPY", "USDINR", "ALL"]:
    subset = rows if p == "ALL" else [r for r in rows if r["pair"] == p]
    print(p)
    for b in calibration(subset, "t20"):
        print(f"  bin {b[0]} n={b[1]} avg_conf={b[2]:.3f} obs_acc={b[3]:.3f}")

# Compare with stored validation_stats
print("\n=== Compare raw validation_log vs stored validation_stats ===")
client = writer._client()
res = client.table("validation_stats").select("*").order("as_of_date", desc=True).execute()
stats_rows: list[dict[str, Any]] = cast(list[dict[str, Any]], res.data or [])
max_date = max(s["as_of_date"] for s in stats_rows) if stats_rows else None
latest_stats: dict[str, dict[str, Any]] = {
    r["pair"]: r for r in stats_rows if r["as_of_date"] == max_date
}
for p in ["EURUSD", "USDJPY", "USDINR", "ALL"]:
    subset = rows if p == "ALL" else [r for r in rows if r["pair"] == p]
    m5 = compute_metrics(p, subset, "t5")
    m20 = compute_metrics(p, subset, "t20")
    s = latest_stats.get(p, {})
    print(
        f"{p}: raw t5_wr={m5['wr']:.6f} stored={s.get('t5_win_rate')} | "
        f"raw t20_wr={m20['wr']:.6f} stored={s.get('t20_win_rate')} | "
        f"raw t5_brier={m5['mean_brier']:.6f} stored={s.get('t5_mean_brier')} | "
        f"raw t20_brier={m20['mean_brier']:.6f} stored={s.get('t20_mean_brier')}"
    )

# Date coverage summary
print("\n=== Date coverage ===")
for p in ["EURUSD", "USDJPY", "USDINR"]:
    subset = [r for r in rows if r["pair"] == p]
    dates = sorted(r["date"] for r in subset)
    print(f"{p}: {len(subset)} rows, from {dates[0]} to {dates[-1]}")

# NEUTRAL impact
print("\n=== NEUTRAL row impact ===")
neutral = [r for r in rows if (r.get("predicted_direction") or "").upper() == "NEUTRAL"]
print(f"Total NEUTRAL rows: {len(neutral)} ({len(neutral)/len(rows)*100:.1f}%)")
for p in ["EURUSD", "USDJPY", "USDINR"]:
    pn = [r for r in neutral if r["pair"] == p]
    print(f"{p}: {len(pn)} neutral rows")
