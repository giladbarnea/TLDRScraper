#!/usr/bin/env python3

"""
Cleanup script for Vercel Edge Config keys older than a given epoch timestamp.

Behavior:
- Reads items from Edge Config using the read token from the connection string
  provided in env var TLDR_SCRAPER_EDGE_CONFIG_CONN_STRING.
- Determines which keys are older than --before (epoch seconds), based on the
  date encoded in the key name: {YYYY-MM-DD}-{type}.
- Deletes matching keys via Vercel REST API using env var VERCEL_TOKEN.
- If --team-id is not provided, attempts to fetch defaultTeamId via /v2/user.

Usage examples:
  uv run python scripts/cleanup_edge_config.py --before=1737500000 --dry-run
  uv run python scripts/cleanup_edge_config.py --before=1737500000 --team-id TEAM_XXXX

Notes:
- This script performs a single batch PATCH of delete operations. If many keys
  must be removed and an API limit is hit, split into chunks.
- Requires only Python stdlib (no third-party deps).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


EDGE_READ_HOST = "https://edge-config.vercel.com"
VERCEL_API_HOST = "https://api.vercel.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cleanup Edge Config keys older than an epoch timestamp.")
    parser.add_argument("--before", required=True, type=int, help="Epoch timestamp (seconds). Delete keys with a date before this.")
    parser.add_argument("--team-id", default=None, help="Vercel team id to scope write API calls (optional).")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without performing changes.")
    return parser.parse_args()


def get_env_or_exit(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"ERROR: Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(2)
    return value


def extract_edge_id_and_token(conn_string: str) -> Tuple[str, str]:
    # Format: https://edge-config.vercel.com/<EDGE_ID>?token=<READ_TOKEN>
    conn_string = conn_string.strip()
    if not conn_string.startswith(EDGE_READ_HOST):
        raise ValueError("Connection string does not start with expected host")
    path_part = conn_string[len(EDGE_READ_HOST) :]
    # path_part like: /ecfg_...?...token=...
    edge_id = path_part.split("?")[0].lstrip("/")
    if "token=" not in conn_string:
        raise ValueError("Connection string missing token query param")
    read_token = conn_string.split("token=", 1)[1]
    return edge_id, read_token


def http_json(method: str, url: str, headers: Dict[str, str], body: Optional[dict] = None) -> dict:
    data: Optional[bytes] = None
    req_headers = {"User-Agent": "edge-cleaner/1.0"}
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


KEY_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<type>ai|tech)$", re.IGNORECASE)


def parse_key_date_epoch(key: str) -> Optional[int]:
    m = KEY_RE.match(key)
    if not m:
        return None
    date_str = m.group("date")
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return None


def infer_team_id_if_needed(team_id: Optional[str], api_token: str) -> Optional[str]:
    if team_id:
        return team_id
    # Attempt to fetch defaultTeamId
    url = f"{VERCEL_API_HOST}/v2/user"
    headers = {"Authorization": f"Bearer {api_token}"}
    data = http_json("GET", url, headers)
    try:
        return data.get("user", {}).get("defaultTeamId")
    except Exception:
        return None


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


def main() -> None:
    args = parse_args()
    before_epoch = int(args.before)
    now_epoch = int(time.time())
    if before_epoch <= 0 or before_epoch > now_epoch + 365 * 24 * 3600:
        print("ERROR: --before must be a reasonable epoch timestamp in seconds", file=sys.stderr)
        sys.exit(2)

    conn_string = get_env_or_exit("TLDR_SCRAPER_EDGE_CONFIG_CONN_STRING")
    api_token = get_env_or_exit("VERCEL_TOKEN")
    edge_id, read_token = extract_edge_id_and_token(conn_string)

    items = read_all_items(edge_id, read_token)
    all_keys = list(items.keys())

    candidate_deletes: List[str] = []
    skipped_non_matching: List[str] = []
    for key in all_keys:
        # Only consider object values and keys that match our schema
        value = items.get(key)
        if not isinstance(value, dict):
            # Non-object values are legacy or noise; include in delete candidates
            candidate_deletes.append(key)
            continue
        epoch = parse_key_date_epoch(key)
        if epoch is None:
            skipped_non_matching.append(key)
            continue
        if epoch < before_epoch:
            candidate_deletes.append(key)

    candidate_deletes = sorted(set(candidate_deletes))

    print(json.dumps({
        "edge_id": edge_id,
        "before_epoch": before_epoch,
        "delete_count": len(candidate_deletes),
        "keys_to_delete": candidate_deletes,
        "skipped_non_matching": skipped_non_matching,
    }, indent=2))

    if args.dry_run:
        return

    team_id = infer_team_id_if_needed(args.team_id, api_token)
    result = delete_keys(edge_id, api_token, team_id, candidate_deletes)
    print(json.dumps({"delete_result": result}, indent=2))


if __name__ == "__main__":
    main()

