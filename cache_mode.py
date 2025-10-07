"""
Cache mode management module.

Provides a simple, thread-safe, and web-server-instance-safe way to manage
cache behavior across the entire application.

Cache modes:
- DISABLED: No caching (no reads, no writes)
- READ_ONLY: Only read from cache, never write
- WRITE_ONLY: Never read from cache, always write to cache
- READ_WRITE: Normal caching (read on miss, write on cache miss)
"""

import logging
import threading
from enum import Enum
from typing import Optional
from blob_store import put_file
import util
import requests

logger = logging.getLogger("cache_mode")


class CacheMode(Enum):
    """Cache operation modes."""

    DISABLED = "disabled"
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    READ_WRITE = "read_write"


# Thread-local lock for thread safety
_lock = threading.RLock()

# In-memory cache for current mode (reduces blob reads)
_cached_mode: Optional[CacheMode] = None

# Blob storage pathname for cache mode
CACHE_MODE_PATHNAME = "cache-mode.txt"


def get_cache_mode() -> CacheMode:
    """
    Get the current cache mode.

    Thread-safe and web-server-instance-safe via blob storage.
    Returns READ_WRITE as default if not set.
    """
    global _cached_mode

    if util.resolve_env_var("FORCE_CACHE_MODE", "").strip():
        return CacheMode(util.resolve_env_var("FORCE_CACHE_MODE", "").strip())

    with _lock:
        # First check in-memory cache
        if _cached_mode is not None:
            return _cached_mode

        # Try to read from blob storage
        blob_base_url = util.resolve_env_var("BLOB_STORE_BASE_URL", "").strip()
        if blob_base_url:
            blob_url = f"{blob_base_url}/{CACHE_MODE_PATHNAME}"
            try:
                util.log(
                    "[cache_mode.get_cache_mode] Reading mode from blob storage",
                    logger=logger,
                )
                resp = requests.get(
                    blob_url,
                    timeout=10,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"
                    },
                )
                resp.raise_for_status()
                mode_str = resp.content.decode("utf-8").strip()

                try:
                    mode = CacheMode(mode_str)
                    _cached_mode = mode
                    util.log(
                        f"[cache_mode.get_cache_mode] Loaded mode from blob: {mode.value}",
                        logger=logger,
                    )
                    return mode
                except ValueError:
                    util.log(
                        f"[cache_mode.get_cache_mode] Invalid mode in blob: {mode_str}, using default",
                        level=logging.WARNING,
                        logger=logger,
                    )
            except Exception as e:
                util.log(
                    f"[cache_mode.get_cache_mode] Failed to read mode from blob: {repr(e)}",
                    level=logging.WARNING,
                    logger=logger,
                )

        # Default to READ_WRITE
        _cached_mode = CacheMode.READ_WRITE
        return _cached_mode


def set_cache_mode(mode: CacheMode) -> bool:
    """
    Set the cache mode.

    Thread-safe and web-server-instance-safe via blob storage.
    Returns True on success, False on failure.
    """
    global _cached_mode

    if not isinstance(mode, CacheMode):
        raise ValueError(f"Invalid cache mode: {mode}")

    with _lock:
        try:
            # Write to blob storage first
            put_file(CACHE_MODE_PATHNAME, mode.value)

            # Update in-memory cache
            _cached_mode = mode

            util.log(
                f"[cache_mode.set_cache_mode] Set mode to: {mode.value}",
                logger=logger,
            )
            return True
        except Exception as e:
            util.log(
                f"[cache_mode.set_cache_mode] Failed to set mode: {repr(e)}",
                level=logging.ERROR,
                exc_info=True,
                logger=logger,
            )
            return False


def invalidate_mode_cache():
    """
    Invalidate the in-memory cache mode, forcing a reload on next get.

    Useful when the mode might have been changed by another instance.
    """
    global _cached_mode
    with _lock:
        _cached_mode = None
        util.log(
            "[cache_mode.invalidate_mode_cache] Invalidated in-memory mode cache",
            logger=logger,
        )


def can_read() -> bool:
    """Check if cache reads are allowed in current mode."""
    mode = get_cache_mode()
    return mode in (CacheMode.READ_ONLY, CacheMode.READ_WRITE)


def can_write() -> bool:
    """Check if cache writes are allowed in current mode."""
    mode = get_cache_mode()
    return mode in (CacheMode.WRITE_ONLY, CacheMode.READ_WRITE)
