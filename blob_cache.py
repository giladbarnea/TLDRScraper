import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Any, Dict

from edge_config import is_available as ec_available, get_json as ec_get_json, set_json as ec_set_json


logger = logging.getLogger("blob_cache")
if not logger.handlers:
    # In serverless, basicConfig might be set elsewhere; ensure at least a StreamHandler exists
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


 


def build_blob_key(newsletter_type: str, date_value: datetime) -> str:
    date_str = date_value.strftime("%Y-%m-%d")
    # Keep a stable, deterministic key to allow lookups and overwrites.
    # Public JSON payload containing either a hit (articles) or a miss marker.
    key = f"tldr-scraper-cache/{newsletter_type}/{date_str}.json"
    logger.info(
        "[blob_cache.build_blob_key] newsletter_type=%s date=%s key=%s",
        newsletter_type, date_str, key,
    )
    return key

 


 

    


def get_cached_json(newsletter_type: str, date_value: datetime) -> Optional[Dict[str, Any]]:
    """
    If a cached JSON exists for (newsletter_type, date), return it as a dict.
    Otherwise return None.
    """
    key = build_blob_key(newsletter_type, date_value)

    # If EDGE_CONFIG missing, skip cache entirely per env rules
    date_str = date_value.strftime("%Y-%m-%d")
    if not ec_available():
        return None

    # Read via Edge URL only
    ec_key = f"tldr-cache-{newsletter_type}-{date_str}"
    ec_val = ec_get_json(ec_key)
    if ec_val is not None:
        logger.info("[blob_cache.get_cached_json] EdgeConfig hit key=%s", ec_key)
        return ec_val
    return None


def put_cached_json(newsletter_type: str, date_value: datetime, payload: Dict[str, Any]) -> Optional[str]:
    """Write cache to Edge Config. If EDGE_CONFIG is absent, do nothing."""
    if not ec_available():
        return None
    date_str = date_value.strftime("%Y-%m-%d")
    key = f"tldr-cache-{newsletter_type}-{date_str}"
    # Ensure payload is JSON-serializable (dates as strings)
    safe_payload = payload
    try:
        articles = payload.get('articles') if isinstance(payload, dict) else None
        if isinstance(articles, list):
            fixed = []
            for a in articles:
                if isinstance(a, dict):
                    b = dict(a)
                    if 'date' in b and not isinstance(b['date'], str):
                        try:
                            b['date'] = b['date'].strftime('%Y-%m-%d')
                        except Exception:
                            b['date'] = str(b['date'])
                    fixed.append(b)
                else:
                    fixed.append(a)
            safe_payload = dict(payload)
            safe_payload['articles'] = fixed
    except Exception:
        pass
    ok = ec_set_json(key, safe_payload)
    logger.info("[blob_cache.put_cached_json] EdgeConfig write key=%s ok=%s", key, ok)
    return "edge://ok" if ok else None

