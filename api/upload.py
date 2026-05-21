"""
FastAPI upload endpoint.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from api.auth import require_api_key
from schemas import JobStatus
from tasks.process_document import job_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=JobStatus)
async def upload_file(
    file: UploadFile = File(...),
    process_type: str = Form("auto"),
    use_ocr: bool = Form(False),
    _key: None = Depends(require_api_key),
):
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    job_id = str(uuid.uuid4())
    filename = file.filename or "unnamed"

    job_manager.create_job(
        job_id=job_id,
        filename=filename,
        content=content,
        process_type=process_type,
        use_ocr=use_ocr,
    )

    logger.info(
        "upload: %s (%d bytes, type=%s)",
        filename, len(content), process_type,
    )

    return JobStatus(
        job_id=job_id,
        status="pending",
        progress=0.0,
    )
