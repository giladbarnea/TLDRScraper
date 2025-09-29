import logging
from typing import Callable, TypeVar
import requests
import util

T = TypeVar("T")


def blob_cached(
    pathname_fn: Callable[[str], str],
    logger: logging.Logger = None,
) -> Callable[[Callable[[str], T]], Callable[[str], T]]:
    """Decorator that caches function results in blob store.
    
    Args:
        pathname_fn: Function that converts the input arg to a blob pathname
        logger: Optional logger for debug output
    """

    def decorator(fn: Callable[[str], T]) -> Callable[[str], T]:
        def wrapper(arg: str) -> T:
            pathname = pathname_fn(arg)
            blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()

            if blob_base_url:
                blob_url = f"{blob_base_url}/{pathname}"
                try:
                    util.log(
                        f"[blob_cache] Trying cache for {fn.__name__}: {pathname}",
                        logger=logger,
                    )
                    resp = requests.get(
                        blob_url,
                        timeout=10,
                        headers={
                            "User-Agent": "Mozilla/5.0 (compatible; TLDR-Summarizer/1.0)"
                        },
                    )
                    resp.raise_for_status()
                    util.log(
                        f"[blob_cache] Cache HIT for {fn.__name__}: {pathname}",
                        logger=logger,
                    )
                    return resp.text.strip()
                except Exception as e:
                    util.log(
                        f"[blob_cache] Cache MISS for {fn.__name__}: {pathname} - {repr(e)}",
                        level=logging.WARNING,
                        logger=logger,
                    )

            result = fn(arg)

            try:
                from blob_store import put_file

                put_file(pathname, result)
                util.log(
                    f"[blob_cache] Cached result for {fn.__name__}: {pathname}",
                    logger=logger,
                )
            except Exception as e:
                util.log(
                    f"[blob_cache] Failed to cache {fn.__name__}: {pathname} - {repr(e)}",
                    level=logging.WARNING,
                    logger=logger,
                )

            return result

        return wrapper

    return decorator