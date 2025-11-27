# util.py
"""
Shared utilities for date handling, URL normalization, and list merging.
"""

import logging
import os
from datetime import timedelta
import urllib.parse as urlparse

# ... existing resolve_env_var, get_date_range, format_date_for_url, canonicalize_url ...

def merge_article_lists(existing_articles: list[dict], new_articles: list[dict]) -> list[dict]:
    """
    Merges two lists of articles, prioritizing existing state.
    
    Strategy:
    1. Index existing articles by canonical URL.
    2. Iterate new articles:
       - If URL exists in index: Use the EXISTING article (to preserve 'read', 'removed', 'tldr' flags).
       - If URL is new: Use the NEW article.
    3. Return the combined list.
    
    Args:
        existing_articles: Articles from DB (may have 'read', 'removed', 'tldr' flags)
        new_articles: Freshly scraped articles
        
    Returns:
        Merged list containing super-set of all unique articles.
    """
    # 1. Build map of existing articles
    # url_map = {canonicalize_url(a['url']): a for a in existing_articles}
    
    # 2. Process new articles
    # for article in new_articles:
        # url = canonicalize_url(article['url'])
        # if url not in url_map:
            # url_map[url] = article
            
    # Note: We prioritize existing objects to keep user state, 
    # but we might want to update mutable fields (like score) if needed.
    # For now, simplistic state preservation is safer.
            
    # 3. Return values
    # return list(url_map.values())

def count_articles_by_source(articles: list[dict]) -> dict[str, int]:
    """
    Helper to count articles grouped by source_id.
    """
    # counts = {}
    # for article in articles:
        # source = article.get('source_id')
        # if source:
            # counts[source] = counts.get(source, 0) + 1
    # return counts