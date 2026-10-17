"""Read-only MetaTrader 5 connectivity + spread spike for the personal desk.

Trading subset: EURUSD + USDJPY (owner decision 2026-10-17). Read-only: this
script never places, modifies, or closes orders. Credentials are never printed
(it attaches to an already-logged-in local terminal).

What it does (when a terminal is installed & logged in):
  1. initialize() against the local MT5 terminal
  2. report terminal + account *type* (DEMO/REAL), server name (no login number)
  3. resolve + select EURUSD, USDJPY (tries common broker suffixes)
  4. print digits, current spread (points + pips), bid/ask
  5. print the last D1 bar and sample live spreads a few times

Usage:
    python -P pipeline/scripts/desk_mt5_spike.py
"""

from __future__ import annotations

import statistics
import sys
import time

PAIRS = ("EURUSD", "USDJPY")
SUFFIX_CANDIDATES = ("", "m", ".", "#", "pro", "raw", "ecn", "z")
D1 = None  # set after import


def _resolve_symbol(mt5, pair: str) -> str | None:
    for suffix in SUFFIX_CANDIDATES:
        candidate = f"{pair}{suffix}"
        if mt5.symbol_info(candidate) is not None:
            return candidate
    return None


def _pip_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol.upper() else 0.0001


def main() -> int:
    try:
        import MetaTrader5 as mt5  # noqa: N813  # package name is CamelCase
    except ImportError:
        print("MetaTrader5 package not installed. Run: python -m pip install MetaTrader5")
        return 2

    if not mt5.initialize():
        print("initialize() failed:", mt5.last_error())
        print("Is the MT5 terminal installed and logged in on this PC?")
        return 1

    try:
        term = mt5.terminal_info()
        print(
            "terminal:", getattr(term, "name", "?"),
            "| connected:", getattr(term, "connected", "?"),
        )
        acc = mt5.account_info()
        if acc is None:
            print("account: none logged in — open a demo account in the terminal first")
        else:
            mode = {
                mt5.ACCOUNT_TRADE_MODE_DEMO: "DEMO",
                mt5.ACCOUNT_TRADE_MODE_CONTEST: "CONTEST",
                mt5.ACCOUNT_TRADE_MODE_REAL: "REAL",
            }.get(acc.trade_mode, str(acc.trade_mode))
            print(f"account type: {mode} | server: {acc.server} | currency: {acc.currency}")

        ok = True
        for pair in PAIRS:
            symbol = _resolve_symbol(mt5, pair)
            if symbol is None:
                print(
                    f"\n{pair}: NOT FOUND at this broker "
                    "(check Market Watch / broker symbol names)"
                )
                ok = False
                continue
            if not mt5.symbol_select(symbol, True):
                print(f"\n{symbol}: symbol_select failed ({mt5.last_error()})")
                ok = False
                continue

            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            pip = _pip_size(symbol)
            spread_pips = ((tick.ask - tick.bid) / pip) if tick else float("nan")
            print(
                f"\n{symbol}: digits={info.digits} current spread={info.spread} points "
                f"({spread_pips:.2f} pips) "
                f"bid={getattr(tick, 'bid', '-')} ask={getattr(tick, 'ask', '-')}"
            )

            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 5)
            if rates is not None and len(rates):
                last = rates[-1]
                t_str = time.strftime("%Y-%m-%d", time.gmtime(int(last["time"])))
                print(
                    f"  last D1 bar {t_str}: O={last['open']} H={last['high']} "
                    f"L={last['low']} C={last['close']} (bars returned: {len(rates)})"
                )

            samples: list[float] = []
            for _ in range(5):
                t = mt5.symbol_info_tick(symbol)
                if t is not None:
                    samples.append((t.ask - t.bid) / pip)
                time.sleep(0.4)
            if samples:
                print(
                    f"  spread samples (pips): {[round(s, 2) for s in samples]} "
                    f"median={statistics.median(samples):.2f}"
                )

        print("\nDone. Read-only spike — no orders placed.")
        return 0 if ok else 3
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
