import os
import re
import hashlib
import subprocess
import tempfile
import urllib.parse


def _default_prefix() -> str:
    return os.getenv("BLOB_STORE_PREFIX",
           os.getenv("TLDR_SCRAPER_BLOB_STORE_PREFIX", "tldr-scraper-blob")).strip("/")


def normalize_url_to_pathname(url: str, prefix: str | None = None) -> str:
    """
    Deterministically convert a canonical URL into a Blob pathname:

    - lower-case
    - strip scheme and fragment
    - keep host + path
    - percent-decode path
    - replace any non-alphanumeric with a single '-'
    - collapse repeats; trim leading/trailing '-'
    - ensure '.md' suffix
    - prepend prefix directory
    - truncate overly long names and add a short hash
    """
    u = urllib.parse.urlsplit(url)
    host = (u.netloc or "").lower()
    path = urllib.parse.unquote(u.path or "/").lower()

    # Preserve dots in host, hyphenate other non-alphanumerics
    host_clean = re.sub(r"[^a-z0-9.]+", "-", host)
    # For path, replace any non-alphanumeric with '-'
    path_clean = re.sub(r"[^a-z0-9]+", "-", path)
    # Collapse repeated hyphens
    host_clean = re.sub(r"-{2,}", "-", host_clean).strip("-")
    path_clean = re.sub(r"-{2,}", "-", path_clean).strip("-")

    s = f"{host_clean}{('-' + path_clean) if path_clean else ''}"
    if not s:
        s = "root"

    if not s:
        s = "root"

    # Length guard: keep pathnames sane; append a short hash if truncated
    MAX = 180
    if len(s) > MAX:
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
        s = f"{s[:MAX-11]}-{h}"

    base = f"{s}.md"
    pfx = (prefix if isinstance(prefix, str) else _default_prefix()).strip("/")
    return f"{pfx}/{base}" if pfx else base


def _resolve_rw_token() -> str:
    return (os.getenv("BLOB_READ_WRITE_TOKEN")
         or os.getenv("TLDR_SCRAPER_BLOB_READ_WRITE_TOKEN")
         or "")


def _resolve_store_id() -> str | None:
    return (os.getenv("BLOB_STORE_ID")
         or os.getenv("TLDR_SCRAPER_BLOB_STORE_ID")
         or None)


def put_markdown(pathname: str, markdown: str) -> str:
    """
    Upload `markdown` to Vercel Blob at the exact `pathname`, overwriting if it exists.
    Returns the public URL if it can be determined (using BLOB_STORE_ID or CLI output).
    Raises RuntimeError on upload failure.
    """
    token = _resolve_rw_token()
    if not token:
        raise RuntimeError("BLOB_READ_WRITE_TOKEN not set")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as f:
        f.write(markdown.encode("utf-8"))
        tmp = f.name

    try:
        cmd = [
            "vercel", "blob", "put", tmp,
            "--pathname", pathname,
            "--force",
            "--rw-token", token,
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"vercel blob put failed: {e.output.strip()}") from e
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass

    store_id = _resolve_store_id()
    if store_id:
        return f"https://{store_id}.public.blob.vercel-storage.com/{pathname}"

    # Fallback: best-effort extract from CLI stdout
    for tok in (out or "").split():
        if ".public.blob.vercel-storage.com/" in tok:
            return tok.strip().strip('"').rstrip()
    return ""  # Unknown but upload succeeded

