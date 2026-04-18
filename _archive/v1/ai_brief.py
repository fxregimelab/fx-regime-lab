import json
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv

"""
AI narrative brief Pipeline.

Execution context:
- Called by run.py as STEP 9 (ai)
- Depends on: morning_brief.py (brief text must exist)
- Outputs: data/ai_article.json, data/ai_regime_read.json
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

SYSTEM_PROMPT = (
    "You are a senior FX macro analyst writing the daily morning brief for an "
    "institutional research terminal. Your output is read by discretionary macro "
    "portfolio managers. Write in clean, direct prose. No bullet points. No headers. "
    "No markdown. No em-dashes. No pipeline variable names, no placeholder text, no "
    "bracketed labels. Never write things like [MISSING DATA], [N/A], signal_name=value, "
    "or any raw Python variable output. "
    "Structure: one paragraph per currency pair (EUR/USD, USD/JPY, USD/INR). Each "
    "paragraph must: state the current regime and confidence level in plain English, "
    "name the primary driver, note any signal that changed materially since the prior "
    "session, and close with one sentence on what a PM would watch next. Macro context "
    "goes at the top in one sentence before the pair paragraphs. Total output must be "
    "180-250 words. Practitioner tone throughout: this is not educational content, "
    "it is a live market brief."
)

_FORBIDDEN_SUBSTRINGS = (
    "[missing",
    "[n/a]",
    "[error",
    "signal_",
    "_norm",
    "_raw",
    "_pipeline",
    "={",
    "= {",
    "traceback",
    "keyerror",
    "typeerror",
)
_NONE_WORD_RE = re.compile(r"\bnone\b", re.IGNORECASE)


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


def _fmt_spread_pp(value: Optional[float]) -> str:
    if value is None:
        return "unavailable"
    return f"{value:+.2f} percentage points"


def _fmt_pctile(value: Optional[float], label: str) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.1f} ({label})"


def build_signal_context_lines(signal_data: dict) -> str:
    """Plain-text key-value lines for the user prompt (no JSON or snake_case)."""
    lines: List[str] = []
    d = signal_data.get("date")
    lines.append(f"Observation date: {d}")
    order = ("eurusd", "usdjpy", "usdinr")
    for pair_key in order:
        cfg = PAIR_CONFIG[pair_key]
        lab = cfg["label"]
        pdata = (signal_data.get("pairs") or {}).get(pair_key) or {}
        regime = pdata.get("regime")
        conf = pdata.get("confidence")
        conf_pct = (
            round(float(conf) * 100) if conf is not None else None
        )
        lines.append(
            f"{lab} composite regime label: {regime if regime is not None else 'unavailable'}"
        )
        if conf_pct is not None:
            lines.append(f"{lab} model confidence (approximate): {conf_pct}%")
        spread = pdata.get("spread")
        lines.append(
            f"{lab} {cfg['spread_name']} (level versus prior close proxy): "
            f"{_fmt_spread_pp(spread if isinstance(spread, (int, float)) else None)}"
        )
        cot = pdata.get("cot_percentile")
        cot_label = (
            "COT leveraged positioning percentile"
            if pair_key != "usdinr"
            else "Positioning proxy percentile (FPI-style window)"
        )
        lines.append(f"{lab} {cot_label}: {_fmt_pctile(cot, 'percentile')}")
        volp = pdata.get("vol_percentile")
        lines.append(
            f"{lab} implied volatility percentile: {_fmt_pctile(volp, 'percentile')}"
        )
        drv = pdata.get("driver")
        if drv:
            lines.append(f"{lab} desk-style driver summary: {drv}")
        lines.append("")

    changes = signal_data.get("signal_changes") or []
    if changes:
        lines.append("Material signal changes since the prior session:")
        for ch in changes:
            lines.append(f"- {ch}")
    else:
        lines.append("Material signal changes since the prior session: none flagged.")
    return "\n".join(lines).strip()


def build_user_prompt(signal_data: dict, brief_text: str = "") -> str:
    """User message: optional desk brief plus labeled signal lines."""
    signal_block = build_signal_context_lines(signal_data)
    parts = [
        "Write today's institutional morning brief per your system instructions.",
        "Use only the facts below and the desk brief when present. Output plain prose only.",
        "",
        "Supporting inputs (readable labels):",
        signal_block,
        "",
    ]
    if brief_text.strip():
        parts.extend(
            [
                "Primary desk brief for narrative alignment (do not contradict):",
                "----- BRIEF BEGIN -----",
                brief_text.strip()[:6000],
                "----- BRIEF END -----",
                "",
            ]
        )
    parts.append(
        "Respond with the brief only: one macro sentence, then one paragraph each "
        "for EUR/USD, USD/JPY, and USD/INR, separated by blank lines. No other text."
    )
    return "\n".join(parts)


def _first_sentence(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    for i, ch in enumerate(text):
        if ch in ".?!" and (i == len(text) - 1 or text[i + 1].isspace()):
            return text[: i + 1].strip()
    return text


def _split_pair_paragraphs(after_macro: str) -> List[str]:
    s = after_macro.strip()
    if not s:
        return ["", "", ""]
    chunks = [p.strip() for p in re.split(r"\n\s*\n+", s) if p.strip()]
    if len(chunks) >= 3:
        return chunks[:3]
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    if len(lines) >= 3:
        return lines[:3]
    if len(chunks) == 2:
        return [chunks[0], chunks[1], ""]
    if len(chunks) == 1:
        return [chunks[0], "", ""]
    if len(lines) == 2:
        return [lines[0], lines[1], ""]
    if len(lines) == 1:
        return [lines[0], "", ""]
    return ["", "", ""]


def parse_plain_text_brief(raw_text: str, pair_signals: Dict[str, Any]) -> Dict[str, Any]:
    """Turn model plain-text output into the article dict shape expected by _merge_article."""
    raw = (raw_text or "").strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    macro = _first_sentence(raw)
    rest = raw[len(macro) :].strip() if macro else raw
    paras = _split_pair_paragraphs(rest)
    for i, pair in enumerate(("eurusd", "usdjpy", "usdinr")):
        if not paras[i]:
            ps = pair_signals[pair]
            paras[i] = (
                f"{ps['label']} is in a {ps['regime']} regime with "
                f"{round(ps['confidence'] * 100)}% confidence. {ps['driver']}"
            )
    eur_p, jpy_p, inr_p = paras[0], paras[1], paras[2]
    headline = macro[:80] + ("…" if len(macro) > 80 else "") if macro else "G10 FX regime brief"

    return {
        "headline": headline,
        "sections": {
            "macro_context": macro,
            "eurusd": {"narrative": eur_p},
            "usdjpy": {"narrative": jpy_p},
            "usdinr": {"narrative": inr_p},
        },
        "generated_at": _iso_utc_now(),
    }


def validate_brief_quality(brief_text: str) -> Tuple[bool, str]:
    """Quality gate on the raw institutional brief string."""
    t = (brief_text or "").strip()
    words = t.split()
    if len(words) < 150:
        return False, f"brief too short ({len(words)} words, minimum 150)"

    low = t.lower()
    for sub in _FORBIDDEN_SUBSTRINGS:
        if sub in low:
            return False, f"forbidden marker or leak: {sub!r}"

    if _NONE_WORD_RE.search(t):
        return False, "forbidden marker or leak: standalone 'none'"

    def _has_pair(s: str, slash_pat: str, compact_pat: str) -> bool:
        u = s.upper()
        return slash_pat in u or compact_pat in u

    if not _has_pair(t, "EUR/USD", "EURUSD"):
        return False, "missing EUR/USD (or EURUSD)"
    if not _has_pair(t, "USD/JPY", "USDJPY"):
        return False, "missing USD/JPY (or USDJPY)"
    if not _has_pair(t, "USD/INR", "USDINR"):
        return False, "missing USD/INR (or USDINR)"

    return True, ""


def _tokenize_overlap(s: str) -> Counter:
    return Counter(re.findall(r"[a-z0-9]+", s.lower()))


def _overlap_coefficient(a: str, b: str) -> float:
    ca, cb = _tokenize_overlap(a), _tokenize_overlap(b)
    if not ca:
        return 0.0
    inter = sum(min(ca[w], cb[w]) for w in ca)
    return inter / sum(ca.values())


def _load_latest_brief_log_text() -> Optional[str]:
    """Most recent brief_log row (typically today's desk brief after text step)."""
    try:
        from core.supabase_client import get_client

        cli = get_client()
        if cli is None:
            return None
        res = (
            cli.table("brief_log")
            .select("brief_text")
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        rows = getattr(res, "data", None) or []
        if rows and rows[0].get("brief_text"):
            return str(rows[0]["brief_text"]).strip()
        return None
    except Exception:
        return None


def _load_prior_brief_log_text(current_date: str) -> Optional[str]:
    try:
        from core.supabase_client import get_client

        cli = get_client()
        if cli is None:
            return None
        res = (
            cli.table("brief_log")
            .select("date,brief_text")
            .order("date", desc=True)
            .limit(15)
            .execute()
        )
        rows = getattr(res, "data", None) or []
        for row in rows:
            if row.get("date") == current_date:
                continue
            bt = row.get("brief_text")
            if bt and str(bt).strip():
                return str(bt).strip()
        return None
    except Exception:
        return None


def _similarity_fail_reason(brief_text: str, current_date: str) -> Optional[str]:
    prior = _load_prior_brief_log_text(current_date)
    if not prior:
        return None
    coeff = _overlap_coefficient(brief_text, prior)
    if coeff > 0.85:
        return "brief too similar to prior day"
    return None


def validate_brief_quality_full(brief_text: str, current_date: str) -> Tuple[bool, str]:
    ok, reason = validate_brief_quality(brief_text)
    if not ok:
        return ok, reason
    sim = _similarity_fail_reason(brief_text, current_date)
    if sim:
        return False, sim
    return True, ""


def _macro_from_desk_brief(brief_text: str) -> str:
    idx = brief_text.find("DESK SUMMARY")
    if idx < 0:
        t = brief_text.strip()
        return _first_sentence(t) if t else "Prior desk brief (quality gate fallback)."
    tail = brief_text[idx:]
    grabbed: List[str] = []
    for ln in tail.splitlines()[1:]:
        s = ln.strip()
        if not s or s.startswith("---"):
            if grabbed:
                break
            continue
        if s.startswith("Near-term catalyst"):
            break
        if s.startswith("REGIME CALL ACCURACY"):
            break
        grabbed.append(s)
    joined = " ".join(grabbed).strip()
    return joined[:800] if joined else "Prior desk brief (quality gate fallback)."


def _article_from_brief_log_text(
    brief_text: str, signal_data: dict, pair_signals: Dict[str, Any]
) -> Dict[str, Any]:
    """Rebuild article JSON from a saved desk brief (REGIME READ + summary)."""
    macro = _macro_from_desk_brief(brief_text)
    eur_m = re.search(
        r"EUR/USD\s+(.+?)(?=\n\s*\n\s*USD/JPY|\n\s*USD/JPY\s)",
        brief_text,
        re.DOTALL | re.IGNORECASE,
    )
    jpy_m = re.search(
        r"USD/JPY\s+(.+?)(?=\n\s*\n\s*=+|\n\s*=+\s*$|\Z)",
        brief_text,
        re.DOTALL | re.IGNORECASE,
    )
    eur_body = re.sub(r"\s+", " ", eur_m.group(1).strip()) if eur_m else ""
    jpy_body = re.sub(r"\s+", " ", jpy_m.group(1).strip()) if jpy_m else ""
    inr = pair_signals["usdinr"]
    inr_body = (
        f"USD/INR is in a {inr['regime']} regime with "
        f"{round(inr['confidence'] * 100)}% confidence (directional read). {inr['driver']}"
    )
    if not eur_body:
        ps = pair_signals["eurusd"]
        eur_body = (
            f"EUR/USD is in a {ps['regime']} regime with "
            f"{round(ps['confidence'] * 100)}% confidence. {ps['driver']}"
        )
    if not jpy_body:
        ps = pair_signals["usdjpy"]
        jpy_body = (
            f"USD/JPY is in a {ps['regime']} regime with "
            f"{round(ps['confidence'] * 100)}% confidence. {ps['driver']}"
        )

    hl = "G10 FX regime brief (prior desk snapshot)"
    mtitle = re.search(r"G10 FX MORNING BRIEF", brief_text, re.IGNORECASE)
    if mtitle:
        hl = "G10 FX Morning Brief (prior desk snapshot)"

    return {
        "date": signal_data.get("date"),
        "headline": hl,
        "sections": {
            "macro_context": macro,
            "eurusd": {"narrative": eur_body},
            "usdjpy": {"narrative": jpy_body},
            "usdinr": {"narrative": inr_body},
        },
        "generated_at": _iso_utc_now(),
    }


def _call_claude_plain(
    client: Any, user_prompt: str, retry_suffix: str = ""
) -> str:
    up = user_prompt + (retry_suffix or "")
    message = client.messages.create(
        model=_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": up}],
    )
    return message.content[0].text


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


def generate_brief_article(
    signal_data: dict, pair_signals: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calls Claude with system + user prompts; returns article dict after
    plain-text quality checks (retry once, then brief_log fallback).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key or anthropic is None:
        raise RuntimeError("Anthropic API unavailable.")

    client = anthropic.Anthropic(api_key=api_key, timeout=120.0)
    brief_text = _load_morning_brief()
    user_prompt = build_user_prompt(signal_data, brief_text=brief_text)
    date_s = str(signal_data.get("date", ""))

    raw_text = _call_claude_plain(client, user_prompt)
    ok, reason = validate_brief_quality_full(raw_text, date_s)
    if not ok:
        raw_text = _call_claude_plain(
            client,
            user_prompt,
            f"\n\nPrevious attempt failed quality check: {reason}. Rewrite fully.",
        )
        ok, reason = validate_brief_quality_full(raw_text, date_s)

    if not ok:
        from core.signal_write import log_pipeline_error

        log_pipeline_error("ai_brief_quality_gate", reason, pair=None)
        print(f"[AI] WARN quality gate failed after retry: {reason}")
        latest_bt = _load_latest_brief_log_text()
        if latest_bt:
            print("[AI] WARN using latest brief_log desk brief as fallback")
            return _article_from_brief_log_text(latest_bt, signal_data, pair_signals)
        raise RuntimeError(f"quality gate failed and brief_log empty: {reason}")

    wc = len(raw_text.split())
    print(f"[AI] institutional brief passed quality gate ({wc} words)")
    print("[AI] ----- institutional brief (plain text) -----")
    print(raw_text.strip())
    print("[AI] ----- end institutional brief -----")

    parsed = parse_plain_text_brief(raw_text, pair_signals)
    parsed["date"] = signal_data.get("date")
    return parsed


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
        model_article = generate_brief_article(signal_data, pair_signals)
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
