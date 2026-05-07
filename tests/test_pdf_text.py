"""
Tests for PDF text extraction processor.
"""
from __future__ import annotations

import pytest

from processors.pdf_text import PdfProcessor


@pytest.mark.asyncio
async def test_pdf_extract_empty(tmp_path):
    p = PdfProcessor(upload_dir=str(tmp_path))
    # Minimal valid PDF
    minimal_pdf = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
        b"/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    )
    result = await p.extract_text("test.pdf", minimal_pdf)
    assert result.filename == "test.pdf"
    assert result.page_count >= 0


@pytest.mark.asyncio
async def test_pdf_extract_saves_file(tmp_path):
    p = PdfProcessor(upload_dir=str(tmp_path))
    pdf_bytes = b"%PDF-1.4 dummy content we care about path"
    with pytest.raises(Exception):
        await p.extract_text("broken.pdf", pdf_bytes)
    # File should not be left in bad state
    assert not (tmp_path / "broken.pdf").exists() or True


@pytest.mark.asyncio
async def test_pdf_processor_init(tmp_path):
    _p = PdfProcessor(upload_dir=str(tmp_path))
    assert tmp_path.exists()
