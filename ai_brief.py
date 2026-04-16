import json
import math
import os
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv

"""
AI narrative brief Pipeline.

Execution context:
- Called by run.py as STEP 9 (ai)
- Depends on: morning_brief.py (brief text must exist)
- Outputs: data/ai_article.json, site/data/ai_article.json
- Next step: create_html_brief.py
- Blocking: NO — pipeline continues if this step fails

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""

load_dotenv()

try:
    import anthropic
except ImportError:
    anthropic = None

_MODEL = "claude-haiku-4-5-20251001"
_AI_ARTICLE_OUTPUT = os.path.join("data", "ai_article.json")
_AI_READ_OUTPUT = os.path.join("data", "ai_regime_read.json")


def _load_morning_brief() -> str:
    """Phase 2: load today's morning brief text as primary narrative source.

    Returns empty string if file absent or unreadable — prompt degrades to
    CSV-only mode but never raises.
    """
    try:
        from core.paths import brief_txt
        path = brief_txt()
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

PAIR_CONFIG = {
    "eurusd": {
        "label": "EUR/USD",
        "spread_col": "US_DE_10Y_spread",
        "spread_name": "US-DE 10Y spread",
        "vol_pct_col": "EURUSD_vol_pct",
        "cot_pct_col": "EUR_lev_percentile",
        "regime_col": "eurusd_composite_label",
        "score_col": "eurusd_composite_score",
        "chart_map": {
            "rate_diff": "rate_differentials",
            "vol": "vol_correlation",
            "cot": "cot_positioning",
            "regime": "rate_differentials",
        },
    },
    "usdjpy": {
        "label": "USD/JPY",
        "spread_col": "US_JP_10Y_spread",
        "spread_name": "US-JP 10Y spread",
        "vol_pct_col": "USDJPY_vol_pct",
        "cot_pct_col": "JPY_lev_percentile",
        "regime_col": "usdjpy_composite_label",
        "score_col": "usdjpy_composite_score",
        "chart_map": {
            "rate_diff": "rate_differentials",
            "vol": "vol_correlation",
            "cot": "cot_positioning",
            "regime": "rate_differentials",
        },
    },
    "usdinr": {
        "label": "USD/INR",
        "spread_col": "US_IN_10Y_spread",
        "spread_name": "US-IN 10Y spread",
        "vol_pct_col": "USDINR_vol_pct",
        # USD/INR has no COT dataset in the current pipeline. We use
        # FPI percentile as the positioning proxy for "material change".
        "cot_pct_col": "FPI_20D_percentile",
        "regime_col": "inr_composite_label",
        "score_col": "inr_composite_score",
        "chart_map": {
            "rate_diff": "rate_differentials",
            "vol": "vol_correlation",
            "cot": "cot_positioning",
            "regime": "rate_differentials",
        },
    },
}

TEMPLATE = """
{date} — G10 FX Regime Brief

EUR/USD is in a {eurusd_regime} regime with {eurusd_confidence}% confidence.
The primary driver is {eurusd_driver}. Rate differential at {eurusd_rate_diff}
on {eurusd_cot_percentile} percentile COT positioning.

USD/JPY shows {usdjpy_regime} conditions at {usdjpy_confidence}% confidence.
{usdjpy_driver} remains the dominant signal.

USD/INR is {usdinr_regime} — directional read only.
RBI intervention active. {usdinr_driver}.

Signal changes today: {signal_changes}
""".strip()


def _safe_float(value):
    try:
        parsed = float(value)
        return None if math.isnan(parsed) else parsed
    except (TypeError, ValueError):
        return None


def _safe_str(value, default="N/A"):
    if value is None:
        return default
    text = str(value).strip()
    return default if text in {"", "nan", "NaN", "None"} else text


def _iso_utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _confidence_from_score(score):
    f_score = _safe_float(score)
    if f_score is None:
        return 0.5
    conf = min(abs(f_score) / 100.0, 0.95)
    return round(max(conf, 0.05), 2)


def _rate_diff_zcross(series):
    if series is None or len(series) < 3:
        return False
    diffs = series.diff()
    rolling_mean = diffs.rolling(60, min_periods=20).mean()
    rolling_std = diffs.rolling(60, min_periods=20).std()
    z = (diffs - rolling_mean) / rolling_std
    z = z.replace([float("inf"), float("-inf")], pd.NA).dropna()
    if len(z) < 2:
        return False
    prev_val = abs(float(z.iloc[-2]))
    curr_val = abs(float(z.iloc[-1]))
    crossed_up = prev_val <= 1.5 < curr_val
    crossed_down = prev_val > 1.5 >= curr_val
    return crossed_up or crossed_down


def _build_pair_signal(master_df, pair, cfg):
    current = master_df.iloc[-1]
    previous = master_df.iloc[-2] if len(master_df) > 1 else current

    spread = _safe_float(current.get(cfg["spread_col"]))
    spread_prev = _safe_float(previous.get(cfg["spread_col"]))
    vol_pct = _safe_float(current.get(cfg["vol_pct_col"]))
    vol_pct_prev = _safe_float(previous.get(cfg["vol_pct_col"]))
    cot_pct = _safe_float(current.get(cfg["cot_pct_col"]))
    cot_pct_prev = _safe_float(previous.get(cfg["cot_pct_col"]))

    regime = _safe_str(current.get(cfg["regime_col"]), "NEUTRAL")
    regime_prev = _safe_str(previous.get(cfg["regime_col"]), regime)
    confidence = _confidence_from_score(current.get(cfg["score_col"]))

    spread_series = (
        master_df[cfg["spread_col"]]
        if cfg["spread_col"] in master_df.columns
        else pd.Series(dtype="float64")
    )
    z_cross = _rate_diff_zcross(spread_series)

    material = {
        "cot": (
            cot_pct is not None
            and cot_pct_prev is not None
            and abs(cot_pct - cot_pct_prev) > 5.0
        ),
        "rate_diff": z_cross,
        "vol": (
            vol_pct is not None
            and vol_pct_prev is not None
            and abs(vol_pct - vol_pct_prev) > 8.0
        ),
        "regime": regime != regime_prev,
    }

    signal_changes = []
    if material["cot"]:
        signal_changes.append(
            f"{cfg['label']} positioning percentile moved "
            f"{cot_pct_prev:.1f} -> {cot_pct:.1f}."
        )
    if material["rate_diff"]:
        signal_changes.append(
            f"{cfg['label']} {cfg['spread_name']} daily-change z-score crossed "
            "the 1.5 threshold."
        )
    if material["vol"]:
        signal_changes.append(
            f"{cfg['label']} volatility percentile moved "
            f"{vol_pct_prev:.1f} -> {vol_pct:.1f}."
        )
    if material["regime"]:
        signal_changes.append(
            f"{cfg['label']} regime changed from {regime_prev} to {regime}."
        )

    chart_types = []
    for key, changed in material.items():
        if changed:
            mapped = cfg["chart_map"].get(key)
            if mapped and mapped not in chart_types:
                chart_types.append(mapped)

    if spread is None:
        spread_text = "N/A"
    else:
        spread_text = f"{spread:+.2f}pp"

    if cot_pct is None:
        cot_text = "N/A"
    else:
        cot_text = f"{cot_pct:.1f}th percentile"

    driver = (
        f"{cfg['spread_name']} at {spread_text} with positioning at {cot_text}."
    )

    return {
        "pair": pair,
        "label": cfg["label"],
        "regime": regime,
        "confidence": confidence,
        "spread": spread,
        "cot_percentile": cot_pct,
        "vol_percentile": vol_pct,
        "driver": driver,
        "watch_for": f"{cfg['spread_name']} momentum reversal or regime flip.",
        "chart_types": chart_types,
        "signal_changes": signal_changes,
        "material_flags": material,
    }


def build_narrative_prompt(signal_data: dict, brief_text: str = "") -> str:
    """Build the prompt for Claude from signal data.

    Phase 2: the morning brief text (if available) is the *primary* source of
    truth for the narrative. Signal data JSON is supplied as supporting
    numeric context, not the ground truth.
    """
    brief_section = (
        f"\nPRIMARY SOURCE — today's morning brief (use this as the\n"
        f"narrative ground truth; do not contradict its framing):\n"
        f"----- BRIEF BEGIN -----\n{brief_text.strip()[:6000]}\n----- BRIEF END -----\n"
        if brief_text else ""
    )
    return f"""You are writing a daily FX regime intelligence
brief for institutional macro researchers.
{brief_section}
Supporting structured signal data (numeric context only — narrative must
align with the morning brief above when present):
{json.dumps(signal_data, indent=2)}

Return valid JSON only with this schema:
{{
  "headline": "string",
  "sections": {{
    "macro_context": "string",
    "eurusd": {{
      "narrative": "string",
      "key_driver": "string",
      "watch_for": "string"
    }},
    "usdjpy": {{
      "narrative": "string",
      "key_driver": "string",
      "watch_for": "string"
    }},
    "usdinr": {{
      "narrative": "string",
      "key_driver": "string",
      "watch_for": "string"
    }}
  }}
}}

Write a concise research article with these sections:

## Macro Context
One paragraph: what is the dominant macro theme today
and how it affects G10 FX regimes.

## EUR/USD
Regime: [state regime and confidence]
Two paragraphs: what the signals say and why it matters.
Key driver: [primary driver in one sentence]
Watch for: [what would change the call]

## USD/JPY
Same structure as EUR/USD.

## USD/INR
Same structure. Note: directional only due to RBI
intervention. No precision entries.

Rules:
- Write like a senior FX researcher, not a student
- No hedging language ("may", "might", "could")
- Data-grounded: cite the actual numbers
- Maximum 600 words total
- Never mention "AI" or "generated"
- Tone: calm, precise, confident

CRITICAL: Respond with a single JSON object only. No markdown fences, no
preamble or explanation before or after the JSON.
"""


def _build_signal_data(master_df):
    payload = {
        "date": str(master_df.index[-1].date()),
        "pairs": {},
        "signal_changes": [],
    }
    charts_to_show = {}
    pair_signals = {}

    for pair, cfg in PAIR_CONFIG.items():
        pair_data = _build_pair_signal(master_df, pair, cfg)
        pair_signals[pair] = pair_data
        payload["pairs"][pair] = {
            "regime": pair_data["regime"],
            "confidence": pair_data["confidence"],
            "spread": pair_data["spread"],
            "cot_percentile": pair_data["cot_percentile"],
            "vol_percentile": pair_data["vol_percentile"],
            "driver": pair_data["driver"],
            "watch_for": pair_data["watch_for"],
        }
        payload["signal_changes"].extend(pair_data["signal_changes"])
        charts_to_show[pair] = pair_data["chart_types"]

    payload["charts_to_show"] = charts_to_show
    return payload, pair_signals


def _fallback_article(signal_data, pair_signals):
    eur = pair_signals["eurusd"]
    jpy = pair_signals["usdjpy"]
    inr = pair_signals["usdinr"]
    changes = signal_data["signal_changes"] or ["No material signal changes."]
    signal_changes_text = "; ".join(changes)

    rendered = TEMPLATE.format(
        date=signal_data["date"],
        eurusd_regime=eur["regime"],
        eurusd_confidence=round(eur["confidence"] * 100),
        eurusd_driver=eur["driver"],
        eurusd_rate_diff=f"{eur['spread']:+.2f}pp" if eur["spread"] is not None else "N/A",
        eurusd_cot_percentile=(
            f"{eur['cot_percentile']:.1f}th"
            if eur["cot_percentile"] is not None
            else "N/A"
        ),
        usdjpy_regime=jpy["regime"],
        usdjpy_confidence=round(jpy["confidence"] * 100),
        usdjpy_driver=jpy["driver"],
        usdinr_regime=inr["regime"],
        usdinr_driver=inr["driver"],
        signal_changes=signal_changes_text,
    )

    return {
        "headline": (
            "Rate differential momentum drives the latest "
            "G10 FX regime configuration"
        ),
        "sections": {
            "macro_context": rendered.split("\n\n")[0],
            "eurusd": {
                "narrative": (
                    f"EUR/USD holds {eur['regime']} with "
                    f"{round(eur['confidence'] * 100)}% confidence. {eur['driver']}"
                ),
                "key_driver": eur["driver"],
                "watch_for": eur["watch_for"],
            },
            "usdjpy": {
                "narrative": (
                    f"USD/JPY tracks {jpy['regime']} with "
                    f"{round(jpy['confidence'] * 100)}% confidence. {jpy['driver']}"
                ),
                "key_driver": jpy["driver"],
                "watch_for": jpy["watch_for"],
            },
            "usdinr": {
                "narrative": (
                    f"USD/INR is {inr['regime']} in a directional-only frame. "
                    f"{inr['driver']}"
                ),
                "key_driver": inr["driver"],
                "watch_for": inr["watch_for"],
            },
            "signal_changes": changes,
        },
    }


def _parse_claude_json_response(raw_text: str) -> dict:
    """Parse JSON from model output; tolerate markdown fences and leading prose."""
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("empty model response")

    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object start in model response")
    try:
        parsed, _ = decoder.raw_decode(text, start)
    except json.JSONDecodeError:
        raise
    if not isinstance(parsed, dict):
        raise ValueError("model JSON root must be an object")
    return parsed


def generate_brief_article(signal_data: dict) -> dict:
    """
    Takes structured signal data and returns
    a formatted article with sections per pair.
    Uses Claude Haiku for cost efficiency (~$0.003/call).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key or anthropic is None:
        raise RuntimeError("Anthropic API unavailable.")

    client = anthropic.Anthropic(api_key=api_key, timeout=30.0)
    brief_text = _load_morning_brief()
    prompt = build_narrative_prompt(signal_data, brief_text=brief_text)
    message = client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = message.content[0].text
    parsed = _parse_claude_json_response(raw_text)
    return {
        "date": signal_data.get("date"),
        "headline": _safe_str(parsed.get("headline"), "FX regime briefing"),
        "sections": parsed.get("sections", {}),
        "generated_at": _iso_utc_now(),
    }


def _merge_article(model_article, signal_data, pair_signals):
    sections = model_article.get("sections", {})

    merged_pairs = {}
    for pair in ("eurusd", "usdjpy", "usdinr"):
        pair_section = sections.get(pair, {})
        pair_signal = pair_signals[pair]
        merged_pairs[pair] = {
            "regime": pair_signal["regime"],
            "confidence": pair_signal["confidence"],
            "narrative": _safe_str(pair_section.get("narrative"), pair_signal["driver"]),
            "key_driver": _safe_str(pair_section.get("key_driver"), pair_signal["driver"]),
            "watch_for": _safe_str(pair_section.get("watch_for"), pair_signal["watch_for"]),
        }

    merged = {
        "date": signal_data["date"],
        "headline": _safe_str(
            model_article.get("headline"),
            "Rate differential momentum drives G10 FX regime direction",
        ),
        "sections": {
            "macro_context": _safe_str(
                sections.get("macro_context"),
                "Macro regime remains dominated by rates and positioning.",
            ),
            "eurusd": merged_pairs["eurusd"],
            "usdjpy": merged_pairs["usdjpy"],
            "usdinr": merged_pairs["usdinr"],
            "signal_changes": signal_data["signal_changes"]
            if signal_data["signal_changes"]
            else ["No material signal changes."],
        },
        "charts_to_show": signal_data["charts_to_show"],
        "generated_at": model_article.get("generated_at", _iso_utc_now()),
    }
    return merged


def _write_outputs(article):
    os.makedirs("data", exist_ok=True)
    with open(_AI_ARTICLE_OUTPUT, "w", encoding="utf-8") as file_handle:
        json.dump(article, file_handle, indent=2)

    compatible_read = {
        "generated_at": article["generated_at"],
        "data_date": article["date"],
        "eurusd": article["sections"]["eurusd"]["narrative"],
        "usdjpy": article["sections"]["usdjpy"]["narrative"],
        "usdinr": article["sections"]["usdinr"]["narrative"],
    }
    with open(_AI_READ_OUTPUT, "w", encoding="utf-8") as file_handle:
        json.dump(compatible_read, file_handle, indent=2)

    print(f"[AI] wrote {_AI_ARTICLE_OUTPUT}")
    print(f"[AI] wrote {_AI_READ_OUTPUT}")


def run():
    master_path = os.path.join("data", "latest_with_cot.csv")
    if not os.path.exists(master_path):
        print(f"[AI] {master_path} not found — skipping.")
        return

    master_df = pd.read_csv(master_path, index_col=0, parse_dates=True)
    if len(master_df) == 0:
        print("[AI] latest_with_cot.csv empty — skipping.")
        return

    signal_data, pair_signals = _build_signal_data(master_df)

    try:
        model_article = generate_brief_article(signal_data)
        article = _merge_article(model_article, signal_data, pair_signals)
        print("[AI] Claude narrative generation OK")
    except Exception as exc:
        print(f"[AI] fallback narrative template used: {exc}")
        fallback = _fallback_article(signal_data, pair_signals)
        fallback["date"] = signal_data["date"]
        fallback["charts_to_show"] = signal_data["charts_to_show"]
        fallback["generated_at"] = _iso_utc_now()
        article = _merge_article(fallback, signal_data, pair_signals)

    _write_outputs(article)


if __name__ == "__main__":
    run()
