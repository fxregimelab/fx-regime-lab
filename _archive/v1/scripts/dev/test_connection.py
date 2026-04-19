import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

load_dotenv(override=True)

from core.supabase_client import get_client


def test_supabase():
    print("Testing Supabase connection...")
    client = get_client()
    if not client:
        print("FAIL: Client not initialised")
        print("  Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
        return False

    # Test signals table read
    try:
        result = (
            client.table("signals")
            .select("date,pair,rate_diff_2y")
            .order("date", desc=True)
            .limit(3)
            .execute()
        )
        rows = result.data
        if not rows:
            print("WARN: signals table is empty — run backfill")
        else:
            print("OK: signals table has data")
            for row in rows:
                print(
                    f"  {row['date']} | {row['pair']} | "
                    f"rate_diff_2y={row.get('rate_diff_2y')}"
                )
    except Exception as e:
        print(f"FAIL: signals read error: {e}")
        return False

    # Test regime_calls table read
    try:
        result = (
            client.table("regime_calls")
            .select("date,pair,regime,confidence")
            .order("date", desc=True)
            .limit(3)
            .execute()
        )
        rows = result.data
        if not rows:
            print("WARN: regime_calls table is empty")
            print("  Run pipeline to generate regime calls")
        else:
            print("OK: regime_calls table has data")
            for row in rows:
                print(
                    f"  {row['date']} | {row['pair']} | "
                    f"{row['regime']} | {row['confidence']}"
                )
    except Exception as e:
        print(f"FAIL: regime_calls read error: {e}")
        return False

    # Test validation_log table read
    try:
        result = (
            client.table("validation_log")
            .select("date,pair,correct_1d")
            .order("date", desc=True)
            .limit(3)
            .execute()
        )
        rows = result.data
        if not rows:
            print("WARN: validation_log is empty — normal if pipeline")
            print("  has not run since wiring validation_regime.py")
        else:
            print("OK: validation_log has data")
    except Exception as e:
        print(f"FAIL: validation_log read error: {e}")

    # Test write permission (service role)
    try:
        client.table("pipeline_errors").insert(
            {
                "date": "2026-01-01",
                "source": "connection_test",
                "error_message": "Test entry - safe to delete",
                "notes": "Automated connection test",
            }
        ).execute()
        print("OK: write permission confirmed (service role)")
        # Clean up test entry
        client.table("pipeline_errors").delete().eq("source", "connection_test").execute()
        print("OK: test entry cleaned up")
    except Exception as e:
        print(f"FAIL: write test failed: {e}")
        return False

    print("\nSUPABASE: All tests passed")
    return True


if __name__ == "__main__":
    success = test_supabase()
    sys.exit(0 if success else 1)
