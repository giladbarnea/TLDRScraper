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
        return self._normalize_response(articles)

    def _parse_articles_from_markdown(self, markdown: str) -> list[dict]:
        """Parse articles from Claude blog markdown.

        The blog renders posts in two disjoint layouts: a curated *featured carousel*
        and the *chronological grid* of latest posts. Both must be parsed, since the
        newest posts only ever appear in the grid.

        Featured carousel (curl_cffi):
            ## Cowork: Claude Code for the rest of your work
            January 12, 2026
            [Read more](</blog/cowork-research-preview>)

        Chronological grid (curl_cffi):
            June 3, 2026
            [How Anthropic enables self-service data analytics with Claude](</blog/how-anthropic-...>)
        """
        articles = []
        matches = self._extract_post_tuples(markdown)

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

    @staticmethod
    def _extract_post_tuples(markdown: str) -> list[tuple[str, str, str]]:
        """Extract (title, date, slug) tuples from both blog layouts, deduped by slug.

        The featured carousel is collected first so its proper title wins over the
        grid pattern's "Read more" link text for any shared post.

        >>> md = '## Featured Post\\nMay 1, 2026\\n[Read more](</blog/featured>)\\n'
        >>> md += 'June 3, 2026\\n[Latest Post](</blog/latest>)'
        >>> ClaudeBlogAdapter._extract_post_tuples(md)
        [('Featured Post', 'May 1, 2026', 'featured'), ('Latest Post', 'June 3, 2026', 'latest')]
        """
        carousel = re.findall(r'## ([^\n]+)\n([A-Za-z]+ \d+, \d{4})\n\[Read more\]\(</blog/([^\)]+)>\)', markdown)
        grid = [(title, date, slug) for date, title, slug in
                re.findall(r'([A-Za-z]+ \d+, \d{4})\n\[([^\]]+)\]\(</blog/([^\)]+)>\)', markdown)]

        # Firecrawl fallback (absolute URLs) only when the curl_cffi formats yield nothing.
        if not carousel and not grid:
            carousel = [(title, date, url.split('/')[-1]) for title, date, url in
                        re.findall(r'## ([^\n]+)\n+([A-Za-z]+ \d+, \d{4})\n+\[Read more\]\((https://claude\.com/blog/[^\)]+)\)', markdown)]
            grid = [(title, date, url.split('/')[-1]) for date, title, url in
                    re.findall(r'([A-Za-z]+ \d+, \d{4})\n+\[([^\]]+)\]\((https://claude\.com/blog/[^\)]+)\)', markdown)]

        seen: set[str] = set()
        tuples = []
        for title, date_str, slug in [*carousel, *grid]:
            if slug in seen:
                continue
            seen.add(slug)
            tuples.append((title, date_str, slug))
        return tuples
