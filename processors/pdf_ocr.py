"""
Real PDF OCR using pytesseract for scanned documents (lazy import).
"""
from __future__ import annotations

import io
import logging
import os

from schemas import DocumentResult

logger = logging.getLogger(__name__)


class OcrProcessor:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)

    async def ocr_pdf(
        self, filename: str, content: bytes, lang: str = "rus+eng"
    ) -> DocumentResult:
        import pypdfium2 as pdfium
        import pytesseract

        filepath = os.path.join(self.upload_dir, filename)
        with open(filepath, "wb") as f:
            f.write(content)

        pdf = pdfium.PdfDocument(filepath)
        page_count = len(pdf)
        texts = []

        for i in range(page_count):
            page = pdf[i]
            bitmap = page.render(scale=2.5)
            pil_image = bitmap.to_pil()
            text = pytesseract.image_to_string(pil_image, lang=lang)
            texts.append(text)

        full_text = "\n".join(texts)
        logger.info("ocr pdf: %s (%d pages)", filename, page_count)

        return DocumentResult(
            filename=filename,
            text=full_text,
            page_count=page_count,
        )

    async def ocr_image(
        self, filename: str, content: bytes, lang: str = "rus+eng"
    ) -> DocumentResult:
        import pytesseract
        from PIL import Image

        filepath = os.path.join(self.upload_dir, filename)
        with open(filepath, "wb") as f:
            f.write(content)

        image = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image, lang=lang)

        logger.info("ocr image: %s", filename)
        return DocumentResult(
            filename=filename,
            text=text,
            page_count=1,
        )
