# newsletter_adapter.py
"""
Abstract base class for newsletter source adapters.
"""

# ... imports ...

class NewsletterAdapter:
    # ... __init__ ...
    
    # ... fetch_issue ...
    
    # ... parse_articles ...

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """
        Template method - orchestrates fetch + parse + normalize.
        
        CRITICAL CONTRACT:
        1. Returns ALL valid articles found on the source (Super-Set).
        2. Returns articles SORTED by importance/relevance (Top K candidates first).
           - HN: Score desc
           - TLDR: Section order
           - Blogs: Date desc
        
        This sorting is vital because the limiter in `newsletter_scraper.py` 
        will simple slice `candidates[:quota]`.

        Args:
            date: Date string to scrape
            excluded_urls: List of canonical URLs to exclude from results

        Returns:
            Normalized response dictionary with source_id, articles, and issues
        """
        # implementation details (fetch, parse, filter excluded, normalize)
        # Ensure final list is sorted according to source-specific logic