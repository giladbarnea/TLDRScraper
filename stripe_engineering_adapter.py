"""
Stripe Engineering Blog adapter using Firecrawl API.

This adapter fetches articles from Stripe's Engineering Blog via Firecrawl,
filtering by date and extracting article metadata.
"""

import logging
import re
import os
from datetime import datetime
from firecrawl import FirecrawlApp

from newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("stripe_engineering_adapter")


class StripeEngineeringAdapter(NewsletterAdapter):
    """Adapter for Stripe Engineering Blog using Firecrawl API."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)
        self.blog_url = "https://stripe.com/blog/engineering"
        api_key = util.resolve_env_var("FIRECRAWL_API_KEY")
        self.firecrawl = FirecrawlApp(api_key=api_key)

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch blog posts for a specific date from Stripe Engineering Blog.

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

        logger.info(
            f"[stripe_engineering_adapter.scrape_date] Fetching articles for {target_date_str} (excluding {len(excluded_urls)} URLs)"
        )

        try:
            result = self.firecrawl.scrape(self.blog_url)
            markdown = result.markdown

            logger.info(
                f"[stripe_engineering_adapter.scrape_date] Successfully scraped blog page"
            )

            parsed_articles = self._parse_articles_from_markdown(markdown)

            logger.info(
                f"[stripe_engineering_adapter.scrape_date] Parsed {len(parsed_articles)} total articles from blog"
            )

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

            logger.info(
                f"[stripe_engineering_adapter.scrape_date] Found {len(articles)} articles for {target_date_str}"
            )

        except Exception as e:
            logger.error(
                f"[stripe_engineering_adapter.scrape_date] Error fetching blog: {e}",
                exc_info=True
            )

        issues = []
        if articles:
            issues.append({
                'date': target_date_str,
                'source_id': self.config.source_id,
                'category': self.config.category_display_names.get('engineering', 'Stripe Engineering'),
                'title': None,
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _parse_articles_from_markdown(self, markdown: str) -> list[dict]:
        """Parse articles from Stripe blog markdown.

        >>> adapter = StripeEngineeringAdapter(None)
        >>> md = '## [Engineering]\\n\\n# [Test Article](https://stripe.com/blog/test)\\n\\n[January 15, 2024](https://stripe.com/blog/test)\\n\\nTest summary.'
        >>> articles = adapter._parse_articles_from_markdown(md)
        >>> len(articles) > 0
        True
        """
        articles = []

        article_pattern = r'## \[Engineering\][^\n]*\n+# \[([^\]]+)\]\(([^\)]+)\)[^\n]*\n+\[([^\]]+)\]\([^\)]+\)[^\n]*\n+(.*?)(?=\n## \[Engineering\]|$)'

        matches = re.findall(article_pattern, markdown, re.DOTALL)

        for title, url, date_str, summary_section in matches:
            try:
                parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                formatted_date = parsed_date.strftime("%Y-%m-%d")
            except Exception:
                logger.warning(
                    f"[stripe_engineering_adapter._parse_articles_from_markdown] Could not parse date: {date_str}"
                )
                continue

            author_name = self._extract_author(summary_section)
            summary_text = self._extract_summary(summary_section)

            article_meta_parts = []
            if author_name:
                article_meta_parts.append(f"By {author_name}")
            if summary_text:
                article_meta_parts.append(summary_text)

            article_meta = " | ".join(article_meta_parts) if article_meta_parts else ""

            articles.append({
                "title": title,
                "article_meta": article_meta,
                "url": url,
                "category": self.config.category_display_names.get('engineering', 'Stripe Engineering'),
                "date": formatted_date,
                "newsletter_type": "engineering",
                "removed": False,
            })

        return articles

    def _extract_author(self, summary_section: str) -> str:
        """Extract author name from summary section.

        >>> adapter = StripeEngineeringAdapter(None)
        >>> summary = '](link)[John Doe](author_link) Engineering Team'
        >>> adapter._extract_author(summary)
        'John Doe'
        """
        author_match = re.search(r'\]\([^\)]+\)\[([^\]]+)\]', summary_section)
        if author_match:
            return author_match.group(1)
        return ""

    def _extract_summary(self, summary_section: str) -> str:
        """Extract summary text from summary section.

        >>> adapter = StripeEngineeringAdapter(None)
        >>> summary = 'Some author info\\n\\n![image](url)\\n\\nActual summary text here.\\n\\n[Read more](url)'
        >>> result = adapter._extract_summary(summary)
        >>> 'Actual summary text' in result
        True
        """
        summary_lines = [
            line.strip()
            for line in summary_section.split('\n')
            if line.strip()
            and not line.strip().startswith('![')
            and not line.strip().startswith('[Read more')
            and not line.strip().startswith('[![')
            and len(line.strip()) > 30
        ]

        if summary_lines:
            summary_text = summary_lines[-1]
            if len(summary_text) > 200:
                summary_text = summary_text[:200] + '...'
            return summary_text

        return ""
