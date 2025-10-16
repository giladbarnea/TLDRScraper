import logging
import json
import time
from typing import Set, Tuple
import requests

import util

logger = logging.getLogger("removed_urls")

REMOVED_URLS_POINTER_PATHNAME = "removed-urls.current.txt"
REMOVED_URLS_SNAPSHOT_PATHNAME_TEMPLATE = "removed-urls-{timestamp}.json"


def _fetch_removed_urls_pointer(blob_base_url: str) -> str | None:
    if not blob_base_url:
        return None

    pointer_url = f"{blob_base_url}/{REMOVED_URLS_POINTER_PATHNAME}"
    try:
        util.log(
            "[removed_urls._fetch_removed_urls_pointer] "
            f"Trying cache pathname={REMOVED_URLS_POINTER_PATHNAME}",
            logger=logger,
        )
        resp = requests.get(
            pointer_url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        resp.raise_for_status()
        util.log(
            "[removed_urls._fetch_removed_urls_pointer] "
            f"x-vercel-cache={resp.headers.get('x-vercel-cache')} "
            f"age={resp.headers.get('age')} etag={resp.headers.get('etag')}",
            logger=logger,
        )
        util.log(
            "[removed_urls._fetch_removed_urls_pointer] "
            f"Cache HIT pathname={REMOVED_URLS_POINTER_PATHNAME}",
            logger=logger,
        )
        pointer_pathname = resp.text.strip()
        return pointer_pathname or None
    except Exception as e:
        util.log(
            "[removed_urls._fetch_removed_urls_pointer] "
            f"Cache MISS pathname={REMOVED_URLS_POINTER_PATHNAME} error={repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )
        return None


def _fetch_removed_urls_snapshot(
    blob_base_url: str, snapshot_pathname: str
) -> Set[str]:
    if not blob_base_url or not snapshot_pathname:
        return set()

    snapshot_url = f"{blob_base_url}/{snapshot_pathname}"
    try:
        util.log(
            "[removed_urls._fetch_removed_urls_snapshot] "
            f"Trying cache pathname={snapshot_pathname}",
            logger=logger,
        )
        resp = requests.get(
            snapshot_url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        resp.raise_for_status()
        util.log(
            "[removed_urls._fetch_removed_urls_snapshot] "
            f"x-vercel-cache={resp.headers.get('x-vercel-cache')} "
            f"age={resp.headers.get('age')} etag={resp.headers.get('etag')}",
            logger=logger,
        )
        util.log(
            "[removed_urls._fetch_removed_urls_snapshot] "
            f"Cache HIT pathname={snapshot_pathname}",
            logger=logger,
        )
        data = json.loads(resp.text)
        if isinstance(data, list):
            return set(data)
        return set()
    except Exception as e:
        util.log(
            "[removed_urls._fetch_removed_urls_snapshot] "
            f"Cache MISS pathname={snapshot_pathname} error={repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )
        return set()


def _load_removed_urls(blob_base_url: str) -> Tuple[Set[str], str | None]:
    snapshot_pathname = _fetch_removed_urls_pointer(blob_base_url)
    if not snapshot_pathname:
        return set(), None
    removed = _fetch_removed_urls_snapshot(blob_base_url, snapshot_pathname)
    return removed, snapshot_pathname


def get_removed_urls() -> Set[str]:
    blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
    removed, _ = _load_removed_urls(blob_base_url)
    return removed


def add_removed_url(url: str) -> bool:
    removed, current_pathname = _load_removed_urls(
        util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
    )
    removed.add(url)

    try:
        from blob_store import delete_file, put_file

        new_pathname = REMOVED_URLS_SNAPSHOT_PATHNAME_TEMPLATE.format(
            timestamp=int(time.time())
        )
        put_file(new_pathname, json.dumps(sorted(list(removed)), indent=2))
        util.log(
            f"[removed_urls.add_removed_url] Persisted url={url} to pathname={new_pathname}",
            logger=logger,
        )
        try:
            put_file(REMOVED_URLS_POINTER_PATHNAME, new_pathname)
            util.log(
                "[removed_urls.add_removed_url] Rotated pointer "
                f"from={current_pathname or 'None'} to={new_pathname}",
                logger=logger,
            )
        except Exception as pointer_error:
            util.log(
                "[removed_urls.add_removed_url] Failed to rotate pointer "
                f"to pathname={new_pathname} error={repr(pointer_error)}",
                level=logging.ERROR,
                logger=logger,
            )
            return False

        if current_pathname and current_pathname != new_pathname:
            try:
                deleted = delete_file(current_pathname)
                if deleted:
                    util.log(
                        "[removed_urls.add_removed_url] Deleted old snapshot "
                        f"pathname={current_pathname}",
                        logger=logger,
                    )
                else:
                    util.log(
                        "[removed_urls.add_removed_url] Failed to delete old snapshot "
                        f"pathname={current_pathname}",
                        level=logging.WARNING,
                        logger=logger,
                    )
            except Exception as deletion_error:
                util.log(
                    "[removed_urls.add_removed_url] Exception deleting old snapshot "
                    f"pathname={current_pathname} error={repr(deletion_error)}",
                    level=logging.WARNING,
                    logger=logger,
                )

        persisted_removed = get_removed_urls()
        if url in persisted_removed:
            util.log(
                "[removed_urls.add_removed_url] ✓ Verified url=%s persisted via pointer=%s",
                url,
                REMOVED_URLS_POINTER_PATHNAME,
                logger=logger,
            )
        else:
            util.log(
                f"[removed_urls.add_removed_url] Unable to verify url={url} persisted via pointer={REMOVED_URLS_POINTER_PATHNAME}",
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
