import logging
import json
from typing import Callable, TypeVar, Any, ParamSpec
from functools import wraps
import requests
import util
import cache_mode

P = ParamSpec("P")
R = TypeVar("R")


def blob_cached(
    pathname_fn: Callable[[str], str],
    logger: logging.Logger = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that caches function results in blob store (text format).

    Args:
        pathname_fn: Function that converts the input arg to a blob pathname
        logger: Optional logger for debug output

    Supports cache_only kwarg: if True, returns None on cache miss instead of calling function.
    Requires wrapped function to have at least one positional arg (the path/URL).
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def wrapper(path: str, *args: P.args, **kwargs: P.kwargs) -> R:
            cache_only = kwargs.pop("cache_only", False)
            pathname = pathname_fn(path, *args, **kwargs)

            # PHASE 1: Early exit if cache_only and cache unavailable
            blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
            cache_read_available = blob_base_url and cache_mode.can_read()

            if cache_only and not cache_read_available:
                util.log(
                    f"[{fn.__name__}] blob_cached: cache_only=True but cache unavailable: {pathname}",
                    level=logging.WARNING,
                    logger=logger,
                )
                return None

            # PHASE 2: Attempt cache read (cohesive, decoupled)
            if cache_read_available:
                cached_result = _try_read_cache(
                    blob_base_url, pathname, fn.__name__, logger
                )
                if cached_result is not None:
                    return cached_result

                if cache_only:
                    util.log(
                        f"[{fn.__name__}] blob_cached: cache_only=True but cache missed: {pathname}",
                        level=logging.INFO,
                        logger=logger,
                    )
                    return None

            # PHASE 3: Execute function (mandatory at this point)
            result = fn(path, *args, **kwargs)

            # PHASE 4: Attempt cache write (cohesive, decoupled, independent)
            if cache_mode.can_write():
                _try_write_cache(pathname, result, fn.__name__, logger)

            # PHASE 5: Return result
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

            # PHASE 1: Attempt cache read (cohesive, decoupled)
            if blob_base_url and cache_mode.can_read():
                cached_result = _try_read_cache_json(
                    blob_base_url, pathname, fn.__name__, logger
                )
                if cached_result is not None:
                    return cached_result

            # PHASE 2: Execute function (mandatory at this point)
            result = fn(*args, **kwargs)

            # PHASE 3: Attempt cache write (cohesive, decoupled, independent)
            if cache_mode.can_write() and (
                should_cache is None or should_cache(result)
            ):
                _try_write_cache_json(pathname, result, fn.__name__, logger)

            # PHASE 4: Return result
            return result

        return wrapper

    return decorator


def _try_read_cache(
    blob_base_url: str, pathname: str, fn_name: str, logger
) -> str | None:
    blob_url = f"{blob_base_url}/{pathname}"
    try:
        util.log(f"[{fn_name}] Trying cache: {pathname}", logger=logger)
        resp = util.fetch_url_with_fallback(
            blob_url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"},
        )
        resp.raise_for_status()
        util.log(f"[{fn_name}] ✔ Cache hit: {pathname}", logger=logger)
        return resp.content.decode("utf-8").strip()
    except Exception as e:
        util.log(
            f"[{fn_name}] ✘ Cache miss: {pathname} - {repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )
        return None


def _try_write_cache(pathname: str, content: str, fn_name: str, logger) -> None:
    try:
        from blob_store import put_file

        put_file(pathname, content)
        util.log(f"[{fn_name}] ✔ Cached result: {pathname}", logger=logger)
    except Exception as e:
        util.log(
            f"[{fn_name}] ✘ Failed to cache: {pathname} - {repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )


def _try_read_cache_json(
    blob_base_url: str, pathname: str, fn_name: str, logger
) -> Any | None:
    blob_url = f"{blob_base_url}/{pathname}"
    try:
        util.log(f"[{fn_name}] Trying cache: {pathname}", logger=logger)
        resp = util.fetch_url_with_fallback(
            blob_url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"},
        )
        resp.raise_for_status()
        util.log(f"[{fn_name}] ✔ Cache hit: {pathname}", logger=logger)
        return json.loads(resp.content.decode("utf-8"))
    except Exception as e:
        util.log(
            f"[{fn_name}] ✘ Cache miss: {pathname} - {repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )
        return None


def _try_write_cache_json(pathname: str, data: Any, fn_name: str, logger) -> None:
    try:
        from blob_store import put_file

        put_file(pathname, json.dumps(data, indent=2))
        util.log(f"[{fn_name}] ✔ Cached result: {pathname}", logger=logger)
    except Exception as e:
        util.log(
            f"[{fn_name}] ✘ Failed to cache: {pathname} - {repr(e)}",
            level=logging.WARNING,
            logger=logger,
        )
