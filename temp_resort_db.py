"""One-time script to re-sort newsletter data in database with new sort_order."""
import os
from datetime import datetime, timedelta
from supabase import create_client
from newsletter_config import NEWSLETTER_CONFIGS

# Connect to Supabase
url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SECRET_KEY"]
supabase = create_client(url, key)

# Get last 3 days
today = datetime.now().date()
dates = [(today - timedelta(days=i)).isoformat() for i in range(3)]

print(f"Re-sorting newsletter data for last 3 days: {dates}")
print("=" * 80)


def sort_issues(issues):
    """Sort issues by date DESC, source sort_order ASC, category ASC."""
    def issue_sort_key(issue):
        date_text = issue.get("date", "") or ""
        try:
            date_ordinal = datetime.fromisoformat(date_text).toordinal()
        except Exception:
            date_ordinal = 0

        source_id = issue.get("source_id")
        sort_order = (
            NEWSLETTER_CONFIGS[source_id].sort_order
            if source_id in NEWSLETTER_CONFIGS
            else 999
        )

        return (-date_ordinal, sort_order, issue.get("category", ""))

    return sorted(issues, key=issue_sort_key)


for date_str in dates:
    print(f"\nProcessing {date_str}...")

    # Fetch existing payload
    response = supabase.table("daily_cache").select("*").eq("date", date_str).execute()

    if not response.data:
        print(f"  No data found for {date_str}")
        continue

    payload = response.data[0]
    issues = payload.get("issues", [])

    if not issues:
        print(f"  No issues found for {date_str}")
        continue

    print(f"  Found {len(issues)} issues")

    # Show old order
    old_order = []
    for i in issues[:5]:
        cat = i.get("category", "?")
        src = i.get("source_id", "?")
        order = NEWSLETTER_CONFIGS.get(src, type("", (), {"sort_order": 999})).sort_order
        old_order.append(f"{cat}({order})")
    print(f"  Old order: {old_order}")

    # Re-sort issues
    sorted_issues = sort_issues(issues)

    # Show new order
    new_order = []
    for i in sorted_issues[:5]:
        cat = i.get("category", "?")
        src = i.get("source_id", "?")
        order = NEWSLETTER_CONFIGS.get(src, type("", (), {"sort_order": 999})).sort_order
        new_order.append(f"{cat}({order})")
    print(f"  New order: {new_order}")

    # Update payload
    update_response = supabase.table("daily_cache").update({
        "issues": sorted_issues
    }).eq("date", date_str).execute()

    print(f"  ✓ Updated {date_str}")

print("\n" + "=" * 80)
print("Re-sorting complete!")
