"""Eval harness for the single LLM reader (faithfulness, numbers, Brier).

Offline and deterministic. No DB writes. No network. No secrets.
Reads frozen calls + analyst notes, writes local JSON + markdown under
``reports/``. Reuses the flagship scorecard shape where it exists
(per-pair ``{t5WinRate, t5Brier, ...}``); until then this local schema is
canonical for the fx-live-personal slice.

Metrics:
- faithfulness: share of required citation tokens present in the note
  (``[REGIME] [CONF] [COMPOSITE] [DRIVER] [BRIEF]``; needs >= 2, plus
  regime string and pair present). Range 0..1.
- number_accuracy: CONF % and COMPOSITE value in the note match the frozen
  inputs within tolerance (CONF ±1pp, COMPOSITE ±0.01). Per-pair share.
- brier_on_conviction: mean ``(confidence - outcome)^2`` over rows with a
  binary outcome (1 correct, 0 incorrect; None skipped).
- versioned_scores: the above grouped by ``model_version``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

__all__ = [
    "EVAL_VERSION",
    "brier_on_conviction",
    "evaluate_notes",
    "number_accuracy",
    "score_faithfulness",
    "write_eval_report",
]

EVAL_VERSION = "llm-reader-eval-v1"

REQUIRED_CITATIONS = ("[REGIME]", "[CONF]", "[COMPOSITE]", "[DRIVER]", "[BRIEF]")

_CONF_RE = re.compile(r"(\d{1,3})\s*%")
_COMPOSITE_RE = re.compile(r"([+-]?\d+\.\d{2})")


def score_faithfulness(note: str, frozen: dict[str, Any]) -> float:
    """0..1 share of grounding checks passed (citations + regime + pair)."""
    text = note or ""
    upper = text.upper()
    cites = sum(1 for tok in REQUIRED_CITATIONS if tok in upper)
    checks = [
        cites >= 2,
        str(frozen.get("regime", "")).upper() in upper
        if frozen.get("regime")
        else False,
        str(frozen.get("pair", "")).replace("/", "").upper() in upper,
        "BUY" not in upper and "SELL" not in upper,
    ]
    return sum(1 for c in checks if c) / len(checks)


def _numbers_in_note(note: str) -> tuple[float | None, float | None]:
    conf: float | None = None
    comp: float | None = None
    m = _CONF_RE.search(note or "")
    if m:
        try:
            conf = int(m.group(1)) / 100.0
        except ValueError:
            conf = None
    m2 = _COMPOSITE_RE.search(note or "")
    if m2:
        try:
            comp = float(m2.group(1))
        except ValueError:
            comp = None
    return conf, comp


def number_accuracy(note: str, frozen: dict[str, Any]) -> bool:
    """True when CONF and COMPOSITE in the note match frozen inputs."""
    conf_note, comp_note = _numbers_in_note(note)
    try:
        conf_frozen = float(frozen.get("confidence", -1))
        comp_frozen = float(frozen.get("signal_composite", frozen.get("composite", -999)))
    except (TypeError, ValueError):
        return False
    if conf_note is None or comp_note is None:
        return False
    return abs(conf_note - conf_frozen) <= 0.01 and abs(comp_note - comp_frozen) <= 0.011


def brier_on_conviction(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean Brier over rows with binary outcome; n + null count reported."""
    se = 0.0
    n = 0
    skipped = 0
    for r in rows:
        outcome = r.get("outcome")
        if outcome not in (0, 1):
            skipped += 1
            continue
        try:
            p = float(r.get("confidence", 0.0))
        except (TypeError, ValueError):
            skipped += 1
            continue
        p = min(1.0, max(0.0, p))
        se += (p - float(outcome)) ** 2
        n += 1
    return {"mean_brier": (se / n) if n else None, "n": n, "skipped": skipped}


def evaluate_notes(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Score a list of ``{frozen..., note, outcome}`` rows (versioned)."""
    by_version: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_version.setdefault(str(r.get("model_version") or "unversioned"), []).append(r)

    per_pair_faith: dict[str, list[float]] = {}
    per_pair_num: dict[str, list[int]] = {}
    for r in rows:
        pair = str(r.get("pair", "UNKNOWN")).replace("/", "").upper()
        faith = score_faithfulness(str(r.get("note", "")), r)
        num_ok = 1 if number_accuracy(str(r.get("note", "")), r) else 0
        per_pair_faith.setdefault(pair, []).append(faith)
        per_pair_num.setdefault(pair, []).append(num_ok)

    overall_faith = (
        sum(sum(v) for v in per_pair_faith.values())
        / sum(len(v) for v in per_pair_faith.values())
        if per_pair_faith
        else 0.0
    )
    overall_num = (
        sum(sum(v) for v in per_pair_num.values())
        / sum(len(v) for v in per_pair_num.values())
        if per_pair_num
        else 0.0
    )
    brier = brier_on_conviction(rows)

    versions: dict[str, Any] = {}
    for ver, vrows in by_version.items():
        versions[ver] = {
            "n": len(vrows),
            "faithfulness": sum(score_faithfulness(str(r.get("note", "")), r) for r in vrows)
            / len(vrows),
            "number_accuracy": sum(
                1 if number_accuracy(str(r.get("note", "")), r) else 0 for r in vrows
            )
            / len(vrows),
            "brier": brier_on_conviction(vrows),
        }

    return {
        "eval_version": EVAL_VERSION,
        "n": len(rows),
        "faithfulness_overall": overall_faith,
        "number_accuracy_overall": overall_num,
        "brier_on_conviction": brier,
        "per_pair": {
            pair: {
                "faithfulness": sum(vals) / len(vals),
                "number_accuracy": sum(per_pair_num[pair]) / len(per_pair_num[pair]),
                "n": len(vals),
            }
            for pair, vals in per_pair_faith.items()
        },
        "versions": versions,
    }


def write_eval_report(
    result: dict[str, Any], out_dir: str | Path = "reports", stem: str = "llm_reader_eval_v1"
) -> tuple[Path, Path]:
    """Write local JSON + markdown report. Returns (json_path, md_path)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"{stem}.json"
    md_path = out / f"{stem}.md"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        f"# LLM Reader Eval — {result.get('eval_version', EVAL_VERSION)}",
        "",
        f"Rows scored: **{result.get('n', 0)}**",
        f"Faithfulness (overall): **{result.get('faithfulness_overall', 0.0):.3f}**",
        f"Number accuracy (overall): **{result.get('number_accuracy_overall', 0.0):.3f}**",
    ]
    brier = result.get("brier_on_conviction", {})
    lines.append(
        f"Brier on conviction: **{brier.get('mean_brier')}** (n={brier.get('n')}, "
        f"skipped={brier.get('skipped')})"
    )
    lines += ["", "## Per pair", ""]
    for pair, row in sorted(result.get("per_pair", {}).items()):
        lines.append(
            f"- {pair}: faithfulness {row['faithfulness']:.3f}, "
            f"number_accuracy {row['number_accuracy']:.3f}, n={row['n']}"
        )
    lines += ["", "## Versions", ""]
    for ver, row in sorted(result.get("versions", {}).items()):
        b = row.get("brier", {})
        lines.append(
            f"- {ver}: n={row['n']}, faithfulness {row['faithfulness']:.3f}, "
            f"number_accuracy {row['number_accuracy']:.3f}, "
            f"brier {b.get('mean_brier')} (n={b.get('n')})"
        )
    lines += [
        "",
        "Guards: no new signals, no new pairs, 3-pair lock, "
        "AI only via pipeline/src/ai/client.py, offline deterministic fallback.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
