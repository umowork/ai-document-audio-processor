"""
Config for 03-ai-document-audio-processor.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    openai_api_key: str
    gigachat_api_key: str
    gigachat_credentials: str
    llm_provider: str
    upload_dir: str
    results_dir: str
    host: str
    port: int
    mock_mode: bool

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            gigachat_api_key=os.getenv("GIGACHAT_API_KEY", ""),
            gigachat_credentials=os.getenv("GIGACHAT_CREDENTIALS", ""),
            llm_provider=os.getenv("LLM_PROVIDER", "gigachat"),
            upload_dir=os.getenv("UPLOAD_DIR", "uploads"),
            results_dir=os.getenv("RESULTS_DIR", "results"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            mock_mode=os.getenv("MOCK_MODE", "0").lower() in ("1", "true", "yes"),
        )
