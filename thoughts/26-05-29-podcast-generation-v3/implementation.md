---
last_updated: 2026-05-29 10:38, d512f28
---

# Podcast Generation v3 — Gemini TTS adapter cleanup

Simplified `gemini_tts_adapter.py` (behavior preserved, verified via doctests + transcode round-trip):

1. `_transcode_pcm_to_mp3` is now pure `bytes → bytes`; saving moved to `generate_speech` via the base class's `save_audio()`, dropping a hand-rolled `mkdir`/`write_bytes`.
2. Collapsed the duplicated 24kHz-mono PCM default — `_parse_pcm_mime_parameters` now owns it and accepts `None`; removed the fallback magic string at the call site.
3. Trimmed `available_voices`/`_get_models` to the single voice/model actually used (`Kore` / `gemini-3.1-flash-tts-preview`); these are never consulted by `podcast_creator`, only satisfy the ABC.
