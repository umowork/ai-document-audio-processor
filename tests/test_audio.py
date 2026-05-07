"""
Tests for audio transcription processor.
"""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from processors.audio_whisper import AudioProcessor


@pytest.mark.asyncio
async def test_audio_mock_mode():
    p = AudioProcessor(mock_mode=True)
    result = await p.transcribe("test.mp3", b"fake audio content")
    assert result.filename == "test.mp3"
    assert len(result.segments) > 0
    assert result.duration > 0


@pytest.mark.asyncio
async def test_audio_whisper_api_success():
    p = AudioProcessor(openai_api_key="sk-test")
    with respx.mock:
        route = respx.post("https://api.openai.com/v1/audio/transcriptions").mock(
            return_value=Response(
                200,
                json={
                    "text": "Привет мир",
                    "duration": 5.0,
                    "segments": [
                        {"start": 0.0, "end": 2.0, "text": "Привет"},
                        {"start": 2.0, "end": 5.0, "text": "мир"},
                    ],
                },
            )
        )
        result = await p.transcribe("test.mp3", b"audio data")
        assert route.called
        assert "Привет" in result.full_text
        assert len(result.segments) == 2


@pytest.mark.asyncio
async def test_audio_no_api_key():
    p = AudioProcessor(openai_api_key="", mock_mode=False)
    # Should fall back to mock
    result = await p.transcribe("test.mp3", b"data")
    assert result.filename == "test.mp3"
