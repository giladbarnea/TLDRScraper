import logging
import os
import re
import hashlib
import subprocess
import tempfile
import urllib.parse
import json

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


def put_markdown(pathname: str, markdown: str) -> str:
    """
    Upload `markdown` to Vercel Blob at the exact `pathname`, overwriting if it exists.
    Returns the public URL if it can be determined (using CLI output).
    Raises RuntimeError on upload failure.
    """
    token = _resolve_rw_token()
    if not token:
        raise RuntimeError("BLOB_READ_WRITE_TOKEN not set")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as f:
        f.write(markdown.encode("utf-8"))
        tmp = f.name
    # from IPython import embed

    # embed()
    try:
        cmd = [
            "vercel",
            "blob",
            "put",
            tmp,
            "--pathname",
            pathname,
            "--force",
            "--no-color",
            "--token",
            token,
        ]
        util.log(
            "[blob_store.put_markdown] Uploading to %s via Vercel CLI",
            pathname,
        )
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        util.log(
            "[blob_store.put_markdown] Error uploading to %s: %s via Vercel CLI",
            pathname,
            e.output.strip(),
            level=logging.ERROR,
            exc_info=True,
        )
        raise RuntimeError(f"vercel blob put failed: {e.output.strip()}") from e
    else:
        util.log(
            "[blob_store.put_markdown] Success uploading to %s via Vercel CLI",
            pathname,
        )
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass

    base_url = _resolve_store_base_url()
    if base_url:
        return f"{base_url}/{pathname}"

    # Fallback: best-effort extract from CLI stdout
    for tok in (out or "").split():
        if ".public.blob.vercel-storage.com/" in tok:
            return tok.strip().strip('"').rstrip()
    return ""  # Unknown but upload succeeded


def list_all_entries(limit: int | None = None) -> list[str]:
    """
    List blob pathnames using the Vercel CLI.

    Attempts JSON output first; falls back to line parsing. Returns a list of
    pathnames (strings). Best-effort: on any error, returns an empty list.
    """
    token = _resolve_rw_token()
    if not token:
        return []
    # Build base command
    base_cmd = ["vercel", "blob", "ls", "--token", token]
    try:
        # Prefer JSON when available
        cmd = base_cmd + ["--json"]
        util.log(
            "[blob_store.list_all_entries] Listing all entries via Vercel CLI with --json",
            level=logging.INFO,
        )
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        # Some versions print one JSON object per line; handle array or NDJSON
        pathnames: list[str] = []
        try:
            data = json.loads(out)
            if isinstance(data, list):
                for item in data:
                    # Accept common shapes: {pathname}, {key}, {url}
                    if isinstance(item, dict):
                        p = item.get("pathname") or item.get("key") or item.get("name")
                        if isinstance(p, str):
                            pathnames.append(p)
            elif isinstance(data, dict):
                # Some outputs may wrap under "blobs"
                items = data.get("blobs") or data.get("items") or []
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            p = (
                                item.get("pathname")
                                or item.get("key")
                                or item.get("name")
                            )
                            if isinstance(p, str):
                                pathnames.append(p)
        except Exception:
            # Try NDJSON lines
            for line in (out or "").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        p = item.get("pathname") or item.get("key") or item.get("name")
                        if isinstance(p, str):
                            pathnames.append(p)
                except Exception:
                    continue
        if limit is not None and isinstance(limit, int) and limit > 0:
            return pathnames[:limit]
        return pathnames
    except Exception as e:
        # Fallback: non-JSON output parsing
        formatted_error = getattr(e, "output", repr(e)).strip()
        util.log(
            "[blob_store.list_all_entries] Error listing all entries via Vercel CLI. Trying without --json. Error: %s",
            formatted_error,
            level=logging.ERROR,
            exc_info=True,
        )
        try:
            out = subprocess.check_output(base_cmd, stderr=subprocess.STDOUT, text=True)
            candidates: list[str] = []
            for line in (out or "").splitlines():
                line = line.strip()
                if not line:
                    continue
                # Heuristic: take tokens that look like pathnames (contain '/'
                # and end with common suffixes)
                for tok in line.split():
                    if "/" in tok and (
                        tok.endswith(".md") or ".vercel-storage.com/" in tok
                    ):
                        # If full URL, extract pathname part
                        idx = tok.find(".vercel-storage.com/")
                        if idx != -1:
                            p = tok[idx + len(".vercel-storage.com/") :]
                            candidates.append(p)
                        else:
                            candidates.append(tok)
            if limit is not None and isinstance(limit, int) and limit > 0:
                return candidates[:limit]
            return candidates
        except Exception as e:
            formatted_error = getattr(e, "output", repr(e)).strip()
            util.log(
                "[blob_store.list_all_entries] Error listing all entries via Vercel CLI even without --json. Error: %s",
                formatted_error,
                level=logging.ERROR,
                exc_info=True,
            )
            return []
