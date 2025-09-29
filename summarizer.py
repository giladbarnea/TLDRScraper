import logging
import requests
import json
from io import BytesIO
from markitdown import MarkItDown

import util
from blob_cache import blob_cached
from blob_store import normalize_url_to_pathname

logger = logging.getLogger("summarizer")
md = MarkItDown()

_PROMPT_CACHE = None


def _url_content_pathname(url: str) -> str:
    """Generate blob pathname for URL content."""
    return normalize_url_to_pathname(url)


def _url_summary_pathname(url: str) -> str:
    """Generate blob pathname for URL summary."""
    base_path = normalize_url_to_pathname(url)
    base = base_path[:-3] if base_path.endswith(".md") else base_path
    return f"{base}-summary.md"


@blob_cached(_url_content_pathname, logger=logger)
def url_to_markdown(url: str) -> str:
    """Fetch URL and convert to markdown."""
    util.log(f"[summarizer.url_to_markdown] Fetching {url}", logger=logger)
    
    response = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; TLDR-Summarizer/1.0)"},
    )
    response.raise_for_status()
    
    stream = BytesIO(response.text.encode("utf-8", errors="ignore"))
    result = md.convert_stream(stream, file_extension=".html")
    
    return result.text_content


@blob_cached(_url_summary_pathname, logger=logger)
def summarize_url(url: str) -> str:
    """Get markdown content from URL and summarize it with LLM."""
    markdown = url_to_markdown(url)
    
    template = _fetch_summarize_prompt()
    prompt = _insert_markdown_into_template(template, markdown)
    summary = _call_llm(prompt)
    
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
    
    token = util.resolve_env_var("GITHUB_API_TOKEN", "")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"
    
    headers = {
        "Accept": "application/vnd.github.v3.raw",
        "User-Agent": "tldr-scraper/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    resp = requests.get(url, headers=headers, timeout=20)
    
    if resp.status_code == 200:
        _PROMPT_CACHE = resp.text
        return _PROMPT_CACHE
    
    if resp.headers.get("Content-Type", "").startswith("application/json"):
        import base64
        data = resp.json()
        if isinstance(data, dict) and "content" in data:
            _PROMPT_CACHE = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
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


def _call_llm(prompt: str) -> str:
    """Call OpenAI API with prompt."""
    api_key = util.resolve_env_var("OPENAI_API_TOKEN", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_TOKEN not set")
    
    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": "gpt-5",
        "input": prompt,
        "reasoning": {"effort": "low"},
        "stream": False,
    }
    
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=600)
    resp.raise_for_status()
    data = resp.json()
    
    if isinstance(data, dict) and "output_text" in data:
        if isinstance(data["output_text"], str):
            return data["output_text"]
        if isinstance(data["output_text"], list):
            return "\n".join([str(x) for x in data["output_text"] if isinstance(x, str)])
    
    outputs = data.get("output") or []
    texts = []
    for item in outputs:
        for c in item.get("content") or []:
            if c.get("type") in ("output_text", "text") and isinstance(c.get("text"), str):
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