"""
Structured extraction from text using instructor + LLM gateway.
Falls back to raw httpx JSON calls when instructor is unavailable.
"""
from __future__ import annotations

import json
import logging

import httpx
from pydantic import BaseModel, Field

from schemas import ExtractedField

logger = logging.getLogger(__name__)


class ExtractionSchema(BaseModel):
    """Схема для извлечения структурированных данных из текста."""
    fields: list[ExtractedField] = Field(
        description="Извлечённые поля из документа"
    )
    summary: str = Field(
        description="Краткое содержание документа (1-3 предложения)"
    )
    document_type: str = Field(
        description="Тип документа: договор, счёт, накладная, акт, другое"
    )


def _create_instructor_client(api_key: str):
    """Create an instructor-patched OpenAI client if instructor is available.

    Returns (client, mode) where mode is 'instructor' or None.
    """
    try:
        import instructor
        from openai import AsyncOpenAI

        client = instructor.from_openai(AsyncOpenAI(api_key=api_key))
        logger.debug("instructor client created successfully")
        return client, "instructor"
    except ImportError:
        logger.debug("instructor not installed, falling back to raw httpx")
        return None, None
    except Exception as e:
        logger.debug("instructor init failed: %s, falling back to raw httpx", e)
        return None, None


class StructuredExtractor:
    def __init__(
        self,
        openai_api_key: str = "",
        gigachat_api_key: str = "",
        mock_mode: bool = False,
    ):
        self.openai_api_key = openai_api_key
        self.gigachat_api_key = gigachat_api_key
        self.mock_mode = mock_mode
        self._instructor_client = None
        self._instructor_mode: str | None = None

    def _get_instructor_client(self):
        """Lazy-init the instructor client."""
        if self._instructor_client is None and self.openai_api_key:
            client, mode = _create_instructor_client(self.openai_api_key)
            self._instructor_client = client
            self._instructor_mode = mode
        return self._instructor_client

    async def extract(
        self, text: str, doc_type: str | None = None
    ) -> ExtractionSchema:
        if self.mock_mode:
            return self._fallback_extract(text)

        prompt = self._build_prompt(text, doc_type)

        # Try instructor first for structured output
        if self.openai_api_key:
            client = self._get_instructor_client()
            if client is not None:
                try:
                    return await self._extract_instructor(client, prompt)
                except Exception as e:
                    logger.warning("instructor extraction failed: %s, falling back", e)
            # Fallback to raw httpx
            return await self._extract_openai(prompt)

        if self.gigachat_api_key:
            return await self._extract_gigachat(prompt)

        return self._fallback_extract(text)

    def _build_prompt(
        self, text: str, doc_type: str | None = None
    ) -> str:
        type_hint = f"Это {doc_type}. " if doc_type else ""
        return (
            f"{type_hint}Извлеки структурированные данные из следующего текста.\n\n"
            f"Текст документа:\n{text[:8000]}\n\n"
            f"Верни JSON с полями: fields (массив объектов с name, value, confidence), "
            f"summary (краткое содержание), document_type (тип документа)."
        )

    async def _extract_instructor(
        self, client, prompt: str
    ) -> ExtractionSchema:
        """Extract using instructor with structured output (Pydantic model).

        Instructor handles JSON schema enforcement and retries automatically.
        """
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=ExtractionSchema,
            max_retries=2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты — ассистент по извлечению данных из документов. "
                        "Извлеки структурированные поля из текста."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        logger.info("instructor extraction succeeded")
        return response

    async def _extract_openai(self, prompt: str) -> ExtractionSchema:
        """Fallback: raw httpx call to OpenAI with JSON mode."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Ты — ассистент по извлечению данных из документов. "
                                "Отвечай строго в JSON формате."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return ExtractionSchema(**parsed)

    async def _extract_gigachat(self, prompt: str) -> ExtractionSchema:
        # GigaChat: token first
        async with httpx.AsyncClient(timeout=30.0) as client:
            auth_resp = await client.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Authorization": f"Basic {self.gigachat_api_key}",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "RqUID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                },
                data={"scope": "GIGACHAT_API_PERS"},
            )
            auth_resp.raise_for_status()
            token = auth_resp.json().get("access_token")

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "GigaChat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ты — ассистент по извлечению данных. Отвечай JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return ExtractionSchema(**parsed)

    def _fallback_extract(self, text: str) -> ExtractionSchema:
        lines = [line for line in text.strip().split("\n") if line.strip()]
        fields = [
            ExtractedField(
                name=f"line_{i}",
                value=line[:100],
                confidence=0.85,
            )
            for i, line in enumerate(lines[:5])
        ]
        return ExtractionSchema(
            fields=fields,
            summary=text[:150] + ("..." if len(text) > 150 else ""),
            document_type="другое",
        )
