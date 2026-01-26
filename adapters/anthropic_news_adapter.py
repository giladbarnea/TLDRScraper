"""
Anthropic News adapter implementation.

This adapter fetches news articles from Anthropic's newsroom,
filtering by date and extracting article metadata.
Uses the standard scraper fallback cascade (curl_cffi -> jina -> firecrawl).
"""

import logging
import re
from datetime import datetime

from adapters.newsletter_adapter import NewsletterAdapter
import util
import summarizer


logger = logging.getLogger("anthropic_news_adapter")


class AnthropicNewsAdapter(NewsletterAdapter):
    """Adapter for Anthropic News."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self.news_url = "https://www.anthropic.com/news"

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch news articles for a specific date from Anthropic News.

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
            markdown = summarizer.url_to_markdown(self.news_url)

            logger.info(f"Successfully scraped news page")

            parsed_articles = self._parse_articles_from_markdown(markdown)

            logger.info(f"Parsed {len(parsed_articles)} total articles from news page")

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
            logger.error(f"Error fetching news: {e}", exc_info=True)

        issues = []
        if articles:
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': self.config.category_display_names.get('news', 'Anthropic News'),
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _parse_articles_from_markdown(self, markdown: str) -> list[dict]:
        """Parse articles from Anthropic news markdown.

        The news page has a table format with Date, Category, and Title columns.
        Example from curl_cffi: "  * [Jan 22, 2026AnnouncementsClaude's new constitution](</news/claude-new-constitution>)"
        Example from firecrawl: "- [Jan 22, 2026Announcements\\\nClaude's new constitution](https://www.anthropic.com/news/...)"
        """
        articles = []

        # Try curl_cffi format first (one line, relative URLs)
        # Format: "  * [Jan 22, 2026AnnouncementsClaude's new constitution](</news/claude-new-constitution>)"
        # Category is one or two title-case words, title is the rest
        article_pattern = r'\* \[([A-Za-z]+ \d+, \d{4})([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)([^\]]+)\]\(</news/([^\)]+)>\)'
        matches = re.findall(article_pattern, markdown)

        # If no matches, try firecrawl format (with escaped newlines, absolute URLs)
        if not matches:
            article_pattern = r'- \[([A-Za-z]+ \d+, \d{4})([A-Za-z\s]+)\\+\n([^\]]+)\]\((https://www\.anthropic\.com/[^\)]+)\)'
            matches_firecrawl = re.findall(article_pattern, markdown)
            # Convert to same format as curl_cffi matches
            matches = [(date, cat, title, url.split('/')[-1]) for date, cat, title, url in matches_firecrawl]

        for date_str, category, title, url_part in matches:
            try:
                parsed_date = datetime.strptime(date_str.strip(), "%b %d, %Y")
                formatted_date = parsed_date.strftime("%Y-%m-%d")
            except Exception:
                logger.warning(f"Could not parse date: {date_str}")
                continue

            category = category.strip()
            title = title.strip()

            # Build full URL from relative path
            full_url = f"https://www.anthropic.com/news/{url_part}" if url_part else url_part

            articles.append({
                "title": title,
                "article_meta": f"{category}",
                "url": full_url,
                "category": self.config.category_display_names.get('news', 'Anthropic News'),
                "date": formatted_date,
                "newsletter_type": "news",
                "removed": False,
            })

        return articles
