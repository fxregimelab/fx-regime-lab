"""Post-deploy smoke: terminal published CSV and supabase-env asset are reachable.

Run from repo root: python scripts/dev/terminal_data_smoke.py
Optional: python scripts/dev/terminal_data_smoke.py --base https://fxregimelab.com
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.request

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
os.chdir(_ROOT)


def _get_prefix(url: str, max_bytes: int = 4096, timeout: float = 25.0) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "fx-regime-terminal-smoke"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        chunk = r.read(max_bytes)
        return r.status, chunk


def main() -> int:
    p = argparse.ArgumentParser(description="Terminal /data and /assets smoke probe")
    p.add_argument(
        "--base",
        default="https://fxregimelab.com",
        help="Site origin (no trailing slash)",
    )
    args = p.parse_args()
    base = args.base.rstrip("/")
    ok = True

    csv_url = base + "/data/latest_with_cot.csv"
    try:
        status, body = _get_prefix(csv_url, max_bytes=256)
        if status != 200 or len(body) < 20:
            print(f"FAIL {csv_url} HTTP {status} len={len(body)}")
            ok = False
        else:
            print(f"OK   {csv_url} ({len(body)}+ bytes)")
    except Exception as e:
        print(f"FAIL {csv_url} {e}")
        ok = False

    env_url = base + "/assets/supabase-env.js"
    try:
        status, body = _get_prefix(env_url, max_bytes=2048)
        if status != 200:
            print(f"FAIL {env_url} HTTP {status}")
            ok = False
        else:
            text = body.decode("utf-8", errors="replace")
            if "__SUPABASE_URL__" in text or "createClient" in text or "supabase.co" in text:
                print(f"OK   {env_url} (env injector shape)")
            else:
                print(f"WARN {env_url} reachable but unexpected body (check Worker injection)")
    except Exception as e:
        print(f"FAIL {env_url} {e}")
        ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
