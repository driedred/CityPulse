from __future__ import annotations

import asyncio
import json
import logging
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
SchemaModelT = TypeVar("SchemaModelT", bound=BaseModel)


class AIServiceError(RuntimeError):
    pass


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
        user_prompt: str,
        max_output_tokens: int = 900,
    ) -> SchemaModelT:
        if not self.settings.openai_api_key:
            raise AIServiceError("OPENAI_API_KEY is not configured.")

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
                    "content": [{"type": "input_text", "text": user_prompt}],
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
                return schema_model.model_validate_json(
                    self._extract_json_text(response_payload)
                )
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

        raise AIServiceError("OpenAI structured request failed.") from last_error

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
