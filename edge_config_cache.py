import os
import logging
from datetime import datetime
from typing import Optional, Any, Dict

from edge_config import (
    is_available as ec_available,
    get_json as ec_get_json,
    set_json as ec_set_json,
)


logger = logging.getLogger("edge_config_cache")
if not logger.handlers:
    # In serverless, basicConfig might be set elsewhere; ensure at least a StreamHandler exists
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


def get_cached_json(
    newsletter_type: str, date_value: datetime
) -> Optional[Dict[str, Any]]:
    """
    If a cached JSON exists for (newsletter_type, date), return it as a dict.
    Otherwise return None.
    """
    date_str = date_value.strftime("%Y-%m-%d")

    # If EDGE_CONFIG missing, skip cache entirely per env rules
    if not ec_available():
        return None

    # Prefer new date-first key; fall back to legacy key for backwards compatibility
    primary_key = f"{date_str}-{newsletter_type}"
    ec_val = ec_get_json(primary_key)
    if ec_val is not None:
        logger.info(
            "[edge_config_cache.get_cached_json] EdgeConfig hit key=%s", primary_key
        )
        return ec_val
    return None


def put_cached_json(
    newsletter_type: str, date_value: datetime, payload: Dict[str, Any]
) -> Optional[str]:
    """Write cache to Edge Config. If EDGE_CONFIG is absent, do nothing."""
    if not ec_available():
        return None
    date_str = date_value.strftime("%Y-%m-%d")
    key = f"{date_str}-{newsletter_type}"

    # Enforce minimal value shape per AGENTS.md: { "articles": [ { "title", "url" } ] }
    articles = []
    if isinstance(payload, dict):
        maybe_articles = payload.get("articles")
        if isinstance(maybe_articles, list):
            for item in maybe_articles:
                if not isinstance(item, dict):
                    continue
                title = item.get("title")
                url = item.get("url")
                if not isinstance(title, str) or not isinstance(url, str):
                    continue
                # Strip utm_* params and normalize URL minimally
                try:
                    import urllib.parse as urlparse

                    p = urlparse.urlparse(url)
                    query_pairs = [
                        (k, v)
                        for (k, v) in urlparse.parse_qsl(
                            p.query, keep_blank_values=True
                        )
                        if not k.lower().startswith("utm_")
                    ]
                    new_query = urlparse.urlencode(query_pairs, doseq=True)
                    cleaned_url = urlparse.urlunparse(
                        (
                            p.scheme,
                            p.netloc.lower(),
                            p.path.rstrip("/") if len(p.path) > 1 and p.path.endswith("/") else p.path,
                            p.params,
                            new_query,
                            p.fragment,
                        )
                    )
                except Exception:
                    cleaned_url = url
                articles.append({"title": title.strip(), "url": cleaned_url})

    # Do not write empty keys
    if not articles:
        logger.info(
            "[edge_config_cache.put_cached_json] skip write (no articles) key=%s",
            key,
        )
        return None

    safe_payload = {"articles": articles}

    ok = ec_set_json(key, safe_payload)
    logger.info(
        "[edge_config_cache.put_cached_json] EdgeConfig write key=%s ok=%s", key, ok
    )
    return "edge://ok" if ok else None
