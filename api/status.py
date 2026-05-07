"""
FastAPI status and download endpoints.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from schemas import JobStatus
from tasks.process_document import job_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    status = job_manager.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@router.get("/download/{job_id}")
async def download_result(job_id: str):
    status = job_manager.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if status.status != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Job not ready (status: {status.status})",
        )
    if not status.result_url:
        raise HTTPException(status_code=400, detail="No result file")

    return FileResponse(
        status.result_url,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"result_{job_id}.xlsx",
    )
