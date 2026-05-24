"""
Anthropic Research adapter implementation.

This adapter fetches research articles from Anthropic's research page,
filtering by date and extracting article metadata.
Uses the standard scraper fallback cascade (curl_cffi -> jina -> firecrawl).
"""

import logging
import re
from datetime import datetime

from adapters.newsletter_adapter import NewsletterAdapter
import util
import summarizer


logger = logging.getLogger("anthropic_research_adapter")


class AnthropicResearchAdapter(NewsletterAdapter):
    """Adapter for Anthropic Research."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self.research_url = "https://www.anthropic.com/research"

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch research articles for a specific date from Anthropic Research.

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
            markdown = summarizer.url_to_markdown(self.research_url)

            logger.info(f"Successfully scraped research page")

            parsed_articles = self._parse_articles_from_markdown(markdown)

            logger.info(f"Parsed {len(parsed_articles)} total articles from research page")

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
            logger.error(f"Error fetching research: {e}", exc_info=True)
        return self._normalize_response(articles)

    def _parse_articles_from_markdown(self, markdown: str) -> list[dict]:
        """Parse articles from Anthropic research markdown.

        The research page has a table format with Date, Category, and Title columns.
        Example from curl_cffi: "  * [Jan 19, 2026InterpretabilityThe assistant axis...](</research/assistant-axis>)"
        Example from firecrawl: "- [Jan 19, 2026Interpretability\\\nThe assistant axis...](https://www.anthropic.com/research/...)"
        """
        articles = []

        # Try curl_cffi format first (one line, relative URLs)
        # Format: "  * [Jan 19, 2026InterpretabilityThe assistant axis...](</research/assistant-axis>)"
        # Category is one or two title-case words, title is the rest
        article_pattern = r'\* \[([A-Za-z]+ \d+, \d{4})([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)([^\]]+)\]\(</(?:research|news)/([^\)]+)>\)'
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

            # Build full URL from relative path (works for both /research/ and /news/ paths)
            full_url = f"https://www.anthropic.com/research/{url_part}" if url_part else url_part

            articles.append({
                "title": title,
                "article_meta": f"{category}",
                "url": full_url,
                "category": self.config.category_display_names.get('research', 'Anthropic Research'),
                "date": formatted_date,
                "newsletter_type": "research",
                "removed": False,
            })

        return articles
