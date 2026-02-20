import logging
import json
import re
import hashlib
from requests.models import Response
from typing import Optional

import requests
from curl_cffi import requests as curl_requests
import html2text

import util
import urllib.parse as urlparse

logger = logging.getLogger("summarizer")

# Configure html2text for optimal conversion
h = html2text.HTML2Text()
h.body_width = 0  # Don't wrap lines
h.unicode_snob = True  # Use unicode instead of ASCII approximations
h.ignore_images = True  # Skip images, we only need text
h.protect_links = True  # Don't wrap URLs
h.single_line_break = True  # Use single line breaks

_SUMMARY_PROMPT_CACHE = None
_DIGEST_PROMPT_CACHE = None

SUMMARIZE_EFFORT_OPTIONS = ("minimal", "low", "medium", "high")
DEFAULT_SUMMARY_EFFORT = "low"
DEFAULT_MODEL = "gemini-3-pro-preview"


def normalize_summarize_effort(value: str) -> str:
    """Normalize summary effort value to a supported option."""
    if not isinstance(value, str):
        return DEFAULT_SUMMARY_EFFORT

    normalized = value.strip().lower()
    if normalized in SUMMARIZE_EFFORT_OPTIONS:
        return normalized

    return DEFAULT_SUMMARY_EFFORT


def _is_github_repo_url(url: str) -> bool:
    """Check if URL is a GitHub repository URL."""
    pattern = r"^https?://(?:www\.)?github\.com/([^/]+)/([^/?#]+)/?(?:\?.*)?(?:#.*)?$"
    return bool(re.match(pattern, url))


def _build_jina_reader_url(url: str) -> str:
    """Build r.jina.ai reader URL for a target page.

    >>> _build_jina_reader_url('https://openai.com/index/introducing-agentkit')
    'https://r.jina.ai/http://openai.com/index/introducing-agentkit'
    >>> _build_jina_reader_url('https://example.com/path?x=1')
    'https://r.jina.ai/http://example.com/path?x=1'
    """
    parsed = urlparse.urlparse(url)
    # Use http scheme within the reader path; it will follow redirects as needed
    target = f"http://{parsed.netloc}{parsed.path}"
    if parsed.query:
        target += f"?{parsed.query}"
    return f"https://r.jina.ai/{target}"


def _scrape_with_curl_cffi(
    url: str, *, timeout: int = 10, allow_redirects: bool = True
) -> requests.Response:
    response = curl_requests.get(
        url,
        impersonate="chrome131",
        timeout=timeout,
        allow_redirects=allow_redirects,
        headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
        },
    )
    response.raise_for_status()

    def response_iter_content_stub(self, *args, **kwargs):
        return [response.content]

    response.__class__.iter_content = response_iter_content_stub
    return response


def _scrape_with_jina_reader(url: str, *, timeout: int) -> requests.Response:
    reader_url = _build_jina_reader_url(url)
    logger.info(
        f"Scraping with Jina reader url={url}",
    )
    response = requests.get(
        reader_url,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"},
    )
    response.raise_for_status()
    text = response.text
    if re.search(r"error \d+", text, flags=re.IGNORECASE):
        raise requests.HTTPError(
            "Jina reader returned an error page", response=response
        )

    return response


def _scrape_with_firecrawl(url: str, *, timeout: int) -> requests.Response:
    api_key = util.resolve_env_var("FIRECRAWL_API_KEY", "")
    if not api_key:
        raise RuntimeError("FIRECRAWL_API_KEY not configured")

    logger.info(
        f"Scraping with Firecrawl url={url}",
    )

    response = requests.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "url": url,
            "formats": ["markdown", "html"],
        },
        timeout=timeout,
    )
    response.raise_for_status()

    data = response.json()
    if not data.get("success"):
        raise requests.HTTPError("Firecrawl scraping failed", response=response)

    html_content = data.get("data", {}).get("html", "")
    if not html_content:
        raise RuntimeError("Firecrawl returned empty content")

    # Create a mock Response object with the HTML content
    # (html2text will convert it to markdown)
    from io import BytesIO
    from urllib3.response import HTTPResponse

    mock_response = requests.Response()
    mock_response.status_code = 200
    mock_response._content = html_content.encode("utf-8")
    mock_response.headers["Content-Type"] = "text/html"

    # Create a proper raw response for iter_content to work
    raw = HTTPResponse(
        body=BytesIO(html_content.encode("utf-8")),
        headers={"Content-Type": "text/html"},
        status=200,
        preload_content=False,
    )
    mock_response.raw = raw

    return mock_response


@util.retry()
def scrape_url(url: str, *, timeout: int = 10) -> Response:
    scraping_methods = [
        ("curl_cffi", _scrape_with_curl_cffi),
        ("jina_reader", _scrape_with_jina_reader),
    ]

    # Add Firecrawl as fallback if API key is configured
    firecrawl_api_key = util.resolve_env_var("FIRECRAWL_API_KEY", "")
    if firecrawl_api_key:
        scraping_methods.append(("firecrawl", _scrape_with_firecrawl))

    last_status_error: Optional[requests.HTTPError] = None
    errors = []

    for name, scrape in scraping_methods:
        try:
            # Use extended timeout for Firecrawl since it does full browser rendering
            method_timeout = 60 if name == "firecrawl" else timeout
            result = scrape(url, timeout=method_timeout)
            # Only log intermediate failures if all methods fail
            if errors:
                logger.info(
                    f"{name} succeeded after {len(errors)} failed attempts for url={url}",
                )
            return result
        except requests.HTTPError as status_error:
            last_status_error = status_error
            errors.append(f"{name}: {status_error}")
            continue
        except Exception as e:
            errors.append(f"{name}: {e}")
            continue

    # Only log errors if all methods failed
    if errors:
        logger.error(
            f"All methods failed for url={url}. Errors: {'; '.join(errors)}",
        )

    if last_status_error is not None:
        raise last_status_error

    raise RuntimeError(f"Failed to scrape {url}")


def _fetch_github_readme(url: str) -> str:
    """Fetch README.md content from a GitHub repository URL."""
    match = re.match(
        r"^https?://(?:www\.)?github\.com/([^/]+)/([^/?#]+)/?(?:\?.*)?(?:#.*)?$", url
    )
    if not match:
        raise ValueError(f"Invalid GitHub repo URL: {url}")

    owner, repo = match.groups()

    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
    logger.info(
        f"Trying raw fetch from {raw_url}",
    )
    github_api_token = util.resolve_env_var("GITHUB_API_TOKEN", "")
    auth_headers = {
        "Authorization": f"token {github_api_token}",
        "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)",
    }

    try:
        response = requests.get(
            raw_url,
            timeout=10,
            headers=auth_headers,
        )
        response.raise_for_status()
        logger.info(
            f"Raw fetch succeeded for {raw_url}",
        )
        return h.handle(response.text)
    except requests.HTTPError as e:
        if e.response and e.response.status_code == 404:
            master_url = (
                f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
            )
            logger.info(
                f"Main branch not found, trying master: {master_url}",
            )
            try:
                response = requests.get(
                    master_url,
                    timeout=10,
                    headers=auth_headers,
                )
                response.raise_for_status()
                logger.info(
                    f"Master branch fetch succeeded for {master_url}",
                )
                return h.handle(response.text)
            except Exception:
                logger.warning(
                    f"Master branch fetch failed for {master_url}",
                )
                raise

    response = scrape_url(url)
    content = h.handle(response.text)

    logger.info(
        f"Direct fetch succeeded for {url}",
    )
    return content


def url_to_markdown(url: str) -> str:
    """Fetch URL and convert to markdown. For GitHub repos, fetches README.md."""
    logger.info(
        f"Fetching and converting to markdown {url}",
    )

    if _is_github_repo_url(url):
        return _fetch_github_readme(url)

    response = scrape_url(url)
    markdown = h.handle(response.text)

    return markdown


def summarize_url(url: str, summarize_effort: str = DEFAULT_SUMMARY_EFFORT, model: str = DEFAULT_MODEL) -> str:
    """Get markdown content from URL and create a summary with LLM.

    Args:
        url: The URL to summarize
        summarize_effort: Reasoning effort level (minimal, low, medium, high)
        model: Gemini model to use

    Returns:
        The summary markdown
    """
    effort = normalize_summarize_effort(summarize_effort)
    markdown = url_to_markdown(url)

    template = _fetch_summary_prompt()
    prompt = f"{template}\n\n<tldr this>\n{markdown}/n</tldr this>"
    summary = _call_llm(prompt, summarize_effort=effort, model=model)

    return summary


def truncate_markdown(markdown: str, max_words: int = 35000) -> str:
    """Truncate markdown to a max number of words.

    >>> truncate_markdown("a b c", max_words=2)
    'a b'
    """
    words = markdown.split()
    if len(words) <= max_words:
        return markdown
    return " ".join(words[:max_words])


def generate_digest_id(canonical_urls: list[str], summarize_effort: str) -> str:
    """Generate a stable digest id from canonical URLs and effort.

    >>> generate_digest_id(["https://a.com", "https://b.com"], "low") == generate_digest_id(["https://b.com", "https://a.com"], "low")
    True
    """
    normalized_effort = normalize_summarize_effort(summarize_effort)
    canonical_list = sorted(canonical_urls)
    digest_source = "\n".join(canonical_list + [normalized_effort])
    return hashlib.sha256(digest_source.encode("utf-8")).hexdigest()


def _build_digest_prompt(articles_with_markdown: list[dict], template: str) -> str:
    sections = []
    for article in articles_with_markdown:
        sections.append(
            "\n".join(
                [
                    f"<article url=\"{article['url']}\" title=\"{article['title']}\" category=\"{article['category']}\">",
                    article["markdown"],
                    "</article>",
                ]
            )
        )
    sections_text = "\n\n".join(sections)
    return f"{template}\n\n<articles>\n{sections_text}\n</articles>"


def summarize_articles(articles_with_markdown: list[dict], summarize_effort: str = DEFAULT_SUMMARY_EFFORT, model: str = DEFAULT_MODEL) -> str:
    normalized_effort = normalize_summarize_effort(summarize_effort)
    template = _fetch_digest_prompt()
    prompt = _build_digest_prompt(articles_with_markdown, template)
    return _call_llm(prompt, summarize_effort=normalized_effort, model=model)


def _fetch_prompt(
    *,
    owner: str,
    repo: str,
    path: str,
    ref: str,
    cache_attr: str,
) -> str:
    cache_value = globals().get(cache_attr)
    if cache_value:
        return cache_value

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"

    headers = {
        "Accept": "application/vnd.github.v3.raw",
        "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)",
    }

    token = util.resolve_env_var("GITHUB_API_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 200:
        globals()[cache_attr] = response.text
        return response.text

    if response.headers.get("Content-Type", "").startswith("application/json"):
        import base64

        data = response.json()
        if isinstance(data, dict) and "content" in data:
            decoded = base64.b64decode(data["content"]).decode(
                "utf-8", errors="replace"
            )
            globals()[cache_attr] = decoded
            return decoded

    if token and response.status_code == 401:
        headers_no_auth = {
            "Accept": "application/vnd.github.v3.raw",
            "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)",
        }
        response_no_auth = requests.get(url, headers=headers_no_auth, timeout=10)
        if response_no_auth.status_code == 200:
            globals()[cache_attr] = response_no_auth.text
            return response_no_auth.text

    raise RuntimeError(f"Failed to fetch {path}: {response.status_code}")


def _fetch_summary_prompt(
    owner: str = "giladbarnea",
    repo: str = "llm-templates",
    path: str = "text/tldr.md",
    ref: str = "main",
) -> str:
    """Fetch summary prompt from GitHub (cached in memory)."""
    return _fetch_prompt(
        owner=owner,
        repo=repo,
        path=path,
        ref=ref,
        cache_attr="_SUMMARY_PROMPT_CACHE",
    )


def _fetch_digest_prompt(
    owner: str = "giladbarnea",
    repo: str = "llm-templates",
    path: str = "text/digest.md",
    ref: str = "main",
) -> str:
    """Fetch digest prompt from GitHub (cached in memory)."""
    return _fetch_prompt(
        owner=owner,
        repo=repo,
        path=path,
        ref=ref,
        cache_attr="_DIGEST_PROMPT_CACHE",
    )


def _map_reasoning_effort_to_thinking_level(summarize_effort: str) -> str:
    """Map OpenAI reasoning effort levels to Gemini thinking_level.

    >>> _map_reasoning_effort_to_thinking_level("minimal")
    'low'
    >>> _map_reasoning_effort_to_thinking_level("low")
    'low'
    >>> _map_reasoning_effort_to_thinking_level("medium")
    'high'
    >>> _map_reasoning_effort_to_thinking_level("high")
    'high'
    """
    effort = normalize_summarize_effort(summarize_effort)
    if effort in ("minimal", "low"):
        return "low"
    return "high"


def _call_llm(prompt: str, summarize_effort: str = DEFAULT_SUMMARY_EFFORT, model: str = DEFAULT_MODEL) -> str:
    """Call Gemini API with prompt."""
    api_key = util.resolve_env_var("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    if not prompt.strip():
        raise ValueError("Prompt is empty")

    thinking_level = _map_reasoning_effort_to_thinking_level(summarize_effort)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }
    body = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "thinkingConfig": {
                "thinkingLevel": thinking_level
            }
        }
    }

    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=600)
    resp.raise_for_status()
    data = resp.json()

    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"No candidates in Gemini response: {data}")

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []

    texts = []
    for part in parts:
        text = part.get("text")
        if isinstance(text, str):
            texts.append(text)

    if texts:
        return "\n".join(texts)

    raise RuntimeError(f"No text found in Gemini response: {data}")
