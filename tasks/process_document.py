"""
Background job manager (in-process async queue).
"""
from __future__ import annotations

import logging

from schemas import JobStatus

logger = logging.getLogger(__name__)


class JobManager:
    """In-process job queue with status tracking.
    Can be replaced by Celery + Redis for production scaling.
    """

    def __init__(self):
        self._jobs: dict[str, JobStatus] = {}
        self._contents: dict[str, bytes] = {}
        self._processors: dict[str, dict] = {}

    def create_job(
        self,
        job_id: str,
        filename: str,
        content: bytes,
        process_type: str = "auto",
        use_ocr: bool = False,
    ):
        self._jobs[job_id] = JobStatus(
            job_id=job_id,
            status="pending",
            progress=0.0,
        )
        self._contents[job_id] = content
        self._processors[job_id] = {
            "filename": filename,
            "process_type": process_type,
            "use_ocr": use_ocr,
        }

    def update_status(
        self,
        job_id: str,
        status: str,
        progress: float | None = None,
        result_url: str | None = None,
        error: str | None = None,
    ):
        if job_id not in self._jobs:
            return
        job = self._jobs[job_id]
        job.status = status
        if progress is not None:
            job.progress = progress
        if result_url is not None:
            job.result_url = result_url
        if error is not None:
            job.error = error

    def get_status(self, job_id: str) -> JobStatus | None:
        return self._jobs.get(job_id)

    def get_content(self, job_id: str) -> bytes | None:
        return self._contents.get(job_id)

    def get_processors(self, job_id: str) -> dict | None:
        return self._processors.get(job_id)


job_manager = JobManager()
