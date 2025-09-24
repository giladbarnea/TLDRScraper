import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Any, Dict

import requests


BLOB_UPLOAD_BASE_URL = "https://blob.vercel-storage.com"
VERCEL_BLOB_API_URL = "https://api.vercel.com/v2/blobs"


def _get_token() -> Optional[str]:
    return os.environ.get("BLOB_READ_WRITE_TOKEN")


def is_cache_eligible(target_date: datetime) -> bool:
    """Return True if target_date is strictly older than 3 days ago (UTC-based)."""
    # Normalize to date (no time) using UTC to avoid TZ ambiguity
    if target_date.tzinfo is None:
        target_date = target_date.replace(tzinfo=timezone.utc)
    else:
        target_date = target_date.astimezone(timezone.utc)

    today_utc = datetime.now(timezone.utc).date()
    cutoff_date = today_utc - timedelta(days=3)
    return target_date.date() < cutoff_date


def build_blob_key(newsletter_type: str, date_value: datetime) -> str:
    date_str = date_value.strftime("%Y-%m-%d")
    # Keep a stable, deterministic key to allow lookups and overwrites.
    # Public JSON payload containing either a hit (articles) or a miss marker.
    return f"tldr-scraper-cache/{newsletter_type}/{date_str}.json"


def _list_blob_exact(pathname: str) -> Optional[Dict[str, Any]]:
    """Return blob metadata for exact pathname using the list API, or None if not found."""
    token = _get_token()
    if not token:
        return None

    try:
        resp = requests.get(
            VERCEL_BLOB_API_URL,
            params={"prefix": pathname, "limit": 100},
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        blobs = data.get("blobs", []) or data.get("items", [])
        for blob in blobs:
            # Some responses use 'pathname', others 'key'
            blob_path = blob.get("pathname") or blob.get("key") or blob.get("path")
            if blob_path == pathname:
                return blob
        return None
    except Exception:
        return None


def get_cached_json(newsletter_type: str, date_value: datetime) -> Optional[Dict[str, Any]]:
    """
    If a cached JSON exists for (newsletter_type, date), return it as a dict.
    Otherwise return None.
    """
    key = build_blob_key(newsletter_type, date_value)
    blob = _list_blob_exact(key)
    if not blob:
        return None

    # Prefer 'url' field; fallback to 'downloadUrl'
    url = blob.get("url") or blob.get("downloadUrl")
    if not url:
        # Construct best-effort URL using upload base + key. This may fail if the store uses a different host.
        url = f"{BLOB_UPLOAD_BASE_URL}/{key}"

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def put_cached_json(newsletter_type: str, date_value: datetime, payload: Dict[str, Any]) -> Optional[str]:
    """
    Upload JSON payload to deterministic key. Returns blob URL on success, else None.
    """
    token = _get_token()
    if not token:
        return None

    key = build_blob_key(newsletter_type, date_value)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

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
        resp = requests.put(f"{BLOB_UPLOAD_BASE_URL}/{key}", data=body, headers=headers, timeout=10)
        if resp.status_code in (200, 201):
            try:
                info = resp.json()
                return info.get("url") or info.get("downloadUrl")
            except Exception:
                # Some deployments may not return JSON; construct best-effort URL
                return f"{BLOB_UPLOAD_BASE_URL}/{key}"
        return None
    except Exception:
        return None

