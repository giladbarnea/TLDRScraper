import logging
import json
import re
from requests.models import Response
from typing import Callable, Optional

import requests
from curl_cffi import requests as curl_requests
from markitdown import MarkItDown

import util
import urllib.parse as urlparse

logger = logging.getLogger("summarizer")
md = MarkItDown()

_TLDR_PROMPT_CACHE = None

SUMMARY_EFFORT_OPTIONS = ("minimal", "low", "medium", "high")
DEFAULT_TLDR_REASONING_EFFORT = "low"
DEFAULT_MODEL = "gpt-5"


def normalize_summary_effort(value: str) -> str:
    """Normalize summary effort value to a supported option."""
    if not isinstance(value, str):
        return DEFAULT_TLDR_REASONING_EFFORT

    normalized = value.strip().lower()
    if normalized in SUMMARY_EFFORT_OPTIONS:
        return normalized

    return DEFAULT_TLDR_REASONING_EFFORT


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
    util.log(
        f"[summarizer.scrape_url] Scraping with Jina reader url={url}",
        logger=logger,
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

    util.log(
        f"[summarizer.scrape_url] Scraping with Firecrawl url={url}",
        logger=logger,
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
    # (MarkItDown will convert it to markdown)
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
                util.log(
                    f"[summarizer.scrape_url] {name} succeeded after {len(errors)} failed attempts for url={url}",
                    logger=logger,
                    level=logging.INFO,
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
        util.log(
            f"[summarizer.scrape_url] All methods failed for url={url}. Errors: {'; '.join(errors)}",
            logger=logger,
            level=logging.ERROR,
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
    util.log(
        f"[summarizer._fetch_github_readme] Trying raw fetch from {raw_url}",
        logger=logger,
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
        util.log(
            f"[summarizer._fetch_github_readme] Raw fetch succeeded for {raw_url}",
            logger=logger,
        )
        return md.convert_response(response).markdown
    except requests.HTTPError as e:
        if e.response and e.response.status_code == 404:
            master_url = (
                f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
            )
            util.log(
                f"[summarizer._fetch_github_readme] Main branch not found, trying master: {master_url}",
                logger=logger,
            )
            try:
                response = requests.get(
                    master_url,
                    timeout=10,
                    headers=auth_headers,
                )
                response.raise_for_status()
                util.log(
                    f"[summarizer._fetch_github_readme] Master branch fetch succeeded for {master_url}",
                    logger=logger,
                )
                return md.convert_response(response).markdown
            except Exception:
                util.log(
                    f"[summarizer._fetch_github_readme] Master branch fetch failed for {master_url}",
                    logger=logger,
                    level=logging.WARNING,
                )
                raise

    response = scrape_url(url)
    result = md.convert_response(response)
    content = result.markdown

    util.log(
        f"[summarizer._fetch_github_readme] Direct fetch succeeded for {url}",
        logger=logger,
    )
    return content


def url_to_markdown(url: str) -> str:
    """Fetch URL and convert to markdown. For GitHub repos, fetches README.md."""
    util.log(
        f"[summarizer.url_to_markdown] Fetching and converting to markdown {url}",
        logger=logger,
    )

    if _is_github_repo_url(url):
        return _fetch_github_readme(url)

    response = scrape_url(url)
    markdown = md.convert_response(response).markdown

    return markdown


def tldr_url(url: str, summary_effort: str = DEFAULT_TLDR_REASONING_EFFORT, model: str = DEFAULT_MODEL) -> str:
    """Get markdown content from URL and create a TLDR with LLM.

    Args:
        url: The URL to TLDR
        summary_effort: OpenAI reasoning effort level
        model: OpenAI model to use

    Returns:
        The TLDR markdown
    """
    effort = normalize_summary_effort(summary_effort)
    markdown = url_to_markdown(url)

    template = _fetch_tldr_prompt()
    prompt = f"{template}\n\n<tldr this>\n{markdown}/n</tldr this>"
    tldr = _call_llm(prompt, summary_effort=effort, model=model)

    return tldr


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


def _fetch_tldr_prompt(
    owner: str = "giladbarnea",
    repo: str = "llm-templates",
    path: str = "text/tldr.md",
    ref: str = "main",
) -> str:
    """Fetch TLDR prompt from GitHub (cached in memory)."""
    return _fetch_prompt(
        owner=owner,
        repo=repo,
        path=path,
        ref=ref,
        cache_attr="_TLDR_PROMPT_CACHE",
    )


def _insert_markdown_into_template(template: str, markdown: str) -> str:
    """Insert markdown between <summarize this> tags."""
    if not template:
        return f"<summarize this>\n{markdown}\n</summarize this>"

    open_tag = "<summarize this>"
    close_tag = "</summarize this>"

    open_idx = template.find(open_tag)
    if open_idx == -1:
        util.log(
            "[summarizer] No <summarize this> tag found, appending markdown",
            level=logging.WARNING,
            logger=logger,
        )
        return f"{template.rstrip()}\n\n{open_tag}\n{markdown}\n{close_tag}\n"

    close_idx = template.find(close_tag, open_idx)
    return template[:open_idx] + markdown + template[close_idx + len(close_tag) :]


def _call_llm(prompt: str, summary_effort: str = DEFAULT_TLDR_REASONING_EFFORT, model: str = DEFAULT_MODEL) -> str:
    """Call OpenAI API with prompt."""
    api_key = util.resolve_env_var("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    if not prompt.strip():
        raise ValueError("Prompt is empty")

    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "input": prompt,
        "reasoning": {"effort": normalize_summary_effort(summary_effort)},
        "stream": False,
    }

    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=600)
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, dict) and "output_text" in data:
        if isinstance(data["output_text"], str):
            return data["output_text"]
        if isinstance(data["output_text"], list):
            return "\n".join([
                str(x) for x in data["output_text"] if isinstance(x, str)
            ])

    outputs = data.get("output") or []
    texts = []
    for item in outputs:
        for c in item.get("content") or []:
            if c.get("type") in ("output_text", "text") and isinstance(
                c.get("text"), str
            ):
                texts.append(c["text"])
    if texts:
        return "\n".join(texts)

    choices = data.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, str):
            return content
    assert data, "No LLM output found"
    return json.dumps(data)
