"""
Pydantic schemas for document and audio processing.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedField(BaseModel):
    name: str = Field(description="Field name")
    value: str = Field(description="Extracted value")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class DocumentResult(BaseModel):
    filename: str
    text: str
    fields: list[ExtractedField] = []
    page_count: int = 0


class AudioSegment(BaseModel):
    start: float = Field(description="Start time (s)")
    end: float = Field(description="End time (s)")
    text: str = Field(description="Transcribed text")


class AudioResult(BaseModel):
    filename: str
    duration: float = 0.0
    segments: list[AudioSegment] = []
    full_text: str = ""
    summary: str | None = None


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending | processing | done | failed
    progress: float = 0.0
    result_url: str | None = None
    error: str | None = None


class JobCreate(BaseModel):
    filename: str
    file_size: int
    process_type: str = "auto"  # auto | document | audio
