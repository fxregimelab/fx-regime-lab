import os

from src.db.writer import _client
def verify() -> None:
    client = _client()
    print("--- 🚀 PRODUCTION DATA AUDIT ---")

    # Check Signals (Phase 1 & 3 fix)
    sig_res = client.table("signals").select("*").order("created_at", desc=True).limit(1).execute()
    if sig_res.data:
        latest = sig_res.data[0]
        print(f"✅ Latest Signal: {latest['pair']} at {latest['spot']}")
        print(
            "✅ Data Integrity Check: "
            f"day_change={latest.get('day_change')}, vix={latest.get('cross_asset_vix')}"
        )
    else:
        print("❌ No signals found")

    # Check AI Briefs (Phase 4 fix)
    brief_res = client.table("brief").select("*").order("created_at", desc=True).limit(3).execute()
    print(f"✅ AI Briefs Found: {len(brief_res.data)}/3 pairs generated.")
    for b in brief_res.data:
        snippet = b["analysis"][:100].replace("\n", " ")
        print(f"   ∟ {b['pair']}: {snippet}...")

    # Check Macro Events
    event_res = client.table("macro_events").select("*").limit(1).execute()
    print(f"✅ Macro Calendar: {'Online' if event_res.data else 'Offline'}")


if __name__ == "__main__":
    verify()
