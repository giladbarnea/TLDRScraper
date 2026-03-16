import logging
import re
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
            return self._normalize_response([], [])

        excluded_set = set(excluded_urls)
        category = self.config.category_display_names["daily_explore"]
        scraped_articles = self._scrape_daily_explore(target_date)

        articles = []
        for article in scraped_articles:
            canonical_url = util.canonicalize_url(article["url"])
            if canonical_url in excluded_set:
                continue
            articles.append(article)

        issues = []
        if articles:
            issues.append(
                {
                    "date": target_date,
                    "source_id": self.config.source_id,
                    "category": category,
                    "title": "Trendshift Daily Explore",
                    "subtitle": None,
                }
            )

        return self._normalize_response(articles, issues)

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
    """Extract repository cards from Trendshift SSR HTML.

    >>> html = '<div class="rounded-lg border border-gray-300 bg-white"><a href="/repositories/1">owner/repo</a><a href="https://github.com/owner/repo">GitHub</a><div class="text-gray-500 text-xs leading-5">A cool project</div></div>'
    >>> repos = _extract_repositories_from_html(html)
    >>> repos[0]['name']
    'owner/repo'
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.rounded-lg.border.border-gray-300.bg-white")
    repositories = []
    seen_urls = set()

    for card in cards:
        repo_name = _extract_repo_name(card)
        if not repo_name:
            continue

        full_url = f"https://github.com/{repo_name}"
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        description_element = card.select_one("div.text-gray-500.text-xs.leading-5")
        description = description_element.get_text(strip=True) if description_element else ""

        repositories.append(
            {"name": repo_name, "url": full_url, "description": description}
        )

    return repositories


def _extract_repo_name(card) -> str | None:
    """Extract 'owner/repo' from a Trendshift card element.

    Tries the internal trendshift link text first (which displays as 'owner/repo'),
    then falls back to parsing a github.com href.
    """
    internal_link = card.select_one('a[href*="/repositories/"]')
    if internal_link:
        text = internal_link.get_text(strip=True)
        if "/" in text:
            return text

    github_link = card.select_one('a[href*="github.com/"]')
    if not github_link:
        return None
    href = github_link.get("href", "")
    match = re.search(r"github\.com/([^/?#]+/[^/?#]+)", href)
    return match.group(1) if match else None
