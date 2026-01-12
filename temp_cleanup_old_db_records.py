#!/usr/bin/env python3
"""
Temporary script to cleanup Supabase database records older than 7 days.
Based on .github/workflows/weekly-supabase-cleanup.yml

Usage:
    uv run python3 temp_cleanup_old_db_records.py
"""
import os
import sys
from datetime import datetime, timedelta
from supabase import create_client

import util

def main():
    # Get Supabase credentials
    url = util.resolve_env_var("SUPABASE_URL")
    key = util.resolve_env_var("SUPABASE_SECRET_KEY")

    supabase = create_client(url, key)

    # Calculate cutoff date (7 days ago)
    cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    print(f"Cleanup script started at {datetime.now().isoformat()}")
    print(f"Cutoff date: {cutoff_date}")
    print(f"Will delete all daily_cache entries with date < {cutoff_date}")
    print()

    # First, check what will be deleted
    print("Checking records to be deleted...")
    check_result = supabase.table('daily_cache').select('date').lt('date', cutoff_date).execute()

    if not check_result.data:
        print("✓ No old records found. Database is already clean.")
        return 0

    print(f"Found {len(check_result.data)} records to delete:")
    for row in check_result.data:
        print(f"  - {row['date']}")
    print()

    # Confirm deletion
    response = input(f"Delete these {len(check_result.data)} records? [y/N]: ").strip().lower()
    if response != 'y':
        print("Cleanup cancelled by user.")
        return 1

    # Delete old cache entries
    print(f"\nDeleting daily_cache entries older than {cutoff_date}...")
    result = supabase.table('daily_cache').delete().lt('date', cutoff_date).execute()

    deleted_count = len(result.data) if result.data else 0
    print(f"✓ Successfully deleted {deleted_count} old cache entries")
    print(f"\nCleanup completed at {datetime.now().isoformat()}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
