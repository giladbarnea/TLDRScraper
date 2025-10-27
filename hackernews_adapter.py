"""
HackerNews adapter implementation using the haxor library.

This adapter implements the NewsletterAdapter interface for HackerNews,
using the HackerNews API instead of HTML scraping.
"""

import asyncio
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
                # Top stories: fetch 5 (already ranked by HN)
                # Other types: fetch 100, then filter to top 5 by leading score
                fetch_limit = 5 if story_type == "top" else 100
                stories = self._fetch_stories_by_type(story_type, limit=fetch_limit)
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

            # For non-top types, sort by leading score and take top 5
            if story_type != "top" and filtered_stories:
                filtered_stories = self._get_leading_stories(filtered_stories, limit=5)

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

    def _get_leading_stories(self, stories: list, limit: int = 5) -> list:
        """Sort stories by leading score and return top N.

        Leading score = (2 * upvotes + comment_count)
        Upvotes are weighted twice as important as comments.

        Args:
            stories: List of HackerNews Item objects
            limit: Number of top stories to return

        Returns:
            List of top N stories sorted by leading score (descending)
        """
        def leading_score(story):
            score = story.score or 0
            comments = story.descendants or 0
            return (2 * score) + comments

        sorted_stories = sorted(stories, key=leading_score, reverse=True)
        return sorted_stories[:limit]

    def _fetch_stories_by_type(self, story_type: str, limit: int = 100):
        """Fetch stories from HackerNews API by type.

        Args:
            story_type: One of "top", "new", "ask", "show", "job"
            limit: Maximum number of stories to fetch

        Returns:
            List of Item objects
        """
        # Ensure we have an event loop in this thread
        # (Flask runs in threads without event loops)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

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

        # Format title with metadata (similar to TLDR's "N minute read" format)
        base_title = story.title or f"HN Story {story.item_id}"
        score = story.score or 0
        comments = story.descendants or 0

        # Build metadata suffix
        meta_parts = []
        if score > 0:
            meta_parts.append(f"{score} upvotes")
        if comments > 0:
            meta_parts.append(f"{comments} comments")

        # Finalize title with metadata
        if meta_parts:
            formatted_title = f"{base_title} ({', '.join(meta_parts)})"
        else:
            formatted_title = base_title

        return {
            "title": formatted_title,
            "url": story.url,
            "category": category,
            "date": util.format_date_for_url(date),
            "newsletter_type": story_type,
            "removed": False,
            "score": score,  # Keep for potential future use
            "comments": comments,  # Keep for potential future use
        }
