#!/usr/bin/env python3
"""
Clean up stuck TLDR states in Supabase cache.

This script removes all articles with status='creating' from the daily cache.
These stuck states occur when a page refresh kills a TLDR request mid-flight,
leaving the status in the database even though no request is running.

Usage:
    uv run python3 scripts/clean_stuck_tldr_states.py
"""

import os
import sys
from supabase import create_client
import util

def main():
    url = util.resolve_env_var("SUPABASE_URL")
    key = util.resolve_env_var("SUPABASE_SERVICE_KEY")

    print("="*80)
    print("CLEANING UP SUPABASE CACHE - REMOVE STALE 'creating' STATUSES")
    print("="*80)

    supabase = create_client(url, key)

    print("\n1. Fetching all daily cache entries...")
    response = supabase.table("daily_cache").select("*").execute()

    if not response.data:
        print("   No daily cache entries found")
        return

    print(f"   ✓ Found {len(response.data)} daily cache entries")

    total_articles = 0
    articles_with_creating = 0
    fixed_articles = 0

    print("\n2. Scanning for articles with status='creating'...")

    for entry in response.data:
        date = entry.get("date", "")
        payload = entry.get("payload", {})

        if not isinstance(payload, dict):
            continue

        articles = payload.get("articles", [])
        if not isinstance(articles, list):
            continue

        total_articles += len(articles)
        modified = False

        for article in articles:
            if not isinstance(article, dict):
                continue

            tldr = article.get("tldr", {})
            if isinstance(tldr, dict) and tldr.get("status") == "creating":
                articles_with_creating += 1
                print(f"\n   Found stuck article on {date}:")
                print(f"   - Title: {article.get('title', 'N/A')[:60]}...")
                print(f"   - URL: {article.get('url', 'N/A')[:60]}...")
                print(f"   - TLDR status: {tldr.get('status')}")

                # Reset the TLDR to empty state
                article["tldr"] = {}
                modified = True
                fixed_articles += 1

        if modified:
            print(f"   Updating date {date}...")
            update_response = supabase.table("daily_cache").update({
                "payload": payload
            }).eq("date", date).execute()

            if update_response.data:
                print(f"   ✓ Updated successfully")
            else:
                print(f"   ⚠ Update may have failed")

    print("\n" + "="*80)
    print("CLEANUP SUMMARY")
    print("="*80)
    print(f"Total articles scanned: {total_articles}")
    print(f"Articles with status='creating': {articles_with_creating}")
    print(f"Articles fixed: {fixed_articles}")

    if fixed_articles > 0:
        print(f"\n✅ Cleaned up {fixed_articles} stuck articles")
        print("   They now have empty TLDR state and can be requested again")
    else:
        print("\n✅ No stuck articles found - cache is clean!")

    print("\n" + "="*80)

if __name__ == "__main__":
    main()
