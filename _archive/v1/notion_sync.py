"""
notion_sync.py — FX Regime Lab Notion Automation
Reads pipeline CSVs → pushes to Notion automatically.
Runs as last step in run.py.

Actual CSV mapping (verified 2026-03-10):
  prices / correlations → data/latest.csv
    EURUSD, USDJPY, Brent
    EURUSD_spread_corr_60d, USDJPY_spread_corr_60d
  COT percentiles → data/cot_latest.csv
    EUR_lev_percentile, JPY_lev_percentile
  INR price → data/inr_latest.csv
    USDINR
  INR correlations → data/latest_with_cot.csv
    dxy_inr_corr_60d   — regime classification for INR
    oil_inr_corr_60d   — separate oil-INR break signal threshold check
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
if not NOTION_TOKEN:
    raise EnvironmentError("NOTION_TOKEN not set. Check your .env file.")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# Notion page ID (no dashes) for the Home Dashboard — integration must have access.
# Override via env when the page is recreated or moved.
HOME_DASHBOARD_PAGE_ID = os.environ.get(
    "NOTION_HOME_DASHBOARD_PAGE_ID",
    "31f4fe96a7b581a9bdbec459bd27f224",
)
WEEKLY_REGIME_DB_ID    = "f09a2ef9119341898799da7ce35940d8"
SIGNAL_LOG_DB_ID       = "913c006dda50479aacfa3d0fe16d6bf3"

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Signal thresholds
COT_CROWDED_LONG  = 85
COT_CROWDED_SHORT = 15
CORR_INTACT       = 0.6
CORR_WEAKENING    = 0.3


# ── Notion API helpers ────────────────────────────────────────────────────────

def notion_get(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def notion_post(url, payload):
    r = requests.post(url, headers=HEADERS, json=payload)
    if not r.ok:
        print(f"  Notion error {r.status_code}: {r.text[:200]}")
        r.raise_for_status()
    return r.json()


def notion_patch(url, payload):
    r = requests.patch(url, headers=HEADERS, json=payload)
    if not r.ok:
        print(f"  Notion error {r.status_code}: {r.text[:200]}")
        r.raise_for_status()
    return r.json()


# ── Data helpers ──────────────────────────────────────────────────────────────

def safe_read(path, **kwargs):
    """Read a CSV, returning None with a warning if missing or empty."""
    if not Path(path).exists():
        print(f"  MISSING: {Path(path).name}")
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True, **kwargs)
        return df if not df.empty else None
    except Exception as e:
        print(f"  Could not read {Path(path).name}: {e}")
        return None


def latest(df, *cols):
    """Return the last non-NaN float from the first matching column."""
    if df is None:
        return None
    for col in cols:
        if col in df.columns:
            s = df[col].dropna()
            if not s.empty:
                return float(s.iloc[-1])
    return None


# ── Regime classification ─────────────────────────────────────────────────────

def classify_regime(corr):
    if corr is None:
        return "BROKEN"
    if corr >= CORR_INTACT:
        return "INTACT"
    if corr >= CORR_WEAKENING:
        return "WEAKENING"
    return "BROKEN"


def classify_driver(ec, jc, ic, ep, jp):
    if all(classify_regime(c) == "BROKEN" for c in [ec, jc, ic] if c is not None):
        return "External Shock"
    if ep and (ep > 85 or ep < 15):
        return "Positioning"
    if jp and (jp > 85 or jp < 15):
        return "Positioning"
    if ec and ec >= CORR_INTACT:
        return "Rate Differential"
    return "Mixed"


# ── Utilities ─────────────────────────────────────────────────────────────────

def week_label():
    today = datetime.today()
    mon = today - timedelta(days=today.weekday())
    return mon.strftime("Week of %b %d, %Y")


def rich_text(s):
    return [{"type": "text", "text": {"content": str(s)}}]


# ── Load data ─────────────────────────────────────────────────────────────────

def load_data():
    print("\nLoading pipeline data...")

    # Core price + correlation file (pipeline.py output)
    master = safe_read(DATA_DIR / "latest.csv")

    # COT positioning file (cot_pipeline.py output)
    cot = safe_read(DATA_DIR / "cot_latest.csv")

    # INR price file (inr_pipeline.py output)
    inr = safe_read(DATA_DIR / "inr_latest.csv")

    # Merged master including INR correlations (pipeline.py merge phase output)
    merged = safe_read(DATA_DIR / "latest_with_cot.csv")

    # ── Prices ──────────────────────────────────────────────────────────────────
    eur_price = latest(master, "EURUSD")
    jpy_price = latest(master, "USDJPY")
    brent_val = latest(master, "Brent")
    inr_price = latest(inr, "USDINR")

    # ── COT percentiles (leveraged money positioning, 0-100 scale) ──────────────
    eur_pct = latest(cot, "EUR_lev_percentile")
    jpy_pct = latest(cot, "JPY_lev_percentile")

    # ── Correlations ────────────────────────────────────────────────────────────
    # EUR and JPY: rate-spread vs FX 60D rolling correlation (from latest.csv)
    eur_corr = latest(master, "EURUSD_spread_corr_60d")
    jpy_corr = latest(master, "USDJPY_spread_corr_60d")

    # INR primary: DXY vs INR 60D correlation (regime classification)
    inr_corr = latest(merged, "dxy_inr_corr_60d")

    # INR secondary: Oil vs INR 60D correlation (separate break-signal check)
    oil_inr_corr = latest(merged, "oil_inr_corr_60d")

    d = {
        "eur_price":    eur_price,
        "jpy_price":    jpy_price,
        "inr_price":    inr_price,
        "brent":        brent_val,
        "eur_pct":      eur_pct,
        "jpy_pct":      jpy_pct,
        "eur_corr":     eur_corr,
        "jpy_corr":     jpy_corr,
        "inr_corr":     inr_corr,
        "oil_inr_corr": oil_inr_corr,
        "eur_regime":   classify_regime(eur_corr),
        "jpy_regime":   classify_regime(jpy_corr),
        "inr_regime":   classify_regime(inr_corr),
        "driver":       classify_driver(eur_corr, jpy_corr, inr_corr, eur_pct, jpy_pct),
    }

    for k, v in d.items():
        print(f"  {k}: {v}")
    return d


# ── Notion writers ────────────────────────────────────────────────────────────

def update_home_dashboard(d):
    print("\nUpdating Home Dashboard...")
    today = datetime.today().strftime("%B %d, %Y")
    emoji = {"INTACT": "🟢", "WEAKENING": "🟡", "BROKEN": "🔴"}
    f = lambda v, n=4: f"{v:.{n}f}" if v is not None else "—"

    text = (
        f"AUTO-UPDATED: {today}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Brent:    ${f(d['brent'], 2)}\n"
        f"EUR/USD:  {f(d['eur_price'])}  {emoji[d['eur_regime']]} {d['eur_regime']}\n"
        f"USD/JPY:  {f(d['jpy_price'])}  {emoji[d['jpy_regime']]} {d['jpy_regime']}\n"
        f"USD/INR:  {f(d['inr_price'])}  {emoji[d['inr_regime']]} {d['inr_regime']}\n"
        f"EUR COT:  {f(d['eur_pct'], 1)}th %ile\n"
        f"JPY COT:  {f(d['jpy_pct'], 1)}th %ile\n"
        f"EUR Corr: {f(d['eur_corr'], 3)}\n"
        f"JPY Corr: {f(d['jpy_corr'], 3)}\n"
        f"INR Corr (DXY): {f(d['inr_corr'], 3)}\n"
        f"Oil-INR Corr:   {f(d['oil_inr_corr'], 3)}\n"
        f"Driver:   {d['driver']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"→ Add your observation below this line manually"
    )

    url = f"https://api.notion.com/v1/blocks/{HOME_DASHBOARD_PAGE_ID}/children"
    blocks = notion_get(url).get("results", [])

    target_id = None
    hit_heading = False
    for b in blocks:
        btype = b.get("type", "")
        if btype == "heading_2":
            heading_text = "".join(
                t.get("text", {}).get("content", "")
                for t in b["heading_2"].get("rich_text", [])
            )
            if "Snapshot" in heading_text or "Today" in heading_text:
                hit_heading = True
                continue
        if hit_heading and btype in ("paragraph", "callout", "quote"):
            target_id = b["id"]
            break

    payload = {"paragraph": {"rich_text": rich_text(text)}}
    if target_id:
        notion_patch(f"https://api.notion.com/v1/blocks/{target_id}", payload)
        print("  ✓ Snapshot block updated")
    else:
        notion_post(url, {"children": [{"object": "block", "type": "paragraph", **payload}]})
        print("  ✓ Snapshot block appended")


def upsert_weekly(d):
    print("\nUpserting Weekly Regime Read...")
    label = week_label()

    url = f"https://api.notion.com/v1/databases/{WEEKLY_REGIME_DB_ID}/query"
    existing = notion_post(url, {
        "filter": {"property": "Week", "title": {"equals": label}}
    }).get("results", [])
    existing_id = existing[0]["id"] if existing else None

    props = {
        "Week":               {"title": rich_text(label)},
        "EUR/USD Price":      {"number": round(d["eur_price"], 4) if d["eur_price"] is not None else None},
        "USD/JPY Price":      {"number": round(d["jpy_price"], 4) if d["jpy_price"] is not None else None},
        "USD/INR Price":      {"number": round(d["inr_price"], 4) if d["inr_price"] is not None else None},
        "Brent":              {"number": round(d["brent"], 2) if d["brent"] is not None else None},
        "EUR Regime":         {"select": {"name": d["eur_regime"]}},
        "JPY Regime":         {"select": {"name": d["jpy_regime"]}},
        "INR Regime":         {"select": {"name": d["inr_regime"]}},
        "EUR COT Percentile": {"number": round(d["eur_pct"], 1) if d["eur_pct"] is not None else None},
        "JPY COT Percentile": {"number": round(d["jpy_pct"], 1) if d["jpy_pct"] is not None else None},
        "EUR Corr 60D":       {"number": round(d["eur_corr"], 4) if d["eur_corr"] is not None else None},
        "JPY Corr 60D":       {"number": round(d["jpy_corr"], 4) if d["jpy_corr"] is not None else None},
        "Dominant Driver":    {"select": {"name": d["driver"]}},
    }

    if existing_id:
        notion_patch(f"https://api.notion.com/v1/pages/{existing_id}", {"properties": props})
        print(f"  ✓ Updated: {label}")
    else:
        notion_post("https://api.notion.com/v1/pages", {
            "parent": {"database_id": WEEKLY_REGIME_DB_ID},
            "properties": props,
        })
        print(f"  ✓ Created: {label}")


def already_logged(signal_fragment):
    """Return True if this signal was already logged in the last 7 days."""
    url = f"https://api.notion.com/v1/databases/{SIGNAL_LOG_DB_ID}/query"
    results = notion_post(url, {
        "filter": {"property": "Signal Date", "title": {"contains": signal_fragment[:25]}}
    }).get("results", [])
    if not results:
        return False
    created = results[0]["created_time"]
    age = (datetime.now().astimezone() - datetime.fromisoformat(created.replace("Z", "+00:00"))).days
    return age <= 7


def log_signal(pair, stype, value, direction, notes):
    label = datetime.today().strftime("%b %d") + f" — {pair} {stype}"
    if already_logged(f"{pair} {stype}"):
        print(f"  Already logged this week: {pair} {stype}")
        return
    notion_post("https://api.notion.com/v1/pages", {
        "parent": {"database_id": SIGNAL_LOG_DB_ID},
        "properties": {
            "Signal Date":        {"title": rich_text(label)},
            "Pair":               {"select": {"name": pair}},
            "Signal Type":        {"select": {"name": stype}},
            "Signal Value":       {"rich_text": rich_text(value)},
            "Direction Implied":  {"select": {"name": direction}},
            "Was Signal Correct": {"select": {"name": "Pending"}},
            "Source":             {"rich_text": rich_text("Auto-logged by notion_sync.py")},
            "Notes":              {"rich_text": rich_text(notes)},
        },
    })
    print(f"  ✓ Signal logged: {label}")


def check_signals(d):
    print("\nChecking signal thresholds...")

    # ── EUR COT extremes ─────────────────────────────────────────────────────
    if d["eur_pct"] is not None:
        if d["eur_pct"] >= COT_CROWDED_LONG:
            log_signal(
                "EUR/USD", "COT Extreme",
                f"EUR Leveraged Money {d['eur_pct']:.1f}th %ile CROWDED LONG",
                "Bearish USD",
                f"Auto: {d['eur_pct']:.1f}th %ile above {COT_CROWDED_LONG} threshold. "
                f"EUR Corr: {d['eur_corr']}. Fill 'What Happened After' next week.",
            )
        elif d["eur_pct"] <= COT_CROWDED_SHORT:
            log_signal(
                "EUR/USD", "COT Extreme",
                f"EUR Leveraged Money {d['eur_pct']:.1f}th %ile CROWDED SHORT",
                "Bullish USD",
                f"Auto: {d['eur_pct']:.1f}th %ile below {COT_CROWDED_SHORT} threshold.",
            )

    # ── JPY COT extremes ─────────────────────────────────────────────────────
    if d["jpy_pct"] is not None:
        if d["jpy_pct"] >= COT_CROWDED_LONG:
            log_signal(
                "USD/JPY", "COT Extreme",
                f"JPY Leveraged Money {d['jpy_pct']:.1f}th %ile CROWDED LONG",
                "Bearish USD",
                f"Auto: {d['jpy_pct']:.1f}th %ile above threshold. JPY Corr: {d['jpy_corr']}.",
            )
        elif d["jpy_pct"] <= COT_CROWDED_SHORT:
            log_signal(
                "USD/JPY", "COT Extreme",
                f"JPY Leveraged Money {d['jpy_pct']:.1f}th %ile CROWDED SHORT",
                "Bullish USD",
                f"Auto: {d['jpy_pct']:.1f}th %ile below threshold.",
            )

    # ── EUR correlation break ────────────────────────────────────────────────
    if d["eur_corr"] is not None and d["eur_corr"] < CORR_WEAKENING:
        log_signal(
            "EUR/USD", "Correlation Break",
            f"EUR 60D Corr = {d['eur_corr']:.3f} BROKEN",
            "Unclear",
            f"Auto: EUR correlation broken. Driver: {d['driver']}.",
        )

    # ── JPY correlation break ────────────────────────────────────────────────
    if d["jpy_corr"] is not None and d["jpy_corr"] < CORR_WEAKENING:
        log_signal(
            "USD/JPY", "Correlation Break",
            f"JPY 60D Corr = {d['jpy_corr']:.3f} BROKEN",
            "Unclear",
            f"Auto: JPY correlation broken. Driver: {d['driver']}.",
        )

    # ── INR Oil-correlation break (separate signal, same threshold) ──────────
    # Fires when the 60D oil-vs-INR correlation drops below CORR_WEAKENING (0.3).
    # This is distinct from inr_corr (DXY-INR) which drives regime classification.
    # A break here signals Oil is no longer driving INR — watch for policy/RBI action.
    if d["oil_inr_corr"] is not None and d["oil_inr_corr"] < CORR_WEAKENING:
        log_signal(
            "USD/INR", "Correlation Break",
            f"Oil-INR 60D Corr = {d['oil_inr_corr']:.3f} BROKEN",
            "Unclear",
            f"Auto: Oil-INR 60D correlation broken (threshold: {CORR_WEAKENING}). "
            f"Oil is no longer tracking INR — possible RBI intervention or external shock. "
            f"DXY-INR corr: {d['inr_corr']}. Driver: {d['driver']}. "
            f"Add manual interpretation in Framework Anomalies.",
        )

    # ── Cross-asset simultaneous break ───────────────────────────────────────
    all_broken = all(
        classify_regime(d[c]) == "BROKEN"
        for c in ["eur_corr", "jpy_corr", "inr_corr"]
        if d[c] is not None
    )
    if all_broken:
        log_signal(
            "All Pairs", "Cross-Asset Break",
            (
                f"ALL THREE BROKEN simultaneously — "
                f"EUR:{d['eur_corr']:.3f} "
                f"JPY:{d['jpy_corr']:.3f} "
                f"INR:{d['inr_corr']:.3f}"
            ),
            "Unclear",
            (
                "Auto: All three pairs broken at once. Rarest regime state. "
                "Add manual interpretation in Framework Anomalies."
            ),
        )

    print("  ✓ Signal check done")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  FX REGIME LAB — Notion Sync")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    try:
        d = load_data()
        update_home_dashboard(d)
        upsert_weekly(d)
        check_signals(d)
        print("\n✅ Notion sync complete.")
        print("→ Open Notion and fill in: What I Learned, Framework Anomalies, Was Signal Correct")
    except Exception as e:
        print(f"\n❌ Sync failed: {e}")
        raise SystemExit(0)


if __name__ == "__main__":
    main()
