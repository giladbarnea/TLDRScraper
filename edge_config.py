import os
import json
import logging
from typing import Optional
from urllib.parse import urlencode, quote, urlparse, urlunparse, parse_qsl

import requests


logger = logging.getLogger("edge_config")
if not logger.handlers:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


def _get_read_base() -> Optional[str]:
    # Full read URL typically in form: https://edge-config.vercel.com/ecfg_xxx?token=...
    return os.environ.get("EDGE_CONFIG")


def _get_config_id() -> Optional[str]:
    return os.environ.get("EDGE_CONFIG_ID")


def _get_vercel_token() -> Optional[str]:
    # Token for write operations via REST API
    return os.environ.get("VERCEL_TOKEN")

def _get_team_id() -> Optional[str]:
    return os.environ.get("VERCEL_TEAM_ID") or os.environ.get("VERCEL_ORG_ID")

def _get_project_id() -> Optional[str]:
    return os.environ.get("VERCEL_PROJECT_ID")


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
        new_url = urlunparse((parsed.scheme, parsed.netloc, new_path, "", new_query, ""))
        return new_url
    except Exception:
        logger.exception("[edge_config._build_item_url] failed for base=%s key=%s", base, key)
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
        logger.info("[edge_config.get_json] non-200 status=%s body=%s", resp.status_code, resp.text[:300])
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
    body = {
        "items": [
            {"operation": "upsert", "key": key, "value": value}
        ]
    }
    try:
        params = {}
        team_id = _get_team_id()
        project_id = _get_project_id()
        if team_id:
            params["teamId"] = team_id
        if project_id:
            params["projectId"] = project_id
        resp = requests.patch(url, params=params, json=body, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }, timeout=8)
        global _LAST_WRITE_STATUS, _LAST_WRITE_BODY
        _LAST_WRITE_STATUS = resp.status_code
        try:
            _LAST_WRITE_BODY = resp.text[:300]
        except Exception:
            _LAST_WRITE_BODY = None
        if resp.status_code in (200, 201):
            return True
        logger.info("[edge_config.set_json] non-2xx status=%s body=%s", resp.status_code, _LAST_WRITE_BODY)
        return False
    except Exception:
        logger.exception("[edge_config.set_json] request failed url=%s", url)
        return False

