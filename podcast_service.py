"""Podcast episode generation: scrape URLs, generate audio via podcast-creator, persist to Supabase.

MVP scope: single-speaker (`solo_expert` profile) with OpenAI TTS, openai-gpt-4o-mini for
outline+transcript (avoids needing ANTHROPIC_API_KEY).
"""
import asyncio
import base64
import hashlib
import logging
import shutil
import tempfile
from pathlib import Path

import storage_service
import tldr_service
import util

logger = logging.getLogger("podcast_service")


async def _generate_audio_bytes(content_markdown: str, episode_name: str) -> bytes:
    from podcast_creator import create_podcast

    work_dir = Path(tempfile.mkdtemp(prefix="podcast_"))
    try:
        result = await create_podcast(
            content=content_markdown,
            episode_profile="solo_expert",
            outline_provider="openai",
            outline_model="gpt-4o-mini",
            transcript_provider="openai",
            transcript_model="gpt-4o-mini",
            episode_name=episode_name,
            output_dir=str(work_dir),
        )
        return Path(result["final_output_file_path"]).read_bytes()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _generate_podcast_cache_key(canonical_urls: list[str]) -> str:
    """Generate a stable cache key from canonical source URLs.

    >>> _generate_podcast_cache_key(["https://b.com", "https://a.com"]) == _generate_podcast_cache_key(["https://a.com", "https://b.com"])
    True
    """
    payload = "|".join(sorted(canonical_urls))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _format_podcast_source_markdown(
    canonical_urls: list[str],
    markdown_by_url: dict[str, str],
) -> str:
    """Join scraped article markdown into one XML-like source document.

    >>> formatted = _format_podcast_source_markdown(["https://example.com/a"], {"https://example.com/a": "Body"})
    >>> '<sources>' in formatted and '<source index="1" url="https://example.com/a">' in formatted
    True
    >>> '</source>' in formatted and '</sources>' in formatted
    True
    """
    source_blocks = [
        f'<source index="{index}" url="{url}">\n{markdown_by_url[url]}\n</source>'
        for index, url in enumerate(canonical_urls, start=1)
    ]
    return "<sources>\n" + "\n\n".join(source_blocks) + "\n</sources>"


def get_or_create_podcast_episode(urls: list[str]) -> dict:
    """Return mp3 bytes for the podcast version of a URL list, cache-first.

    Returns dict with: canonical_urls, audio_bytes, cached (bool).
    """
    if not isinstance(urls, list) or not urls:
        raise ValueError("urls must be a non-empty list")

    cleaned_urls: list[str] = []
    for raw_url in urls:
        if not isinstance(raw_url, str) or not raw_url.strip():
            raise ValueError("urls must contain non-empty strings")
        cleaned_urls.append(raw_url.strip())

    canonical_urls = sorted(util.canonicalize_url(url) for url in cleaned_urls)
    cache_key = _generate_podcast_cache_key(canonical_urls)
    logger.info("podcast lookup cache_key=%s url_count=%d", cache_key[:8], len(canonical_urls))

    cached_b64 = storage_service.get_podcast_episode(cache_key)
    if cached_b64:
        logger.info("podcast cache hit cache_key=%s", cache_key[:8])
        return {
            "canonical_urls": canonical_urls,
            "audio_bytes": base64.b64decode(cached_b64),
            "cached": True,
        }

    logger.info("podcast cache miss; scraping cache_key=%s", cache_key[:8])
    markdown_by_url = tldr_service._fetch_article_markdowns_parallel(canonical_urls)
    content_markdown = _format_podcast_source_markdown(canonical_urls, markdown_by_url)

    logger.info(
        "generating podcast cache_key=%s url_count=%d markdown_chars=%d",
        cache_key[:8],
        len(canonical_urls),
        len(content_markdown),
    )
    audio_bytes = asyncio.run(
        _generate_audio_bytes(content_markdown, f"podcast_{cache_key[:12]}")
    )

    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    storage_service.set_podcast_episode(cache_key, audio_b64)
    logger.info("podcast persisted cache_key=%s audio_bytes=%d", cache_key[:8], len(audio_bytes))

    return {
        "canonical_urls": canonical_urls,
        "audio_bytes": audio_bytes,
        "cached": False,
    }
