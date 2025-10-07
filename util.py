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


def fetch_url_with_fallback(url, timeout=30, headers=None, allow_redirects=True):
    """
    Fetch URL with 401/403 fallback using curl_cffi.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        headers: Optional headers dict
        allow_redirects: Whether to follow redirects
        
    Returns:
        requests.Response object or curl_cffi Response object
        
    Raises:
        requests.RequestException or curl_cffi.RequestError if both methods fail
    """
    import requests
    from curl_cffi import requests as cfre
    
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"}
    
    # First attempt with regular requests
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers=headers,
            allow_redirects=allow_redirects,
        )
        
        # Use fallback for 401/403 or "forbidden" reason
        if response.status_code in [401, 403] or "forbidden" in getattr(response, "reason", "").lower():
            log(
                f"[util.fetch_url_with_fallback] Got {response.status_code} for {url}, trying curl_cffi fallback",
                level=logging.WARNING,
            )
            
            # Use curl_cffi with Chrome impersonation
            fallback_response = cfre.get(
                url,
                impersonate="chrome131",
                timeout=timeout,
                allow_redirects=allow_redirects,
                headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.google.com/",
                    **headers,
                },
            )
            
            log(
                f"[util.fetch_url_with_fallback] curl_cffi fallback successful for {url}",
                level=logging.INFO,
            )
            
            return fallback_response
        else:
            return response
            
    except requests.RequestException as e:
        log(
            f"[util.fetch_url_with_fallback] requests failed for {url}: {e}, trying curl_cffi fallback",
            level=logging.WARNING,
        )
        
        # If requests fails entirely, try curl_cffi as fallback
        try:
            fallback_response = cfre.get(
                url,
                impersonate="chrome131",
                timeout=timeout,
                allow_redirects=allow_redirects,
                headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.google.com/",
                    **headers,
                },
            )
            
            log(
                f"[util.fetch_url_with_fallback] curl_cffi fallback successful for {url}",
                level=logging.INFO,
            )
            
            return fallback_response
            
        except Exception as fallback_error:
            log(
                f"[util.fetch_url_with_fallback] Both requests and curl_cffi failed for {url}: requests={e}, curl_cffi={fallback_error}",
                level=logging.ERROR,
            )
            raise e  # Re-raise the original requests error
