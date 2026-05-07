"""
Tests for structured extractor — including instructor integration.
"""
from __future__ import annotations

import json

import pytest
import respx
from httpx import Response

from processors.structured_extractor import (
    ExtractionSchema,
    StructuredExtractor,
    _create_instructor_client,
)

# ── Existing tests (mock mode, openai httpx fallback, no-key, doc_type) ──────


@pytest.mark.asyncio
async def test_extract_mock_mode():
    ext = StructuredExtractor(mock_mode=True)
    result = await ext.extract("Тестовый текст документа\nСтрока вторая")
    assert len(result.fields) > 0
    assert result.summary
    assert result.document_type


@pytest.mark.asyncio
async def test_extract_openai():
    ext = StructuredExtractor(openai_api_key="sk-test")
    with respx.mock:
        route = respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"fields": [{"name": "title", '
                                    '"value": "Test", "confidence": 0.95}], '
                                    '"summary": "Test doc", '
                                    '"document_type": "contract"}'
                                )
                            }
                        }
                    ]
                },
            )
        )
        result = await ext.extract("Some document text here")
        assert route.called
        assert len(result.fields) >= 1
        assert result.summary == "Test doc"
        assert result.document_type == "contract"


@pytest.mark.asyncio
async def test_extract_no_api_key():
    ext = StructuredExtractor(mock_mode=False)
    result = await ext.extract("No API key but should still work via mock")
    assert len(result.fields) >= 0


@pytest.mark.asyncio
async def test_extract_with_doc_type():
    ext = StructuredExtractor(mock_mode=True)
    result = await ext.extract("Invoice text", doc_type="счёт")
    assert result.document_type


# ── Instructor-specific tests ────────────────────────────────────────────────


def test_instructor_client_creation_no_key():
    """_create_instructor_client with empty key — AsyncOpenAI still creates a client
    (doesn't validate at init), so we verify the function returns a client + mode."""
    client, mode = _create_instructor_client("")
    # AsyncOpenAI doesn't validate keys at init; instructor wraps it regardless
    assert client is not None
    assert mode == "instructor"


def test_instructor_client_creation_with_key():
    """_create_instructor_client with a key should return a client and mode."""
    client, mode = _create_instructor_client("sk-test-key-12345")
    # Should succeed since instructor + openai are installed
    assert client is not None
    assert mode == "instructor"


def test_extraction_schema_is_pydantic_model():
    """ExtractionSchema should be a valid Pydantic BaseModel for instructor."""
    schema = ExtractionSchema(
        fields=[],
        summary="test summary",
        document_type="другое",
    )
    assert isinstance(schema, ExtractionSchema)
    assert schema.summary == "test summary"
    # Verify it can be serialized (instructor needs this)
    d = schema.model_dump()
    assert "fields" in d
    assert "summary" in d
    assert "document_type" in d


def test_extraction_schema_with_fields():
    """ExtractionSchema with ExtractedField objects."""
    from schemas import ExtractedField

    schema = ExtractionSchema(
        fields=[
            ExtractedField(name="title", value="Test", confidence=0.95),
            ExtractedField(name="date", value="2024-01-01", confidence=0.9),
        ],
        summary="A test document",
        document_type="contract",
    )
    assert len(schema.fields) == 2
    assert schema.fields[0].name == "title"
    assert schema.fields[1].confidence == 0.9
    # Round-trip via JSON (instructor sends/receives JSON)
    dumped = schema.model_dump_json()
    restored = ExtractionSchema.model_validate_json(dumped)
    assert restored.summary == schema.summary
    assert len(restored.fields) == len(schema.fields)


@pytest.mark.asyncio
async def test_extract_instructor_lazy_init():
    """Instructor client should be lazily initialized on first extract."""
    ext = StructuredExtractor(openai_api_key="sk-test", mock_mode=True)
    # mock_mode=True means instructor path is skipped, so client stays None
    result = await ext.extract("test text")
    assert ext._instructor_client is None  # not initialized in mock mode
    assert result.document_type  # fallback works


@pytest.mark.asyncio
async def test_extract_fallback_produces_valid_schema():
    """Fallback extraction should always produce a valid ExtractionSchema."""
    ext = StructuredExtractor(mock_mode=True)
    long_text = "\n".join(f"Line {i}: sample content" for i in range(20))
    result = await ext.extract(long_text)
    assert isinstance(result, ExtractionSchema)
    # Fallback returns max 5 fields
    assert len(result.fields) <= 5
    assert result.document_type == "другое"


@pytest.mark.asyncio
async def test_extract_openai_httpx_fallback_on_instructor_failure():
    """When instructor fails, should fall back to raw httpx OpenAI call."""
    ext = StructuredExtractor(openai_api_key="sk-test")

    # Mock the OpenAI HTTP endpoint for the fallback path
    with respx.mock:
        route = respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps({
                                    "fields": [{"name": "fallback",
                                                "value": "yes",
                                                "confidence": 0.8}],
                                    "summary": "Fallback extraction",
                                    "document_type": "other",
                                })
                            }
                        }
                    ]
                },
            )
        )
        # Force instructor path to fail by setting bad client
        ext._instructor_client = "bad_client"
        ext._instructor_mode = "instructor"

        result = await ext.extract("Some text")
        # Should have fallen back to httpx
        assert route.called
        assert result.summary == "Fallback extraction"
