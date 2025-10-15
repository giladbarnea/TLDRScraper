import contextvars
import logging
import json
from typing import Optional, Set, Tuple
import requests

import util

logger = logging.getLogger("removed_urls")

REMOVED_URLS_PATHNAME = "removed-urls.json"
REMOVED_URLS_CONTEXT: contextvars.ContextVar[Optional[Set[str]]] = contextvars.ContextVar(
    "removed_urls_context", default=None
)


def _set_context_removed_urls(urls: Set[str]) -> None:
    REMOVED_URLS_CONTEXT.set(set(urls))


def _fetch_removed_urls_from_blob_store() -> Tuple[Set[str], bool]:
    blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()

    if not blob_base_url:
        return set(), True

    blob_url = f"{blob_base_url}/{REMOVED_URLS_PATHNAME}"
    try:
        util.log(
            f"[removed_urls.get_removed_urls] Trying cache pathname={REMOVED_URLS_PATHNAME}",
            logger=logger,
        )
        resp = requests.get(
            blob_url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        resp.raise_for_status()
        util.log(
            f"[removed_urls.get_removed_urls] "
            f"x-vercel-cache={resp.headers.get('x-vercel-cache')} "
            f"age={resp.headers.get('age')} etag={resp.headers.get('etag')}",
            logger=logger,
        )
        util.log(
            f"[removed_urls.get_removed_urls] Cache HIT pathname={REMOVED_URLS_PATHNAME}",
            logger=logger,
        )
        data = json.loads(resp.text)
        if isinstance(data, list):
            return set(data), True
        return set(), True
    except Exception as e:
        util.log(
            f"[removed_urls.get_removed_urls] Cache MISS pathname={REMOVED_URLS_PATHNAME} error={repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )
        return set(), False


def get_removed_urls() -> Set[str]:
    """Fetch the set of removed canonical URLs, favoring the context cache."""
    context_removed_urls = REMOVED_URLS_CONTEXT.get()
    if context_removed_urls is not None:
        return set(context_removed_urls)

    removed_urls, fetch_successful = _fetch_removed_urls_from_blob_store()
    if fetch_successful:
        _set_context_removed_urls(removed_urls)
    return set(removed_urls)


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
        _set_context_removed_urls(removed)
        persisted_removed, persisted_fetch_successful = _fetch_removed_urls_from_blob_store()
        if persisted_fetch_successful:
            _set_context_removed_urls(persisted_removed)
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
