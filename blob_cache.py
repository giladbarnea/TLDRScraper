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

    # List API by prefix (handles random suffix on names)
    prefix_rel = build_blob_prefix(newsletter_type, date_value)
    prefix_with_store = f"{store}/{prefix_rel}" if store else prefix_rel
    # In-process URL cache lookup to avoid re-listing within a warm process
    cached_url = _URL_INDEX.get(prefix_rel) or _URL_INDEX.get(prefix_with_store)
    if cached_url:
        try:
            resp = requests.get(cached_url, timeout=8)
            if resp.status_code == 200:
                logger.info(
                    "[blob_cache.get_cached_json] index url hit prefix=%s status=%s",
                    prefix_rel, resp.status_code,
                )
                return resp.json()
            else:
                logger.info(
                    "[blob_cache.get_cached_json] index url miss prefix=%s status=%s",
                    prefix_rel, resp.status_code,
                )
        except Exception:
            logger.exception("[blob_cache.get_cached_json] index url fetch failed url=%s", cached_url)
    blobs = _list_blobs_by_prefix(prefix_rel, store)
    if not blobs:
        logger.info("[blob_cache.get_cached_json] list fallback: not found prefix=%s", prefix_with_store)
        return None

    # Choose a candidate that matches the prefix and ends with .json
    chosen = None
    for b in blobs:
        p = b.get("pathname") or b.get("key") or b.get("path") or ""
        if (p.startswith(prefix_rel) or p.startswith(prefix_with_store)) and p.endswith(".json"):
            chosen = b
            break
    if not chosen:
        logger.info(
            "[blob_cache.get_cached_json] list fallback: no .json under prefix=%s",
            prefix_with_store,
        )
        return None

    url = chosen.get("url") or chosen.get("downloadUrl")
    if url:
        # memoize for this process
        _URL_INDEX[prefix_rel] = url
        _URL_INDEX[prefix_with_store] = url
    logger.info(
        "[blob_cache.get_cached_json] list fallback: downloading url=%s chosen_path=%s",
        url, chosen.get("pathname") or chosen.get("key") or chosen.get("path"),
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
    store = _get_store_prefix()
    path_with_store = f"{store}/{key}" if store else key
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
        upload_url = f"{BLOB_UPLOAD_BASE_URL}/{path_with_store}"
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
                # memoize discovered URL for this process
                try:
                    prefix_rel = build_blob_prefix(newsletter_type, date_value)
                    prefix_with_store = f"{store}/{prefix_rel}" if store else prefix_rel
                    if url:
                        _URL_INDEX[prefix_rel] = url
                        _URL_INDEX[prefix_with_store] = url
                except Exception:
                    logger.exception("[blob_cache.put_cached_json] failed to memoize url for prefix")
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

