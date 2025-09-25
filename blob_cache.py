import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Any, Dict

import requests


logger = logging.getLogger("blob_cache")
if not logger.handlers:
    # In serverless, basicConfig might be set elsewhere; ensure at least a StreamHandler exists
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


BLOB_UPLOAD_BASE_URL = "https://blob.vercel-storage.com"
VERCEL_BLOB_API_URL = "https://api.vercel.com/v2/blobs"

def _json_default(obj: Any):
    """Best-effort JSON serializer for cache payloads."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Fallback to string for any other non-serializable objects
    return str(obj)


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


def _list_blob_exact(pathname: str) -> Optional[Dict[str, Any]]:
    """Return blob metadata for exact pathname using the list API, or None if not found."""
    token = _get_token()
    if not token:
        logger.debug("[blob_cache._list_blob_exact] no token, skipping list pathname=%s", pathname)
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
            if blob_path == pathname:
                logger.info("[blob_cache._list_blob_exact] found exact match pathname=%s", pathname)
                return blob
        return None
    except Exception:
        logger.exception("[blob_cache._list_blob_exact] exception while listing pathname=%s", pathname)
        return None


def get_cached_json(newsletter_type: str, date_value: datetime) -> Optional[Dict[str, Any]]:
    """
    If a cached JSON exists for (newsletter_type, date), return it as a dict.
    Otherwise return None.
    """
    key = build_blob_key(newsletter_type, date_value)

    # Fast path: attempt direct GET to the deterministic public URL.
    # This works even if we cannot access the List API (e.g., missing token).
    direct_url = f"{BLOB_UPLOAD_BASE_URL}/{key}"
    try:
        logger.info(
            "[blob_cache.get_cached_json] direct GET url=%s",
            direct_url,
        )
        resp = requests.get(direct_url, timeout=8)
        logger.info(
            "[blob_cache.get_cached_json] direct GET status=%s",
            resp.status_code,
        )
        if resp.status_code == 200:
            data = resp.json()
            logger.info(
                "[blob_cache.get_cached_json] direct hit key=%s articles=%s status=%s",
                key,
                len(data.get("articles", [])) if isinstance(data, dict) else "n/a",
                data.get("status") if isinstance(data, dict) else "n/a",
            )
            return data
    except Exception:
        logger.exception("[blob_cache.get_cached_json] direct GET failed url=%s", direct_url)

    # If direct GET failed, fall back to List API when token is available
    blob = _list_blob_exact(key)
    if not blob:
        logger.info("[blob_cache.get_cached_json] list fallback: not found key=%s", key)
        return None

    # Prefer 'url' field; fallback to 'downloadUrl'; last resort to constructed URL
    url = blob.get("url") or blob.get("downloadUrl") or direct_url
    logger.info(
        "[blob_cache.get_cached_json] list fallback: downloading url=%s key=%s",
        url, key,
    )
    try:
        resp = requests.get(url, timeout=10)
        logger.info(
            "[blob_cache.get_cached_json] list download status=%s",
            resp.status_code,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        logger.info(
            "[blob_cache.get_cached_json] list hit key=%s articles=%s status=%s",
            key,
            len(data.get("articles", [])) if isinstance(data, dict) else "n/a",
            data.get("status") if isinstance(data, dict) else "n/a",
        )
        return data
    except Exception:
        logger.exception("[blob_cache.get_cached_json] list fallback download failed url=%s", url)
        return None


def put_cached_json(newsletter_type: str, date_value: datetime, payload: Dict[str, Any]) -> Optional[str]:
    """
    Upload JSON payload to deterministic key. Returns blob URL on success, else None.
    """
    token = _get_token()
    if not token:
        logger.warning(
            "[blob_cache.put_cached_json] missing token, cannot write key newsletter_type=%s date=%s",
            newsletter_type, date_value.strftime("%Y-%m-%d"),
        )
        return None

    key = build_blob_key(newsletter_type, date_value)
    body = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
    status = payload.get("status")
    num_articles = len(payload.get("articles", [])) if isinstance(payload, dict) else "n/a"
    logger.info(
        "[blob_cache.put_cached_json] writing key=%s status=%s articles=%s bytes=%s",
        key, status, num_articles, len(body),
    )

    headers = {
        "Authorization": f"Bearer {token}",
        # Mark file as public to allow direct GETs
        "x-vercel-blob-public": "true",
        # Deterministic name for read-after-write
        "x-vercel-blob-add-random-suffix": "false",
        # Allow updating cache entries if we recompute
        "x-vercel-blob-allow-overwrite": "true",
        "Content-Type": "application/json; charset=utf-8",
    }

    try:
        upload_url = f"{BLOB_UPLOAD_BASE_URL}/{key}"
        resp = requests.put(upload_url, data=body, headers=headers, timeout=10)
        logger.info(
            "[blob_cache.put_cached_json] write status=%s",
            resp.status_code,
        )
        if resp.status_code in (200, 201):
            try:
                info = resp.json()
                url = info.get("url") or info.get("downloadUrl")
                logger.info(
                    "[blob_cache.put_cached_json] write ok key=%s url=%s",
                    key, url,
                )
                # Post-write verification via direct GET and returned URL
                try:
                    verify_direct = requests.get(upload_url, timeout=6)
                    logger.info(
                        "[blob_cache.put_cached_json] verify direct GET status=%s url=%s",
                        verify_direct.status_code, upload_url,
                    )
                except Exception:
                    logger.exception("[blob_cache.put_cached_json] verify direct GET failed url=%s", upload_url)
                if url:
                    try:
                        verify_returned = requests.get(url, timeout=6)
                        logger.info(
                            "[blob_cache.put_cached_json] verify returned URL status=%s url=%s",
                            verify_returned.status_code, url,
                        )
                    except Exception:
                        logger.exception("[blob_cache.put_cached_json] verify returned URL failed url=%s", url)
                return url
            except Exception:
                # Some deployments may not return JSON; construct best-effort URL
                url = f"{BLOB_UPLOAD_BASE_URL}/{key}"
                logger.info(
                    "[blob_cache.put_cached_json] write ok (non-json body) key=%s url=%s",
                    key, url,
                )
                # Post-write verification
                try:
                    verify_direct = requests.get(url, timeout=6)
                    logger.info(
                        "[blob_cache.put_cached_json] verify direct GET status=%s url=%s",
                        verify_direct.status_code, url,
                    )
                except Exception:
                    logger.exception("[blob_cache.put_cached_json] verify direct GET failed url=%s", url)
                return url
        return None
    except Exception:
        logger.exception("[blob_cache.put_cached_json] exception while writing key=%s", key)
        return None

