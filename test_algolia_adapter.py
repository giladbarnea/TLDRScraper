#!/usr/bin/env python3
"""
Test script for new Algolia-based HackerNews adapter implementation.
"""

from datetime import datetime, timedelta
from hackernews_adapter import HackerNewsAdapter
from newsletter_config import NEWSLETTER_CONFIGS


def test_adapter():
    """Test the new Algolia-based adapter"""
    print("=" * 80)
    print("Testing Algolia-based HackerNews Adapter")
    print("=" * 80)

    # Get HackerNews config
    config = NEWSLETTER_CONFIGS['hackernews']

    # Initialize adapter
    adapter = HackerNewsAdapter(config)
    print(f"✓ Adapter initialized")
    print(f"  Min points: {adapter.min_points}")
    print(f"  Min comments: {adapter.min_comments}")
    print(f"  Max stories: {adapter.max_stories}")

    # Test with yesterday's date
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"\nTesting scrape for date: {yesterday}")

    try:
        result = adapter.scrape_date(yesterday)

        print(f"✓ Scrape successful!")
        print(f"  Articles found: {len(result['articles'])}")
        print(f"  Issues found: {len(result['issues'])}")

        if result['articles']:
            print(f"\n  Top 5 articles by leading score:")
            for i, article in enumerate(result['articles'][:5], 1):
                print(f"    {i}. [{article.get('category', 'N/A')}] {article['title'][:70]}")
                print(f"       {article['url']}")

            # Count by category
            categories = {}
            for article in result['articles']:
                cat = article.get('category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1

            print(f"\n  Articles by category:")
            for cat, count in sorted(categories.items()):
                print(f"    {cat}: {count}")

        print("\n" + "=" * 80)
        print("✅ TEST PASSED")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_adapter()
    exit(0 if success else 1)
