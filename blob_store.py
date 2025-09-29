import logging
import os
import re
import hashlib
import subprocess
import urllib.parse

import util


def normalize_url_to_pathname(url: str) -> str:
    """
    Deterministically convert a canonical URL into a Blob pathname:

    - lower-case
    - strip scheme and fragment
    - keep host + path
    - percent-decode path
    - replace any non-alphanumeric with a single '-'
    - collapse repeats; trim leading/trailing '-'
    - ensure '.md' suffix
    - truncate overly long names and add a short hash
    """
    u = urllib.parse.urlsplit(url)
    host = (u.netloc or "").lower()
    path = urllib.parse.unquote(u.path or "/").lower()

    # Preserve dots in host, hyphenate other non-alphanumerics
    host_clean = re.sub(r"[^a-z0-9]+", "-", host)
    # For path, replace any non-alphanumeric with '-'
    path_clean = re.sub(r"[^a-z0-9]+", "-", path)
    # Collapse repeated hyphens
    host_clean = re.sub(r"-{2,}", "-", host_clean).strip("-")
    path_clean = re.sub(r"-{2,}", "-", path_clean).strip("-")

    s = f"{host_clean}{('-' + path_clean) if path_clean else ''}"
    if not s:
        s = "root"

    # Length guard: keep pathnames sane; append a short hash if truncated
    MAX = 80
    if len(s) > MAX:
        h = hashlib.sha256(s.encode("utf-8")).hexdigest()[:10]
        s = f"{s[: MAX - 11]}-{h}"

    base = f"{s}.md"
    from string import punctuation

    if any(c in s for c in set(punctuation) - {"-"}):
        util.log(
            "[blob_store.normalize_url_to_pathname] result contains punctuation: %s",
            s,
            level=logging.ERROR,
        )
    return f"{base}"


def _resolve_rw_token() -> str:
    return util.resolve_env_var("BLOB_READ_WRITE_TOKEN", "")


def _resolve_store_base_url() -> str | None:
    return util.resolve_env_var("BLOB_STORE_BASE_URL", None)


def put_file(pathname: str, content: str) -> str:
    """
    Upload `content` to Vercel Blob at the exact `pathname`, overwriting if it exists.
    Returns the public URL from the SDK response.
    Raises RuntimeError on upload failure.
    """
    token = _resolve_rw_token()
    if not token:
        raise RuntimeError("BLOB_READ_WRITE_TOKEN not set")

    env = os.environ.copy()
    env["PATHNAME"] = pathname
    env["BLOB_READ_WRITE_TOKEN"] = token

    script_path = os.path.join(os.path.dirname(__file__), "scripts", "blob_put.mjs")

    try:
        util.log(
            "[blob_store.put_file] Uploading to %s via Node SDK...",
            pathname,
        )
        proc = subprocess.run(
            ["node", script_path],
            input=content.encode("utf-8"),
            capture_output=True,
            env=env,
            check=True,
        )
        import json
        out = proc.stdout.decode("utf-8")
        result = json.loads(out)
        url = result.get("url", "")
        util.log(
            "[blob_store.put_file] Success uploading to %s via Node SDK.",
            pathname,
        )
        return url
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8") if e.stderr else ""
        util.log(
            "[blob_store.put_file] Error uploading to %s: %s. Full error: %s",
            pathname,
            stderr,
            repr(e),
            level=logging.ERROR,
            exc_info=True,
        )
        raise RuntimeError(
            f"Node SDK blob upload failed: {stderr}. Full error: {repr(e)}"
        ) from e
    except json.JSONDecodeError as e:
        util.log(
            "[blob_store.put_file] Error parsing SDK response: %s",
            repr(e),
            level=logging.ERROR,
            exc_info=True,
        )
        raise RuntimeError(f"Failed to parse SDK response: {repr(e)}") from e
