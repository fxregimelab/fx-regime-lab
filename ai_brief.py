# ai_brief.py
# Phase 13 — AI regime reads via Claude 3.5 Haiku
#
# Reads the latest data snapshot, sends concise numeric context to Claude,
# and writes data/ai_regime_read.json.  Fails gracefully (exit 0) if
# ANTHROPIC_API_KEY is absent or the API is unreachable.
#
# Output JSON format:
# {
#   "generated_at": "2026-03-11T07:00:00Z",
#   "data_date":    "2026-03-10",
#   "eurusd":       "<2-3 sentence regime read>",
#   "usdjpy":       "<2-3 sentence regime read>",
#   "usdinr":       "<2-3 sentence regime read>"
# }

import os
import json
import math
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

_ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
_MODEL         = "claude-3-5-haiku-20241022"
_OUTPUT        = os.path.join("data", "ai_regime_read.json")

# ── helpers ───────────────────────────────────────────────────────────────────

def _f(v, fmt=".2f", suffix=""):
    """Format a numeric value; return '—' on NaN/missing."""
    try:
        x = float(v)
        if math.isnan(x):
            return "—"
        return f"{x:{fmt}}{suffix}"
    except (TypeError, ValueError):
        return "—"


def _s(v):
    """Safe string for flag/label columns."""
    if v is None:
        return "—"
    sv = str(v)
    return "—" if sv in ("nan", "None", "", "NaN") else sv


# ── data context builders ─────────────────────────────────────────────────────

def _eur_context(m_row):
    return (
        f"EUR/USD {_f(m_row.get('EURUSD'), '.4f')}  "
        f"1D {_f(m_row.get('EURUSD_chg_1D'), '+.2f', '%')}  "
        f"1M {_f(m_row.get('EURUSD_chg_1M'), '+.2f', '%')}  "
        f"12M {_f(m_row.get('EURUSD_chg_12M'), '+.2f', '%')}\n"
        f"US-DE 10Y spread: {_f(m_row.get('US_DE_10Y_spread'), '+.2f', 'pp')}  "
        f"12M chg: {_f(m_row.get('US_DE_10Y_spread_chg_12M'), '+.2f', 'pp')}\n"
        f"BTP-Bund: {_f(m_row.get('BTP_Bund_spread'), '.2f', 'pp')} [{_s(m_row.get('BTP_Bund_flag'))}]\n"
        f"EURUSD vol: {_f(m_row.get('EURUSD_vol30'), '.1f', '% ann')} "
        f"({_f(m_row.get('EURUSD_vol_pct'), '.0f', 'th pct')})\n"
        f"COT EUR leveraged net: {_f(m_row.get('EUR_lev_net'), '.0f')} contracts "
        f"({_f(m_row.get('EUR_lev_percentile'), '.0f', 'th pct')})\n"
        f"COT EUR assetmgr net: {_f(m_row.get('EUR_assetmgr_net'), '.0f')} "
        f"({_f(m_row.get('EUR_assetmgr_percentile'), '.0f', 'th pct')})\n"
        f"G10 composite: {_f(m_row.get('eurusd_composite_score'), '.1f')} "
        f"[{_s(m_row.get('eurusd_composite_label'))}]\n"
        f"Support: {_s(m_row.get('EURUSD_S1'))} / {_s(m_row.get('EURUSD_S2'))}  "
        f"Resistance: {_s(m_row.get('EURUSD_R1'))} / {_s(m_row.get('EURUSD_R2'))}"
    )


def _jpy_context(m_row):
    return (
        f"USD/JPY {_f(m_row.get('USDJPY'), '.2f')}  "
        f"1D {_f(m_row.get('USDJPY_chg_1D'), '+.2f', '%')}  "
        f"1M {_f(m_row.get('USDJPY_chg_1M'), '+.2f', '%')}  "
        f"12M {_f(m_row.get('USDJPY_chg_12M'), '+.2f', '%')}\n"
        f"US-JP 10Y spread: {_f(m_row.get('US_JP_10Y_spread'), '+.2f', 'pp')}  "
        f"12M chg: {_f(m_row.get('US_JP_10Y_spread_chg_12M'), '+.2f', 'pp')}\n"
        f"USDJPY vol: {_f(m_row.get('USDJPY_vol30'), '.1f', '% ann')} "
        f"({_f(m_row.get('USDJPY_vol_pct'), '.0f', 'th pct')})\n"
        f"COT JPY leveraged net: {_f(m_row.get('JPY_lev_net'), '.0f')} contracts "
        f"({_f(m_row.get('JPY_lev_percentile'), '.0f', 'th pct')})\n"
        f"COT JPY assetmgr net: {_f(m_row.get('JPY_assetmgr_net'), '.0f')} "
        f"({_f(m_row.get('JPY_assetmgr_percentile'), '.0f', 'th pct')})\n"
        f"G10 composite: {_f(m_row.get('usdjpy_composite_score'), '.1f')} "
        f"[{_s(m_row.get('usdjpy_composite_label'))}]\n"
        f"Support: {_s(m_row.get('USDJPY_S1'))} / {_s(m_row.get('USDJPY_S2'))}  "
        f"Resistance: {_s(m_row.get('USDJPY_R1'))} / {_s(m_row.get('USDJPY_R2'))}"
    )


def _inr_context(m_row, i_row):
    inr_row = i_row if i_row is not None else {}
    return (
        f"USD/INR {_f(m_row.get('USDINR', inr_row.get('USDINR')), '.4f')}  "
        f"1D {_f(m_row.get('USDINR_chg_1D', inr_row.get('USDINR_chg_1D')), '+.2f', '%')}  "
        f"1M {_f(m_row.get('USDINR_chg_1M', inr_row.get('USDINR_chg_1M')), '+.2f', '%')}  "
        f"12M {_f(m_row.get('USDINR_chg_12M', inr_row.get('USDINR_chg_12M')), '+.2f', '%')}\n"
        f"US-IN 10Y spread: {_f(i_row.get('US_IN_10Y_spread') if i_row else None, '+.2f', 'pp')}\n"
        f"USDINR vol: {_f(i_row.get('USDINR_vol30') if i_row else None, '.1f', '% ann')} "
        f"({_f(i_row.get('USDINR_vol_pct') if i_row else None, '.0f', 'th pct')})\n"
        f"FPI 20D equity flow: {_f(i_row.get('FPI_20D_flow') if i_row else None, '+,.0f', ' Cr INR')} "
        f"({_f(i_row.get('FPI_20D_percentile') if i_row else None, '.0f', 'th pct')})\n"
        f"RBI intervention flag: {_s(i_row.get('rbi_intervention_flag') if i_row else None)}\n"
        f"INR composite: {_f(i_row.get('inr_composite_score') if i_row else None, '.1f')} "
        f"[{_s(i_row.get('inr_composite_label') if i_row else None)}]"
    )


# ── prompt builder ────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a professional G10 FX and EM FX analyst writing a concise morning brief entry. "
    "Given quantitative data for a currency pair, write exactly 2-3 sentences describing "
    "the current regime, key driver, and near-term directional bias. "
    "Be specific and data-driven. No hedging phrases like 'could potentially'. "
    "Match the tone of a Bloomberg or RBC Capital Markets morning note. "
    "Do not use bullet points. Do not repeat the exact numbers provided — synthesise them."
)


def _make_prompt(pair_label, context):
    return (
        f"Data for {pair_label} as of today:\n\n"
        f"{context}\n\n"
        f"Write the regime read paragraph (2-3 sentences)."
    )


# ── main ──────────────────────────────────────────────────────────────────────

def run():
    if not _ANTHROPIC_KEY:
        print("[AI] ANTHROPIC_API_KEY not set — skipping AI regime reads.")
        return

    try:
        import anthropic as _anthropic
    except ImportError:
        print("[AI] anthropic library not installed — skipping AI regime reads.")
        return

    # Load latest master data
    master_path = "data/latest_with_cot.csv"
    inr_path    = "data/inr_latest.csv"

    if not os.path.exists(master_path):
        print(f"[AI] {master_path} not found — skipping.")
        return

    master_df = pd.read_csv(master_path, index_col=0, parse_dates=True)
    if len(master_df) == 0:
        print("[AI] master CSV is empty — skipping.")
        return

    m_row = master_df.iloc[-1].to_dict()
    data_date = str(master_df.index[-1].date())

    i_row = None
    if os.path.exists(inr_path):
        inr_df = pd.read_csv(inr_path, index_col=0, parse_dates=True)
        if len(inr_df) > 0:
            i_row = inr_df.iloc[-1].to_dict()

    client = _anthropic.Anthropic(api_key=_ANTHROPIC_KEY)

    results = {}
    for pair_label, ctx in [
        ("EUR/USD", _eur_context(m_row)),
        ("USD/JPY", _jpy_context(m_row)),
        ("USD/INR", _inr_context(m_row, i_row)),
    ]:
        slug = pair_label.lower().replace("/", "")
        try:
            msg = client.messages.create(
                model=_MODEL,
                max_tokens=220,
                system=_SYSTEM,
                messages=[{"role": "user", "content": _make_prompt(pair_label, ctx)}],
            )
            results[slug] = msg.content[0].text.strip()
            print(f"[AI] {pair_label} OK")
        except Exception as e:
            print(f"[AI] {pair_label} failed: {e}")
            results[slug] = None

    # Only write if at least one result came back
    if any(v is not None for v in results.values()):
        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_date":    data_date,
            "eurusd":       results.get("eurusd"),
            "usdjpy":       results.get("usdjpy"),
            "usdinr":       results.get("usdinr"),
        }
        os.makedirs("data", exist_ok=True)
        with open(_OUTPUT, "w", encoding="utf-8") as fh:
            json.dump(output, fh, indent=2)
        print(f"[AI] wrote {_OUTPUT}")
    else:
        print("[AI] all calls failed — output file not updated.")


if __name__ == "__main__":
    run()
