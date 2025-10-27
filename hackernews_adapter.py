"""
HackerNews adapter implementation using the haxor library.

This adapter implements the NewsletterAdapter interface for HackerNews,
using the HackerNews API instead of HTML scraping.
"""

import logging
from datetime import datetime

from hackernews import HackerNews

from newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("hackernews_adapter")


class HackerNewsAdapter(NewsletterAdapter):
    """Adapter for HackerNews using the haxor library."""

    def __init__(self, config):
        """Initialize with config.

        Note: We don't use the HTML-to-markdown functionality from base class.
        """
        super().__init__(config)
        self.hn = HackerNews()

    def scrape_date(self, date: str) -> dict:
        """Override template method for API-based fetching.

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            Normalized response dictionary
        """
        articles = []

        # Parse target date
        target_date = datetime.fromisoformat(util.format_date_for_url(date)).date()

        for story_type in self.config.types:
            util.log(
                f"[hackernews_adapter.scrape_date] Fetching {story_type} stories for {date}",
                logger=logger,
            )

            # Fetch stories from API
            try:
                stories = self._fetch_stories_by_type(story_type, limit=500)
            except Exception as e:
                util.log(
                    f"[hackernews_adapter.scrape_date] Error fetching {story_type}: {e}",
                    level=logging.ERROR,
                    exc_info=True,
                    logger=logger,
                )
                continue

            # Filter by date
            filtered_stories = [
                s for s in stories
                if s.submission_time.date() == target_date
            ]

            util.log(
                f"[hackernews_adapter.scrape_date] Found {len(filtered_stories)}/{len(stories)} {story_type} stories for {date}",
                logger=logger,
            )

            # Convert to article format
            for story in filtered_stories:
                article = self._story_to_article(story, date, story_type)
                if article:
                    articles.append(article)

        # HackerNews doesn't have newsletter-style issues
        issues = []

        return self._normalize_response(articles, issues)

    def _fetch_stories_by_type(self, story_type: str, limit: int = 500):
        """Fetch stories from HackerNews API by type.

        Args:
            story_type: One of "top", "new", "ask", "show", "job"
            limit: Maximum number of stories to fetch

        Returns:
            List of Item objects
        """
        if story_type == "top":
            return self.hn.top_stories(limit=limit)
        elif story_type == "new":
            return self.hn.new_stories(limit=limit)
        elif story_type == "ask":
            return self.hn.ask_stories(limit=limit)
        elif story_type == "show":
            return self.hn.show_stories(limit=limit)
        elif story_type == "job":
            return self.hn.job_stories(limit=limit)
        else:
            util.log(
                f"[hackernews_adapter._fetch_stories_by_type] Unknown story type: {story_type}",
                level=logging.WARNING,
                logger=logger,
            )
            return []

    def _story_to_article(self, story, date: str, story_type: str) -> dict | None:
        """Convert HackerNews Item to article dict.

        Args:
            story: HackerNews Item object
            date: Date string
            story_type: Story type (top, new, ask, show, job)

        Returns:
            Article dictionary or None if story should be skipped
        """
        # Skip stories without URLs (Ask HN, polls, etc. that are text-only)
        if not story.url:
            return None

        # Skip dead or deleted stories
        if story.dead or story.deleted:
            return None

        # Get category display name from config
        category = self.config.category_display_names.get(
            story_type, f"HN {story_type.capitalize()}"
        )

        return {
            "title": story.title or f"HN Story {story.item_id}",
            "url": story.url,
            "category": category,
            "date": util.format_date_for_url(date),
            "newsletter_type": story_type,
            "removed": False,
        }
