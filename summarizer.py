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
import blob_cache
import blob_store

logger = logging.getLogger("summarizer")
md = MarkItDown()

_PROMPT_CACHE = None
_TLDR_PROMPT_CACHE = None

SUMMARY_EFFORT_OPTIONS = ("minimal", "low", "medium", "high")


def _url_content_pathname(url: str, *args, **kwargs) -> str:
    """Generate blob pathname for URL content."""
    return blob_store.normalize_url_to_pathname(url)


def _url_summary_pathname(url: str, *args, **kwargs) -> str:
    """Generate blob pathname for URL summary."""
    base_path = blob_store.normalize_url_to_pathname(url)
    base = base_path[:-3] if base_path.endswith(".md") else base_path
    summary_effort = normalize_summary_effort(kwargs.get("summary_effort", "low"))
    suffix = "" if summary_effort == "low" else f"-{summary_effort}"
    return f"{base}-summary{suffix}.md"


def _url_tldr_pathname(url: str, *args, **kwargs) -> str:
    """Generate blob pathname for URL TLDR."""
    base_path = blob_store.normalize_url_to_pathname(url)
    base = base_path[:-3] if base_path.endswith(".md") else base_path
    summary_effort = normalize_summary_effort(kwargs.get("summary_effort", "low"))
    suffix = "" if summary_effort == "low" else f"-{summary_effort}"
    return f"{base}-tldr{suffix}.md"


def normalize_summary_effort(value: str) -> str:
    """Normalize summary effort value to a supported option."""
    if not isinstance(value, str):
        return "low"

    normalized = value.strip().lower()
    if normalized in SUMMARY_EFFORT_OPTIONS:
        return normalized

    return "low"


def summary_blob_pathname(url: str, *args, **kwargs) -> str:
    """Generate blob pathname for URL summary."""
    base_path = blob_store.normalize_url_to_pathname(url)
    base = base_path[:-3] if base_path.endswith(".md") else base_path
    summary_effort = normalize_summary_effort(kwargs.get("summary_effort", "low"))
    suffix = "" if summary_effort == "low" else f"-{summary_effort}"
    return f"{base}-summary{suffix}.md"


def tldr_blob_pathname(url: str, *args, **kwargs) -> str:
    """Generate blob pathname for URL TLDR."""
    base_path = blob_store.normalize_url_to_pathname(url)
    base = base_path[:-3] if base_path.endswith(".md") else base_path
    summary_effort = normalize_summary_effort(kwargs.get("summary_effort", "low"))
    suffix = "" if summary_effort == "low" else f"-{summary_effort}"
    return f"{base}-tldr{suffix}.md"


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


def scrape_url(url: str, *, timeout: int = 10) -> Response:
    scraping_methods: tuple[tuple[str, Callable[..., Response]], ...] = (
        ("curl_cffi", _scrape_with_curl_cffi),
        ("jina_reader", _scrape_with_jina_reader),
    )

    last_status_error: Optional[requests.HTTPError] = None
    errors = []

    for name, scrape in scraping_methods:
        try:
            result = scrape(url, timeout=timeout)
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


@blob_cache.blob_cached(_url_content_pathname, logger=logger)
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


@blob_cache.blob_cached(_url_summary_pathname, logger=logger)
def summarize_url(url: str, summary_effort: str = "low") -> str:
    """Get markdown content from URL and summarize it with LLM.

    Args:
        url: The URL to summarize
        summary_effort: OpenAI reasoning effort level

    Returns:
        The summary markdown
    """
    effort = normalize_summary_effort(summary_effort)
    markdown = url_to_markdown(url)

    template = _fetch_summarize_prompt()
    prompt = _insert_markdown_into_template(template, markdown)
    summary = _call_llm(prompt, summary_effort=effort)

    return summary


@blob_cache.blob_cached(_url_tldr_pathname, logger=logger)
def tldr_url(url: str, summary_effort: str = "low") -> str:
    """Get markdown content from URL and create a TLDR with LLM.

    Args:
        url: The URL to TLDR
        summary_effort: OpenAI reasoning effort level

    Returns:
        The TLDR markdown
    """
    effort = normalize_summary_effort(summary_effort)
    markdown = url_to_markdown(url)

    template = _fetch_tldr_prompt()
    prompt = f"{template}\n\n{markdown}"
    tldr = _call_llm(prompt, summary_effort=effort)

    return tldr


def _fetch_summarize_prompt(
    owner: str = "giladbarnea",
    repo: str = "llm-templates",
    path: str = "text/summarize.md",
    ref: str = "main",
) -> str:
    """Fetch summarize prompt from GitHub (cached in memory)."""
    global _PROMPT_CACHE
    if _PROMPT_CACHE:
        return _PROMPT_CACHE

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"

    headers = {
        "Accept": "application/vnd.github.v3.raw",
        "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)",
    }

    token = util.resolve_env_var("GITHUB_API_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"

    resp = requests.get(url, headers=headers, timeout=10)

    if resp.status_code == 200:
        _PROMPT_CACHE = resp.text
        return _PROMPT_CACHE

    if resp.headers.get("Content-Type", "").startswith("application/json"):
        import base64

        data = resp.json()
        if isinstance(data, dict) and "content" in data:
            _PROMPT_CACHE = base64.b64decode(data["content"]).decode(
                "utf-8", errors="replace"
            )
            return _PROMPT_CACHE

    # If authenticated request failed, try without authentication
    if token and resp.status_code == 401:
        headers_no_auth = {
            "Accept": "application/vnd.github.v3.raw",
            "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)",
        }
        resp_no_auth = requests.get(url, headers=headers_no_auth, timeout=10)
        if resp_no_auth.status_code == 200:
            _PROMPT_CACHE = resp_no_auth.text
            return _PROMPT_CACHE

    raise RuntimeError(f"Failed to fetch summarize.md: {resp.status_code}")


def _fetch_tldr_prompt(
    owner: str = "giladbarnea",
    repo: str = "llm-templates",
    path: str = "text/tldr.md",
    ref: str = "main",
) -> str:
    """Fetch TLDR prompt from GitHub (cached in memory)."""
    global _TLDR_PROMPT_CACHE
    if _TLDR_PROMPT_CACHE:
        return _TLDR_PROMPT_CACHE

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"

    headers = {
        "Accept": "application/vnd.github.v3.raw",
        "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)",
    }

    token = util.resolve_env_var("GITHUB_API_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"

    resp = requests.get(url, headers=headers, timeout=10)

    if resp.status_code == 200:
        _TLDR_PROMPT_CACHE = resp.text
        return _TLDR_PROMPT_CACHE

    if resp.headers.get("Content-Type", "").startswith("application/json"):
        import base64

        data = resp.json()
        if isinstance(data, dict) and "content" in data:
            _TLDR_PROMPT_CACHE = base64.b64decode(data["content"]).decode(
                "utf-8", errors="replace"
            )
            return _TLDR_PROMPT_CACHE

    if token and resp.status_code == 401:
        headers_no_auth = {
            "Accept": "application/vnd.github.v3.raw",
            "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)",
        }
        resp_no_auth = requests.get(url, headers=headers_no_auth, timeout=10)
        if resp_no_auth.status_code == 200:
            _TLDR_PROMPT_CACHE = resp_no_auth.text
            return _TLDR_PROMPT_CACHE

    raise RuntimeError(f"Failed to fetch tldr.md: {resp.status_code}")


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


def _call_llm(prompt: str, summary_effort: str = "low") -> str:
    """Call OpenAI API with prompt."""
    api_key = util.resolve_env_var("OPENAI_API_TOKEN", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_TOKEN not set")
    if not prompt.strip():
        raise ValueError("Prompt is empty")

    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": "gpt-5",
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
