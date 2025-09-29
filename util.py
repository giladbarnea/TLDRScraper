import collections
import logging
import os

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
