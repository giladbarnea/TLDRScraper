"""
Software Lead Weekly adapter implementation.

This adapter fetches curated articles from Software Lead Weekly newsletter,
which publishes weekly issues every Friday. The adapter calculates the
appropriate issue number based on the target date and parses articles
from the HTML content.
"""

import logging
import re
from datetime import datetime, timedelta

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("softwareleadweekly_adapter")

# Reference point for issue number calculation
# Issue 677 was published on 2025-11-14 (Friday)
REFERENCE_ISSUE = 677
REFERENCE_DATE = datetime(2025, 11, 14)


class SoftwareLeadWeeklyAdapter(NewsletterAdapter):
    """Adapter for Software Lead Weekly newsletter."""

    def __init__(self, config):
        """Initialize with config."""
        super().__init__(config)

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch articles for a specific date.

        Software Lead Weekly publishes every Friday. This method:
        1. Calculates which Friday the target date falls on
        2. Determines the issue number based on the reference point
        3. Fetches and parses that issue's content

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

        logger.info(f"[softwareleadweekly_adapter.scrape_date] Fetching articles for {target_date_str} (excluding {len(excluded_urls)} URLs)")

        # Calculate which Friday to use
        issue_date = self._get_issue_date_for_target(target_date)
        issue_number = self._calculate_issue_number(issue_date)

        logger.info(f"[softwareleadweekly_adapter.scrape_date] Target date {target_date_str} maps to issue {issue_number} ({issue_date.strftime('%Y-%m-%d')})")

        try:
            html = self.fetch_issue(str(issue_number), "newsletter")
            if html is None:
                logger.info(f"[softwareleadweekly_adapter.scrape_date] No content found for issue {issue_number}")
                return self._normalize_response([], [])

            markdown = self._html_to_markdown(html)
            parsed_articles = self.parse_articles(markdown, issue_date.strftime("%Y-%m-%d"), "newsletter")

            for article in parsed_articles:
                canonical_url = util.canonicalize_url(article['url'])
                if canonical_url not in excluded_set:
                    articles.append(article)

            logger.info(f"[softwareleadweekly_adapter.scrape_date] Found {len(articles)} articles for issue {issue_number}")

        except Exception as e:
            logger.error(f"[softwareleadweekly_adapter.scrape_date] Error fetching issue {issue_number}: {e}", exc_info=True)

        issues = []
        if articles:
            issues.append({
                'date': issue_date.strftime("%Y-%m-%d"),
                'source_id': self.config.source_id,
                'category': self.config.category_display_names.get('newsletter', 'Software Lead Weekly'),
                'title': f"Issue #{issue_number}",
                'subtitle': None
            })

        return self._normalize_response(articles, issues)

    def _get_issue_date_for_target(self, target_date: datetime) -> datetime:
        """Get the Friday that corresponds to the target date.

        Software Lead Weekly publishes every Friday. This returns:
        - The target date if it's a Friday
        - The previous Friday if target is not a Friday

        >>> adapter = SoftwareLeadWeeklyAdapter(None)
        >>> result = adapter._get_issue_date_for_target(datetime(2025, 11, 14))
        >>> result.strftime("%Y-%m-%d")
        '2025-11-14'
        >>> result = adapter._get_issue_date_for_target(datetime(2025, 11, 16))
        >>> result.strftime("%Y-%m-%d")
        '2025-11-14'
        """
        weekday = target_date.weekday()
        if weekday == 4:
            return target_date
        days_since_friday = (weekday - 4) % 7
        return target_date - timedelta(days=days_since_friday)

    def _calculate_issue_number(self, issue_date: datetime) -> int:
        """Calculate issue number based on date.

        Uses the reference point (issue 677 = 2025-11-14) and calculates
        the issue number based on weekly intervals.

        >>> adapter = SoftwareLeadWeeklyAdapter(None)
        >>> adapter._calculate_issue_number(datetime(2025, 11, 14))
        677
        >>> adapter._calculate_issue_number(datetime(2025, 11, 7))
        676
        >>> adapter._calculate_issue_number(datetime(2025, 11, 21))
        678
        """
        days_diff = (issue_date - REFERENCE_DATE).days
        weeks_diff = days_diff // 7
        return REFERENCE_ISSUE + weeks_diff

    @util.retry()
    def fetch_issue(self, issue_number: str, newsletter_type: str) -> str | None:
        """Fetch raw HTML for a specific issue."""
        url = f"https://softwareleadweekly.com/issues/{issue_number}"

        response = util.fetch(
            url,
            headers={"User-Agent": self.config.user_agent},
            timeout=10
        )

        if response.status_code == 404:
            logger.info(f"[softwareleadweekly_adapter.fetch_issue] Issue {issue_number} not found (404)")
            return None

        response.raise_for_status()
        return response.text

    def parse_articles(self, markdown: str, date: str, newsletter_type: str) -> list[dict]:
        """Parse articles from markdown content.

        Args:
            markdown: Converted markdown content
            date: Date string for the issue
            newsletter_type: Type (not used, included for interface compatibility)

        Returns:
            List of article dictionaries
        """
        articles = []
        current_section = None

        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('### ') and not line.startswith('### Subscribe'):
                current_section = line[4:].strip()
                logger.info(f"[softwareleadweekly_adapter.parse_articles] Found section: {current_section}")
                i += 1
                continue

            link_match = re.match(r'\[(.*?)\]\((https?://[^\s\)]+)', line)
            if link_match:
                title = link_match.group(1)
                url = link_match.group(2)

                if any(domain in url for domain in ['getpocket.com', 'instapaper.com', 'twitter.com/share']):
                    i += 1
                    continue

                read_time = ""
                description = ""

                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    read_time_match = re.match(r'(\d+)\s+minutes?\s+read\.?', next_line)
                    if read_time_match:
                        read_time = read_time_match.group(0)

                        desc_lines = []
                        j = i + 2
                        while j < len(lines):
                            desc_line = lines[j].strip()
                            if not desc_line:
                                j += 1
                                continue
                            if desc_line.startswith('**Read**') or desc_line.startswith('['):
                                break
                            desc_lines.append(desc_line)
                            j += 1

                        description = ' '.join(desc_lines)

                article_meta = read_time if read_time else ""
                category = current_section or "Software Lead Weekly"

                article = {
                    "title": title,
                    "article_meta": article_meta,
                    "url": url,
                    "category": category,
                    "date": date,
                    "newsletter_type": "newsletter",
                    "removed": False,
                }

                articles.append(article)

            i += 1

        return articles

    def extract_issue_metadata(self, markdown: str, date: str, newsletter_type: str) -> dict | None:
        """Extract issue metadata from markdown.

        Args:
            markdown: Converted markdown content
            date: Date string for the issue
            newsletter_type: Type (not used, included for interface compatibility)

        Returns:
            Dictionary with issue metadata
        """
        title_match = re.search(r'Issue #(\d+),\s+(.+)', markdown)
        if title_match:
            issue_number = title_match.group(1)
            issue_date = title_match.group(2)
            return {
                'date': date,
                'source_id': self.config.source_id,
                'category': self.config.category_display_names.get('newsletter', 'Software Lead Weekly'),
                'title': f"Issue #{issue_number}",
                'subtitle': issue_date
            }

        return None
