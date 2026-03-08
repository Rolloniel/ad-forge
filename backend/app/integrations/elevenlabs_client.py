from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
OUTPUTS_DIR = Path("outputs")


class ElevenLabsClient:
    """Async client for ElevenLabs text-to-speech synthesis."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._api_key = api_key or settings.elevenlabs_api_key
        self._timeout = timeout
        self._max_retries = max_retries

    def _headers(self) -> dict[str, str]:
        return {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
        }

    async def list_voices(self) -> list[dict[str, Any]]:
        """List available ElevenLabs voices."""
        data = await self._get("/voices")
        return data.get("voices", [])

    async def text_to_speech(
        self,
        text: str,
        *,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
    ) -> bytes:
        """Synthesize speech from text and return raw audio bytes (MP3)."""
        payload: dict[str, Any] = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
            },
        }
        return await self._post_binary(
            f"/text-to-speech/{voice_id}", payload
        )

    async def download_audio(
        self,
        audio_bytes: bytes,
        filename: str,
    ) -> Path:
        """Write audio bytes to the outputs directory."""
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        dest = OUTPUTS_DIR / filename
        dest.write_bytes(audio_bytes)
        return dest

    async def _get(self, path: str) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.get(
                        f"{BASE_URL}{path}", headers=self._headers()
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
            f"ElevenLabs request failed after {self._max_retries} retries"
        ) from last_exc

    async def _post_binary(
        self, path: str, payload: dict[str, Any]
    ) -> bytes:
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
                    return resp.content
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
            f"ElevenLabs request failed after {self._max_retries} retries"
        ) from last_exc


async def _backoff(attempt: int) -> None:
    await asyncio.sleep(min(2**attempt, 30))
