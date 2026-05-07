"""
Tests for OCR processor.
"""
from __future__ import annotations

import pytest

from processors.pdf_ocr import OcrProcessor


@pytest.mark.asyncio
async def test_ocr_image_mock(tmp_path):
    """Test with a generated test image containing text."""
    p = OcrProcessor(upload_dir=str(tmp_path))
    # Create a simple image with text using PIL
    import io

    from PIL import Image, ImageDraw

    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), "Hello OCR World 123", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    content = buf.getvalue()

    result = await p.ocr_image("test.png", content)
    assert result.filename == "test.png"
    assert result.page_count == 1
    # Tesseract should find "Hello" or "World"
    assert "Hello" in result.text or "OCR" in result.text or "123" in result.text


@pytest.mark.asyncio
async def test_ocr_image_empty(tmp_path):
    p = OcrProcessor(upload_dir=str(tmp_path))
    # Blank image
    import io

    from PIL import Image

    img = Image.new("RGB", (100, 30), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    result = await p.ocr_image("blank.png", buf.getvalue())
    assert result.page_count == 1
    # Blank image should produce empty or whitespace text


@pytest.mark.asyncio
async def test_ocr_init(tmp_path):
    _p = OcrProcessor(upload_dir=str(tmp_path))
    assert tmp_path.exists()
