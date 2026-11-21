"""Regime call persistence with rationale and versioning.

Replaces direct writer.write_regime_call() usage in the orchestrator
with a unified persist layer that also writes call_rationale.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date
from typing import Any

from src.db import writer
from src.types import RegimeCall, SignalRow

logger = logging.getLogger(__name__)


def _build_call_rationale(
    call_id: int | str | None,
    call_date: date,
    pair: str,
    signals: SignalRow,
    composite: float,
    *,
    call: RegimeCall | None = None,
) -> dict[str, Any]:
    """Build a call_rationale payload from signals and composite.

    Fields:
    - layer1_reasoning: Marcus gate + hysteresis logic
    - layer2_reasoning: COT crowding, directional bias, conviction
    - layer3_reasoning: Entry timing, position size, stop level
    - primary_driver_detail: Which family dominated and why
    - confidence_explanation: How confidence was derived
    - contrarian_flags: Any crowding or divergence warnings
    """
    driver_text = str(call.primary_driver or "not recorded") if call is not None else "not recorded"

    layer1 = (
        f"Composite={composite:.3f} on {call_date.isoformat()}. "
        f"Rate Z tactical={signals.rate_z_tactical}, "
        f"structural={signals.rate_z_structural}. "
        f"Vol RV20={signals.realized_vol_20d}, RV5={signals.realized_vol_5d}."
    )

    layer2 = (
        f"COT percentile={signals.cot_percentile}. "
        f"Asset mgr={signals.cot_asset_mgr_net}, "
        f"lev money={signals.cot_lev_money_net}."
    )

    layer3 = (
        f"OI delta={signals.oi_delta}. "
        f"FPI flow={signals.fpi_flow}. "
        f"Structural instability={signals.structural_instability}."
    )

    primary = (
        f"Primary driver detail: {driver_text}. "
        f"Special signal={signals.ecb_balance_sheet} (ECB BS) / "
        f"{signals.bund_btp_spread} (Bund-BTP)."
        if pair == "EURUSD"
        else f"Primary driver detail: {driver_text}."
    )

    conf_exp = "Confidence is a heuristic score, not a calibrated probability. "
    if call is not None:
        conf_exp += f"Published score={call.confidence}; DQS={call.data_quality_score}."
        layer3 = (
            f"Published timing={call.entry_timing}, size={call.position_size}, "
            f"stop={call.stop_level}. " + layer3
        )
    else:
        conf_exp += "Retrospective explanation; original confidence derivation unavailable."

    flags: list[str] = []
    if signals.structural_instability:
        flags.append("STRUCTURAL_INSTABILITY")
    if signals.oi_delta is not None and abs(signals.oi_delta) > 500:
        flags.append("HIGH_OI_DELTA")

    return {
        "call_id": call_id,
        "date": call_date.isoformat(),
        "pair": pair,
        "layer1_reasoning": layer1,
        "layer2_reasoning": layer2,
        "layer3_reasoning": layer3,
        "primary_driver_detail": primary,
        "confidence_explanation": conf_exp,
        "contrarian_flags": flags,
    }


def _write_call_rationale(payload: dict[str, Any]) -> None:
    """Insert into call_rationale table; graceful if table missing."""
    writer.write_call_rationale([payload])
    logger.info("Wrote call_rationale for call_id=%s", payload.get("call_id"))


def compute_write_hash(inputs: dict[str, Any]) -> str:
    """SHA-256 hex digest of sorted JSON-serialized inputs."""
    canonical = json.dumps(inputs, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def persist_regime_call(
    call: RegimeCall,
    signals: SignalRow,
    *,
    correlation_id: str | None = None,
) -> int | str | None:
    """Build descriptive rationale and atomically publish without changing provenance."""
    rationale = _build_call_rationale(
        call_id=None,
        call_date=call.date,
        pair=call.pair,
        signals=signals,
        composite=float(call.signal_composite),
        call=call,
    )
    return writer.publish_regime_call(
        call,
        signals,
        rationale=rationale,
        correlation_id=correlation_id,
    )
