"""
Claude Blog adapter implementation.

This adapter fetches blog posts from Claude's blog,
filtering by date and extracting article metadata.
Uses the standard scraper fallback cascade (curl_cffi -> jina -> firecrawl).
"""

import logging
import re
from datetime import datetime

from adapters.newsletter_adapter import NewsletterAdapter
import util
import summarizer


logger = logging.getLogger("claude_blog_adapter")


class ClaudeBlogAdapter(NewsletterAdapter):
    """Adapter for Claude Blog."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self.blog_url = "https://claude.com/blog"

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch blog posts for a specific date from Claude Blog.

        Args:
            date: Date string in YYYY-MM-DD format
            excluded_urls: List of canonical URLs to exclude from results

        Returns:
            Normalized response dictionary
        """
        articles = []
        excluded_set = set(excluded_urls)

        target_date = datetime.fromisoformat(util.format_date_for_url(date))
        target_date_str = target_date.strftime("%Y-%m-%d")

        logger.info(f"Fetching articles for {target_date_str} (excluding {len(excluded_urls)} URLs)")

        try:
            markdown = summarizer.url_to_markdown(self.blog_url)

            logger.info(f"Successfully scraped blog page")

            parsed_articles = self._parse_articles_from_markdown(markdown)

            logger.info(f"Parsed {len(parsed_articles)} total articles from blog")

            for article in parsed_articles:
                article_date_str = article.get('date', '')
                if article_date_str != target_date_str:
                    continue

                url = article.get('url', '')
                if not url:
                    continue

                canonical_url = util.canonicalize_url(url)

                if canonical_url in excluded_set:
                    continue

                article['url'] = canonical_url
                articles.append(article)

            logger.info(f"Found {len(articles)} articles for {target_date_str}")

        except Exception as e:
            logger.error(f"Error fetching blog: {e}", exc_info=True)

        issues = []
        if articles:
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': self.config.category_display_names.get('blog', 'Claude Blog'),
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _parse_articles_from_markdown(self, markdown: str) -> list[dict]:
        """Parse articles from Claude blog markdown.

        Example from curl_cffi:
        ## Cowork: Claude Code for the rest of your work
        January 12, 2026
        [Read more](</blog/cowork-research-preview>)Read more

        Example from firecrawl:
        ## Title
        Date
        [Read more](https://claude.com/blog/slug)
        """
        articles = []

        # Try curl_cffi format first (relative URLs with angle brackets)
        article_pattern = r'## ([^\n]+)\n([A-Za-z]+ \d+, \d{4})\n\[Read more\]\(</blog/([^\)]+)>\)'
        matches = re.findall(article_pattern, markdown)

        # If no matches, try firecrawl format (absolute URLs without angle brackets)
        if not matches:
            article_pattern = r'## ([^\n]+)\n+([A-Za-z]+ \d+, \d{4})\n+\[Read more\]\((https://claude\.com/blog/[^\)]+)\)'
            matches_firecrawl = re.findall(article_pattern, markdown)
            # Convert to same format as curl_cffi matches
            matches = [(title, date, url.split('/')[-1]) for title, date, url in matches_firecrawl]

        for title, date_str, url_part in matches:
            try:
                parsed_date = datetime.strptime(date_str.strip(), "%B %d, %Y")
                formatted_date = parsed_date.strftime("%Y-%m-%d")
            except Exception:
                logger.warning(f"Could not parse date: {date_str}")
                continue

            title = title.strip()

            # Build full URL from relative path
            full_url = f"https://claude.com/blog/{url_part}" if url_part else url_part

            articles.append({
                "title": title,
                "article_meta": "",
                "url": full_url,
                "category": self.config.category_display_names.get('blog', 'Claude Blog'),
                "date": formatted_date,
                "newsletter_type": "blog",
                "removed": False,
            })

        return articles
