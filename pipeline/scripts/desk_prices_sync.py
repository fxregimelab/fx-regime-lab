"""Sync broker D1 bars (EURUSD + USDJPY) into the local desk store.

Read-only market-data tool: never places, modifies, or closes orders.
Credentials come from repo-root ``.env.local`` and are never printed.

Usage (from ``pipeline/``):
    .venv\\Scripts\\python scripts\\desk_prices_sync.py [--timeframe D1] [--pairs EURUSD,USDJPY]

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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeframe", default="D1", help="bar timeframe (default: D1)")
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
    timeframe = str(args.timeframe).upper()
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
                bars = feed.fetch_bars(symbol, timeframe=timeframe)
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
