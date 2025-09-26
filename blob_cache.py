import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Any, Dict

import requests
from edge_config import is_available as ec_available, get_json as ec_get_json, set_json as ec_set_json


logger = logging.getLogger("blob_cache")
if not logger.handlers:
    # In serverless, basicConfig might be set elsewhere; ensure at least a StreamHandler exists
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


BLOB_UPLOAD_BASE_URL = "https://blob.vercel-storage.com"
VERCEL_BLOB_API_URL = "https://api.vercel.com/v2/blobs"

_URL_INDEX: Dict[str, str] = {}

def _json_default(obj: Any):
    """Best-effort JSON serializer for cache payloads."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Fallback to string for any other non-serializable objects
    return str(obj)

def _get_store_prefix() -> Optional[str]:
    """Optional store prefix to include in blob path, e.g., 'my-store'."""
    # Support multiple env names; prefer explicit BLOB_STORE_PREFIX
    return os.environ.get("BLOB_STORE_PREFIX") or os.environ.get("VERCEL_BLOB_STORE")


def _get_token() -> Optional[str]:
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    return token


def is_cache_eligible(target_date: datetime) -> bool:
    """Return True if target_date is strictly older than 3 days ago (UTC-based)."""
    # Normalize to date (no time) using UTC to avoid TZ ambiguity
    if target_date.tzinfo is None:
        target_date = target_date.replace(tzinfo=timezone.utc)
    else:
        target_date = target_date.astimezone(timezone.utc)

    today_utc = datetime.now(timezone.utc).date()
    cutoff_date = today_utc - timedelta(days=3)
    eligible = target_date.date() < cutoff_date
    logger.info(
        "[blob_cache.is_cache_eligible] target_date=%s today_utc=%s cutoff_date=%s eligible=%s",
        target_date.date(), today_utc, cutoff_date, eligible,
    )
    return eligible


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

def build_blob_dir(newsletter_type: str) -> str:
    return f"tldr-scraper-cache/{newsletter_type}"

def build_blob_prefix(newsletter_type: str, date_value: datetime) -> str:
    date_str = date_value.strftime("%Y-%m-%d")
    # No trailing hyphen: matches both deterministic ".json" and "-<suffix>.json"
    return f"{build_blob_dir(newsletter_type)}/{date_str}"


def _list_blob_exact(pathname: str) -> Optional[Dict[str, Any]]:
    """Return blob metadata for exact pathname using the list API, or None if not found."""
    token = _get_token()
    if not token:
        logger.info("[blob_cache._list_blob_exact] no token, skipping list pathname=%s", pathname)
        return None
    try:
        logger.info(
            "[blob_cache._list_blob_exact] listing path prefix=%s limit=%s",
            pathname, 100,
        )
        resp = requests.get(
            VERCEL_BLOB_API_URL,
            params={"prefix": pathname, "limit": 100},
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        logger.info(
            "[blob_cache._list_blob_exact] list status=%s",
            resp.status_code,
        )
        if resp.status_code != 200:
            try:
                txt = resp.text[:500]
            except Exception:
                txt = "<no body>"
            logger.info(
                "[blob_cache._list_blob_exact] list non-200 status=%s body=%s",
                resp.status_code, txt,
            )
            return None
        data = resp.json()
        blobs = data.get("blobs", []) or data.get("items", [])
        logger.info(
            "[blob_cache._list_blob_exact] list returned count=%s keys=%s",
            len(blobs), [b.get("pathname") or b.get("key") or b.get("path") for b in blobs[:5]],
        )
        for blob in blobs:
            # Some responses use 'pathname', others 'key'
            blob_path = blob.get("pathname") or blob.get("key") or blob.get("path")
            if blob_path == pathname or (blob_path and pathname and blob_path.endswith("/" + pathname)):
                logger.info("[blob_cache._list_blob_exact] found exact match pathname=%s", pathname)
                return blob
        return None
    except Exception:
        logger.exception("[blob_cache._list_blob_exact] exception while listing pathname=%s", pathname)
        return None
def _list_blobs_by_prefix(prefix_rel: str, store_prefix: Optional[str]) -> Optional[list]:
    token = _get_token()
    if not token:
        logger.info("[blob_cache._list_blobs_by_prefix] no token, skipping list prefix_rel=%s", prefix_rel)
        return None

    # Try multiple API paths and prefix forms for compatibility
    api_bases = [
        os.environ.get("BLOB_API_BASE") or "https://api.vercel.com",
    ]
    # Prefer endpoints observed working in logs first
    paths = [
        "/v2/blob", "/v1/blob", "/v2/blobs", "/v1/blobs",
    ]
    # Two prefix variants: relative to store, and including store prefix
    prefixes = [prefix_rel]
    if store_prefix:
        prefixes.append(f"{store_prefix}/{prefix_rel}")

    params_base = {"limit": 100}
    team_id = os.environ.get("VERCEL_TEAM_ID") or os.environ.get("VERCEL_ORG_ID")
    project_id = os.environ.get("VERCEL_PROJECT_ID")
    if team_id:
        params_base["teamId"] = team_id
    if project_id:
        params_base["projectId"] = project_id

    for base in api_bases:
        for path in paths:
            url = f"{base}{path}"
            for prefix in prefixes:
                try:
                    params = dict(params_base)
                    params["prefix"] = prefix
                    logger.info(
                        "[blob_cache._list_blobs_by_prefix] GET %s params=%s",
                        url, params,
                    )
                    resp = requests.get(
                        url,
                        params=params,
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10,
                    )
                    status = resp.status_code
                    if status != 200:
                        body_snip = None
                        try:
                            body_snip = resp.text[:500]
                        except Exception:
                            body_snip = "<no body>"
                        logger.info(
                            "[blob_cache._list_blobs_by_prefix] %s status=%s body=%s",
                            url, status, body_snip,
                        )
                        continue
                    data = resp.json()
                    blobs = data.get("blobs") or data.get("items") or data.get("data") or []
                    logger.info(
                        "[blob_cache._list_blobs_by_prefix] OK count=%s sample=%s",
                        len(blobs), [
                            (b.get("pathname") or b.get("key") or b.get("path")) for b in blobs[:5]
                        ],
                    )
                    return blobs
                except Exception:
                    logger.exception(
                        "[blob_cache._list_blobs_by_prefix] exception url=%s prefix=%s",
                        url, prefix,
                    )
                    continue
    return None

    


def get_cached_json(newsletter_type: str, date_value: datetime) -> Optional[Dict[str, Any]]:
    """
    If a cached JSON exists for (newsletter_type, date), return it as a dict.
    Otherwise return None.
    """
    key = build_blob_key(newsletter_type, date_value)

    store = _get_store_prefix()
    path_with_store = f"{store}/{key}" if store else key

    # If EDGE_CONFIG missing, skip cache entirely per env rules
    date_str = date_value.strftime("%Y-%m-%d")
    if not ec_available():
        return None

    # Read via Edge URL only
    ec_key = f"tldr-cache:{newsletter_type}:{date_str}"
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
    key = f"tldr-cache:{newsletter_type}:{date_str}"
    ok = ec_set_json(key, payload)
    logger.info("[blob_cache.put_cached_json] EdgeConfig write key=%s ok=%s", key, ok)
    return "edge://ok" if ok else None

