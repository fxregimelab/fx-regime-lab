"""Pair-level analyst brief renderer."""

from __future__ import annotations

from dataclasses import dataclass

from src.ai.providers.groq import GROQ_PRIMARY_MODEL
from src.types import SignalRow


@dataclass(frozen=True, slots=True)
class PairBriefInput:
    pair: str
    regime: str
    confidence: float
    composite: float
    signal_row: SignalRow
    date_str: str
    primary_driver: str | None = None
    polymarket_context: str = ""
    dollar_dominance_pct: float | None = None
    polymarket_odds_json: str = "[]"


class PairBriefRenderer:
    """Prompt builder for per-pair FX analyst briefs."""

    max_tokens = 280
    primary_model = GROQ_PRIMARY_MODEL

    def build_messages(self, input_data: PairBriefInput) -> list[dict[str, str]]:
        chg = input_data.signal_row.day_change_pct
        chg_s = f"{chg:+.2f}%" if chg is not None else "NA"
        dom_txt = (
            "null"
            if input_data.dollar_dominance_pct is None
            else f"{float(input_data.dollar_dominance_pct):.2f}"
        )
        prompt = (
            "TASK: FX analyst brief. 3 short paragraphs. Under 200 words total.\n"
            f"PAIR:{input_data.pair} DATE:{input_data.date_str}\n"
            f"REGIME:{input_data.regime} CONF:{input_data.confidence:.0%} "
            f"COMPOSITE:{input_data.composite:+.2f}\n"
            f"PRIMARY_DRIVER:{input_data.primary_driver or 'unknown'} "
            f"RATE_DIFF_2Y:{input_data.signal_row.rate_diff_2y} "
            f"RATE_DIFF_10Y:{input_data.signal_row.rate_diff_10y} "
            f"CROSS_ASSET_OIL:{input_data.signal_row.cross_asset_oil} "
            f"COT_PCT:{input_data.signal_row.cot_percentile} "
            f"RVOL20:{input_data.signal_row.realized_vol_20d} "
            f"RVOL5:{input_data.signal_row.realized_vol_5d} "
            f"SPOT:{input_data.signal_row.spot} CHG:{chg_s}\n"
            f"DOLLAR_DOMINANCE_PCT:{dom_txt}\n"
            f"POLYMARKET_ODDS_JSON:{input_data.polymarket_odds_json}\n"
            f"{input_data.polymarket_context}\n"
            "STRUCTURE: Block1 signals Block2 call and key level Block3 primary risk.\n"
            "Use 10Y and Oil context to distinguish narrow rates-driven moves "
            "from broader macro moves.\n"
            "Explicitly mention if the Primary Driver is shifting from 2Y rates "
            "to broader macro (Oil/10Y).\n"
            "You MUST synthesize DOLLAR_DOMINANCE_PCT with POLYMARKET_ODDS_JSON to explain "
            "today's move: reconcile book-wide USD thematic alignment with prediction-market "
            "macro odds (Fed path, recession, etc.).\n"
            "If Polymarket odds are provided, treat them as cutting-edge market sentiment and use "
            "them in Primary Risk or Macro Context.\n"
            "OUTPUT: plain text only. No headers. No markdown."
        )
        return [{"role": "user", "content": prompt}]

    def parse(self, payload_text: str) -> str:
        return payload_text

    def purpose(self, input_data: PairBriefInput) -> str:
        return f"brief{input_data.pair}"
