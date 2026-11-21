"""Immutable current-review inputs and reproducible bindings, without AI replay."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.ai.client import (
    LEGACY_PRIVATE_REVIEW_METHOD,
    PRIVATE_REVIEW_METHOD,
    private_brief_input,
    private_packet_text,
)
from src.private_desk.bidask import bounded_path

AI_FIELDS = ("status", "model", "generated_at", "reason", "payload_sha256", "method_version")
CONTEXT_FIELDS = {
    "news",
    "ai_summary",
    "prior_ai_summary",
    "current_review",
    "prior_current_review",
    "current_context_updated_at",
}
PAIR_CONTEXT_FIELDS = {"fundamentals", "ai_analysis", "prior_ai_analysis"}


def quantitative_fingerprint(report: dict[str, Any]) -> str:
    value = {k: v for k, v in report.items() if k not in CONTEXT_FIELDS | {"pair_reports"}}
    value["pair_reports"] = [
        {k: v for k, v in item.items() if k not in PAIR_CONTEXT_FIELDS}
        for item in report["pair_reports"]
    ]
    return hashlib.sha256(private_packet_text(value).encode()).hexdigest()


def capture_review_input(
    report: dict[str, Any],
    root: Path,
    *,
    as_of: str,
    parent_bytes: bytes | None = None,
) -> dict[str, Any]:
    pairs = report["pair_reports"]
    fundamentals = pairs[0].get("fundamentals", {}) if pairs else {}
    if any(item.get("fundamentals", {}) != fundamentals for item in pairs):
        raise ValueError("Inconsistent current fundamental snapshots")
    payload = private_brief_input(pairs, report["news"], fundamentals, as_of=as_of)
    raw = private_packet_text(payload).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    root.mkdir(parents=True, exist_ok=True)
    path = root / (digest + ".json")
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("Current input capture collision/tampering")
    else:
        with path.open("xb") as handle:
            handle.write(raw)
    parent = None
    if parent_bytes is not None:
        parent_hash = hashlib.sha256(parent_bytes).hexdigest()
        parent_path = root / ("parent-" + parent_hash + ".json")
        if parent_path.exists():
            if parent_path.read_bytes() != parent_bytes:
                raise ValueError("Parent review capture changed")
        else:
            with parent_path.open("xb") as handle:
                handle.write(parent_bytes)
        parent = {"capture_path": str(parent_path.resolve()), "sha256": parent_hash}
    return {
        "method_version": PRIVATE_REVIEW_METHOD,
        "reviewed_at": as_of,
        "status": "PENDING",
        "forecast_qualification": "UNQUALIFIED",
        "input_packet": {"capture_path": str(path.resolve()), "sha256": digest},
        "parent_report": parent,
        "quantitative_sha256": quantitative_fingerprint(report),
        "quantitative_methods": {
            item["pair"]: item.get("backtest", {}).get("method_version") for item in pairs
        },
        "input_admission": payload["input_admission"],
        "limitations": [
            "Dated headline hypotheses; article-body grounding is absent.",
            "Receipt binding does not validate model prose or predictive value.",
            "Current context is excluded from historical calibration and trading qualification.",
        ],
    }


def verify_current_review(report: dict[str, Any], root: Path) -> None:
    receipt = report.get("current_review")
    if receipt is None or receipt.get("status") == "DETACHED":
        return
    if receipt["method_version"] not in (LEGACY_PRIVATE_REVIEW_METHOD, PRIVATE_REVIEW_METHOD):
        raise ValueError("Unsupported current review method")
    reference = receipt["input_packet"]
    raw = bounded_path(root, reference["capture_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError("Current review input hash changed")
    pairs = report["pair_reports"]
    fundamentals = pairs[0].get("fundamentals", {}) if pairs else {}
    if any(item.get("fundamentals", {}) != fundamentals for item in pairs):
        raise ValueError("Current fundamental snapshots diverge")
    expected = private_brief_input(
        pairs,
        report["news"],
        fundamentals,
        as_of=receipt["reviewed_at"],
        method_version=receipt["method_version"],
    )
    if raw != private_packet_text(expected).encode("utf-8"):
        raise ValueError("Current review inputs no longer match report")
    if receipt["input_admission"] != expected["input_admission"]:
        raise ValueError("Current review admission changed")
    if receipt["quantitative_sha256"] != quantitative_fingerprint(report):
        raise ValueError("Current review quantitative binding changed")
    ai = report["ai_summary"]
    if receipt["status"] != ai["status"] or receipt["reviewed_at"] != ai["generated_at"]:
        raise ValueError("Current review response clock/status changed")
    if ai.get("payload_sha256") != reference["sha256"]:
        raise ValueError("AI input does not match captured packet")
    if ai.get("method_version") != receipt["method_version"]:
        raise ValueError("AI method no longer matches review receipt")
    output = receipt["output_packet"]
    output_raw = bounded_path(root, output["capture_path"]).read_bytes()
    if hashlib.sha256(output_raw).hexdigest() != output["sha256"]:
        raise ValueError("Current review output hash changed")
    if private_packet_text(ai).encode("utf-8") != output_raw:
        raise ValueError("Current review output no longer matches report")
    by_pair = {item["pair"]: item for item in ai.get("pairs", [])}
    for item in pairs:
        projected = {name: ai.get(name) for name in AI_FIELDS}
        projected.update(by_pair.get(item["pair"], {}))
        if projected != item["ai_analysis"]:
            raise ValueError("Current pair review differs from captured output")
    methods = {item["pair"]: item.get("backtest", {}).get("method_version") for item in pairs}
    if methods != receipt["quantitative_methods"]:
        raise ValueError("Current review quantitative methods changed")
    if receipt.get("parent_report"):
        parent_ref = receipt["parent_report"]
        parent_raw = bounded_path(root, parent_ref["capture_path"]).read_bytes()
        if hashlib.sha256(parent_raw).hexdigest() != parent_ref["sha256"]:
            raise ValueError("Current review parent hash changed")
        parent = json.loads(parent_raw)
        if quantitative_fingerprint(parent) != receipt["quantitative_sha256"]:
            raise ValueError("Current review changed parent quantitative evidence")
        old = {k: v for k, v in parent.items() if k not in CONTEXT_FIELDS | {"pair_reports"}}
        new = {k: v for k, v in report.items() if k not in CONTEXT_FIELDS | {"pair_reports"}}
        old["pair_reports"] = [
            {k: v for k, v in item.items() if k not in PAIR_CONTEXT_FIELDS}
            for item in parent["pair_reports"]
        ]
        new["pair_reports"] = [
            {k: v for k, v in item.items() if k not in PAIR_CONTEXT_FIELDS} for item in pairs
        ]
        if old != new:
            raise ValueError("Current review changed preserved parent research")
        for current, prior, absent in (
            ("ai_summary", "prior_ai_summary", (None, "UNAVAILABLE")),
            ("current_review", "prior_current_review", (None, "DETACHED")),
        ):
            expected_prior = (
                parent[current]
                if parent.get(current, {}).get("status") not in absent
                else parent.get(prior)
            )
            if report.get(prior) != expected_prior:
                raise ValueError("Current review predecessor does not match parent")
        for before, after in zip(parent["pair_reports"], pairs, strict=True):
            expected_pair = (
                before["ai_analysis"]
                if before.get("ai_analysis", {}).get("status") not in (None, "UNAVAILABLE")
                else before.get("prior_ai_analysis")
            )
            if after.get("prior_ai_analysis") != expected_pair:
                raise ValueError("Pair review predecessor does not match parent")


def capture_review_output(ai: dict[str, Any], root: Path) -> dict[str, str]:
    raw = private_packet_text(ai).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    path = root / ("output-" + digest + ".json")
    root.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("Current output capture collision/tampering")
    else:
        with path.open("xb") as handle:
            handle.write(raw)
    return {"capture_path": str(path.resolve()), "sha256": digest}
