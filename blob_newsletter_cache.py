import logging
import json
from datetime import datetime
from typing import Optional, Any, Dict
import requests

import util
import cache_mode

logger = logging.getLogger("blob_newsletter_cache")


def _cache_pathname(newsletter_type: str, date_value: datetime) -> str:
    """Generate blob pathname for newsletter cache."""
    date_str = date_value.strftime("%Y-%m-%d")
    return f"newsletter-{newsletter_type}-{date_str}.json"


def get_cached_json(
    newsletter_type: str, date_value: datetime
) -> Optional[Dict[str, Any]]:
    """
    If a cached JSON exists for (newsletter_type, date), return it as a dict.
    Otherwise return None.
    """
    # Early return: Check if cache reads are allowed
    if not cache_mode.can_read():
        return None
    
    pathname = _cache_pathname(newsletter_type, date_value)
    blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()

    if not blob_base_url:
        return None

    blob_url = f"{blob_base_url}/{pathname}"
    try:
        util.log(
            "[blob_newsletter_cache.get_cached_json] Trying cache pathname=%s",
            pathname,
            logger=logger,
        )
        resp = requests.get(
            blob_url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Scraper/1.0)"},
        )
        resp.raise_for_status()
        util.log(
            "[blob_newsletter_cache.get_cached_json] Cache HIT pathname=%s",
            pathname,
            logger=logger,
        )
        return json.loads(resp.text)
    except Exception as e:
        util.log(
            "[blob_newsletter_cache.get_cached_json] Cache MISS pathname=%s error=%s",
            pathname,
            repr(e),
            level=logging.WARNING,
            logger=logger,
        )
        return None


def put_cached_json(
    newsletter_type: str, date_value: datetime, payload: Dict[str, Any]
) -> Optional[str]:
    """Write cache to Blob store."""
    # Early return: Check if cache writes are allowed
    if not cache_mode.can_write():
        return None
    
    pathname = _cache_pathname(newsletter_type, date_value)

    safe_payload = payload
    try:
        articles = payload.get("articles") if isinstance(payload, dict) else None
        if isinstance(articles, list):
            fixed = []
            for a in articles:
                if isinstance(a, dict):
                    b = dict(a)
                    if "date" in b and not isinstance(b["date"], str):
                        try:
                            b["date"] = b["date"].strftime("%Y-%m-%d")
                        except Exception:
                            b["date"] = str(b["date"])
                    fixed.append(b)
                else:
                    fixed.append(a)
            safe_payload = dict(payload)
            safe_payload["articles"] = fixed
    except Exception:
        pass

    try:
        from blob_store import put_file

        put_file(pathname, json.dumps(safe_payload, indent=2))
        util.log(
            "[blob_newsletter_cache.put_cached_json] Cache write OK pathname=%s",
            pathname,
            logger=logger,
        )
        blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
        return f"{blob_base_url}/{pathname}" if blob_base_url else "blob://ok"
    except Exception as e:
        util.log(
            "[blob_newsletter_cache.put_cached_json] Cache write FAILED pathname=%s error=%s",
            pathname,
            repr(e),
            level=logging.ERROR,
            exc_info=True,
            logger=logger,
        )
        return None
