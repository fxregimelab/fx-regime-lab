# One-off: truncate Supabase validation_log (does not touch regime_calls).

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(override=True)

from core.supabase_client import get_client


def main() -> None:
    print(
        "This will delete all rows in validation_log. Type CONFIRM to proceed:",
        end=" ",
        flush=True,
    )
    if input().strip() != "CONFIRM":
        print("Aborted.")
        return

    cli = get_client()
    if cli is None:
        print("ERROR: Supabase client not available (check .env).")
        sys.exit(1)

    try:
        cnt_res = (
            cli.table("validation_log")
            .select("date", count="exact")
            .execute()
        )
        total = getattr(cnt_res, "count", None)
        if total is None:
            total = len(getattr(cnt_res, "data", None) or [])

        cli.table("validation_log").delete().gte("date", "1970-01-01").execute()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print(f"validation_log truncated. Rows deleted: {total}")


if __name__ == "__main__":
    main()
