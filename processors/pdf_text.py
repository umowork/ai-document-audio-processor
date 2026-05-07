"""
Real PDF text extraction using pypdfium2 (lazy import).
"""
from __future__ import annotations

import logging
import os

from schemas import DocumentResult

logger = logging.getLogger(__name__)


class PdfProcessor:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)

    async def extract_text(
        self, filename: str, content: bytes
    ) -> DocumentResult:
        import pypdfium2 as pdfium

        filepath = os.path.join(self.upload_dir, filename)
        with open(filepath, "wb") as f:
            f.write(content)

        pdf = pdfium.PdfDocument(filepath)
        page_count = len(pdf)
        texts = []

        for i in range(page_count):
            page = pdf[i]
            textpage = page.get_textpage()
            text = textpage.get_text_bounded()
            texts.append(text)

        full_text = "\n".join(texts)
        logger.info("pdf extracted: %s (%d pages)", filename, page_count)

        return DocumentResult(
            filename=filename,
            text=full_text,
            page_count=page_count,
        )
