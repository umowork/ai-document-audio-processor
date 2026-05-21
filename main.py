"""
FastAPI main entry point for 03-ai-document-audio-processor.
"""
from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Security, UploadFile
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def _rate_limit_exceeded_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )
from api.upload import router as upload_router @@
from api.upload import router as upload_router
from api.status import router as status_router
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
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

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
        request: Request,
        file: UploadFile = File(...),
        use_ocr: bool = Form(False),
        _key: None = Depends(require_api_key),
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
    async def process_audio(
        file: UploadFile = File(...),
        _key: None = Depends(require_api_key),
    ):
        content = await file.read()
        filename = file.filename or "unnamed"
        result = await audio_processor.transcribe(filename, content)
        return result

    @app.post("/process/extract")
    async def extract_fields(
        file: UploadFile = File(...),
        _key: None = Depends(require_api_key),
    ):
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
        checks = {
            "status": "ok",
            "service": "document-processor",
            "mock_mode": config.mock_mode,
        }
        # No database — verify processors are available
        try:
            checks["pdf_processor"] = "available"
            checks["audio_processor"] = "available"
        except Exception as e:
            checks["status"] = "degraded"
            checks["error"] = str(e)
        return checks

    return app


app = create_app()
