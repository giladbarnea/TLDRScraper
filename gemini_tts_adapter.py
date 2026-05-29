"""Gemini TTS adapter for podcast_creator/Esperanto.

References:
- https://docs.cloud.google.com/text-to-speech/docs/gemini-tts
- https://ai.google.dev/gemini-api/docs/speech-generation
"""
import asyncio
import os
import re
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import types

from esperanto.common_types.model import Model
from esperanto.common_types.tts import AudioResponse, Voice
from esperanto.providers.tts.base import TextToSpeechModel

_PCM_MIME_PARAMETER_PATTERN = re.compile(r"(rate|channels)\s*=\s*(\d+)", re.IGNORECASE)


def _parse_pcm_mime_parameters(mime_type: str) -> tuple[int, int]:
    """Return sample rate and channel count from Gemini PCM mime type.

    >>> _parse_pcm_mime_parameters("audio/l16; rate=24000; channels=1")
    (24000, 1)
    """
    sample_rate_hertz = 24_000
    channel_count = 1
    for key, value in _PCM_MIME_PARAMETER_PATTERN.findall(mime_type):
        if key.lower() == "rate":
            sample_rate_hertz = int(value)
        if key.lower() == "channels":
            channel_count = int(value)
    return sample_rate_hertz, channel_count


@dataclass
class GeminiTextToSpeechModel(TextToSpeechModel):
    """Generate podcast-ready MP3 clips with Gemini TTS."""

    DEFAULT_MODEL = "gemini-3.1-flash-tts-preview"
    DEFAULT_VOICE = "Kore"
    PROVIDER = "google"

    def __post_init__(self):
        super().__post_init__()
        self._api_key = (
            self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        )
        if not self._api_key:
            raise ValueError(
                "Google API key not found. Please set GEMINI_API_KEY or GOOGLE_API_KEY."
            )
        self.model_name = self.model_name or self.DEFAULT_MODEL

    @property
    def provider(self) -> str:
        return self.PROVIDER

    @property
    def available_voices(self) -> dict[str, Voice]:
        return {
            "Kore": Voice(
                name="Kore",
                id="Kore",
                gender="FEMALE",
                language_code="en-US",
                description="Balanced American English voice",
            ),
            "Charon": Voice(
                name="Charon",
                id="Charon",
                gender="MALE",
                language_code="en-US",
                description="Measured American English voice",
            ),
            "Puck": Voice(
                name="Puck",
                id="Puck",
                gender="MALE",
                language_code="en-US",
                description="Brisk American English voice",
            ),
            "Aoede": Voice(
                name="Aoede",
                id="Aoede",
                gender="FEMALE",
                language_code="en-US",
                description="Warm American English voice",
            ),
            "Callirrhoe": Voice(
                name="Callirrhoe",
                id="Callirrhoe",
                gender="FEMALE",
                language_code="en-US",
                description="Expressive American English voice",
            ),
        }

    def _get_models(self) -> list[Model]:
        return [
            Model(
                id="gemini-2.5-flash-preview-tts",
                owned_by="Google",
                type="text_to_speech",
            ),
            Model(
                id="gemini-2.5-pro-preview-tts",
                owned_by="Google",
                type="text_to_speech",
            ),
            Model(
                id="gemini-3.1-flash-tts-preview",
                owned_by="Google",
                type="text_to_speech",
            ),
        ]

    def _transcode_pcm_to_mp3(
        self,
        pcm_audio_data: bytes,
        mime_type: str,
        output_file: str | Path | None,
    ) -> bytes:
        sample_rate_hertz, channel_count = _parse_pcm_mime_parameters(mime_type)
        ffmpeg_binary = self._config.get("ffmpeg_binary", "ffmpeg")

        with tempfile.TemporaryDirectory(prefix="gemini_tts_") as temporary_directory:
            temporary_directory_path = Path(temporary_directory)
            wav_path = temporary_directory_path / "clip.wav"
            temporary_mp3_path = temporary_directory_path / "clip.mp3"

            with wave.open(str(wav_path), "wb") as wav_file:
                wav_file.setnchannels(channel_count)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate_hertz)
                wav_file.writeframes(pcm_audio_data)

            subprocess.run(
                [
                    ffmpeg_binary,
                    "-y",
                    "-loglevel",
                    "error",
                    "-i",
                    str(wav_path),
                    str(temporary_mp3_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            mp3_audio_data = temporary_mp3_path.read_bytes()

        if output_file is not None:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(mp3_audio_data)

        return mp3_audio_data

    def generate_speech(
        self,
        text: str,
        voice: str,
        output_file: str | Path | None = None,
        **kwargs,
    ) -> AudioResponse:
        self.validate_parameters(text, voice, self.model_name)

        language_code = kwargs.pop("language_code", "en-US")
        temperature = kwargs.pop("temperature", 0)
        prompt = kwargs.pop("prompt", "")
        contents = text if not prompt else f"{prompt}\n\n{text}"

        client = genai.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                speech_config=types.SpeechConfig(
                    language_code=language_code,
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice,
                        )
                    ),
                ),
            ),
        )

        part = response.candidates[0].content.parts[0]
        if not getattr(part, "inline_data", None) or not part.inline_data.data:
            raise RuntimeError(f"No audio returned by Gemini TTS: {response}")

        mime_type = part.inline_data.mime_type or "audio/l16; rate=24000; channels=1"
        mp3_audio_data = self._transcode_pcm_to_mp3(
            pcm_audio_data=part.inline_data.data,
            mime_type=mime_type,
            output_file=output_file,
        )
        return AudioResponse(
            audio_data=mp3_audio_data,
            content_type="audio/mp3",
            model=self.model_name,
            voice=voice,
            provider=self.PROVIDER,
            metadata={
                "text": text,
                "source_mime_type": mime_type,
                "language_code": language_code,
            },
        )

    async def agenerate_speech(
        self,
        text: str,
        voice: str,
        output_file: str | Path | None = None,
        **kwargs,
    ) -> AudioResponse:
        return await asyncio.to_thread(
            self.generate_speech,
            text=text,
            voice=voice,
            output_file=output_file,
            **kwargs,
        )
