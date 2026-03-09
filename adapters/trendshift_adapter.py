import logging
import re
from datetime import datetime

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from adapters.newsletter_adapter import NewsletterAdapter
import util


logger = logging.getLogger("trendshift_adapter")


class TrendshiftAdapter(NewsletterAdapter):
    """Adapter for Trendshift Daily Explore rankings."""

    def scrape_date(self, date: str, excluded_urls: list[str]) -> dict:
        """Scrape Trendshift Daily Explore repositories for a specific date."""
        target_date = util.format_date_for_url(date)
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
        """Drive Trendshift with Playwright and extract repository cards."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1366, "height": 2200}, ignore_https_errors=True)

            page.goto(self.config.base_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3500)

            self._select_daily_explore_mode(page)
            self._select_date(page, target_date)
            page.wait_for_timeout(2500)

            repositories = self._extract_repositories(page)
            browser.close()

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

    def _select_daily_explore_mode(self, page: Page) -> None:
        """Ensure the Daily Explore mode is active."""
        daily_explore_button = page.get_by_role("button", name="Daily Explore")
        if daily_explore_button.count() == 0:
            return
        daily_explore_button.first.click()
        page.wait_for_timeout(400)

    def _select_date(self, page: Page, target_date: str) -> None:
        """Pick target date from Trendshift date picker."""
        date_picker_button = page.locator('button:has-text("-")').first
        current_date_text = date_picker_button.inner_text().strip()
        if current_date_text == target_date:
            return

        date_picker_button.click()
        aria_label = _build_calendar_aria_label(target_date)

        try:
            page.locator(f'button[aria-label="{aria_label}"]').first.click(timeout=5000)
        except PlaywrightTimeoutError as error:
            raise RuntimeError(
                f"Trendshift calendar day button not found for {target_date} ({aria_label})"
            ) from error

    def _extract_repositories(self, page: Page) -> list[dict]:
        """Extract repository cards from loaded Trendshift page."""
        card_locator = page.locator("div.rounded-lg.border.border-gray-300.bg-white")
        card_count = card_locator.count()
        repositories = []
        seen_urls = set()

        for card_index in range(card_count):
            card = card_locator.nth(card_index)
            github_link = card.locator('a[href*="github.com/"]')
            if github_link.count() == 0:
                continue

            repository_url = github_link.first.get_attribute("href")
            if not repository_url:
                continue

            match = re.search(r"github\.com/([^/?#]+/[^/?#]+)", repository_url)
            if not match:
                continue

            full_repository_url = f"https://github.com/{match.group(1)}"
            if full_repository_url in seen_urls:
                continue

            lines = [line.strip() for line in card.inner_text().splitlines() if line.strip()]
            description = _extract_description_line(lines)

            seen_urls.add(full_repository_url)
            repositories.append(
                {
                    "name": match.group(1),
                    "url": full_repository_url,
                    "description": description,
                }
            )

        return repositories


def _build_calendar_aria_label(date_string: str) -> str:
    """Build the exact date button aria-label used by Trendshift calendar.

    >>> _build_calendar_aria_label("2026-03-05")
    'Thursday, March 5th, 2026'
    >>> _build_calendar_aria_label("2026-03-02")
    'Monday, March 2nd, 2026'
    """
    target_date = datetime.strptime(date_string, "%Y-%m-%d")
    weekday = target_date.strftime("%A")
    month = target_date.strftime("%B")
    day_number = target_date.day
    suffix = _ordinal_suffix(day_number)
    year = target_date.year
    return f"{weekday}, {month} {day_number}{suffix}, {year}"


def _ordinal_suffix(day_number: int) -> str:
    """Return ordinal suffix for calendar day number.

    >>> [_ordinal_suffix(day) for day in [1, 2, 3, 4, 11, 12, 13, 21]]
    ['st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'st']
    """
    if 11 <= day_number % 100 <= 13:
        return "th"
    if day_number % 10 == 1:
        return "st"
    if day_number % 10 == 2:
        return "nd"
    if day_number % 10 == 3:
        return "rd"
    return "th"


def _extract_description_line(lines: list[str]) -> str:
    """Extract a likely repository description line from card text lines.

    >>> _extract_description_line(['1', 'owner/repo', 'TypeScript', '9.5k', '1.1k', 'GitHub', 'Open-source orchestration'])
    'Open-source orchestration'
    >>> _extract_description_line(['1', 'owner/repo', 'TypeScript', '9.5k', '1.1k', 'GitHub'])
    ''
    """
    if not lines:
        return ""
    last_line = lines[-1]
    if last_line == "GitHub":
        return ""
    if re.fullmatch(r"\d+", last_line):
        return ""
    return last_line
