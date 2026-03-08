from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings

BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 3


class OpenAIClient:
    """Async client for OpenAI chat completions with structured output."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._api_key = api_key or settings.openai_api_key
        self._timeout = timeout
        self._max_retries = max_retries

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def chat_completion(
        self,
        *,
        system: str,
        user: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a chat completion request and return the response content."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = await self._post("/chat/completions", payload)
        return data

    async def structured_output(
        self,
        *,
        system: str,
        user: str,
        json_schema: dict[str, Any],
        model: str = DEFAULT_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Generate a chat completion with structured JSON output.

        Uses OpenAI's response_format with json_schema to guarantee
        the response conforms to the provided schema.
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": json_schema,
            },
        }
        data = await self._post("/chat/completions", payload)
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)

    async def _post(
        self, path: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{BASE_URL}{path}",
                        headers=self._headers(),
                        json=payload,
                    )
                    resp.raise_for_status()
                    return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (429, 500, 502, 503):
                    last_exc = exc
                    await _backoff(attempt)
                    continue
                raise
            except httpx.TransportError as exc:
                last_exc = exc
                await _backoff(attempt)
        raise RuntimeError(
            f"OpenAI request failed after {self._max_retries} retries"
        ) from last_exc


async def _backoff(attempt: int) -> None:
    import asyncio

    await asyncio.sleep(min(2**attempt, 30))
