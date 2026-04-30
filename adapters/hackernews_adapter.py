"""Hacker News adapter that fetches Show HN stories for a specific date."""

import logging
from datetime import datetime

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("hackernews_adapter")
ALGOLIA_API_BASE = "http://hn.algolia.com/api/v1"


class HackerNewsAdapter(NewsletterAdapter):
    """Adapter for Hacker News Show HN stories via Algolia."""

    def __init__(self, config):
        super().__init__(config)
        self.min_points = 30
        self.min_comments = 5
        self.max_stories = 50

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Fetch and normalize Show HN stories for a date."""
        target_date = datetime.fromisoformat(util.format_date_for_url(date))
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=0)

        stories = self._fetch_stories_algolia(
            start_timestamp=int(start_of_day.timestamp()),
            end_timestamp=int(end_of_day.timestamp()),
            min_points=self.min_points,
            min_comments=self.min_comments,
            limit=self.max_stories,
        )

        excluded_set = set(excluded_urls)
        articles = []
        for story in stories:
            url = story.get("url")
            if not url:
                continue
            canonical_url = util.canonicalize_url(url)
            if canonical_url in excluded_set:
                continue
            article = self._algolia_story_to_article(story, date)
            if article:
                articles.append(article)

        issues = []
        if articles:
            issues = [{
                "date": util.format_date_for_url(date),
                "source_id": self.config.source_id,
                "category": "HN Show",
                "title": None,
                "subtitle": None,
            }]

        return self._normalize_response(articles, issues)

    @util.retry()
    def _fetch_stories_algolia(self, start_timestamp: int, end_timestamp: int, min_points: int, min_comments: int, limit: int) -> list:
        """Query Algolia API for show_hn stories in a time range."""
        params = {
            "tags": "show_hn",
            "numericFilters": f"created_at_i>{start_timestamp},created_at_i<{end_timestamp},points>={min_points},num_comments>={min_comments}",
            "hitsPerPage": limit,
        }
        response = util.fetch(f"{ALGOLIA_API_BASE}/search_by_date", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("hits", [])

    def _algolia_story_to_article(self, story: dict, date: str) -> dict | None:
        """Convert a Show HN Algolia story into article payload."""
        if not story.get("url"):
            return None

        points = story.get("points", 0)
        comments = story.get("num_comments", 0)
        return {
            "title": story.get("title", f"HN Show {story.get('objectID', '')}"),
            "article_meta": f"{points} upvotes, {comments} comments",
            "url": story["url"],
            "category": self.config.category_display_names["show"],
            "date": util.format_date_for_url(date),
            "newsletter_type": "show",
            "removed": False,
        }
