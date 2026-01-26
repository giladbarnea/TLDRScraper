#!/usr/bin/env python3
"""
Full pipeline test for all Anthropic sources.
Shows intermediate and final results at each step with actual function calls.
"""

import sys
from datetime import date

from newsletter_config import NEWSLETTER_CONFIGS
from newsletter_scraper import _get_adapter_for_source
import summarizer
import util


def test_source_full_pipeline(source_id: str, test_date: str):
    """Test a source through the full pipeline with intermediate outputs."""

    print(f"\n{'='*80}")
    print(f"TESTING SOURCE: {source_id}")
    print(f"Test date: {test_date}")
    print('='*80)

    # Step 1: Get config and adapter
    print("\n[STEP 1] Loading configuration and adapter...")
    config = NEWSLETTER_CONFIGS[source_id]
    print(f"  Display name: {config.display_name}")
    print(f"  Base URL: {config.base_url}")
    print(f"  Types: {config.types}")
    print(f"  Sort order: {config.sort_order}")

    adapter = _get_adapter_for_source(config)
    print(f"  Adapter class: {adapter.__class__.__name__}")

    if hasattr(adapter, 'research_url'):
        url = adapter.research_url
    elif hasattr(adapter, 'news_url'):
        url = adapter.news_url
    elif hasattr(adapter, 'blog_url'):
        url = adapter.blog_url
    else:
        raise ValueError("Unknown URL attribute")

    print(f"  Scraping URL: {url}")

    # Step 2: Fetch page via fallback cascade
    print("\n[STEP 2] Fetching page via scraper fallback cascade...")
    print(f"  URL: {url}")
    print(f"  Using: summarizer.url_to_markdown()")
    print(f"  Cascade: curl_cffi -> jina.ai -> firecrawl")

    try:
        markdown = summarizer.url_to_markdown(url)
        print(f"  ✓ Successfully fetched and converted to markdown")
        print(f"  Markdown length: {len(markdown)} characters")
        print(f"  Markdown lines: {len(markdown.split(chr(10)))}")

        # Show relevant section of markdown
        lines = markdown.split('\n')
        print(f"\n  Markdown snippet (looking for article list):")

        # Find the section with articles
        for i, line in enumerate(lines):
            if source_id == "anthropic" and ("Publications" in line or "Jan" in line):
                start_idx = max(0, i - 2)
                for j in range(start_idx, min(len(lines), i + 15)):
                    print(f"    {j:3d}: {lines[j][:120]}")
                break
            elif source_id == "anthropic_news" and ("News" in line and "##" in line or "Jan" in line):
                start_idx = max(0, i - 2)
                for j in range(start_idx, min(len(lines), i + 15)):
                    print(f"    {j:3d}: {lines[j][:120]}")
                break
            elif source_id == "claude_blog" and "## Cowork" in line:
                start_idx = max(0, i - 2)
                for j in range(start_idx, min(len(lines), i + 10)):
                    print(f"    {j:3d}: {lines[j][:120]}")
                break

    except Exception as e:
        print(f"  ✗ Failed to fetch: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 3: Parse articles from markdown using adapter's parser
    print(f"\n[STEP 3] Parsing articles from markdown...")
    print(f"  Using: adapter._parse_articles_from_markdown()")

    try:
        parsed_articles = adapter._parse_articles_from_markdown(markdown)
        print(f"  ✓ Parsed {len(parsed_articles)} total articles from page")

        # Show all parsed articles with full details
        print(f"\n  All parsed articles ({len(parsed_articles)} total):")
        for i, article in enumerate(parsed_articles, 1):
            print(f"\n    Article #{i}:")
            print(f"      Title: {article.get('title', 'N/A')}")
            print(f"      Date: {article.get('date', 'N/A')}")
            print(f"      URL: {article.get('url', 'N/A')}")
            print(f"      Category: {article.get('category', 'N/A')}")
            print(f"      Meta: {article.get('article_meta', 'N/A')}")

    except Exception as e:
        print(f"  ✗ Failed to parse: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 4: Extract URLs and canonicalize
    print(f"\n[STEP 4] Extracting and canonicalizing URLs...")
    urls = [article['url'] for article in parsed_articles]
    print(f"  Extracted {len(urls)} URLs")

    canonical_urls = [util.canonicalize_url(url) for url in urls[:5]]
    print(f"\n  First 5 canonical URLs:")
    for i, (orig, canon) in enumerate(zip(urls[:5], canonical_urls), 1):
        print(f"    {i}. Original: {orig}")
        print(f"       Canonical: {canon}")

    # Step 5: Filter by date using adapter.scrape_date()
    print(f"\n[STEP 5] Filtering articles for date {test_date}...")
    print(f"  Using: adapter.scrape_date('{test_date}', excluded_urls=[])")

    try:
        scrape_result = adapter.scrape_date(test_date, excluded_urls=[])
        articles = scrape_result.get('articles', [])
        issues = scrape_result.get('issues', [])

        print(f"  ✓ Found {len(articles)} articles matching date {test_date}")

        if articles:
            print(f"\n  Matching articles for {test_date}:")
            for i, article in enumerate(articles, 1):
                print(f"\n    Article #{i}:")
                print(f"      Title: {article['title']}")
                print(f"      Date: {article['date']}")
                print(f"      URL: {article['url']}")
                print(f"      Category: {article['category']}")
                print(f"      Meta: {article.get('article_meta', 'N/A')}")
                print(f"      Newsletter type: {article.get('newsletter_type', 'N/A')}")
                print(f"      Removed: {article.get('removed', False)}")
        else:
            print(f"  ℹ No articles found for this specific date {test_date}")
            print(f"  (This is OK - article may have been published on a different date)")

        if issues:
            print(f"\n  Issue metadata created:")
            for issue in issues:
                print(f"    Date: {issue['date']}")
                print(f"    Source ID: {issue['source_id']}")
                print(f"    Category: {issue['category']}")

    except Exception as e:
        print(f"  ✗ Failed during scrape_date: {e}")
        import traceback
        traceback.print_exc()
        return

    print(f"\n{'='*80}")
    print(f"✓ COMPLETED: {source_id}")
    print('='*80)


def main():
    """Test all three Anthropic sources."""

    print("\n" + "="*80)
    print("FULL PIPELINE TEST - ANTHROPIC SOURCES WITH FALLBACK CASCADE")
    print("Testing: curl_cffi -> jina.ai -> firecrawl")
    print("="*80)

    test_cases = [
        ("anthropic", "2026-01-19"),       # Anthropic Research
        ("anthropic_news", "2026-01-22"),  # Anthropic News
        ("claude_blog", "2026-01-12"),     # Claude Blog
    ]

    results = []

    for source_id, test_date in test_cases:
        try:
            test_source_full_pipeline(source_id, test_date)
            results.append((source_id, "✓ SUCCESS"))
        except Exception as e:
            print(f"\n✗ ERROR testing {source_id}: {e}")
            import traceback
            traceback.print_exc()
            results.append((source_id, f"✗ FAILED: {e}"))

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    for source_id, status in results:
        print(f"  {source_id:20s}: {status}")

    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
