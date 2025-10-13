import logging
import json
from typing import Set
import requests

import util

logger = logging.getLogger("removed_urls")

REMOVED_URLS_PATHNAME = "removed-urls.json"


def get_removed_urls() -> Set[str]:
    """Fetch the set of removed canonical URLs from blob store."""
    blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()

    if not blob_base_url:
        return set()

    blob_url = f"{blob_base_url}/{REMOVED_URLS_PATHNAME}"
    try:
        util.log(
            f"[removed_urls.get_removed_urls] Trying cache pathname={REMOVED_URLS_PATHNAME}",
            logger=logger,
        )
        resp = requests.get(
            blob_url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"},
        )
        resp.raise_for_status()
        util.log(
            f"[removed_urls.get_removed_urls] Cache HIT pathname={REMOVED_URLS_PATHNAME}",
            logger=logger,
        )
        data = json.loads(resp.text)
        if isinstance(data, list):
            return set(data)
        return set()
    except Exception as e:
        util.log(
            f"[removed_urls.get_removed_urls] Cache MISS pathname={REMOVED_URLS_PATHNAME} error={repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )
        return set()


def add_removed_url(url: str) -> bool:
    """Add a URL to the removed set and persist to blob store."""
    removed = get_removed_urls()
    removed.add(url)

    try:
        from blob_store import put_file

        put_file(REMOVED_URLS_PATHNAME, json.dumps(sorted(list(removed)), indent=2))
        util.log(
            f"[removed_urls.add_removed_url] Added url={url} pathname={REMOVED_URLS_PATHNAME}",
            logger=logger,
        )
        persisted_removed = get_removed_urls()
        if url in persisted_removed:
            util.log(
                f"[removed_urls.add_removed_url] ✓ Verified url={url} persisted in pathname={REMOVED_URLS_PATHNAME}",
                logger=logger,
            )
        else:
            util.log(
                f"[removed_urls.add_removed_url] Unable to verify url={url} persisted in pathname={REMOVED_URLS_PATHNAME}",
                level=logging.WARNING,
                logger=logger,
            )
        return True
    except Exception as e:
        util.log(
            f"[removed_urls.add_removed_url] Failed to add url={url} error={repr(e)}",
            level=logging.ERROR,
            logger=logger,
        )
        return False
