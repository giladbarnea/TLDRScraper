import logging
import json
from typing import Set
import requests
import util

logger = logging.getLogger("url_blocklist")

BLOCKLIST_PATHNAME = "url-blocklist.json"


def _get_blocklist() -> Set[str]:
    """Read blocklist from blob storage, return canonical URLs."""
    blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
    if not blob_base_url:
        return set()

    blob_url = f"{blob_base_url}/{BLOCKLIST_PATHNAME}"
    try:
        util.log(
            "[url_blocklist._get_blocklist] Fetching blocklist from %s",
            blob_url,
            logger=logger,
        )
        resp = requests.get(
            blob_url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Scraper/1.0)"},
        )
        resp.raise_for_status()
        data = json.loads(resp.text)
        blocked_urls = set(data.get("blocked_urls", []))
        util.log(
            "[url_blocklist._get_blocklist] Loaded %d blocked URLs",
            len(blocked_urls),
            logger=logger,
        )
        return blocked_urls
    except Exception as e:
        util.log(
            "[url_blocklist._get_blocklist] Failed to fetch blocklist: %s",
            repr(e),
            level=logging.WARNING,
            logger=logger,
        )
        return set()


def _put_blocklist(blocked_urls: Set[str]) -> bool:
    """Write blocklist to blob storage."""
    try:
        from blob_store import put_file

        payload = {"blocked_urls": sorted(list(blocked_urls))}
        put_file(BLOCKLIST_PATHNAME, json.dumps(payload, indent=2))
        util.log(
            "[url_blocklist._put_blocklist] Wrote %d blocked URLs",
            len(blocked_urls),
            logger=logger,
        )
        return True
    except Exception as e:
        util.log(
            "[url_blocklist._put_blocklist] Failed to write blocklist: %s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return False


def add_to_blocklist(url: str) -> bool:
    """Add URL to blocklist."""
    from serve import canonicalize_url

    canonical = canonicalize_url(url)
    blocked = _get_blocklist()
    if canonical in blocked:
        util.log(
            "[url_blocklist.add_to_blocklist] URL already blocked: %s",
            canonical,
            logger=logger,
        )
        return True

    blocked.add(canonical)
    success = _put_blocklist(blocked)
    if success:
        util.log(
            "[url_blocklist.add_to_blocklist] Added URL to blocklist: %s",
            canonical,
            logger=logger,
        )
    return success


def is_blocked(url: str) -> bool:
    """Check if URL is in blocklist."""
    from serve import canonicalize_url

    canonical = canonicalize_url(url)
    blocked = _get_blocklist()
    return canonical in blocked


def filter_articles(articles: list) -> list:
    """Filter out blocked URLs from articles list."""
    blocked = _get_blocklist()
    if not blocked:
        return articles

    from serve import canonicalize_url

    filtered = []
    removed_count = 0
    for article in articles:
        url = article.get("url", "")
        if not url:
            filtered.append(article)
            continue

        canonical = canonicalize_url(url)
        if canonical not in blocked:
            filtered.append(article)
        else:
            removed_count += 1

    if removed_count > 0:
        util.log(
            "[url_blocklist.filter_articles] Filtered out %d blocked URLs",
            removed_count,
            logger=logger,
        )

    return filtered