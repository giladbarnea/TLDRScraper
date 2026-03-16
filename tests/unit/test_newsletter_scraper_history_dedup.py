import datetime

import newsletter_scraper


class _FakeAdapter:
    def __init__(self, scrape_result):
        self._scrape_result = scrape_result

    def scrape_date(self, date, excluded_urls):
        return self._scrape_result


def test_scrape_single_source_for_date_prunes_issues_when_history_dedup_removes_all_articles(monkeypatch):
    scrape_result = {
        "articles": [
            {
                "url": "https://github.com/acme/repo",
                "title": "Repo",
                "date": "2026-03-16",
                "category": "Trendshift Daily Explore",
            }
        ],
        "issues": [
            {
                "date": "2026-03-16",
                "source_id": "trendshift",
                "category": "Trendshift Daily Explore",
                "title": "Trendshift Daily Explore",
                "subtitle": None,
            }
        ],
    }

    monkeypatch.setattr(
        newsletter_scraper,
        "_get_adapter_for_source",
        lambda config: _FakeAdapter(scrape_result),
    )
    monkeypatch.setattr(
        newsletter_scraper.storage_service,
        "filter_new_urls_for_history_dedup",
        lambda source_id, first_seen_date, canonical_urls: set(),
    )

    _, result = newsletter_scraper.scrape_single_source_for_date(
        datetime.date(2026, 3, 16),
        "trendshift",
        [],
    )

    assert result["articles"] == []
    assert result["issues"] == []


def test_scrape_single_source_for_date_keeps_issue_when_articles_remain_after_history_dedup(monkeypatch):
    scrape_result = {
        "articles": [
            {
                "url": "https://github.com/acme/repo",
                "title": "Repo",
                "date": "2026-03-16",
                "category": "Trendshift Daily Explore",
            }
        ],
        "issues": [
            {
                "date": "2026-03-16",
                "source_id": "trendshift",
                "category": "Trendshift Daily Explore",
                "title": "Trendshift Daily Explore",
                "subtitle": None,
            }
        ],
    }

    monkeypatch.setattr(
        newsletter_scraper,
        "_get_adapter_for_source",
        lambda config: _FakeAdapter(scrape_result),
    )
    monkeypatch.setattr(
        newsletter_scraper.storage_service,
        "filter_new_urls_for_history_dedup",
        lambda source_id, first_seen_date, canonical_urls: set(canonical_urls),
    )

    _, result = newsletter_scraper.scrape_single_source_for_date(
        datetime.date(2026, 3, 16),
        "trendshift",
        [],
    )

    assert len(result["articles"]) == 1
    assert len(result["issues"]) == 1
