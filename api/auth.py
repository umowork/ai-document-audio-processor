"""
Optional API key authentication dependency.

Set the API_KEY environment variable to enable authentication.
When API_KEY is not set, all requests are allowed through.
"""
from __future__ import annotations

import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)):
    """Optional API key auth. Set API_KEY env var to enable."""
    expected = os.getenv("API_KEY")
    if expected and api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
