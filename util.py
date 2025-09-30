import collections
import logging
import os
from datetime import timedelta

LOGS = collections.deque(maxlen=200)


def log(msg, *args, **kwargs):
    logger = kwargs.pop("logger", logging.getLogger("tldr-scraper"))
    try:
        LOGS.append(msg)
    except Exception:
        logger.warning("Failed to append to LOGS", exc_info=True)
        pass
    kwargs.setdefault("stacklevel", 2)
    level = kwargs.pop("level", logging.INFO)
    logger.log(level, msg, *args, **kwargs)


def resolve_env_var(name: str, default: str = "") -> str:
    return os.getenv(name) or os.getenv(f"TLDR_SCRAPER_{name}") or default


def get_date_range(start_date, end_date):
    """Generate list of dates between start and end (inclusive)"""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def format_date_for_url(date):
    """Format date as YYYY-MM-DD for TLDR URL"""
    if isinstance(date, str):
        return date
    return date.strftime("%Y-%m-%d")


def canonicalize_url(url) -> str:
    """Canonicalize URL for better deduplication"""
    import urllib.parse as urlparse

    parsed = urlparse.urlparse(url)
    canonical = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path}"
    if canonical.endswith("/") and len(canonical) > 1:
        canonical = canonical[:-1]
    return canonical
