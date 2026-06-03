import json
import logging
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("trendshift_adapter")


class TrendshiftAdapter(NewsletterAdapter):
    """Adapter for Trendshift Daily Explore rankings.

    Scrapes the server-rendered HTML from trendshift.io using HTTP.
    Trendshift's date picker is client-side JS only — the SSR HTML always
    returns today's trending repos regardless of query params. Therefore
    this adapter only returns results when the requested date is today.
    """

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Scrape Trendshift Daily Explore repositories for a specific date."""
        target_date = util.format_date_for_url(date)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if target_date != today:
            logger.info("Trendshift only serves today's data via SSR; skipping %s", target_date)
            return self._normalize_response([])

        excluded_set = set(excluded_urls)
        category = self.config.category_display_names["daily_explore"]
        scraped_articles = self._scrape_daily_explore(target_date)

        articles = []
        for article in scraped_articles:
            canonical_url = util.canonicalize_url(article["url"])
            if canonical_url in excluded_set:
                continue
            articles.append(article)
        return self._normalize_response(articles)

    @util.retry(max_attempts=2, delay=1.0)
    def _scrape_daily_explore(self, target_date: str) -> list[dict]:
        """Fetch Trendshift SSR HTML and extract repository cards."""
        response = util.fetch(self.config.base_url, timeout=30)
        response.raise_for_status()

        repositories = _extract_repositories_from_html(response.text)
        category = self.config.category_display_names["daily_explore"]
        return [
            {
                "title": repository["name"],
                "article_meta": repository["description"],
                "url": repository["url"],
                "category": category,
                "date": target_date,
                "newsletter_type": "daily_explore",
                "removed": False,
            }
            for repository in repositories
        ]


def _extract_repositories_from_html(html: str) -> list[dict]:
    """Extract repositories from Trendshift's schema.org JSON-LD ItemList.

    Trendshift server-renders its live trending ranking as an ItemList of
    SoftwareSourceCode items inside a <script type="application/ld+json"> tag,
    independent of client-side hydration.

    >>> html = '<script type="application/ld+json">{"@type":"ItemList","itemListElement":[{"item":{"name":"owner/repo","description":"A cool project","codeRepository":"https://github.com/owner/repo"}}]}</script>'
    >>> repos = _extract_repositories_from_html(html)
    >>> repos[0]['name']
    'owner/repo'
    """
    soup = BeautifulSoup(html, "html.parser")
    json_ld_blocks = (json.loads(script.string) for script in soup.find_all("script", type="application/ld+json"))
    item_list = next(block for block in json_ld_blocks if block.get("@type") == "ItemList")

    repositories = []
    seen_urls = set()
    for entry in item_list["itemListElement"]:
        item = entry["item"]
        url = item["codeRepository"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        repositories.append(
            {
                "name": item["name"],
                "url": url,
                "description": item.get("description", "").strip(),
            }
        )

    return repositories
