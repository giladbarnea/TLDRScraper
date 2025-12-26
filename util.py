import functools
import logging
import os
import time
from datetime import timedelta

import requests
from curl_cffi import requests as curl_requests


def resolve_env_var(name: str, default: str = "") -> str:
    """
    Resolve environment variable, trying both direct name and TLDR_SCRAPER_ prefixed version.
    Strips surrounding quotes from the value if present.

    >>> os.environ['TEST_VAR'] = '"value"'
    >>> resolve_env_var('TEST_VAR')
    'value'
    >>> os.environ['TEST_VAR'] = 'value'
    >>> resolve_env_var('TEST_VAR')
    'value'
    """
    value = os.getenv(name) or os.getenv(f"TLDR_SCRAPER_{name}") or default
    return value.strip('"').strip("'") if value else value


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
    """Canonicalize URL for better deduplication.

    Normalizes:
    - Removes scheme (http:// or https://)
    - Removes www. prefix
    - Removes query parameters
    - Removes URL fragments
    - Removes trailing slashes (including root)
    - Lowercases domain
    """
    import urllib.parse as urlparse

    # Handle protocol-less URLs by adding a temporary scheme for parsing
    if not url.startswith(('http://', 'https://', '//')):
        url = f'https://{url}'

    parsed = urlparse.urlparse(url)

    # Normalize netloc: lowercase and remove www. prefix
    netloc = parsed.netloc.lower()
    if netloc.startswith('www.'):
        netloc = netloc[4:]

    # Build canonical URL without scheme (strips query params and fragments)
    path = parsed.path
    canonical = f"{netloc}{path}"

    # Remove trailing slash (including root to normalize example.com/ → example.com)
    if canonical.endswith('/'):
        canonical = canonical[:-1]

    return canonical


def get_domain_name(url) -> str:
    """Extract a friendly domain name from a URL"""
    import urllib.parse as urlparse

    try:
        parsed = urlparse.urlparse(url)
        hostname = parsed.netloc.lower()

        # Remove www. prefix if present
        if hostname.startswith("www."):
            hostname = hostname[4:]

        # Remove port number if present
        hostname = hostname.split(":")[0]

        # Map common domains to friendly names
        domain_map = {
            "google.com": "Google",
            "youtube.com": "YouTube",
            "github.com": "GitHub",
            "stackoverflow.com": "Stack Overflow",
            "reddit.com": "Reddit",
            "twitter.com": "Twitter",
            "x.com": "X",
            "facebook.com": "Facebook",
            "linkedin.com": "LinkedIn",
            "medium.com": "Medium",
            "techcrunch.com": "TechCrunch",
            "theverge.com": "The Verge",
            "arstechnica.com": "Ars Technica",
            "wired.com": "Wired",
            "engadget.com": "Engadget",
            "reuters.com": "Reuters",
            "bloomberg.com": "Bloomberg",
            "nytimes.com": "New York Times",
            "washingtonpost.com": "Washington Post",
            "bbc.com": "BBC",
            "bbc.co.uk": "BBC",
            "cnn.com": "CNN",
            "theguardian.com": "The Guardian",
            "forbes.com": "Forbes",
            "wsj.com": "Wall Street Journal",
            "arxiv.org": "arXiv",
            "nature.com": "Nature",
            "science.org": "Science",
            "openai.com": "OpenAI",
            "anthropic.com": "Anthropic",
            "deepmind.com": "DeepMind",
            "microsoft.com": "Microsoft",
            "apple.com": "Apple",
            "amazon.com": "Amazon",
            "netflix.com": "Netflix",
            "spotify.com": "Spotify",
            "slack.com": "Slack",
            "discord.com": "Discord",
            "notion.so": "Notion",
            "figma.com": "Figma",
            "vercel.com": "Vercel",
            "netlify.com": "Netlify",
        }

        if hostname in domain_map:
            return domain_map[hostname]

        # For unmapped domains, capitalize the main part
        # e.g., "example.com" -> "Example"
        parts = hostname.split(".")
        if len(parts) >= 2:
            # Use the second-to-last part (main domain name)
            main_part = parts[-2]
            return main_part.capitalize()
        elif len(parts) == 1:
            return parts[0].capitalize()

        return hostname.capitalize()

    except Exception:
        return "Unknown"


logger = logging.getLogger(__name__)

RETRIABLE_EXCEPTIONS = (
    requests.Timeout,
    requests.ConnectionError,
    IOError,
)


def retry(max_attempts: int = 2, delay: float = 2.0):
    """
    Retry decorator with fixed delay between attempts.

    >>> attempt_count = 0
    >>> @retry(max_attempts=2, delay=0.01)
    ... def flaky():
    ...     global attempt_count
    ...     attempt_count += 1
    ...     if attempt_count < 2:
    ...         raise IOError("transient")
    ...     return "ok"
    >>> flaky()
    'ok'
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except RETRIABLE_EXCEPTIONS as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"[util.retry] {func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                        )
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


def fetch(
    url: str,
    *,
    timeout: int = 30,
    headers: dict | None = None,
    params: dict | None = None,
    allow_redirects: bool = True,
) -> requests.Response:
    """Fetch URL content using curl_cffi with browser impersonation."""
    default_headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }
    if headers:
        default_headers.update(headers)

    return curl_requests.get(
        url,
        impersonate="chrome131",
        timeout=timeout,
        headers=default_headers,
        params=params,
        allow_redirects=allow_redirects,
    )
