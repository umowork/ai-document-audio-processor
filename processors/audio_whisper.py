"""
Real audio transcription via OpenAI Whisper API.
"""
from __future__ import annotations

import asyncio
import logging
import os

import httpx

from schemas import AudioResult, AudioSegment

logger = logging.getLogger(__name__)


class AudioProcessor:
    def __init__(
        self,
        openai_api_key: str = "",
        upload_dir: str = "uploads",
        mock_mode: bool = False,
    ):
        self.openai_api_key = openai_api_key
        self.upload_dir = upload_dir
        self.mock_mode = mock_mode
        os.makedirs(upload_dir, exist_ok=True)

    async def transcribe(
        self, filename: str, content: bytes
    ) -> AudioResult:
        safe_name = os.path.basename(filename)
        filepath = os.path.join(self.upload_dir, safe_name)
        real_upload = os.path.realpath(self.upload_dir)
        real_file = os.path.realpath(filepath)
        if not real_file.startswith(real_upload + os.sep) and real_file != real_upload:
            raise ValueError("Path traversal detected")
        with open(filepath, "wb") as f:
            f.write(content)

        if self.mock_mode:
            return await self._fallback_transcribe(filename)

        if self.openai_api_key:
            return await self._whisper_api(filename, content)

        return await self._fallback_transcribe(filename)

    async def _fallback_transcribe(
        self, filename: str
    ) -> AudioResult:
        await asyncio.sleep(0.5)
        segments = [
            AudioSegment(start=0.0, end=3.0, text="Это тестовая транскрипция."),
            AudioSegment(
                start=3.0, end=6.0,
                text="Реальный Whisper API будет использоваться при наличии ключа."
            ),
        ]
        return AudioResult(
            filename=filename,
            duration=6.0,
            segments=segments,
            full_text=" ".join(s.text for s in segments),
            summary="Тестовая запись.",
        )

    async def _whisper_api(
        self, filename: str, content: bytes
    ) -> AudioResult:
        """Transcribe via OpenAI Whisper API."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {
                "file": (filename, content, "audio/mpeg"),
                "model": (None, "whisper-1"),
                "response_format": (None, "verbose_json"),
                "language": (None, "ru"),
            }
            resp = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.openai_api_key}"},
                files=files,
            )
            resp.raise_for_status()
            data = resp.json()

        segments = []
        for seg in data.get("segments", []):
            segments.append(
                AudioSegment(
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"].strip(),
                )
            )
        full_text = data.get("text", "").strip()
        duration = data.get("duration", 0.0)

        logger.info(
            "whisper transcribed: %s (%.1fs, %d segments)",
            filename, duration, len(segments),
        )

        return AudioResult(
            filename=filename,
            duration=duration,
            segments=segments,
            full_text=full_text,
            summary=full_text[:200] + ("..." if len(full_text) > 200 else ""),
        )
