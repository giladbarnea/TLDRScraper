import logging
import requests
import json
import re
from io import BytesIO
from markitdown import MarkItDown

import util
import urllib.parse as urlparse
from blob_cache import blob_cached
from blob_store import normalize_url_to_pathname

logger = logging.getLogger("summarizer")
md = MarkItDown()

_PROMPT_CACHE = None

SUMMARY_EFFORT_OPTIONS = ("minimal", "low", "medium", "high")


def normalize_summary_effort(value: str) -> str:
    """Normalize summary effort value to a supported option."""
    if not isinstance(value, str):
        return "low"

    normalized = value.strip().lower()
    if normalized in SUMMARY_EFFORT_OPTIONS:
        return normalized

    return "low"


def _url_content_pathname(url: str, *args, **kwargs) -> str:
    """Generate blob pathname for URL content."""
    return normalize_url_to_pathname(url)


def _url_summary_pathname(url: str, *args, **kwargs) -> str:
    """Generate blob pathname for URL summary."""
    base_path = normalize_url_to_pathname(url)
    base = base_path[:-3] if base_path.endswith(".md") else base_path
    summary_effort = normalize_summary_effort(kwargs.get("summary_effort", "low"))
    suffix = "" if summary_effort == "low" else f"-{summary_effort}"
    return f"{base}-summary{suffix}.md"


def summary_blob_pathname(url: str, summary_effort: str = "low") -> str:
    """Expose summary blob pathname generation for external use."""
    return _url_summary_pathname(url, summary_effort=summary_effort)


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


def _fetch_via_jina_reader(url: str) -> str:
    reader_url = _build_jina_reader_url(url)
    util.log(
        f"[summarizer] Falling back to Jina reader for 403 url={url}",
        logger=logger,
    )
    resp = requests.get(
        reader_url,
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"},
    )
    resp.raise_for_status()
    return resp.text


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

    try:
        response = requests.get(
            raw_url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"},
        )
        response.raise_for_status()
        util.log(
            f"[summarizer._fetch_github_readme] Raw fetch succeeded for {raw_url}",
            logger=logger,
        )
        return response.text
    except requests.HTTPError as e:
        if e.response and e.response.status_code == 404:
            master_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
            util.log(
                f"[summarizer._fetch_github_readme] Main branch not found, trying master: {master_url}",
                logger=logger,
            )
            try:
                response = requests.get(
                    master_url,
                    timeout=30,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"
                    },
                )
                response.raise_for_status()
                util.log(
                    f"[summarizer._fetch_github_readme] Master branch fetch succeeded for {master_url}",
                    logger=logger,
                )
                return response.text
            except Exception:
                pass

    util.log(
        f"[summarizer._fetch_github_readme] Raw README not found, trying direct page fetch from {url}",
        logger=logger,
    )

    try:
        response = util.fetch_url_with_fallback(
            url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"},
            is_scraping=True,
        )
        if response.status_code == 403:
            return _fetch_via_jina_reader(url)
        response.raise_for_status()
    except requests.HTTPError as e:
        if getattr(e, "response", None) is not None and e.response.status_code == 403:
            return _fetch_via_jina_reader(url)
        raise

    stream = BytesIO(response.text.encode("utf-8", errors="ignore"))
    result = md.convert_stream(stream, file_extension=".html")
    content = result.text_content

    util.log(
        f"[summarizer._fetch_github_readme] Direct fetch succeeded for {url}",
        logger=logger,
    )
    return content


@blob_cached(_url_content_pathname, logger=logger)
def url_to_markdown(url: str) -> str:
    """Fetch URL and convert to markdown. For GitHub repos, fetches README.md."""
    util.log(f"[summarizer.url_to_markdown] Fetching {url}", logger=logger)

    if _is_github_repo_url(url):
        return _fetch_github_readme(url)

    try:
        response = util.fetch_url_with_fallback(
            url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Newsletter/1.0)"},
            is_scraping=True,
        )
        if response.status_code == 403:
            # Return reader text directly; it is already markdown-like
            return _fetch_via_jina_reader(url)
        response.raise_for_status()
    except requests.HTTPError as e:
        if getattr(e, "response", None) is not None and e.response.status_code == 403:
            return _fetch_via_jina_reader(url)
        raise

    stream = BytesIO(response.text.encode("utf-8", errors="ignore"))
    result = md.convert_stream(stream, file_extension=".html")

    return result.text_content


@blob_cached(_url_summary_pathname, logger=logger)
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

    resp = requests.get(url, headers=headers, timeout=20)

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

    raise RuntimeError(f"Failed to fetch summarize.md: {resp.status_code}")


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

    return json.dumps(data)
