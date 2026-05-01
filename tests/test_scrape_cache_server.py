import threading
from datetime import date as date_type
from datetime import timedelta

import requests
from werkzeug.serving import make_server

import serve
import storage_service
import tldr_service


def _build_payload(date_text, *, url, title, tldr_status="unknown", removed=False, is_read=False):
    return {
        "date": date_text,
        "articles": [
            {
                "url": url,
                "title": title,
                "articleMeta": "",
                "issueDate": date_text,
                "category": "Newsletter",
                "sourceId": None,
                "section": None,
                "sectionEmoji": None,
                "sectionOrder": None,
                "newsletterType": None,
                "removed": removed,
                "tldr": {
                    "status": tldr_status,
                    "markdown": "# Existing",
                    "effort": "low",
                    "checkedAt": None,
                    "errorMessage": None,
                },
                "read": {"isRead": is_read, "markedAt": None},
            }
        ],
        "issues": [{"date": date_text, "source_id": "tldr_tech", "category": "TLDR Tech"}],
    }


def _start_server():
    server = make_server("127.0.0.1", 0, serve.app)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server, thread


def _stub_storage(monkeypatch):
    from datetime import datetime, timezone
    store = {}
    cached_at_store = {}
    patch_counter = {"value": 0}

    def get_daily_payload(date_text):
        return store.get(date_text)

    def get_daily_payload_row(date_text):
        payload = store.get(date_text)
        if payload is None:
            return None
        return {
            "payload": payload,
            "updated_at": payload.get("storage_updated_at") or cached_at_store.get(date_text),
        }

    def set_daily_payload(date_text, payload):
        store[date_text] = payload
        return {"date": date_text, "payload": payload}

    def set_daily_payload_from_scrape(date_text, payload):
        store[date_text] = payload
        cached_at_store[date_text] = datetime.now(timezone.utc).isoformat()
        return {"date": date_text, "payload": payload, "cached_at": cached_at_store[date_text]}

    def get_daily_payloads_range(start_date, end_date):
        dates = sorted(store.keys(), reverse=True)
        filtered = [
            {'date': date_text, 'payload': store[date_text], 'cached_at': cached_at_store.get(date_text)}
            for date_text in dates if start_date <= date_text <= end_date
        ]
        return filtered

    def is_date_cached(date_text):
        return date_text in store

    def patch_daily_article(date_text, url, patch, expected_updated_at):
        payload = store.get(date_text)
        if payload is None:
            raise RuntimeError(f"daily_cache row not found for date {date_text}")

        current_updated_at = payload.get("storage_updated_at") or cached_at_store.get(date_text)
        if current_updated_at != expected_updated_at:
            return {
                "conflict": True,
                "payload": payload,
                "updated_at": current_updated_at,
            }

        article_index = next(
            (index for index, article in enumerate(payload["articles"]) if article["url"] == url),
            None,
        )
        if article_index is None:
            raise RuntimeError(f"article not found for url {url}")

        next_payload = {
            **payload,
            "articles": list(payload["articles"]),
        }
        next_payload["articles"][article_index] = {
            **next_payload["articles"][article_index],
            **patch,
        }
        patch_counter["value"] += 1
        next_updated_at = f"2026-05-01T00:00:00.{patch_counter['value']:06d}+00:00"
        next_payload["storage_updated_at"] = next_updated_at
        store[date_text] = next_payload

        return {
            "conflict": False,
            "payload": next_payload,
            "updated_at": next_updated_at,
        }

    monkeypatch.setattr(storage_service, "get_daily_payload", get_daily_payload)
    monkeypatch.setattr(storage_service, "get_daily_payload_row", get_daily_payload_row)
    monkeypatch.setattr(storage_service, "set_daily_payload", set_daily_payload)
    monkeypatch.setattr(storage_service, "set_daily_payload_from_scrape", set_daily_payload_from_scrape)
    monkeypatch.setattr(storage_service, "get_daily_payloads_range", get_daily_payloads_range)
    monkeypatch.setattr(storage_service, "is_date_cached", is_date_cached)
    monkeypatch.setattr(storage_service, "patch_daily_article", patch_daily_article)
    return store, cached_at_store


def test_scrape_returns_cached_payloads_when_range_fully_cached(monkeypatch):
    from datetime import datetime, timedelta as td, timezone
    store, cached_at_store = _stub_storage(monkeypatch)
    start_date = (date_type.today() - timedelta(days=3)).isoformat()
    end_date = (date_type.today() - timedelta(days=2)).isoformat()
    store[start_date] = _build_payload(start_date, url="https://example.com/a", title="Cached A")
    store[end_date] = _build_payload(end_date, url="https://example.com/b", title="Cached B")
    # Set cached_at to a fresh timestamp (after Pacific midnight of next day)
    cached_at_store[start_date] = (datetime.now(timezone.utc) + td(days=1)).isoformat()
    cached_at_store[end_date] = (datetime.now(timezone.utc) + td(days=1)).isoformat()

    def fail_scrape(*args, **kwargs):
        raise AssertionError("Scrape should not run on full cache hit")

    monkeypatch.setattr(tldr_service, "scrape_single_source_for_date", fail_scrape)

    server, thread = _start_server()
    try:
        response = requests.post(
            f"http://127.0.0.1:{server.server_port}/api/scrape",
            json={"start_date": start_date, "end_date": end_date},
            timeout=5,
        )
        payload = response.json()
    finally:
        server.shutdown()
        thread.join()

    assert payload["success"] is True
    assert payload["source"] == "cache"
    assert len(payload["payloads"]) == 2


def test_scrape_populates_cache_on_miss(monkeypatch):
    store, cached_at_store = _stub_storage(monkeypatch)
    test_date = (date_type.today() - timedelta(days=4)).isoformat()

    def scrape_stub(_date, source_id, _excluded):
        return (
            test_date,
            {
                "articles": [
                    {
                        "url": "https://example.com/new",
                        "title": "Fresh Article",
                        "article_meta": "",
                        "date": test_date,
                        "category": "Newsletter",
                        "source_id": source_id,
                    }
                ],
                "issues": [{"date": test_date, "source_id": source_id, "category": "TLDR Tech"}],
                "network_articles": 1,
                "error": None,
                "source_id": source_id,
            },
        )

    monkeypatch.setattr(tldr_service, "get_default_source_ids", lambda: ["tldr_tech"])
    monkeypatch.setattr(tldr_service, "scrape_single_source_for_date", scrape_stub)

    server, thread = _start_server()
    try:
        response = requests.post(
            f"http://127.0.0.1:{server.server_port}/api/scrape",
            json={"start_date": test_date, "end_date": test_date},
            timeout=5,
        )
        payload = response.json()
    finally:
        server.shutdown()
        thread.join()

    assert payload["success"] is True
    assert payload["source"] == "live"
    assert test_date in store
    article = store[test_date]["articles"][0]
    assert article["url"] == "https://example.com/new"
    assert article["tldr"]["status"] == "unknown"


def test_scrape_unions_stale_cache_with_new_articles(monkeypatch):
    from datetime import datetime, timezone
    store, cached_at_store = _stub_storage(monkeypatch)
    test_date = (date_type.today() - timedelta(days=1)).isoformat()
    store[test_date] = _build_payload(
        test_date,
        url="https://example.com/existing",
        title="Existing Article",
        tldr_status="available",
        removed=True,
        is_read=True,
    )
    # Set cached_at to a stale timestamp (before Pacific midnight of next day)
    # Using a timestamp from yesterday makes it stale
    cached_at_store[test_date] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    def scrape_stub(_date, source_id, _excluded):
        return (
            test_date,
            {
                "articles": [
                    {
                        "url": "https://example.com/existing",
                        "title": "Existing Article Fresh",
                        "article_meta": "",
                        "date": test_date,
                        "category": "Newsletter",
                        "source_id": source_id,
                    },
                    {
                        "url": "https://example.com/new",
                        "title": "New Article",
                        "article_meta": "",
                        "date": test_date,
                        "category": "Newsletter",
                        "source_id": source_id,
                    },
                ],
                "issues": [{"date": test_date, "source_id": source_id, "category": "TLDR Tech"}],
                "network_articles": 2,
                "error": None,
                "source_id": source_id,
            },
        )

    monkeypatch.setattr(tldr_service, "get_default_source_ids", lambda: ["tldr_tech"])
    monkeypatch.setattr(tldr_service, "scrape_single_source_for_date", scrape_stub)

    server, thread = _start_server()
    try:
        response = requests.post(
            f"http://127.0.0.1:{server.server_port}/api/scrape",
            json={"start_date": test_date, "end_date": test_date},
            timeout=5,
        )
        payload = response.json()
    finally:
        server.shutdown()
        thread.join()

    assert payload["success"] is True
    merged_payload = store[test_date]
    existing = next(item for item in merged_payload["articles"] if item["url"] == "https://example.com/existing")
    assert existing["removed"] is True
    assert existing["read"]["isRead"] is True
    assert existing["tldr"]["status"] == "available"
    new_article = next(item for item in merged_payload["articles"] if item["url"] == "https://example.com/new")
    assert new_article["tldr"]["status"] == "unknown"


def test_get_storage_daily_returns_updated_at(monkeypatch):
    from datetime import datetime, timezone
    store, cached_at_store = _stub_storage(monkeypatch)
    test_date = (date_type.today() - timedelta(days=5)).isoformat()
    store[test_date] = _build_payload(test_date, url="https://example.com/metadata", title="Metadata Article")
    cached_at_store[test_date] = datetime.now(timezone.utc).isoformat()

    server, thread = _start_server()
    try:
        response = requests.get(
            f"http://127.0.0.1:{server.server_port}/api/storage/daily/{test_date}",
            timeout=5,
        )
        payload = response.json()
    finally:
        server.shutdown()
        thread.join()

    assert payload["success"] is True
    assert payload["payload"]["date"] == test_date
    assert payload["updated_at"] == cached_at_store[test_date]


def test_patch_storage_daily_article_updates_single_article(monkeypatch):
    from datetime import datetime, timezone
    store, cached_at_store = _stub_storage(monkeypatch)
    test_date = (date_type.today() - timedelta(days=6)).isoformat()
    store[test_date] = {
        "date": test_date,
        "articles": [
            {
                "url": "https://example.com/first",
                "title": "First",
                "articleMeta": "",
                "issueDate": test_date,
                "category": "Newsletter",
                "sourceId": None,
                "section": None,
                "sectionEmoji": None,
                "sectionOrder": None,
                "newsletterType": None,
                "removed": False,
                "summary": {"status": "unknown", "markdown": "", "effort": "low", "checkedAt": None, "errorMessage": None},
                "read": {"isRead": False, "markedAt": None},
            },
            {
                "url": "https://example.com/second",
                "title": "Second",
                "articleMeta": "",
                "issueDate": test_date,
                "category": "Newsletter",
                "sourceId": None,
                "section": None,
                "sectionEmoji": None,
                "sectionOrder": None,
                "newsletterType": None,
                "removed": False,
                "summary": {"status": "unknown", "markdown": "", "effort": "low", "checkedAt": None, "errorMessage": None},
                "read": {"isRead": False, "markedAt": None},
            },
        ],
        "issues": [],
    }
    cached_at_store[test_date] = datetime.now(timezone.utc).isoformat()

    server, thread = _start_server()
    try:
        initial_response = requests.get(
            f"http://127.0.0.1:{server.server_port}/api/storage/daily/{test_date}",
            timeout=5,
        ).json()
        patch_response = requests.patch(
            f"http://127.0.0.1:{server.server_port}/api/storage/daily/{test_date}/article",
            json={
                "url": "https://example.com/second",
                "patch": {"read": {"isRead": True, "markedAt": "2026-05-01T00:00:00Z"}},
                "expected_updated_at": initial_response["updated_at"],
            },
            timeout=5,
        )
        payload = patch_response.json()
    finally:
        server.shutdown()
        thread.join()

    assert patch_response.status_code == 200
    assert payload["success"] is True
    assert payload["payload"]["articles"][1]["read"]["isRead"] is True
    assert payload["payload"]["articles"][0]["read"]["isRead"] is False
    assert payload["updated_at"] != initial_response["updated_at"]


def test_patch_storage_daily_article_conflict_returns_latest_payload(monkeypatch):
    from datetime import datetime, timezone
    store, cached_at_store = _stub_storage(monkeypatch)
    test_date = (date_type.today() - timedelta(days=7)).isoformat()
    store[test_date] = {
        "date": test_date,
        "articles": [
            {
                "url": "https://example.com/conflict",
                "title": "Conflict",
                "articleMeta": "",
                "issueDate": test_date,
                "category": "Newsletter",
                "sourceId": None,
                "section": None,
                "sectionEmoji": None,
                "sectionOrder": None,
                "newsletterType": None,
                "removed": False,
                "summary": {"status": "unknown", "markdown": "", "effort": "low", "checkedAt": None, "errorMessage": None},
                "read": {"isRead": False, "markedAt": None},
            }
        ],
        "issues": [],
    }
    cached_at_store[test_date] = datetime.now(timezone.utc).isoformat()

    server, thread = _start_server()
    try:
        initial_response = requests.get(
            f"http://127.0.0.1:{server.server_port}/api/storage/daily/{test_date}",
            timeout=5,
        ).json()
        success_response = requests.patch(
            f"http://127.0.0.1:{server.server_port}/api/storage/daily/{test_date}/article",
            json={
                "url": "https://example.com/conflict",
                "patch": {"read": {"isRead": True, "markedAt": "2026-05-01T00:00:00Z"}},
                "expected_updated_at": initial_response["updated_at"],
            },
            timeout=5,
        ).json()
        conflict_response = requests.patch(
            f"http://127.0.0.1:{server.server_port}/api/storage/daily/{test_date}/article",
            json={
                "url": "https://example.com/conflict",
                "patch": {"removed": True},
                "expected_updated_at": initial_response["updated_at"],
            },
            timeout=5,
        )
        payload = conflict_response.json()
    finally:
        server.shutdown()
        thread.join()

    assert success_response["success"] is True
    assert conflict_response.status_code == 409
    assert payload["success"] is False
    assert payload["conflict"] is True
    assert payload["updated_at"] == success_response["updated_at"]
    assert payload["payload"]["articles"][0]["read"]["isRead"] is True
