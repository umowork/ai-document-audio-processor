"""
FastAPI main entry point for 03-ai-document-audio-processor.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, File, Form, UploadFile

from api.status import router as status_router
from api.upload import router as upload_router
from config import Config
from exporters.excel import ExcelExporter
from processors.audio_whisper import AudioProcessor
from processors.docx_processor import DocxProcessor
from processors.pdf_ocr import OcrProcessor
from processors.pdf_text import PdfProcessor
from processors.structured_extractor import StructuredExtractor
from schemas import AudioResult, DocumentResult

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    config = Config.from_env()

    app = FastAPI(title="AI Document & Audio Processor", version="1.0.0")

    pdf_processor = PdfProcessor(upload_dir=config.upload_dir)
    ocr_processor = OcrProcessor(upload_dir=config.upload_dir)
    docx_processor = DocxProcessor(upload_dir=config.upload_dir)
    audio_processor = AudioProcessor(
        openai_api_key=config.openai_api_key,
        upload_dir=config.upload_dir,
        mock_mode=config.mock_mode,
    )
    extractor = StructuredExtractor(
        openai_api_key=config.openai_api_key,
        gigachat_api_key=config.gigachat_api_key,
        mock_mode=config.mock_mode,
    )
    exporter = ExcelExporter(output_dir=config.results_dir)

    # Store in app.state for access in routes
    app.state.pdf_processor = pdf_processor
    app.state.ocr_processor = ocr_processor
    app.state.docx_processor = docx_processor
    app.state.audio_processor = audio_processor
    app.state.extractor = extractor
    app.state.exporter = exporter

    # Register routers
    app.include_router(upload_router)
    app.include_router(status_router)

    @app.post("/process/document", response_model=DocumentResult)
    async def process_document(
        file: UploadFile = File(...),
        use_ocr: bool = Form(False),
    ):
        content = await file.read()
        filename = file.filename or "unnamed"
        suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if suffix == "docx":
            result = await docx_processor.extract_text(filename, content)
        elif file.content_type and file.content_type.startswith("image/"):
            result = await ocr_processor.ocr_image(filename, content)
        elif use_ocr:
            result = await ocr_processor.ocr_pdf(filename, content)
        else:
            result = await pdf_processor.extract_text(filename, content)

        # Run structured extraction
        schema = await extractor.extract(result.text)
        result.fields = schema.fields

        return result

    @app.post("/process/audio", response_model=AudioResult)
    async def process_audio(file: UploadFile = File(...)):
        content = await file.read()
        filename = file.filename or "unnamed"
        result = await audio_processor.transcribe(filename, content)
        return result

    @app.post("/process/extract")
    async def extract_fields(file: UploadFile = File(...)):
        content = await file.read()
        filename = file.filename or "unnamed"
        text = content.decode("utf-8", errors="replace")

        result = await extractor.extract(text)

        # Export to Excel
        doc_result = DocumentResult(
            filename=filename,
            text=text,
            fields=result.fields,
            page_count=1,
        )
        filepath = exporter.export_document(doc_result)

        return {
            "status": "done",
            "fields": [f.dict() for f in result.fields],
            "summary": result.summary,
            "document_type": result.document_type,
            "excel_url": filepath,
        }

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "document-processor"}

    return app


app = create_app()
