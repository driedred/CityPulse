from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
SchemaModelT = TypeVar("SchemaModelT", bound=BaseModel)


class AIServiceError(RuntimeError):
    def __init__(self, message: str, *, raw_output: str | None = None) -> None:
        super().__init__(message)
        self.raw_output = raw_output


class OpenAIResponsesClient:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()

    async def generate_structured_output(
        self,
        *,
        schema_name: str,
        schema_model: type[SchemaModelT],
        system_prompt: str,
        user_prompt: str | None = None,
        user_content: list[dict[str, Any]] | None = None,
        max_output_tokens: int = 900,
    ) -> SchemaModelT:
        if not self.settings.openai_api_key:
            raise AIServiceError("OPENAI_API_KEY is not configured.")
        if (user_prompt is None) == (user_content is None):
            raise ValueError("Provide exactly one of user_prompt or user_content.")

        url = f"{self.settings.openai_api_base_url.rstrip('/')}/responses"
        payload = {
            "model": self.settings.openai_model,
            "store": False,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": user_content
                    or [{"type": "input_text", "text": user_prompt}],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema_model.model_json_schema(),
                }
            },
            "max_output_tokens": max_output_tokens,
        }

        last_error: Exception | None = None
        last_raw_output: str | None = None
        attempts = max(self.settings.openai_max_retries, 0) + 1
        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.settings.openai_timeout_seconds
                ) as client:
                    response = await client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {self.settings.openai_api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                response.raise_for_status()
                response_payload = response.json()
                last_raw_output = self._extract_json_text(response_payload)
                return schema_model.model_validate_json(last_raw_output)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                last_raw_output = self._truncate_raw_output(exc.response.text)
                logger.warning(
                    "OpenAI structured request failed on attempt %s/%s with status %s: %s",
                    attempt,
                    attempts,
                    exc.response.status_code if exc.response is not None else "unknown",
                    exc,
                )
                if attempt < attempts:
                    await asyncio.sleep(0.25 * attempt)
            except (httpx.HTTPError, ValidationError, json.JSONDecodeError, KeyError) as exc:
                last_error = exc
                logger.warning(
                    "OpenAI structured request failed on attempt %s/%s: %s",
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    await asyncio.sleep(0.25 * attempt)

        raise AIServiceError(
            "OpenAI structured request failed.",
            raw_output=last_raw_output,
        ) from last_error

    @staticmethod
    def _extract_json_text(payload: dict) -> str:
        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        for item in payload.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                for key in ("json", "parsed"):
                    value = content.get(key)
                    if isinstance(value, (dict, list)):
                        return json.dumps(value)
                text_value = content.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    return text_value

        raise KeyError("Structured OpenAI response did not contain parseable text output.")

    @staticmethod
    def _truncate_raw_output(value: str | None, *, limit: int = 4000) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized[:limit]
