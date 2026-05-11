"""Podcast episode generation: scrape URL, generate audio via podcast-creator, persist to Supabase.

POC/MVP scope: single-speaker (`solo_expert` profile) with OpenAI TTS, openai-gpt-4o-mini for
outline+transcript (avoids needing ANTHROPIC_API_KEY).
"""
import asyncio
import base64
import logging
import shutil
import tempfile
from pathlib import Path

import storage_service
import summarizer
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


def get_or_create_podcast_episode(url: str) -> dict:
    """Return mp3 bytes for the podcast version of `url`, cache-first.

    Returns dict with: canonical_url, audio_bytes, cached (bool).
    """
    canonical_url = util.canonicalize_url(url)
    logger.info("podcast lookup canonical_url=%s", canonical_url)

    cached_b64 = storage_service.get_podcast_episode(canonical_url)
    if cached_b64:
        logger.info("podcast cache hit canonical_url=%s", canonical_url)
        return {
            "canonical_url": canonical_url,
            "audio_bytes": base64.b64decode(cached_b64),
            "cached": True,
        }

    logger.info("podcast cache miss; scraping canonical_url=%s", canonical_url)
    markdown = summarizer.url_to_markdown(canonical_url)

    logger.info("generating podcast canonical_url=%s markdown_chars=%d", canonical_url, len(markdown))
    episode_name = canonical_url.replace("/", "_").replace(".", "_")[:60]
    audio_bytes = asyncio.run(_generate_audio_bytes(markdown, episode_name))

    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    storage_service.set_podcast_episode(canonical_url, audio_b64)
    logger.info("podcast persisted canonical_url=%s audio_bytes=%d", canonical_url, len(audio_bytes))

    return {
        "canonical_url": canonical_url,
        "audio_bytes": audio_bytes,
        "cached": False,
    }
