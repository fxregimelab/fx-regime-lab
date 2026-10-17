"""Sync broker bars (EURUSD + USDJPY) into the local desk store.

Read-only market-data tool: never places, modifies, or closes orders.
Credentials come from repo-root ``.env.local`` and are never printed.

Usage (from ``pipeline/``):
    .venv\\Scripts\\python scripts\\desk_prices_sync.py
        [--timeframes D1,H4,H1,M15] [--pairs EURUSD,USDJPY]

Multi-timeframe by design (playbook §5): D1 = regime, H4 = structure,
H1 = trigger/ATR math, M15 = entry precision + liquidity map. Each timeframe
has its own fetch cap (older intraday history beyond the cap is not requested).

Output: per-pair fetch/validation counts, store summary, and ledger chain status.
Note: MetaTrader5 ``initialize`` may start a hidden helper terminal instance;
this script shuts it down on exit but does not kill a lingering process.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

# Bars to request per timeframe. The terminal rejects count > 99_999
# ("Terminal: Invalid params", chart_max_bars = 100,000; observed 2026-10-17).
# Broker history: D1 dense since 2018-07; H1/H4 dense since 2021 (2018–2020 carry
# one snapshot/day only); M15 dense since 2022-10 (~100k-bar cap).
FETCH_COUNTS: dict[str, int] = {
    "D1": 20_000,   # full available history (since 2018-07)
    "H4": 20_000,   # full available history
    "H1": 99_999,   # max accepted count (returns all available)
    "M15": 99_999,  # max accepted count (~4 years)
}
DEFAULT_TIMEFRAMES = "D1,H4,H1,M15"
DEFAULT_COUNT = 20_000


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeframes",
        default=DEFAULT_TIMEFRAMES,
        help=f"comma-separated timeframes (default: {DEFAULT_TIMEFRAMES})",
    )
    parser.add_argument(
        "--pairs", default="EURUSD,USDJPY", help="comma-separated pairs (default: EURUSD,USDJPY)"
    )
    return parser.parse_args(argv)


def _fmt_time(epoch: int | None) -> str:
    if not epoch:
        return "-"
    return datetime.fromtimestamp(epoch, tz=UTC).strftime("%Y-%m-%d")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    timeframes = tuple(t.strip().upper() for t in str(args.timeframes).split(",") if t.strip())
    pairs = tuple(p.strip().upper() for p in str(args.pairs).split(",") if p.strip())

    from src.paper.prices import Mt5BarFeed, load_mt5_env, sync_bars
    from src.paper.store import DeskStore

    store = DeskStore()
    failures: list[str] = []
    try:
        with Mt5BarFeed(load_mt5_env()) as feed:
            print("connected to terminal (credentials hidden)")
            for pair in pairs:
                symbol = feed.resolve_symbol(pair)
                if symbol is None:
                    print(f"{pair}: symbol not found at this broker")
                    failures.append(pair)
                    continue
                for timeframe in timeframes:
                    count = FETCH_COUNTS.get(timeframe, DEFAULT_COUNT)
                    bars = feed.fetch_bars(symbol, timeframe=timeframe, count=count)
                    report = sync_bars(store, pair, symbol, bars, timeframe=timeframe)
                    print(
                        f"{pair} ({symbol}/{timeframe}): fetched={report.fetched} "
                        f"stored={report.stored} quarantined={len(report.quarantined)}"
                    )
                    for time_srv, reason in report.quarantined[:5]:
                        print(f"  quarantined {_fmt_time(time_srv)}: {reason}")
                    if len(report.quarantined) > 5:
                        print(f"  ... and {len(report.quarantined) - 5} more")
        print()
        print(f"store: {store.db_path}")
        for stat in store.bar_stats():
            first = _fmt_time(stat["first_srv"])
            last = _fmt_time(stat["last_srv"])
            print(
                f"  {stat['symbol']} {stat['timeframe']}: {stat['n']} bars "
                f"{first} -> {last} (server time)"
            )
        chain = store.verify_chain()
        print(f"ledger chain: ok={chain.ok} rows={chain.rows} head={chain.head_hash[:16]}...")
    finally:
        store.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
