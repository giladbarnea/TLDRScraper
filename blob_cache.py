import logging
import json
from typing import Callable, TypeVar, Any
from functools import wraps
import requests
import util
import cache_mode

T = TypeVar("T")


def blob_cached(
    pathname_fn: Callable[[str], str],
    logger: logging.Logger = None,
) -> Callable[[Callable[[str], T]], Callable[[str], T]]:
    """Decorator that caches function results in blob store (text format).

    Args:
        pathname_fn: Function that converts the input arg to a blob pathname
        logger: Optional logger for debug output
    """

    def decorator(fn: Callable[[str], T]) -> Callable[[str], T]:
        @wraps(fn)
        def wrapper(arg: str) -> T:
            pathname = pathname_fn(arg)
            blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()

            # Early return: Check if cache reads are allowed
            if blob_base_url and cache_mode.can_read():
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
                    return resp.content.decode("utf-8").strip()
                except Exception as e:
                    util.log(
                        f"[blob_cache] Cache MISS for {fn.__name__}: {pathname} - {repr(e)}",
                        level=logging.WARNING,
                        logger=logger,
                    )

            # Execute the function
            result = fn(arg)

            # Early return: Check if cache writes are allowed
            if not cache_mode.can_write():
                return result

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


def blob_cached_json(
    pathname_fn: Callable[..., str],
    should_cache: Callable[[Any], bool] = None,
    logger: logging.Logger = None,
) -> Callable:
    """Decorator that caches function results as JSON in blob store.

    Args:
        pathname_fn: Function that converts function args to a blob pathname
        should_cache: Optional predicate to determine if result should be cached (default: cache everything)
        logger: Optional logger for debug output
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            pathname = pathname_fn(*args, **kwargs)
            blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()

            # Early return: Check if cache reads are allowed
            if blob_base_url and cache_mode.can_read():
                blob_url = f"{blob_base_url}/{pathname}"
                try:
                    util.log(
                        f"[blob_cache_json] Trying cache for {fn.__name__}: {pathname}",
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
                        f"[blob_cache_json] Cache HIT for {fn.__name__}: {pathname}",
                        logger=logger,
                    )
                    return json.loads(resp.content.decode("utf-8"))
                except Exception as e:
                    util.log(
                        f"[blob_cache_json] Cache MISS for {fn.__name__}: {pathname} - {repr(e)}",
                        level=logging.WARNING,
                        logger=logger,
                    )

            # Execute the function
            result = fn(*args, **kwargs)

            # Early return: Check if cache writes are allowed
            if not cache_mode.can_write():
                return result

            if should_cache is None or should_cache(result):
                try:
                    from blob_store import put_file

                    put_file(pathname, json.dumps(result, indent=2))
                    util.log(
                        f"[blob_cache_json] Cached result for {fn.__name__}: {pathname}",
                        logger=logger,
                    )
                except Exception as e:
                    util.log(
                        f"[blob_cache_json] Failed to cache {fn.__name__}: {pathname} - {repr(e)}",
                        level=logging.WARNING,
                        logger=logger,
                    )

            return result

        return wrapper

    return decorator
