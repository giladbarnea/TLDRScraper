import os
import logging
from typing import Optional
from urllib.parse import urlencode, quote, urlparse, urlunparse, parse_qsl

import requests


logger = logging.getLogger("edge_config")
if not logger.handlers:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


def _resolve_env(*names: str) -> Optional[str]:
    """Return the first non-empty env var value among provided names, also
    checking for a TLDR_SCRAPER_ prefixed variant for each name.
    """
    for name in names:
        # exact name first (production style)
        val = os.environ.get(name)
        if val:
            return val
        # local style with TLDR_SCRAPER_ prefix
        prefixed = f"TLDR_SCRAPER_{name}"
        val = os.environ.get(prefixed)
        if val:
            return val
    return None


def _get_read_base() -> Optional[str]:
    # Canonical env var for full read URL
    # Example: https://edge-config.vercel.com/ecfg_xxx?token=...
    return _resolve_env("EDGE_CONFIG_CONNECTION_STRING")


def _get_config_id() -> Optional[str]:
    return _resolve_env("EDGE_CONFIG_ID")


def _get_vercel_token() -> Optional[str]:
    # Token for write operations via REST API
    # VERCEL_TOKEN is unprefixed uniformly in local and production
    return os.environ.get("VERCEL_TOKEN")


# Team/organization/project scoping is intentionally not used to keep env minimal


def get_effective_env_summary() -> dict:
    """Summarize effective env detection for diagnostics/UI without exposing secrets."""
    read_base_present = bool(_get_read_base())
    config_id_present = bool(_get_config_id())
    vercel_token_present = bool(_get_vercel_token())
    return {
        "edge_config_present": read_base_present,
        "edge_config_id_present": config_id_present,
        "vercel_token_present": vercel_token_present,
    }


def is_available() -> bool:
    return _get_read_base() is not None


def _build_item_url(key: str) -> Optional[str]:
    base = _get_read_base()
    if not base:
        return None
    try:
        parsed = urlparse(base)
        # Preserve existing query (e.g., token=...)
        query_pairs = dict(parse_qsl(parsed.query))
        new_path = parsed.path.rstrip("/") + "/item/" + quote(key, safe="")
        new_query = urlencode(query_pairs)
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            new_path,
            "",
            new_query,
            "",
        ))
        return new_url
    except Exception:
        logger.exception(
            "[edge_config._build_item_url] failed for base=%s key=%s", base, key
        )
        return None


def get_json(key: str) -> Optional[dict]:
    url = _build_item_url(key)
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return None
        logger.info(
            "[edge_config.get_json] non-200 status=%s body=%s",
            resp.status_code,
            resp.text[:300],
        )
        return None
    except Exception:
        logger.exception("[edge_config.get_json] request failed url=%s", url)
        return None


_LAST_WRITE_STATUS: Optional[int] = None
_LAST_WRITE_BODY: Optional[str] = None


def get_last_write_status() -> Optional[int]:
    return _LAST_WRITE_STATUS


def get_last_write_body() -> Optional[str]:
    return _LAST_WRITE_BODY


def set_json(key: str, value: dict) -> bool:
    config_id = _get_config_id()
    token = _get_vercel_token()
    if not config_id or not token:
        return False
    url = f"https://api.vercel.com/v1/edge-config/{config_id}/items"
    body = {"items": [{"operation": "upsert", "key": key, "value": value}]}
    try:
        resp = requests.patch(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=8,
        )
        global _LAST_WRITE_STATUS, _LAST_WRITE_BODY
        _LAST_WRITE_STATUS = resp.status_code
        try:
            _LAST_WRITE_BODY = resp.text[:300]
        except Exception:
            _LAST_WRITE_BODY = None
        if resp.status_code in (200, 201):
            return True
        logger.info(
            "[edge_config.set_json] non-2xx status=%s body=%s",
            resp.status_code,
            _LAST_WRITE_BODY,
        )
        return False
    except Exception:
        logger.exception("[edge_config.set_json] request failed url=%s", url)
        return False
