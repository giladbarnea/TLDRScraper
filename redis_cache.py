import os
import json
import logging
from typing import Any, Optional

try:
    from upstash_redis import Redis as UpstashRedis
except Exception:  # pragma: no cover - optional dependency
    UpstashRedis = None  # type: ignore


logger = logging.getLogger("redis_cache")
if not logger.handlers:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


def _get_upstash_client() -> Optional[Any]:
    """Return a configured Upstash Redis REST client if env vars exist, else None."""
    # Support both Vercel KV and Upstash env names
    url = (
        os.environ.get("UPSTASH_REDIS_REST_URL")
        or os.environ.get("KV_REST_API_URL")
        or os.environ.get("KV_URL")
    )
    token = (
        os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        or os.environ.get("KV_REST_API_TOKEN")
    )
    if not url or not token or UpstashRedis is None:
        return None
    try:
        return UpstashRedis(url=url, token=token)
    except Exception:  # pragma: no cover
        logger.exception("[redis_cache._get_upstash_client] failed to create client")
        return None


_CLIENT = _get_upstash_client()


def is_available() -> bool:
    return _CLIENT is not None


def build_kv_key(newsletter_type: str, date_str: str) -> str:
    # Keep it short for Redis key limits
    return f"tldr-cache:{newsletter_type}:{date_str}"


def get_json(key: str) -> Optional[dict]:
    if _CLIENT is None:
        return None
    try:
        raw = _CLIENT.get(key)
        if raw is None:
            return None
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="ignore")
        if isinstance(raw, str):
            return json.loads(raw)
        # Some clients may return parsed JSON already
        if isinstance(raw, dict):
            return raw
        return None
    except Exception:
        logger.exception("[redis_cache.get_json] failed key=%s", key)
        return None


def set_json(key: str, value: dict, ttl_seconds: Optional[int] = None) -> bool:
    if _CLIENT is None:
        return False
    try:
        payload = json.dumps(value, ensure_ascii=False)
        if ttl_seconds and ttl_seconds > 0:
            _CLIENT.set(key, payload, ex=ttl_seconds)
        else:
            _CLIENT.set(key, payload)
        return True
    except Exception:
        logger.exception("[redis_cache.set_json] failed key=%s", key)
        return False

