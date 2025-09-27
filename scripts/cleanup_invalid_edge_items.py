#!/usr/bin/env python3

"""
Remove invalid-shaped items from Vercel Edge Config for TLDR cache keys.

This script reads all items, validates only keys matching
  tldr-cache-{ai|tech}-{YYYY-MM-DD}
and values matching the expected schema used by the app, and deletes all others.

Environment:
- EDGE_CONFIG_CONNECTION_STRING or TLDR_SCRAPER_EDGE_CONFIG_CONNECTION_STRING
    Example: https://edge-config.vercel.com/ecfg_xxx?token=READ_TOKEN
- VERCEL_TOKEN: required to perform delete writes
- Optional: VERCEL_TEAM_ID (or provide --team-id) to scope writes

Usage:
  # Dry-run (no deletions)
  python scripts/cleanup_invalid_edge_items.py --dry-run

  # Actually delete invalid items
  python scripts/cleanup_invalid_edge_items.py

  # With explicit team id
  python scripts/cleanup_invalid_edge_items.py --team-id TEAM_XXXX
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


EDGE_READ_HOST = "https://edge-config.vercel.com"
VERCEL_API_HOST = "https://api.vercel.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete invalid-shaped Edge Config items for TLDR cache.")
    parser.add_argument("--team-id", default=None, help="Vercel team id to scope write API calls (optional).")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without performing changes.")
    return parser.parse_args()


def get_env_or_exit(name: str, alt_names: Optional[List[str]] = None) -> str:
    names = [name] + (alt_names or [])
    for n in names:
        value = os.getenv(n)
        if value:
            return value
    print(f"ERROR: Missing required environment variable. Tried: {', '.join(names)}", file=sys.stderr)
    sys.exit(2)


def get_env_any(name: str, alt_names: Optional[List[str]] = None) -> Optional[str]:
    names = [name] + (alt_names or [])
    for n in names:
        value = os.getenv(n)
        if value:
            return value
    return None


def extract_edge_id_and_token(conn_string: str) -> Tuple[str, str]:
    # Format: https://edge-config.vercel.com/<EDGE_ID>?token=<READ_TOKEN>
    conn_string = conn_string.strip()
    if not conn_string.startswith(EDGE_READ_HOST):
        raise ValueError("Connection string does not start with expected host")
    path_part = conn_string[len(EDGE_READ_HOST) :]
    edge_id = path_part.split("?")[0].lstrip("/")
    if "token=" not in conn_string:
        raise ValueError("Connection string missing token query param")
    read_token = conn_string.split("token=", 1)[1]
    return edge_id, read_token


def http_json(method: str, url: str, headers: Dict[str, str], body: Optional[dict] = None) -> dict:
    data: Optional[bytes] = None
    req_headers = {"User-Agent": "edge-invalid-cleaner/1.0"}
    req_headers.update(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = Request(url, data=data, headers=req_headers, method=method)
    try:
        with urlopen(req) as resp:
            content = resp.read()
            if not content:
                return {}
            return json.loads(content.decode("utf-8"))
    except HTTPError as e:
        payload = e.read().decode("utf-8", errors="ignore")
        print(f"HTTPError {e.code} for {method} {url}: {payload}", file=sys.stderr)
        raise
    except URLError as e:
        print(f"URLError for {method} {url}: {e}", file=sys.stderr)
        raise


def read_all_items(edge_id: str, read_token: str) -> dict:
    url = f"{EDGE_READ_HOST}/{edge_id}/items"
    headers = {"Authorization": f"Bearer {read_token}"}
    return http_json("GET", url, headers)


def delete_keys(edge_id: str, api_token: str, team_id: Optional[str], keys: List[str]) -> dict:
    if not keys:
        return {"status": "noop", "deleted": 0}
    url = f"{VERCEL_API_HOST}/v1/edge-config/{edge_id}/items"
    params = {}
    if team_id:
        params["teamId"] = team_id
    if params:
        url = f"{url}?{urlencode(params)}"
    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {"items": [{"operation": "delete", "key": k} for k in keys]}
    return http_json("PATCH", url, headers, body=payload)


# Valid TLDR cache key: tldr-cache-{ai|tech}-{YYYY-MM-DD}
KEY_RE = re.compile(r"^tldr-cache-(?P<type>ai|tech)-(?P<date>\d{4}-\d{2}-\d{2})$", re.IGNORECASE)


def _is_iso_date_string(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except Exception:
        return False


def validate_item(key: str, value: Any) -> Tuple[bool, str]:
    """Return (is_valid, reason_if_invalid)."""
    m = KEY_RE.match(key)
    if not m:
        return False, "key_does_not_match_pattern"

    if not isinstance(value, dict):
        return False, "value_not_object"

    key_type = m.group("type").lower()
    key_date = m.group("date")

    status = value.get("status")
    if status != "hit":
        return False, "status_not_hit"

    date_field = value.get("date")
    if not _is_iso_date_string(date_field) or date_field != key_date:
        return False, "date_mismatch_or_invalid"

    ntype = value.get("newsletter_type")
    if ntype != key_type:
        return False, "newsletter_type_mismatch"

    articles = value.get("articles")
    if not isinstance(articles, list):
        return False, "articles_not_list"

    # Validate a sample of up to 10 articles for essential fields
    sample = articles[:10]
    for idx, a in enumerate(sample):
        if not isinstance(a, dict):
            return False, f"article_{idx}_not_object"
        title = a.get("title")
        url = a.get("url")
        category = a.get("category")
        if not (isinstance(title, str) and title.strip() and isinstance(url, str) and url.startswith("http")):
            return False, f"article_{idx}_missing_title_or_url"
        if not isinstance(category, str) or not category:
            return False, f"article_{idx}_missing_category"
        # If present, validate article date and newsletter_type
        adate = a.get("date")
        if adate is not None and (not _is_iso_date_string(adate)):
            return False, f"article_{idx}_date_not_iso"
        atype = a.get("newsletter_type")
        if atype is not None and not isinstance(atype, str):
            return False, f"article_{idx}_newsletter_type_invalid"

    return True, "ok"


def infer_team_id_if_needed(team_id: Optional[str], api_token: str) -> Optional[str]:
    if team_id:
        return team_id
    url = f"{VERCEL_API_HOST}/v2/user"
    headers = {"Authorization": f"Bearer {api_token}"}
    try:
        data = http_json("GET", url, headers)
        return data.get("user", {}).get("defaultTeamId")
    except Exception:
        return None


def main() -> None:
    args = parse_args()

    # Support multiple env var names for compatibility
    conn_string = get_env_or_exit(
        "EDGE_CONFIG_CONNECTION_STRING",
        alt_names=[
            "TLDR_SCRAPER_EDGE_CONFIG_CONNECTION_STRING",
            "TLDR_SCRAPER_EDGE_CONFIG_CONN_STRING",
        ],
    )
    api_token = get_env_or_exit("VERCEL_TOKEN")

    edge_id, read_token = extract_edge_id_and_token(conn_string)

    items = read_all_items(edge_id, read_token)
    all_keys = list(items.keys())

    invalid_keys: List[str] = []
    skipped_valid: List[str] = []
    reasons: Dict[str, str] = {}

    for key in all_keys:
        value = items.get(key)
        ok, reason = validate_item(key, value)
        if ok:
            skipped_valid.append(key)
        else:
            invalid_keys.append(key)
            reasons[key] = reason

    invalid_keys = sorted(set(invalid_keys))
    print(json.dumps({
        "edge_id": edge_id,
        "invalid_count": len(invalid_keys),
        "invalid_keys": invalid_keys,
        "reasons_sample": {k: reasons[k] for k in invalid_keys[:20]},
        "valid_kept_count": len(skipped_valid),
    }, indent=2))

    if args.dry_run or not invalid_keys:
        return

    # Delete in batches of up to 100 to be safe
    team_id = infer_team_id_if_needed(args.team_id, api_token)
    deleted_total = 0
    for i in range(0, len(invalid_keys), 100):
        batch = invalid_keys[i:i+100]
        result = delete_keys(edge_id, api_token, team_id, batch)
        print(json.dumps({"batch_from": i, "batch_count": len(batch), "delete_result": result}, indent=2))
        deleted_total += len(batch)

    print(json.dumps({"deleted_total": deleted_total}, indent=2))


if __name__ == "__main__":
    main()

